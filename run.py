import requests
import json
import os
from datetime import datetime, timezone
from FilterRepo import Filterby_Python_percentage, Load_repos, cleaned_repos
from config import OWNED_REPOS_FILE, FILTERED_REPOS_FILE, REJECTED_REPOS_FILE

# Load the existed repos
owned_repos = Load_repos(OWNED_REPOS_FILE)
rejected_repos = Load_repos(REJECTED_REPOS_FILE)
merged_repos = owned_repos.union(rejected_repos)
# SEARCH CRITERIA HERE
query = 'language:Python stars:>500 pushed:>2024-11-01'
per_page = 100 # first 100 results

# GitHub API Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

url = f"https://api.github.com/search/repositories?q={query}&per_page={per_page}"

headers = {
    "Accept": "application/vnd.github.v3+json",
}
if GITHUB_TOKEN and GITHUB_TOKEN.strip() and GITHUB_TOKEN != "YOUR_GITHUB_TOKEN": # Check if token is not empty/whitespace
    headers["Authorization"] = f"token {GITHUB_TOKEN}"
    print("Using GitHub token for authentication.")
else:
    print("Warning: No GitHub token provided or token is placeholder/empty. Requests will be unauthenticated and subject to stricter rate limits.")

print(f"Searching GitHub with query: {query}")

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    results = response.json()
    cleaned_filtered_repos = cleaned_repos(merged_repos, results)
    cleaned_filtered_repos = Filterby_Python_percentage(cleaned_filtered_repos, headers)

    # Sort the repositories:
    # Primary key: pushed_at (descending - more recent first)
    # Secondary key: stars (descending)
    def sort_key(repo_item):
        pushed_at_str = repo_item.get('pushed_at')
        try:
            pushed_at_dt = datetime.fromisoformat(pushed_at_str.replace('Z', '+00:00')) if pushed_at_str else datetime.min.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            pushed_at_dt = datetime.min.replace(tzinfo=timezone.utc) # Fallback for invalid date format

        stars_count = repo_item.get('stars', 0)
        if stars_count is None: # Handle None case for stars
            stars_count = 0
        return (pushed_at_dt, stars_count) # Tuple for multi-level sorting

    # Sorts by pushed_at (recent first), then by stars (more first)
    cleaned_filtered_repos.sort(key=sort_key, reverse=True)

    # Output the cleaned and sorted list as JSON
    with open(FILTERED_REPOS_FILE, "w", encoding="utf-8") as out:
        json.dump(cleaned_filtered_repos, out, indent=2, ensure_ascii=False)

    print(f"Saved {len(cleaned_filtered_repos)} filtered, cleaned, and sorted repos to {FILTERED_REPOS_FILE}")
    if 'total_count' in results:
        print(f"Total repositories found by query: {results['total_count']}")
        if results['total_count'] > per_page and len(cleaned_filtered_repos) <= per_page:
            print(f"Note: Only the first {per_page} results were processed (as requested).")

except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
    if response is not None:
        print(f"Status Code: {response.status_code}")
        print("Response content:", response.text)
        if response.status_code == 403:
            print("A 403 Forbidden error often indicates rate limiting. Check response headers for 'X-RateLimit-Remaining' and 'X-RateLimit-Reset'. Using a GitHub token can help.")
except requests.exceptions.RequestException as req_err:
    print(f"Request error occurred: {req_err}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
