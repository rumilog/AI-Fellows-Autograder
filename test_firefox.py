import os
from playwright.sync_api import sync_playwright

def test_firefox():
    """Simple test to open Firefox Nightly with persistent profile"""
    
    with sync_playwright() as p:
        # Launch Firefox Nightly with a persistent profile directory
        # This will save your login for future runs
        browser = p.firefox.launch_persistent_context(
            user_data_dir="./firefox_profile",  # Save profile in project folder
            headless=False  # Show the browser window
        )
        
        # Get the first page
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        # Navigate to Gradescope
        print("Opening Firefox...")
        print("Navigating to Gradescope...")
        page.goto("https://www.gradescope.com")
        
        # Wait for page to load
        page.wait_for_load_state("networkidle")
        
        print("Firefox opened successfully!")
        print("Current URL:", page.url)
        print("Page title:", page.title())
        
        # Keep browser open longer so you can log in
        import time
        print("Browser will stay open for 60 seconds so you can log into Gradescope...")
        print("Please log in now - your login will be saved for future runs!")
        time.sleep(60)
        
        browser.close()
        print("Firefox closed.")

if __name__ == "__main__":
    test_firefox()
