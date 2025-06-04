import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import json
import os
import time
import random
from bs4 import BeautifulSoup
from config import (REJECTED_REPOS_FILE, SWE_BENCH_BASE_URL, SWE_BENCH_FILTER_PARAMS,
                    SWE_BENCH_GREEN_LIST_FILE, SWE_BENCH_BLACKLIST_FILE,
                    SWE_BENCH_MAX_RETRIES, SWE_BENCH_BACKOFF_FACTOR,
                    SWE_BENCH_MIN_DELAY, SWE_BENCH_MAX_DELAY,
                    SWE_BENCH_MAX_CONSECUTIVE_REQUESTS, SWE_BENCH_LONG_PAUSE_DURATION,
                    get_swe_bench_header, get_random_user_agent)

# Filter by Python language percentage
def Filterby_Python_percentage(cleaned_filtered_repos, headers):
    filtered_by_python = []
    rejected_by_python = []
    for repo in cleaned_filtered_repos:
        owner, repo_name = repo["full_name"].split("/", 1)
        lang_url = f"https://api.github.com/repos/{owner}/{repo_name}/languages"
        try:
            lang_resp = requests.get(lang_url, headers=headers)
            lang_resp.raise_for_status()
            lang_data = lang_resp.json()
            total_bytes = sum(lang_data.values())
            python_bytes = lang_data.get("Python", 0)
            python_percent = (python_bytes / total_bytes) * 100 if total_bytes > 0 else 0
            if python_percent >= 75:
                repo["python_percent"] = round(python_percent, 2)
                filtered_by_python.append(repo)
            else:
                rejected_by_python.append(repo["html_url"])
        except Exception as e:
            print(f"Error fetching languages for {repo['full_name']}: {e}")
    if rejected_by_python:
        try:
            # Load existing rejected repos if file exists
            try:
                with open(REJECTED_REPOS_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = []
            except (FileNotFoundError, json.JSONDecodeError):
                existing = []
            # Append new rejected repos
            existing.extend(rejected_by_python)
            with open(REJECTED_REPOS_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing to {REJECTED_REPOS_FILE}: {e}")
    return filtered_by_python


def Load_repos(file_path):
    # Load the existed repos
    owned_repos = set()
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    loaded_data = json.loads(content)
                    if isinstance(loaded_data, list):
                        owned_repos = set(loaded_data)
                    else:
                        print(f"Warning: '{file_path}' does not contain a JSON list. Starting with an empty set.")
                else:
                    print(f"Warning: '{file_path}' is empty. Starting with an empty set of owned repos.")
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from '{file_path}'. Starting with an empty set of owned repos.")
        except Exception as e:
            print(f"Error loading '{file_path}': {e}. Starting with an empty set of owned repos.")
    else:
        print(f"Info: '{file_path}' not found. Starting with an empty set of owned repos.")
    return owned_repos


def cleaned_repos(merged_repos, results):
    cleaned_filtered_repos = []
    for repo_data in results.get('items', []):
        if repo_data.get('html_url') not in merged_repos:
            cleaned_repo_info = {
                "full_name": repo_data.get('full_name'),
                "html_url": repo_data.get('html_url'),
                "stars": repo_data.get('stargazers_count'),
                "forks": repo_data.get('forks_count'),
                "watchers": repo_data.get('watchers_count'),
                "open_issues": repo_data.get('open_issues_count'),
                "language": repo_data.get('language'),
                "description": repo_data.get('description', ''),
                "created_at": repo_data.get('created_at'),
                "updated_at": repo_data.get('updated_at'),
                "pushed_at": repo_data.get('pushed_at'),
                "license": repo_data.get('license', {}).get('name') if repo_data.get('license') else None,
            }
            cleaned_filtered_repos.append(cleaned_repo_info)
    return cleaned_filtered_repos

def create_session_with_retries():
    session = requests.Session()
    retry_strategy = Retry(
        total=SWE_BENCH_MAX_RETRIES,
        status_forcelist=[429, 500, 502, 503, 504], # Retry on these status codes
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=SWE_BENCH_BACKOFF_FACTOR
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def filter_by_swe_bench_batches(repos_to_check, initial_swe_bench_headers):
    """
    Checks repositories for batch validity.

    Args:
        repos_to_check (list): List of repository dictionaries.
        swe_bench_auth_headers (dict): Authentication headers.

    Returns:
        list: Repositories that passed the SWE-Bench check.
    """
    passed_repos = []
    failed_or_problematic_repo_urls = []

    if not repos_to_check:
        return []

    print(f"\nChecking {len(repos_to_check)} repos against SWE-Bench Plus for batch validity...")

    session = create_session_with_retries()
    consecutive_requests_count = 0

    for i, repo_info in enumerate(repos_to_check):
        full_name = repo_info.get("full_name")
        html_url = repo_info.get("html_url")

        if not full_name or not html_url:
            print(f"  Skipping repo due to missing full_name or html_url: {repo_info}")
            if html_url:
                failed_or_problematic_repo_urls.append(html_url)
            continue

        # Rotate User-Agent for each request if desired, or set once per session
        # The session itself doesn't rotate User-Agent per request automatically.
        # So, we update the headers for each request if we want dynamic User-Agents.
        current_headers = initial_swe_bench_headers.copy() # Start with base auth headers
        current_headers.update({"User-Agent": get_random_user_agent()}) # Update/add random User-Agent

        swe_bench_repo_name = full_name.replace("/", "__")
        target_url = f"{SWE_BENCH_BASE_URL}{swe_bench_repo_name}{SWE_BENCH_FILTER_PARAMS}"

        print(f"({i+1}/{len(repos_to_check)}) Checking SWE-Bench for: {full_name} (Attempting...)")
        print(f"  URL: {target_url}")

        try:
            response = session.get(target_url, headers=current_headers, timeout=30) # Use session object
            response.raise_for_status() # Will trigger retries for status_forcelist before raising here

            # If we reach here, the request was successful
            soup = BeautifulSoup(response.content, 'lxml')
            tbody_tag = soup.find("tbody", class_="bg-white divide-y divide-gray-200")

            if tbody_tag:
                tr_tags = tbody_tag.find_all("tr", class_="hover:bg-gray-50 cursor-pointer")
                if tr_tags:
                    print(f"  [SWE-BENCH PASSED] Found {len(tr_tags)} valid batch(es) for {full_name}.")
                    repo_info["swe_bench_batch_count"] = len(tr_tags)
                    passed_repos.append(repo_info)
                else:
                    print(f"  [SWE-BENCH FAILED] Found <tbody> but no valid <tr> for {full_name}.")
                    failed_or_problematic_repo_urls.append(html_url)
            else:
                print(f"  [SWE-BENCH FAILED] No <tbody> structure for {full_name}.")
                failed_or_problematic_repo_urls.append(html_url)

            consecutive_requests_count += 1

        except requests.exceptions.HTTPError as http_err:
            print(f"  [HTTP ERROR] (final attempt) for {full_name}: {http_err}")
            failed_or_problematic_repo_urls.append(html_url)
            consecutive_requests_count = 0 # Reset on error
        except requests.exceptions.RequestException as req_err: # Catches other errors like ConnectionError
            print(f"  [REQUEST ERROR] (final attempt) for {full_name}: {req_err}")
            failed_or_problematic_repo_urls.append(html_url)
            consecutive_requests_count = 0 # Reset on error
        except Exception as e:
            print(f"  [UNEXPECTED ERROR] processing {full_name}: {e}")
            failed_or_problematic_repo_urls.append(html_url)
            consecutive_requests_count = 0 # Reset on error

        # Delays and long pause
        if consecutive_requests_count >= SWE_BENCH_MAX_CONSECUTIVE_REQUESTS:
            print(f"Reached {SWE_BENCH_MAX_CONSECUTIVE_REQUESTS} consecutive successful requests. Pausing for {SWE_BENCH_LONG_PAUSE_DURATION}s...")
            time.sleep(SWE_BENCH_LONG_PAUSE_DURATION)
            consecutive_requests_count = 0 # Reset counter
        else:
            # Apply random delay between requests
            sleep_duration = random.uniform(SWE_BENCH_MIN_DELAY, SWE_BENCH_MAX_DELAY)
            print(f"  Sleeping for {sleep_duration:.2f} seconds...")
            if i < len(repos_to_check) - 1: # Don't sleep after the last item
                 time.sleep(sleep_duration)


    # Update the SWE_BENCH_BLACKLIST_FILE
    if failed_or_problematic_repo_urls:
        try:
            existing_blacklist = Load_repos(SWE_BENCH_BLACKLIST_FILE)
            combined_blacklist = list(existing_blacklist.union(set(failed_or_problematic_repo_urls)))
            with open(SWE_BENCH_BLACKLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(combined_blacklist, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing to {SWE_BENCH_BLACKLIST_FILE}: {e}")

    return passed_repos
