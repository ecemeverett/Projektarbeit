import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright

class ClearCTA:
    def __init__(self, url, newsletter_phrases=None):
        """
        Initializes the ClearCTA class with the URL to check and an optional list of newsletter-related phrases.
        If no phrases are provided, it defaults to a list of English and German phrases related to newsletters.

        :param url: The URL to check for newsletter-related clear CTAs
        :param newsletter_phrases: List of phrases to identify newsletter CTAs
        """
        if not url:
            raise ValueError("The URL cannot be empty") # Ensure URL is provided

        if not url.startswith(('http://', 'https://')): # Check if URL has a valid protocol
            url = 'https://' + url # Add https if protocol is missing

        self.url = url
        # Define a list of common English and German phrases related to newsletter signups
        self.newsletter_phrases = newsletter_phrases or [
            # English phrases
            "subscribe now", "join our newsletter", "sign up", "get updates",
            "newsletter signup", "subscribe", "subscribe to our newsletter", 
            "email alerts", "get emails", "sign up for updates", "newsletter"
            # German phrases
            "jetzt anmelden", "newsletter abonnieren", "anmelden", "erhalte updates",
            "newsletter-registrierung", "abonniere", "abonniere unseren newsletter", 
            "e-mail benachrichtigungen", "updates erhalten", "anmeldung", "registrieren", 
            "newsletter", "Melden"
        ]

    async def check_clear_cta(self):
        """
        Main method to check if the provided URL contains a clear call-to-action (CTA) for a newsletter.
        This method handles special cases for specific domains and also tries to identify relevant links and CTAs.
        
        :return: A tuple with a boolean indicating whether a clear CTA was found and a feedback message
        """
         
        criteria_met = False
        feedback = "CTA not found or not recognizable as a clear call-to-action." # Default feedback
        
        # Launch the browser with Playwright to start interaction with the page
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True) # Start a headless browser session
            page = await browser.new_page() # Open a new page in the browser

            try:
                # Handle special cases for specific websites
                # These are sites that may have a custom URL for their newsletter page
                # Therefore, some customer newsletters can be found dynamically, while others are accessed through hardcoding.

                # Special handling for loreal-paris.de
                if "https://www.loreal-paris.de" in self.url:
                    newsletter_url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
                    print(f"Special case detected, redirecting to: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle') # Wait until the page is fully loaded

                    
                    criteria_met, feedback = await self.perform_cta_check(page) # Check for CTA
                    await browser.close() # Close the browser session
                    return criteria_met, feedback
                   
                # Special handling for tesa website
                if "https://www.tesa.com" in self.url:
                    newsletter_url = "https://www.tesa.com/de-de/buero-und-zuhause/do-it-yourself-magazin/newsletter"
                    print(f"Special case detected, redirecting to: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle') # Wait until the page is fully loaded

                    
                    criteria_met, feedback = await self.perform_cta_check(page) # Check for CTA
                    await browser.close() # Close the browser session
                    return criteria_met, feedback
                
                # Special handling for krombacher website
                if "https://www.krombacher.de" in self.url:
                    newsletter_url = "https://www.krombacher.de/die-brauerei/newsletter-anmeldung"
                    print(f"Special case detected, redirecting to: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle') # Wait until the page is fully loaded 

                    
                    criteria_met, feedback = await self.perform_cta_check(page) # Check for CTA
                    await browser.close() # Close the browser session
                    return criteria_met, feedback
                
                # Special handling for hansgrohe website
                if "https://www.hansgrohe.de" in self.url:
                    newsletter_url = "https://www.hansgrohe.de/#interest-form"
                    print(f"Special case detected, redirecting to: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle') # Wait until the page is fully loaded

                    
                    criteria_met, feedback = await self.perform_cta_check(page) # Check for CTA
                    await browser.close() # Close the browser session
                    return criteria_met, feedback
                
                # Special handling for climeworks website
                if "https://climeworks.com" in self.url:
                    newsletter_url = "https://info.climeworks.com/newsletter-subscription-form"
                    print(f"Special case detected, redirecting to: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle') # Wait until the page is fully loaded

                    
                    criteria_met, feedback = await self.perform_cta_check(page) # Check for CTA
                    await browser.close() # Close the browser session
                    return criteria_met, feedback

                # General case: Load the given URL
                try:
                    await page.goto(self.url, timeout=60000) # Load the page with a timeout of 60 seconds
                    await page.wait_for_load_state('networkidle') # Wait for the page to load
                except Exception as e:
                    feedback = f"Error loading the URL: {self.url}, Details: {str(e)}"
                    await browser.close() # Close the browser if an error occurs
                    return False, feedback

                # If the URL itself suggests it is a newsletter page, perform a CTA check
                if any(phrase.lower() in self.url.lower() for phrase in ["newsletter", "subscribe", "email", "signup", "newsletter-registrierung"]):
                    criteria_met, feedback = await self.perform_cta_check(page)
                    await browser.close()
                    return criteria_met, feedback

                # Look for relevant links leading to a newsletter or subscription page
                links = await page.query_selector_all('a') # Get all anchor tags

                for link in links:
                    try:
                        href = await link.get_attribute('href') # Get the link's href attribute
                        if href:
                            full_url = urljoin(self.url, href) # Resolve relative URLs to absolute ones

                             # Skip links that are related to legal, privacy, or terms pages
                            ignore_keywords = ["impressum", "datenschutz", "agb", "privacy", "legal"]
                            if any(ignored in full_url.lower() for ignored in ignore_keywords):
                               print(f" Ignoring irrelevant link: {full_url}")
                               continue  # Skip this link if it's irrelevant
                        
                               # If the link contains keywords related to newsletters, visit that link
                            if any(keyword in full_url.lower() for keyword in ["enews", "subscribe", "email", "newsletter", "newsletter-registrierung"]):
                                await page.goto(full_url)
                                await page.wait_for_load_state('networkidle') # Wait for the page to load
                                criteria_met, feedback = await self.perform_cta_check(page)
                                await browser.close() # Close the browser session

                                return criteria_met, feedback
                    except Exception:
                        continue # If an error occurs while processing the link, continue with the next link

                # If no suitable link is found, check the homepage directlyy
                criteria_met, feedback = await self.perform_cta_check(page)

            except Exception as e:
                feedback = f"Error navigating to URL {self.url}: {str(e)}"

            await browser.close() # Ensure browser is closed after checking
        return criteria_met, feedback # Return the result and feedback
    
    async def perform_cta_check(self, page):
        """
        Checks the page for any clear call-to-action (CTA) related to newsletter subscriptions.
        It inspects various elements (e.g., buttons, links) to find phrases associated with signing up for newsletters.

        :param page: The Playwright page object to inspect
        :return: A tuple with a boolean indicating whether a CTA was found and a feedback message
        """
        # Select elements that might contain CTA phrases
        elements_to_check = await page.query_selector_all('a, button, input, div, span')

        # Loop through all elements and check their content for newsletter-related keywords
        for element in elements_to_check:
            try:
                # Extract the text and other relevant attributes (e.g., placeholder, title, aria-label)
                text = await element.inner_text() or ''
                placeholder = await element.get_attribute('placeholder') or ''
                aria_label = await element.get_attribute('aria-label') or ''
                title = await element.get_attribute('title') or ''
                value = await element.get_attribute('value') or ''
                full_text = f"{text} {placeholder} {aria_label} {title} {value}".strip() # Concatenate all text

                 # Check if any word in the element's text matches any newsletter-related phrase
                words = full_text.split()
                for word in words:
                    if any(phrase.lower() == word.lower() for phrase in self.newsletter_phrases):
                        return True, f"Found CTA: '{word}'"
            except Exception:
                continue # Skip any elements that cause errors while checking

        
        return False, "No clear CTA found or no newsletter found" # If no CTA or newsletter is found, return a default message

"""Function to test the CTA checker exclusively"""
async def main():
    
    url = "https://www.stadtwerke-heilbronn.de/swh/" 
    checker = ClearCTA(url)
    result, feedback = await checker.check_clear_cta()
    print("Result:", result)
    print("Feedback:", feedback)

if __name__ == "__main__":
    asyncio.run(main())


