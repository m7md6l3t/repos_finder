import json
import os
from datetime import datetime, timezone
from pagination import get_github_repositories
from FilterRepo import (Filterby_Python_percentage, Load_repos, cleaned_repos,
                        filter_by_swe_bench_batches)
from config import (OWNED_REPOS_FILE, FILTERED_REPOS_FILE, REJECTED_REPOS_FILE,
                    SWE_BENCH_GREEN_LIST_FILE, SWE_BENCH_BLACKLIST_FILE,
                    get_github_header, get_swe_bench_header)

def run_filter_pipeline():
    # Load all owned repository URLs
    owned_repo_urls = Load_repos(OWNED_REPOS_FILE)
    rejected_by_python_urls = Load_repos(REJECTED_REPOS_FILE)
    failed_swe_bench_urls = Load_repos(SWE_BENCH_BLACKLIST_FILE)

    # Load repos that previously passed ALL filters (are in the current green list)
    # These should also not be re-fetched from GitHub.
    # SWE_BENCH_GREEN_LIST_FILE stores full repo objects, Load_repos extracts html_url
    previously_passed_all_urls = Load_repos(SWE_BENCH_GREEN_LIST_FILE)

    # Combine all URLs to ignore for the initial GitHub fetch
    # These are repos we definitely don't want to query GitHub for again if they've been fully processed or blacklisted.
    ignore_for_github_fetch = owned_repo_urls.union(rejected_by_python_urls) \
                                           .union(failed_swe_bench_urls) \
                                           .union(previously_passed_all_urls)

    print(f"Initializing... Will ignore {len(ignore_for_github_fetch)} URLs for new GitHub fetch.")

    # Fetch new repositories from GitHub
    # (Adjust query and pagination settings in pagination.py or here as needed)
    github_query = 'language:Python stars:>500 pushed:>2024-11-01'
    print(f"\nFetching new repositories from GitHub with query: {github_query}")
    try:
        new_github_items = get_github_repositories(github_query)
    except ImportError:
        print("Error: pagination.py or get_github_repositories function not found. Please ensure it's correctly defined.")
        new_github_items = [] # Default to empty list if pagination fails

    github_api_results = {'items': new_github_items}
    print(f"Fetched {len(new_github_items)} new items from GitHub API.")

    # Clean newly fetched GitHub repos
    newly_cleaned_github_repos = cleaned_repos(ignore_for_github_fetch, github_api_results)
    print(f"Cleaned {len(newly_cleaned_github_repos)} new GitHub repos (after initial ignore).")

    # # Filter by Python Percentage
    # github_headers = get_github_header()
    # passed_python_filter = Filterby_Python_percentage(newly_cleaned_github_repos, github_headers)
    # print(f"{len(passed_python_filter)} repos passed Python percentage filter.")

    # Filter by SWE-Bench Batches
    repos_for_swe_bench_check = [
        repo for repo in newly_cleaned_github_repos
        if repo.get("html_url") not in failed_swe_bench_urls and repo.get("html_url") not in owned_repo_urls
    ]

    swe_bench_base_headers = get_swe_bench_header(include_user_agent=False) # Get auth headers without UA initially
    # filter_by_swe_bench_batches updates SWE_BENCH_BLACKLIST_FILE internally
    newly_passed_swe_bench = filter_by_swe_bench_batches(repos_for_swe_bench_check, swe_bench_base_headers)
    print(f"{len(newly_passed_swe_bench)} new repos passed SWE-Bench batch check.")

    # Combine and Finalize Green List
    # Start with repos that previously passed all filters and are still valid (not owned)
    final_green_list = []
    if os.path.exists(SWE_BENCH_GREEN_LIST_FILE):
        try:
            with open(SWE_BENCH_GREEN_LIST_FILE, "r", encoding="utf-8") as f:
                final_green_list = json.load(f)
            # Ensure these are not in owned_repo_urls now
            final_green_list = [repo for repo in final_green_list if repo.get("html_url") not in owned_repo_urls]
        except Exception as e:
            print(f"Error loading {SWE_BENCH_GREEN_LIST_FILE}: {e}")
            final_green_list = []

    # Add newly passed repos
    final_green_list.extend(newly_passed_swe_bench)

    # Deduplicate the final list based on 'html_url'
    seen_urls = set()
    deduplicated_green_list = []
    for repo in final_green_list:
        url = repo.get("html_url")
        if url and url not in seen_urls:
            deduplicated_green_list.append(repo)
            seen_urls.add(url)

    # Sort the final green list
    def sort_key(repo_item):
        pushed_at_str = repo_item.get('pushed_at')
        try:
            pushed_at_dt = datetime.fromisoformat(pushed_at_str.replace('Z', '+00:00')) if pushed_at_str else datetime.min.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            pushed_at_dt = datetime.min.replace(tzinfo=timezone.utc)
        stars_count = repo_item.get('stars', 0)
        stars_count = stars_count if stars_count is not None else 0
        return (pushed_at_dt, stars_count)

    deduplicated_green_list.sort(key=sort_key, reverse=True)

    # Save the final green list
    with open(SWE_BENCH_GREEN_LIST_FILE, "w", encoding="utf-8") as out:
        json.dump(deduplicated_green_list, out, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(deduplicated_green_list)} repos to the final green list: {SWE_BENCH_GREEN_LIST_FILE}")

    # Also update FILTERED_REPOS_FILE to be the same as the final green list
    with open(FILTERED_REPOS_FILE, "w", encoding="utf-8") as out:
        json.dump(deduplicated_green_list, out, indent=2, ensure_ascii=False)
    print(f"Updated {FILTERED_REPOS_FILE} to match the final green list.")

    print("\nPipeline finished.")
    print(f"Summary:")
    print(f"  - Owned Repos: {len(owned_repo_urls)}")
    print(f"  - Rejected by Python % (cumulative): {len(rejected_by_python_urls)}")
    print(f"  - Failed SWE-Bench (cumulative): {len(failed_swe_bench_urls)}")
    print(f"  - Final Green List ({SWE_BENCH_GREEN_LIST_FILE}): {len(deduplicated_green_list)}")


if __name__ == "__main__":
    if not hasattr(globals().get('get_github_repositories', None), '__call__'):
        print("Defining a placeholder get_github_repositories for run.py to be executable.")
        def get_github_repositories(query, max_pages=1, per_page_count=10): # Default to 1 page, 10 items for placeholder
            print(f"  (Placeholder Pagination) Searching GitHub with query: {query}, max_pages={max_pages}")
            all_items_placeholder = []
            headers_placeholder = get_github_header()
            for page_num in range(1, max_pages + 1):
                url_placeholder = f"https://api.github.com/search/repositories?q={query}&per_page={per_page_count}&page={page_num}"
                print(f"  (Placeholder Pagination) Fetching page {page_num}...")
                try:
                    response_placeholder = requests.get(url_placeholder, headers=headers_placeholder, timeout=15)
                    response_placeholder.raise_for_status()
                    results_placeholder = response_placeholder.json()
                    items_placeholder = results_placeholder.get('items', [])
                    if not items_placeholder:
                        break
                    all_items_placeholder.extend(items_placeholder)
                    if len(items_placeholder) < per_page_count:
                        break
                except Exception as e_placeholder:
                    print(f"  (Placeholder Pagination) Error fetching page {page_num}: {e_placeholder}")
                    break
            return all_items_placeholder
        globals()['get_github_repositories'] = get_github_repositories

    run_filter_pipeline()
