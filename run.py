
import json
import os
from datetime import datetime, timezone
from FilterRepo import Filterby_Python_percentage, Load_repos, cleaned_repos
from config import OWNED_REPOS_FILE, FILTERED_REPOS_FILE, REJECTED_REPOS_FILE, get_header
from pagination import get_github_repositories

# Load the existed repos
owned_repos = Load_repos(OWNED_REPOS_FILE)
rejected_repos = Load_repos(REJECTED_REPOS_FILE)
merged_repos = owned_repos.union(rejected_repos)

# Load filtered_repos.json if exists and filter out items in merged_repos
if os.path.exists(FILTERED_REPOS_FILE):
    with open(FILTERED_REPOS_FILE, "r", encoding="utf-8") as f:
        try:
            existing_filtered = json.load(f)
            # Remove items whose html_url is in merged_repos
            existing_filtered = [
                repo for repo in existing_filtered
                if repo.get("html_url") not in merged_repos
            ]
        except Exception:
            existing_filtered = []
else:
    existing_filtered = []

# Merge existing filtered repos with owned and rejected repos
merged_repos = merged_repos.union({repo.get("html_url") for repo in existing_filtered})
query = 'language:Python stars:>500 pushed:>2024-11-01'
all_items = get_github_repositories(query)
results = {'items': all_items}
cleaned_filtered_repos = cleaned_repos(merged_repos, results)
cleaned_filtered_repos = Filterby_Python_percentage(cleaned_filtered_repos, get_header())

def sort_key(repo_item):
    pushed_at_str = repo_item.get('pushed_at')
    try:
        pushed_at_dt = datetime.fromisoformat(pushed_at_str.replace('Z', '+00:00')) if pushed_at_str else datetime.min.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        pushed_at_dt = datetime.min.replace(tzinfo=timezone.utc)
    stars_count = repo_item.get('stars', 0)
    if stars_count is None:
        stars_count = 0
    return (pushed_at_dt, stars_count)

cleaned_filtered_repos.sort(key=sort_key, reverse=True)

# Append new cleaned_filtered_repos to existing_filtered and save
final_filtered = existing_filtered + cleaned_filtered_repos

with open(FILTERED_REPOS_FILE, "w", encoding="utf-8") as out:
    json.dump(final_filtered, out, indent=2, ensure_ascii=False)

print(f"Saved {len(final_filtered)} filtered, cleaned, and sorted repos to {FILTERED_REPOS_FILE}")
print(f"Total repositories fetched: {len(all_items)}")