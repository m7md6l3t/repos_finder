import os
import random

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

# user agent rotation list
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
]

# Min and max delay between requests to SWE-Bench (in seconds)
SWE_BENCH_MIN_DELAY = 6.0
SWE_BENCH_MAX_DELAY = 10.0

# Retry configuration for SWE-Bench requests
SWE_BENCH_MAX_RETRIES = 3
SWE_BENCH_BACKOFF_FACTOR = 0.5

# Maximum consecutive requests before a longer pause
SWE_BENCH_MAX_CONSECUTIVE_REQUESTS = 40
SWE_BENCH_LONG_PAUSE_DURATION = 300

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def get_github_header():
    headers = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": get_random_user_agent()
    }
    if GITHUB_TOKEN and GITHUB_TOKEN.strip() and GITHUB_TOKEN != "YOUR_GITHUB_TOKEN": # Check if token is not empty/whitespace
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
        print("Using GitHub token for authentication.")
    else:
        print("Warning: No GitHub token provided for GitHub API. Requests will be unauthenticated and subject to stricter rate limits.")
    return headers

def get_swe_bench_header(include_user_agent=True):
    """
    Returns headers for swe-bench-plus.turing.com requests.
    REMEBER: set your session's cookies in the environment vairable
    """
    headers = {}
    if include_user_agent:
        headers["User-Agent"] = get_random_user_agent()

    # Using an environment variable for a session cookie
    # swe_bench_cookie = "" # uncomment this line if you want to use your cookie string directly for quick testing, don't forget to comment out the below line if you enable this
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
