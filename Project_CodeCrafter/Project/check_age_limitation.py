
import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright

class AgeLimitation:
    def __init__(self, url):
        if not url:
            raise ValueError("The URL cannot be empty")
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url # Ensure the URL has a valid protocol
        
        self.url = url
        # Define newsletter-related keywords in English and German
        self.age_restriction_phrases = [
            # English Phrases
            "You must be 18 or older", "18+", "You must be over 18", "Age verification",
            "Enter your birthdate", "Please confirm your age", "Restricted to users 18 and older",
            "DOB", "Date of Birth", "Birth date",

            # German Phrases
            "Sie müssen 18 Jahre oder älter sein", "18+", "Sie müssen über 18 Jahre alt sein",
            "Altersverifikation", "Geben Sie Ihr Geburtsdatum ein", "Bitte bestätigen Sie Ihr Alter",
            "Beschränkt auf Benutzer ab 18 Jahren", "Geburtsdatum", "Geburtstag",
        ]   

    async def check_age_limitation(self):
     async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()


        try:
            
            # Special handling for loreal-paris.de
            if "https://www.loreal-paris.de" in self.url:
                newsletter_url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
                print(f"Detected 'loreal-paris.de', redirecting to newsletter URL: {newsletter_url}")
                await page.goto(newsletter_url)
                await page.wait_for_load_state('networkidle')

                
                result, feedback = await self.perform_age_limitation_check(page)
                await browser.close()
                return result, feedback
            
            # Special handling for hansgrohe.de
            if "https://www.hansgrohe.de" in self.url:
                newsletter_url = "https://www.hansgrohe.de/#interest-form"
                print(f"Detected 'hansgrohe.de', redirecting to newsletter URL: {newsletter_url}")
                await page.goto(newsletter_url)
                await page.wait_for_load_state('networkidle')

                
                result, feedback = await self.perform_age_limitation_check(page)
                await browser.close()
                return result, feedback
            
            # Special handling for tesa
            if "https://www.tesa.com" in self.url:
                newsletter_url = "https://www.tesa.com/de-de/buero-und-zuhause/do-it-yourself-magazin/newsletter"
                print(f"Detected 'tesa', redirecting to newsletter URL: {newsletter_url}")
                await page.goto(newsletter_url)
                await page.wait_for_load_state('networkidle')

                
                result, feedback = await self.perform_age_limitation_check(page)
                await browser.close()
                return result, feedback
            
            # Special handling for royal canin
            if "https://www.royalcanin.com/de" in self.url:
                 newsletter_url = "https://www.royalcanin.com/de/about-us/newsletter"
                 print(f"Detected 'royalcanin.com', redirecting to newsletter URL: {newsletter_url}")
                 await page.goto(newsletter_url)
                 await page.wait_for_load_state('networkidle')
    
                 # Assuming there's a button to click that will take us to the actual form
                 try:
                    # Wait for and click the button that leads to the newsletter form
                    newsletter_button = await page.query_selector('a:has-text("Zum Newsletter anmelden")')  # Update the selector to match the button
                    if newsletter_button:
                        await newsletter_button.click()
                        await page.wait_for_load_state('networkidle')
            
                        # After the redirection, check for the Age Limitation again
                        criteria_met, feedback = await self.perform_age_limitation_check(page)
                        await browser.close()
                        return criteria_met, feedback
                 except Exception as e:
                    feedback = f"Error clicking the button for newsletter: {str(e)}"
                    await browser.close()
                    return False, feedback
                 
            if "https://www.schwarzkopf.de" in self.url:
                print(f"Detected 'schwarzkopf.de', clicking 'ANMELDEN' for newsletter.")
    
                # Navigate to the homepage
                await page.goto(self.url)
                await page.wait_for_load_state('networkidle')

                # Wait for the "ANMELDEN" button and ensure it is visible
                sign_up_button = await page.query_selector('button.calltoaction__link.cta:has-text("ANMELDEN")')
                if sign_up_button:
                    print("Clicking 'ANMELDEN' button to trigger the modal.")
                    await sign_up_button.click()

                    # Wait for the modal container to become visible
                    try:
                        print("Waiting for modal to appear...")

                        # Wait for the modal to appear (using the wrapper or a more general modal container)
                        await page.wait_for_selector('div.calltoaction__wrapper.cta', state='visible', timeout=20000)

                        # Optionally, add a small delay to allow any dynamic content to fully load
                        await asyncio.sleep(2)

                        # Now perform age verification on the modal page
                        result, feedback = await self.perform_age_limitation_check(page)
                        await browser.close()
                        return result, feedback
                    except Exception as e:
                        print(f"Error or timeout waiting for modal: {str(e)}")
                        result = False
                        feedback = "Error: Modal did not appear or was not visible."
            else:
                print("Sign-up button not found.")

            # direct rendering for gardena because the homepage blocks the webcrawler
            if "https://www.gardena.com/de" in self.url:
                newsletter_url = "https://www.gardena.com/de/c/gardena-newsletter"
                print(f"Detected 'gardena.', redirecting to newsletter URL: {newsletter_url}")
                await page.goto(newsletter_url)
                await page.wait_for_load_state('networkidle')

                
                result, feedback = await self.perform_age_limitation_check(page)
                await browser.close()
                return result, feedback
                        
            


            # direct rendering for vileda because the homepage blocks the webcrawler
            if "https://www.vileda.de" in self.url:
                newsletter_url = "https://www.vileda.de/newsletter"
                print(f"Detected 'vileda.de', redirecting to newsletter URL: {newsletter_url}")
                await page.goto(newsletter_url)
                await page.wait_for_load_state('networkidle')

                
                result, feedback = await self.perform_age_limitation_check(page)
                await browser.close()
                return result, feedback

            # General case: Load the given URL and check for Age Limitations
            await page.goto(self.url, timeout=90000)
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            current_url =page.url
            if current_url != self.url:
               print(f"Redirected to: {current_url}")
               self.url = current_url

            # Check the main page for age restrictions
            result, feedback = await self.perform_age_limitation_check(page)
            if result:
                await browser.close()
                return result, feedback

            # Search for relevant links like Newsroom or Newsletter
            await page.wait_for_selector('a', timeout=15000)
            links = await page.query_selector_all('a')
            for link in links:
                href = await link.get_attribute('href')
                if href:
                    full_url = urljoin(self.url, href)

                    # Ignore legal, privacy, and terms links
                    ignore_keywords = ["impressum", "datenschutz", "agb", "privacy", "legal"]
                    if any(ignored in full_url.lower() for ignored in ignore_keywords):
                         print(f" Ignoring irrelevant link: {full_url}")
                         continue  # Skip irrelevant links
                    
                    if any(keyword in full_url.lower() for keyword in ["newsroom", "press", "enews", "newsletter", "newsletter-registrierung"]):
                        print(f"Found a relevant link: {full_url}")
                        await page.goto(full_url)
                        await page.wait_for_load_state('networkidle')

                         # Check the linked page for age restrictions
                        result, feedback = await self.perform_age_limitation_check(page)
                        if result:
                            await browser.close()
                            return result, feedback

            # Standard feedback if nothing is found
            feedback = "No Age Limitation or relevant Newsletter link found."
            result = False

        except Exception as e:
            result = False
            feedback = f"Error: No Newsletter found."

        await browser.close()
        return result, feedback


    async def perform_age_limitation_check(self, page):
        elements_to_check = await page.query_selector_all('a, button, input, div, span')

        for element in elements_to_check:
            try:
                if not await element.is_visible():
                    continue
                # Extract text and relevant attributes
                text = await element.inner_text() or ''
                aria_label = await element.get_attribute('aria-label') or ''
                placeholder = await element.get_attribute('placeholder') or ''
                full_text = f"{text} {aria_label} {placeholder}".strip()

                # Check for matches in age restriction phrases
                for phrase in self.age_restriction_phrases:
                    if phrase.lower() in full_text.lower():
                        return True, f"Age Limitation found: '{phrase}'"
            except Exception:
                continue

        # If no Age Limitation is found
        return False, "No Age Limitation or Newsletter found"

    async def check_for_sign_up(self, page):
        # Look for all potential Sign-Up related elements
        elements_to_check = await page.query_selector_all('a, button')

        for element in elements_to_check:
            try:
                text = await element.inner_text() or ''
                aria_label = await element.get_attribute('aria-label') or ''
                placeholder = await element.get_attribute('placeholder') or ''
                full_text = f"{text} {aria_label} {placeholder}".strip()

                # Check if the text matches Sign-Up related phrases
                if any(phrase in full_text.lower() for phrase in ["sign up", "subscribe", "join"]):
                    href = await element.get_attribute('href')
                    if href:
                        sign_up_url = urljoin(page.url, href)
                        print(f"Found Sign-Up link: {sign_up_url}")
                        await page.goto(sign_up_url)
                        await page.wait_for_load_state('networkidle')
                        # Perform Age Limitation check on the redirected page
                        return await self.perform_age_limitation_check(page)
            except Exception:
                continue

        return False, "No Sign-Up button or link found"

async def main():
    url = "https://www.de.weber"  # Replace with the URL you want to check
    checker = AgeLimitation(url)
    result, feedback = await checker.check_age_limitation()
    print("Result:", result)
    print("Feedback:", feedback)

if __name__ == "__main__":
    asyncio.run(main())



