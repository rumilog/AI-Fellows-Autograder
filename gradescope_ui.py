import os
import time
import re
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

class GradescopeDownloader:
    def __init__(self):
        load_dotenv()
        self.download_folder = Path(os.getenv("DOWNLOAD_FOLDER", "downloads"))
        self.headless = os.getenv("HEADLESS", "false").lower() == "true"
        self.download_folder.mkdir(exist_ok=True)
        
    def get_course_url(self):
        """Get course URL from user input"""
        print("=" * 60)
        print("🎓 GRADESCOPE ASSIGNMENT DOWNLOADER")
        print("=" * 60)
        print(f"Download folder: {self.download_folder.absolute()}")
        print("=" * 60)
        
        while True:
            url = input("\n📝 Enter your Gradescope course URL: ").strip()
            if url.lower() == 'q' or url.lower() == 'quit':
                print("👋 Goodbye!")
                exit()
            if url and "gradescope.com" in url and "courses" in url:
                # Ensure it ends with /assignments to show the assignments tab
                if not url.endswith('/assignments'):
                    url = url.rstrip('/') + '/assignments'
                return url
            print("❌ Please enter a valid Gradescope course URL (e.g., https://www.gradescope.com/courses/1083338)")
    
    def get_login_credentials(self):
        """Get login credentials from user"""
        print("\n🔐 Login required. Please enter your Gradescope credentials:")
        email = input("📧 Email: ").strip()
        password = input("🔒 Password: ").strip()
        return email, password
    
    async def handle_login(self, page, email, password):
        """Handle the login process"""
        print("🔐 Attempting to log in...")
        
        try:
            # Wait for login form to be visible
            await page.wait_for_selector('input[type="email"], input[name="email"], input[id="email"]', timeout=10000)
            
            # Fill in email
            email_selectors = ['input[type="email"]', 'input[name="email"]', 'input[id="email"]']
            for selector in email_selectors:
                try:
                    email_input = await page.query_selector(selector)
                    if email_input:
                        await email_input.fill(email)
                        break
                except:
                    continue
            
            # Fill in password
            password_selectors = ['input[type="password"]', 'input[name="password"]', 'input[id="password"]']
            for selector in password_selectors:
                try:
                    password_input = await page.query_selector(selector)
                    if password_input:
                        await password_input.fill(password)
                        break
                except:
                    continue
            
            # Click login button
            login_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Log in")',
                'button:has-text("Sign in")',
                '.btn-primary',
                '#login-button'
            ]
            
            for selector in login_selectors:
                try:
                    login_button = await page.query_selector(selector)
                    if login_button:
                        await login_button.click()
                        break
                except:
                    continue
            
            # Wait for navigation after login
            await asyncio.sleep(3)
            
            # Check if login was successful (not on login page anymore)
            current_url = page.url
            if "login" not in current_url.lower():
                print("✅ Login successful!")
                return True
            else:
                print("❌ Login failed. Please check your credentials.")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
        
    async def get_assignments(self, page):
        """Extract assignment names and URLs from the course page"""
        print("\n📋 Fetching available assignments...")
        
        # Wait for assignments to load
        await asyncio.sleep(3)
        
        # Look for assignment links - they're typically in a table or list
        assignment_selectors = [
            'a[href*="/assignments/"]',
            'table tbody tr td a',
            '.assignment-row a',
            '.assignment a'
        ]
        
        assignments = []
        
        for selector in assignment_selectors:
            try:
                links = await page.query_selector_all(selector)
                for link in links:
                    href = await link.get_attribute('href')
                    text = await link.text_content()
                    text = text.strip() if text else ""
                    
                    # Filter for assignment links and meaningful text
                    if (href and '/assignments/' in href and 
                        text and len(text) > 3 and 
                        'review' not in text.lower() and
                        'grade' not in text.lower()):
                        
                        # Extract assignment ID from URL
                        match = re.search(r'/assignments/(\d+)', href)
                        if match:
                            assignment_id = match.group(1)
                            full_url = f"https://www.gradescope.com{href}" if href.startswith('/') else href
                            assignments.append({
                                'name': text,
                                'id': assignment_id,
                                'url': full_url
                            })
                
                if assignments:
                    break
                    
            except Exception as e:
                continue
        
        # Remove duplicates based on assignment ID
        unique_assignments = []
        seen_ids = set()
        for assignment in assignments:
            if assignment['id'] not in seen_ids:
                unique_assignments.append(assignment)
                seen_ids.add(assignment['id'])
        
        return unique_assignments
    
    def display_assignments(self, assignments):
        """Display available assignments in a numbered list"""
        if not assignments:
            print("\n❌ No assignments found!")
            print("Make sure you're logged in and the course page has loaded properly.")
            return
        
        print(f"\n📚 Found {len(assignments)} assignment(s):")
        print("-" * 50)
        
        for i, assignment in enumerate(assignments, 1):
            print(f"{i:2d}. {assignment['name']}")
        
        print("-" * 50)
    
    def get_user_choice(self, assignments):
        """Get user's assignment choice"""
        while True:
            try:
                choice = input(f"\n🎯 Enter assignment number (1-{len(assignments)}) or 'q' to quit: ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(assignments):
                    return assignments[choice_num - 1]
                else:
                    print(f"❌ Please enter a number between 1 and {len(assignments)}")
                    
            except ValueError:
                print("❌ Please enter a valid number or 'q' to quit")
    
    async def download_original_submission(self, page, student_name):
        """Download the original submission for a student"""
        print(f"  📥 Downloading original submission...")
        
        # Look for download submission button (try both variations)
        download_button = await page.query_selector('button:has-text("Download submission"), a:has-text("Download submission"), button:has-text("Download Original"), a:has-text("Download Original")')
        
        if download_button:
            await download_button.click()
            await asyncio.sleep(1)
            
            # Check if there's a popup (for PDFs) or if download starts directly (for ZIPs)
            continue_button = await page.query_selector('button:has-text("Continue")')
            
            if continue_button:
                print(f"  🔄 Clicking 'Continue' on popup...")
                
                try:
                    async with page.expect_download(timeout=10000) as download_info:
                        await continue_button.click()
                    
                    download = await download_info.value
                    safe_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '-', '_')).strip()
                    
                    # Get the suggested filename from the download
                    suggested_name = download.suggested_filename
                    if suggested_name:
                        # Use the suggested filename but add _original prefix
                        name_parts = suggested_name.rsplit('.', 1)
                        if len(name_parts) == 2:
                            file_path = self.download_folder / f"{safe_name}_original.{name_parts[1]}"
                        else:
                            file_path = self.download_folder / f"{safe_name}_original_{suggested_name}"
                    else:
                        file_path = self.download_folder / f"{safe_name}_original.pdf"
                    
                    await download.save_as(file_path)
                    print(f"  ✅ Original saved to: {file_path}")
                except Exception as download_error:
                    print(f"  ⚠️  Original download may have started in background")
                    await asyncio.sleep(2)
            else:
                # No popup - download should start directly (like ZIP files)
                print(f"  🔄 Original download started directly...")
                
                try:
                    # For direct downloads, we need to set up the download listener BEFORE clicking
                    async with page.expect_download(timeout=10000) as download_info:
                        # Re-click the button to trigger the download
                        await download_button.click()
                        await asyncio.sleep(1)
                    
                    download = await download_info.value
                    safe_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '-', '_')).strip()
                    
                    # Get the suggested filename from the download
                    suggested_name = download.suggested_filename
                    print(f"  🔍 Suggested filename: {suggested_name}")
                    
                    if suggested_name:
                        # Use the suggested filename but add _original prefix
                        name_parts = suggested_name.rsplit('.', 1)
                        if len(name_parts) == 2:
                            file_path = self.download_folder / f"{safe_name}_original.{name_parts[1]}"
                        else:
                            file_path = self.download_folder / f"{safe_name}_original_{suggested_name}"
                    else:
                        file_path = self.download_folder / f"{safe_name}_original.pdf"
                    
                    print(f"  💾 Saving to: {file_path}")
                    await download.save_as(file_path)
                    print(f"  ✅ Original saved to: {file_path}")
                except Exception as download_error:
                    print(f"  ❌ Download failed: {download_error}")
                    print(f"  ⚠️  Original download may have started in background")
                    await asyncio.sleep(2)
        else:
            print(f"  ❌ No 'Download submission' or 'Download Original' button found")
    
    async def download_graded_copy(self, page, student_name):
        """Download the graded copy for a student"""
        print(f"  📥 Downloading graded copy...")
        
        # Look for download graded copy button
        graded_button = await page.query_selector('button:has-text("Download Graded Copy"), a:has-text("Download Graded Copy")')
        
        if graded_button:
            await graded_button.click()
            await asyncio.sleep(1)
            
            # No need to wait for "Continue" button - download should start directly
            print(f"  🔄 Graded copy download started...")
            
            try:
                # Wait for download to complete
                async with page.expect_download(timeout=15000) as download_info:
                    # The download should already be triggered by the button click
                    pass
                
                download = await download_info.value
                safe_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '-', '_')).strip()
                
                # Get the suggested filename from the download
                suggested_name = download.suggested_filename
                if suggested_name:
                    # Use the suggested filename but add _graded prefix
                    name_parts = suggested_name.rsplit('.', 1)
                    if len(name_parts) == 2:
                        file_path = self.download_folder / f"{safe_name}_graded.{name_parts[1]}"
                    else:
                        file_path = self.download_folder / f"{safe_name}_graded_{suggested_name}"
                else:
                    file_path = self.download_folder / f"{safe_name}_graded.pdf"
                
                await download.save_as(file_path)
                print(f"  ✅ Graded copy saved to: {file_path}")
                
            except Exception as download_error:
                print(f"  ⚠️  Graded copy download may have started in background")
                await asyncio.sleep(2)
        else:
            print(f"  ℹ️  No 'Download Graded Copy' button found (assignment may not be graded yet)")
    
    async def download_assignment(self, assignment):
        """Download all submissions for the selected assignment"""
        print(f"\n🚀 Starting download for: {assignment['name']}")
        print(f"📁 Assignment URL: {assignment['url']}")
        
        # Modify the URL to go to the review grades page
        if assignment['url'].endswith('/review_grades'):
            review_url = assignment['url']
        else:
            review_url = assignment['url'] + '/review_grades'
        
        async with async_playwright() as p:
            browser = await p.firefox.launch_persistent_context(
                user_data_dir="./firefox_profile",
                headless=self.headless,
                accept_downloads=True
            )
            
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            try:
                print(f"🌐 Navigating to: {review_url}")
                await page.goto(review_url, wait_until="networkidle")
                
                # Check if we're logged in
                if "login" in page.url.lower() or "sign in" in (await page.title()).lower():
                    print("\n🔐 You're not logged in!")
                    print("Please log in to Gradescope in the browser window...")
                    input("Press Enter after you've logged in...")
                    await page.goto(review_url, wait_until="networkidle")
                
                print("\n✅ Logged in successfully!")
                print("🔍 Looking for student submissions...")
                
                # Wait for the page to load
                await asyncio.sleep(3)
                
                # Get student links
                async def get_student_links():
                    student_links = await page.query_selector_all('table tbody tr td a')
                    result = []
                    for link in student_links:
                        text = await link.text_content()
                        if text and ' ' in text.strip():
                            result.append(link)
                    return result
                
                student_links = await get_student_links()
                total_students = len(student_links)
                
                if total_students == 0:
                    print("❌ No student submissions found!")
                    return
                
                print(f"👥 Found {total_students} student submission(s)")
                
                # Process each student
                for i in range(total_students):
                    try:
                        student_links = await get_student_links()
                        
                        if i >= len(student_links):
                            print(f"\n[{i+1}/{total_students}] ⏭️  Skipping - link no longer available")
                            continue
                        
                        link = student_links[i]
                        student_name = await link.text_content()
                        student_name = student_name.strip() if student_name else ""
                        print(f"\n[{i+1}/{total_students}] 👤 Processing: {student_name}")
                        
                        # Click on the student's name
                        await link.click()
                        print(f"  🔄 Waiting for student's page to load...")
                        await page.wait_for_load_state("networkidle")
                        await asyncio.sleep(3)  # Additional wait to ensure page is fully loaded
                        
                        # Download original submission
                        await self.download_original_submission(page, student_name)
                        
                        # Download graded copy if available
                        await self.download_graded_copy(page, student_name)
                        
                        # Go back to the review grades page
                        await page.goto(review_url, wait_until="networkidle")
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        print(f"  ❌ Error processing student: {e}")
                        try:
                            await page.goto(review_url, wait_until="networkidle")
                            await asyncio.sleep(2)
                        except:
                            pass
                        continue
                
                print(f"\n🎉 Download complete!")
                print(f"📁 Files saved to: {self.download_folder.absolute()}")
                
                # Keep browser open briefly
                print("\n⏳ Closing browser in 3 seconds...")
                await asyncio.sleep(3)
                
            except KeyboardInterrupt:
                print("\n\n⏹️  Download cancelled by user")
            except Exception as e:
                print(f"\n❌ Error: {e}")
            finally:
                await browser.close()
                print("🔒 Browser closed.")
    
    async def download_assignment_from_url(self, page, assignment_url):
        """Download submissions from a specific assignment URL"""
        try:
            # Navigate to the review grades page for this assignment
            review_url = assignment_url.replace('/assignments/', '/assignments/').rstrip('/') + '/review_grades'
            print(f"🔄 Navigating to review page: {review_url}")
            await page.goto(review_url, wait_until="networkidle")
            
            # Wait for the page to load
            await asyncio.sleep(3)
            
            # Get student links
            async def get_student_links():
                student_links = await page.query_selector_all('table tbody tr td a')
                result = []
                for link in student_links:
                    text = await link.text_content()
                    if text and ' ' in text.strip():
                        result.append(link)
                return result
            
            student_links = await get_student_links()
            total_students = len(student_links)
            
            if total_students == 0:
                print("❌ No student submissions found!")
                return
            
            print(f"👥 Found {total_students} student submission(s)")
            
            # Process each student
            for i in range(total_students):
                try:
                    student_links = await get_student_links()
                    
                    if i >= len(student_links):
                        print(f"\n[{i+1}/{total_students}] ⏭️  Skipping - link no longer available")
                        continue
                    
                    link = student_links[i]
                    student_name = await link.text_content()
                    student_name = student_name.strip() if student_name else ""
                    print(f"\n[{i+1}/{total_students}] 👤 Processing: {student_name}")
                    
                    # Click on the student's name
                    await link.click()
                    print(f"  🔄 Waiting for student's page to load...")
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(3)  # Additional wait to ensure page is fully loaded
                    
                    # Download original submission
                    await self.download_original_submission(page, student_name)
                    
                    # Download graded copy if available
                    await self.download_graded_copy(page, student_name)
                    
                    # Go back to the review grades page
                    await page.goto(review_url, wait_until="networkidle")
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"  ❌ Error processing student: {e}")
                    try:
                        await page.goto(review_url, wait_until="networkidle")
                        await asyncio.sleep(2)
                    except:
                        pass
                    continue
            
            print(f"\n🎉 Download complete!")
            print(f"📁 Files saved to: {self.download_folder.absolute()}")
            
        except Exception as e:
            print(f"❌ Error downloading assignment: {e}")
    
    async def download_assignment_with_browser(self, page, assignment):
        """Download submissions using the existing browser session"""
        try:
            # Navigate to the review grades page for this assignment
            review_url = assignment['url'].replace('/assignments/', '/assignments/').rstrip('/') + '/review_grades'
            print(f"🔄 Navigating to review page: {review_url}")
            await page.goto(review_url, wait_until="networkidle")
            
            # Wait for the page to load
            await asyncio.sleep(3)
            
            # Get student links
            async def get_student_links():
                student_links = await page.query_selector_all('table tbody tr td a')
                result = []
                for link in student_links:
                    text = await link.text_content()
                    if text and ' ' in text.strip():
                        result.append(link)
                return result
            
            student_links = await get_student_links()
            total_students = len(student_links)
            
            if total_students == 0:
                print("❌ No student submissions found!")
                return
            
            print(f"👥 Found {total_students} student submission(s)")
            
            # Process each student
            for i in range(total_students):
                try:
                    student_links = await get_student_links()
                    
                    if i >= len(student_links):
                        print(f"\n[{i+1}/{total_students}] ⏭️  Skipping - link no longer available")
                        continue
                    
                    link = student_links[i]
                    student_name = await link.text_content()
                    student_name = student_name.strip() if student_name else ""
                    print(f"\n[{i+1}/{total_students}] 👤 Processing: {student_name}")
                    
                    # Click on the student's name
                    await link.click()
                    print(f"  🔄 Waiting for student's page to load...")
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(3)  # Additional wait to ensure page is fully loaded
                    
                    # Download original submission
                    await self.download_original_submission(page, student_name)
                    
                    # Download graded copy if available
                    await self.download_graded_copy(page, student_name)
                    
                    # Go back to the review grades page
                    await page.goto(review_url, wait_until="networkidle")
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"  ❌ Error processing student: {e}")
                    try:
                        await page.goto(review_url, wait_until="networkidle")
                        await asyncio.sleep(2)
                    except:
                        pass
                    continue
            
            print(f"\n🎉 Download complete!")
            print(f"📁 Files saved to: {self.download_folder.absolute()}")
            
        except Exception as e:
            print(f"❌ Error downloading assignment: {e}")
    
    async def run(self):
        """Main application loop"""
        # Get course URL from user
        course_url = self.get_course_url()
        
        async with async_playwright() as p:
            browser = await p.firefox.launch_persistent_context(
                user_data_dir="./firefox_profile",
                headless=self.headless,
                accept_downloads=True
            )
            
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            try:
                print(f"🌐 Navigating to course page...")
                await page.goto(course_url, wait_until="networkidle")
                
                # Check if we need to log in
                if "login" in page.url.lower() or "sign in" in (await page.title()).lower():
                    print("\n🔐 Login required!")
                    email, password = self.get_login_credentials()
                    
                    # Attempt automated login
                    login_success = await self.handle_login(page, email, password)
                    
                    if not login_success:
                        print("❌ Automated login failed. Please try again.")
                        return
                    
                    # Navigate to the course page after login
                    print("🔄 Navigating to course page...")
                    await page.goto(course_url, wait_until="networkidle")
                
                # Get assignments from the course page
                assignments = await self.get_assignments(page)
                self.display_assignments(assignments)
                
                if not assignments:
                    print("\n❌ No assignments found. Exiting...")
                    return
                
                # Get user choice
                selected_assignment = self.get_user_choice(assignments)
                
                if selected_assignment:
                    # Keep the browser open and use the same session for downloading
                    print("📥 Starting download process...")
                    await self.download_assignment_with_browser(page, selected_assignment)
                else:
                    print("\n👋 Goodbye!")
                
            except KeyboardInterrupt:
                print("\n\n⏹️  Application cancelled by user")
            except Exception as e:
                print(f"\n❌ Error: {e}")
            finally:
                try:
                    await browser.close()
                except:
                    pass

async def main():
    """Entry point"""
    try:
        downloader = GradescopeDownloader()
        await downloader.run()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
