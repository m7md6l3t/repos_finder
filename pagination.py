import requests
from config import get_header


per_page = 1 # first 100 results
start_page = 1
to_page = 10
headers = get_header()

def get_github_repositories(query):
    print(f"Searching GitHub with query: {query}")
    all_items = []
    for page in range(start_page, to_page + 1):
        url = f"https://api.github.com/search/repositories?q={query}&per_page={per_page}&page={page}"
        print(f"Fetching page {page}...")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            results = response.json()
            items = results.get('items', [])
            if not items:
                break
            all_items.extend(items)
            if len(items) < per_page:
                break  # Last page reached
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            if response is not None:
                print(f"Status Code: {response.status_code}")
                print("Response content:", response.text)
                if response.status_code == 403:
                    print("A 403 Forbidden error often indicates rate limiting. Check response headers for 'X-RateLimit-Remaining' and 'X-RateLimit-Reset'. Using a GitHub token can help.")
            break
        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred: {req_err}")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break
    if not all_items:
        print("No repositories found.")
    else:
        print(f"Found {len(all_items)} repositories.")
    return all_items