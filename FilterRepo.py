import requests
import json
import os
from config import REJECTED_REPOS_FILE

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