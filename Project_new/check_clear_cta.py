import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright

class ClearCTA:
    def __init__(self, url, newsletter_phrases=None):
        if not url:
            raise ValueError("The URL cannot be empty")

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url # Ensure the URL has a valid protocol

        self.url = url
        # Define newsletter-related keywords in English and German
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
        criteria_met = False
        feedback = "CTA not found or not recognizable as a clear call-to-action."

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Special handling for loreal-paris.de
                if "https://www.loreal-paris.de" in self.url:
                    newsletter_url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
                    print(f"Detected 'loreal-pars.de', redirecting to newsletter URL: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle')

                    
                    criteria_met, feedback = await self.perform_cta_check(page)
                    await browser.close()
                    return criteria_met, feedback
                   
                # Special handling for tesa
                if "https://www.tesa.com" in self.url:
                    newsletter_url = "https://www.tesa.com/de-de/buero-und-zuhause/do-it-yourself-magazin/newsletter"
                    print(f"Detected 'tesa', redirecting to newsletter URL: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle')

                    
                    criteria_met, feedback = await self.perform_cta_check(page)
                    await browser.close()
                    return criteria_met, feedback
                
                # Special handling for krombacher
                if "https://www.krombacher.de" in self.url:
                    newsletter_url = "https://www.krombacher.de/die-brauerei/newsletter-anmeldung"
                    print(f"Detected 'krombacher.de', redirecting to newsletter URL: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle')

                    
                    criteria_met, feedback = await self.perform_cta_check(page)
                    await browser.close()
                    return criteria_met, feedback
                
                # Special handling for hansgrohe
                if "https://www.hansgrohe.de" in self.url:
                    newsletter_url = "https://www.hansgrohe.de/#interest-form"
                    print(f"Detected 'hansgrohe.de', redirecting to newsletter URL: {newsletter_url}")
                    await page.goto(newsletter_url)
                    await page.wait_for_load_state('networkidle')

                    
                    criteria_met, feedback = await self.perform_cta_check(page)
                    await browser.close()
                    return criteria_met, feedback
                

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
            
                        # After the redirection, check for the CTA again
                        criteria_met, feedback = await self.perform_cta_check(page)
                        await browser.close()
                        return criteria_met, feedback
                 except Exception as e:
                    feedback = f"Error clicking the button for newsletter: {str(e)}"
                    await browser.close()
                    return False, feedback

                # General case: Load the given URL
                try:
                    await page.goto(self.url, timeout=60000)
                    await page.wait_for_load_state('networkidle')
                except Exception as e:
                    feedback = f"Error loading the URL: {self.url}, Details: {str(e)}"
                    await browser.close()
                    return False, feedback

                # Check if the URL already indicates a newsletter page
                if any(phrase.lower() in self.url.lower() for phrase in ["newsletter", "subscribe", "email", "signup", "newsletter-registrierung"]):
                    criteria_met, feedback = await self.perform_cta_check(page)
                    await browser.close()
                    return criteria_met, feedback

                # Look for relevant links leading to a newsletter or subscription page
                links = await page.query_selector_all('a')
                for link in links:
                    try:
                        href = await link.get_attribute('href')
                        if href:
                            full_url = urljoin(self.url, href)

                            # Ignore legal, privacy, and terms links
                            ignore_keywords = ["impressum", "datenschutz", "agb", "privacy", "legal"]
                            if any(ignored in full_url.lower() for ignored in ignore_keywords):
                               print(f" Ignoring irrelevant link: {full_url}")
                               continue  # Skip irrelevant links
                        
                            if any(keyword in full_url.lower() for keyword in ["newsroom", "press", "enews", "newsletter", "newsletter-registrierung"]):
                                await page.goto(full_url)
                                await page.wait_for_load_state('networkidle')
                                criteria_met, feedback = await self.perform_cta_check(page)
                                await browser.close()
                                return criteria_met, feedback
                    except Exception:
                        continue

                 # If no suitable link was found, check the homepage directly
                criteria_met, feedback = await self.perform_cta_check(page)

            except Exception as e:
                feedback = f"Error navigating to URL {self.url}: {str(e)}"

            await browser.close()
        return criteria_met, feedback
    
    async def perform_cta_check(self, page):
        """Checks the page for any clear CTA related to newsletter subscriptions."""
        elements_to_check = await page.query_selector_all('a, button, input, div, span')

        for element in elements_to_check:
            try:
                text = await element.inner_text() or ''
                placeholder = await element.get_attribute('placeholder') or ''
                aria_label = await element.get_attribute('aria-label') or ''
                title = await element.get_attribute('title') or ''
                value = await element.get_attribute('value') or ''
                full_text = f"{text} {placeholder} {aria_label} {title} {value}".strip()

                
                words = full_text.split()
                for word in words:
                    if any(phrase.lower() == word.lower() for phrase in self.newsletter_phrases):
                        return True, f"Found CTA: '{word}'"
            except Exception:
                continue

        
        return False, "No clear CTA found or no newsletter found"

async def main():
    """Main function to test the CTA checker."""
    url = "https://www.beiersdorf.de"
    checker = ClearCTA(url)
    result, feedback = await checker.check_clear_cta()
    print("Result:", result)
    print("Feedback:", feedback)

if __name__ == "__main__":
    asyncio.run(main())

