import requests
import json

# ---- Load the repos you already have ----
with open("repos_list.json", "r", encoding="utf-8") as f:
    owned_repos = set(json.load(f))  # A set for fast lookup

# ---- EDIT YOUR SEARCH CRITERIA HERE ----
query = 'language:Python stars:>2000 pushed:>2024-11-01'  # Change as needed
per_page = 100  # Up to 100 per request

url = f"https://api.github.com/search/repositories?q={query}&per_page={per_page}"

headers = {
    "Accept": "application/vnd.github.v3+json",
    # "Authorization": "token YOUR_GITHUB_TOKEN",  # Optional
}

response = requests.get(url, headers=headers)
response.raise_for_status()
results = response.json()

# Filter and collect
filtered_repos = [
    repo for repo in results.get('items', [])
    if repo['full_name'] not in owned_repos
]

# Output as JSON
with open("filtered_repos.json", "w", encoding="utf-8") as out:
    json.dump(filtered_repos, out, indent=2, ensure_ascii=False)

print(f"Saved {len(filtered_repos)} filtered repos to filtered_repos.json")