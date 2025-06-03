import os

OWNED_REPOS_FILE = "repos_list.json"
FILTERED_REPOS_FILE = "filtered_repos.json"
REJECTED_REPOS_FILE = "rejected_repos.json"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

SWE_BENCH_GREEN_LIST_FILE = "swe_bench_passed_repos.json"
SWE_BENCH_BLACKLIST_FILE = "swe_bench_failed_repos.json"

# SWE-Bench configurations
SWE_BENCH_BASE_URL = "https://swe-bench-plus.turing.com/repos/"
# The filter query parameter, URL encoded
SWE_BENCH_FILTER_PARAMS = "?filter=%7B%22minDate%22%3A%222024-11-01%22%7D"

def get_github_header():
    headers = {
    "Accept": "application/vnd.github.v3+json",
    }
    if GITHUB_TOKEN and GITHUB_TOKEN.strip() and GITHUB_TOKEN != "YOUR_GITHUB_TOKEN": # Check if token is not empty/whitespace
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
        print("Using GitHub token for authentication.")
    else:
        print("Warning: No GitHub token provided for GitHub API. Requests will be unauthenticated and subject to stricter rate limits.")
    return headers

def get_swe_bench_header():
    """
    Returns headers for swe-bench-plus.turing.com requests.
    REMEBER: set your session's cookies in the environment vairable
    """
    headers = {
        "User-Agent": "Python GitHub Repo Filter Script/1.0"
    }
    # Using an environment variable for a session cookie
    swe_bench_cookie = os.getenv("SWE_BENCH_COOKIE")
    if swe_bench_cookie:
        headers["Cookie"] = swe_bench_cookie
        print("Using SWE_BENCH_COOKIE for swe-bench-plus.turing.com authentication.")
    else:
        # Using an environment variable for a token
        swe_bench_token = os.getenv("SWE_BENCH_TOKEN")
        if swe_bench_token:
            headers["Authorization"] = f"Bearer {swe_bench_token}"
            print("Using SWE_BENCH_TOKEN for swe-bench-plus.turing.com authentication.")
        else:
            print("Warning: No authentication method configured for swe-bench-plus.turing.com (SWE_BENCH_COOKIE or SWE_BENCH_TOKEN not set). Requests may fail.")
    return headers
