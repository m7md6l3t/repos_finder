import os


OWNED_REPOS_FILE = "repos_list.json"
FILTERED_REPOS_FILE = "filtered_repos.json"
REJECTED_REPOS_FILE = "rejected_repos.json"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_header():
    headers = {
    "Accept": "application/vnd.github.v3+json",
    }
    if GITHUB_TOKEN and GITHUB_TOKEN.strip() and GITHUB_TOKEN != "YOUR_GITHUB_TOKEN": # Check if token is not empty/whitespace
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
        print("Using GitHub token for authentication.")
    else:
        print("Warning: No GitHub token provided or token is placeholder/empty. Requests will be unauthenticated and subject to stricter rate limits.")