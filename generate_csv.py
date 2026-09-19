import json
from playwright.sync_api import sync_playwright

def fetch_nascar_schedule():
    with sync_playwright() as p:
        # Launch browser with realistic context settings
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.nascar.com/schedule"
            }
        )
        page = context.new_page()
        
        # Navigate to the main page first to establish cookies/session
        page.goto("https://www.nascar.com/schedule", wait_until="networkidle")
        
        # Request the JSON endpoint within the authenticated browser context
        response = page.request.get("https://cf.nascar.com/cpm/prod/2026/1/schedule.json")
        
        if response.status == 200:
            schedule_data = response.json()
            return schedule_data
        else:
            print(f"Failed with status code: {response.status}")
            return None

if __name__ == "__main__":
    data = fetch_nascar_schedule()
    if data:
        print("Successfully retrieved schedule data!")
