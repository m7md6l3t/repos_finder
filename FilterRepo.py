import requests
import json
import os
import time
from bs4 import BeautifulSoup
from config import (REJECTED_REPOS_FILE, SWE_BENCH_BASE_URL, SWE_BENCH_FILTER_PARAMS,
                    SWE_BENCH_GREEN_LIST_FILE, SWE_BENCH_BLACKLIST_FILE)

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

def filter_by_swe_bench_batches(repos_to_check, swe_bench_auth_headers):
    """
    Checks repositories for batch validity.

    Args:
        repos_to_check (list): List of repository dictionaries.
        swe_bench_auth_headers (dict): Authentication headers.

    Returns:
        list: Repositories that passed the SWE-Bench check.
    """
    passed_repos = []
    failed_or_problematic_repo_urls = [] # Store URLs of empty repos

    if not repos_to_check:
        return []

    print(f"\nChecking {len(repos_to_check)} repos against SWE-Bench Plus for batch validity...")

    for i, repo_info in enumerate(repos_to_check):
        full_name = repo_info.get("full_name")
        html_url = repo_info.get("html_url")

        if not full_name or not html_url:
            print(f"  Skipping repo due to missing full_name or html_url: {repo_info}")
            if html_url:
                 failed_or_problematic_repo_urls.append(html_url)
            continue

        swe_bench_repo_name = full_name.replace("/", "__")
        target_url = f"{SWE_BENCH_BASE_URL}{swe_bench_repo_name}{SWE_BENCH_FILTER_PARAMS}"

        print(f"({i+1}/{len(repos_to_check)}) Checking SWE-Bench for: {full_name}")
        print(f"  URL: {target_url}")

        try:
            response = requests.get(target_url, headers=swe_bench_auth_headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            tbody_tag = soup.find("tbody", class_="bg-white divide-y divide-gray-200")

            if tbody_tag:
                tr_tags = tbody_tag.find_all("tr", class_="hover:bg-gray-50 cursor-pointer")
                if tr_tags:
                    print(f"  [SWE-BENCH PASSED] Found {len(tr_tags)} valid batch(es) for {full_name}.")
                    repo_info["swe_bench_batch_count"] = len(tr_tags)
                    passed_repos.append(repo_info)
                else:
                    print(f"  [SWE-BENCH FAILED] Found <tbody> but no valid <tr> batches for {full_name}.")
                    failed_or_problematic_repo_urls.append(html_url)
            else:
                print(f"  [SWE-BENCH FAILED] Could not find expected <tbody> for {full_name}.")
                print(f"  Response snippet for {full_name}: {response.text[:200]}")
                failed_or_problematic_repo_urls.append(html_url)

        except requests.exceptions.HTTPError as http_err:
            print(f"  [HTTP ERROR] for {full_name} at SWE-Bench ({target_url}): {http_err}")
            if http_err.response is not None:
                print(f"  Status Code: {http_err.response.status_code}")
                if http_err.response.status_code in [401, 403]:
                    print("  SWE-Bench Authentication error. Please check your token/cookie.")
            failed_or_problematic_repo_urls.append(html_url)
        except requests.exceptions.RequestException as req_err:
            print(f"  [REQUEST ERROR] for {full_name} at SWE-Bench ({target_url}): {req_err}")
            failed_or_problematic_repo_urls.append(html_url)
        except Exception as e:
            print(f"  [UNEXPECTED ERROR] processing {full_name} at SWE-Bench ({target_url}): {e}")
            failed_or_problematic_repo_urls.append(html_url)

        if i < len(repos_to_check) -1:
            time.sleep(4)

    # Update the SWE_BENCH_BLACKLIST_FILE
    if failed_or_problematic_repo_urls:
        try:
            existing_blacklist = Load_repos(SWE_BENCH_BLACKLIST_FILE) # Returns a set of URLs
            # Combine, ensuring uniqueness, then convert to list for JSON
            combined_blacklist = list(existing_blacklist.union(set(failed_or_problematic_repo_urls)))
            with open(SWE_BENCH_BLACKLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(combined_blacklist, f, indent=2, ensure_ascii=False)
            print(f"Updated {SWE_BENCH_BLACKLIST_FILE} with {len(failed_or_problematic_repo_urls)} new/updated entries.")
        except Exception as e:
            print(f"Error writing to {SWE_BENCH_BLACKLIST_FILE}: {e}")

    return passed_repos
