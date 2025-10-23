import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

def download_student_submissions():
    """Download all student submissions from a Gradescope assignment"""
    
    load_dotenv()
    
    # Configuration from .env
    course_url = os.getenv("COURSE_URL", "https://www.gradescope.com/courses/1083338/assignments/6501730/review_grades")
    download_folder = Path(os.getenv("DOWNLOAD_FOLDER", "downloads"))
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    
    # Create download folder
    download_folder.mkdir(exist_ok=True)
    print(f"Downloads will be saved to: {download_folder.absolute()}")
    
    with sync_playwright() as p:
        # Launch Firefox Nightly with persistent profile (saves login)
        browser = p.firefox.launch_persistent_context(
            user_data_dir="./firefox_profile",
            headless=headless,
            accept_downloads=True
        )
        
        # Get the first page
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        try:
            print(f"Navigating to: {course_url}")
            page.goto(course_url, wait_until="networkidle")
            
            print(f"Current page: {page.title()}")
            print(f"URL: {page.url}")
            
            # Wait a moment for the page to fully load
            time.sleep(2)
            
            # Check if we're logged in
            if "login" in page.url.lower() or "sign in" in page.title().lower():
                print("\n[!] You're not logged in!")
                print("Please log in to Gradescope in the browser window...")
                print("The script will wait for you to log in.")
                input("Press Enter after you've logged in...")
                page.goto(course_url, wait_until="networkidle")
            
            print("\n[OK] Logged in successfully!")
            print("Looking for student submissions...")
            
            # Find all student name links in the "First & Last Name" column
            # Wait for the table to load
            time.sleep(2)
            
            # Get the initial count of students
            def get_student_links():
                student_links = page.query_selector_all('table tbody tr td a')
                return [
                    link for link in student_links 
                    if link.text_content() and ' ' in link.text_content().strip()
                ]
            
            student_links = get_student_links()
            total_students = len(student_links)
            print(f"Found {total_students} student submissions")
            
            # Process each student by index (re-find links each time to avoid stale references)
            for i in range(total_students):
                try:
                    # Re-find all links (in case page was refreshed)
                    student_links = get_student_links()
                    
                    if i >= len(student_links):
                        print(f"\n[{i+1}/{total_students}] Skipping - link no longer available")
                        continue
                    
                    link = student_links[i]
                    student_name = link.text_content().strip()
                    print(f"\n[{i+1}/{total_students}] Processing: {student_name}")
                    
                    # Click on the student's name
                    link.click()
                    page.wait_for_load_state("networkidle")
                    time.sleep(1)
                    
                    # Look for "Download Original" button
                    download_button = page.query_selector('button:has-text("Download Original"), a:has-text("Download Original")')
                    
                    if download_button:
                        print(f"  Downloading submission for {student_name}...")
                        
                        # Click the download button
                        download_button.click()
                        
                        # Wait for the popup and click "Continue"
                        time.sleep(1)
                        continue_button = page.query_selector('button:has-text("Continue")')
                        
                        if continue_button:
                            print(f"  Clicking 'Continue' on popup...")
                            
                            # Now wait for the actual download after clicking Continue
                            try:
                                with page.expect_download(timeout=10000) as download_info:
                                    continue_button.click()
                                
                                download = download_info.value
                                # Save with student's name
                                safe_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '-', '_')).strip()
                                file_path = download_folder / f"{safe_name}.pdf"
                                download.save_as(file_path)
                                print(f"  Saved to: {file_path}")
                            except Exception as download_error:
                                print(f"  Note: Download may have started in background")
                                time.sleep(2)
                        else:
                            print(f"  No 'Continue' button found - download may have started directly")
                            time.sleep(2)
                    else:
                        print(f"  No 'Download Original' button found for {student_name}")
                    
                    # Go back to the review grades page
                    page.goto(course_url, wait_until="networkidle")
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"  Error processing student: {e}")
                    # Try to go back if we're stuck
                    try:
                        page.goto(course_url, wait_until="networkidle")
                        time.sleep(2)
                    except:
                        pass
                    continue
            
            print("\n[DONE] All submissions downloaded!")
            print(f"Files saved to: {download_folder.absolute()}")
            
            # Keep browser open for a moment to see results
            print("\nClosing browser in 5 seconds...")
            time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n\nClosing browser...")
        except Exception as e:
            print(f"\n[ERROR] {e}")
        finally:
            browser.close()
            print("Browser closed.")

if __name__ == "__main__":
    download_student_submissions()
