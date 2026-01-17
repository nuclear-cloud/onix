from playwright.sync_api import sync_playwright
import json
import time

def run():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("Navigating to Vivat...")
        
        # Capture network requests
        def handle_response(response):
            try:
                if "json" in response.headers.get("content-type", ""):
                    url = response.url
                    # Filter for likely catalog APIs
                    if "api" in url or "catalog" in url or "products" in url or "search" in url:
                        print(f"\n[API FOUND] {url}")
                        print(f"Status: {response.status}")
                        try:
                            data = response.json()
                            # Print a snippet of the data to verify structure
                            snippet = json.dumps(data, ensure_ascii=False)[:200]
                            print(f"Data Snippet: {snippet}...")
                        except:
                            print("Could not parse JSON body")
            except Exception as e:
                pass

        page.on("response", handle_response)

        # Go to home page first
        page.goto("https://vivat.com.ua/", timeout=60000)
        time.sleep(2)
        
        # Try to navigate to "Книги" -> "Художні книги" to trigger product load
        print("Navigating to Catalog Category...")
        try:
            # Direct link to a category usually triggers product fetch
            page.goto("https://vivat.com.ua/knyhy/khudozhni-knyhy/", timeout=60000)
        except Exception as e:
            print(f"Error navigating: {e}")

        # Scroll down to trigger pagination/lazy loading
        print("Scrolling...")
        for _ in range(5):
            page.mouse.wheel(0, 1000)
            time.sleep(2)

        browser.close()

if __name__ == "__main__":
    run()
