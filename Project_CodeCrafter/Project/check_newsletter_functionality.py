import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright
import httpx


class NewsletterFunctionality:
    def __init__(self, url=None):
        self.url = url # URL of the page to be checked for newsletter links
         # Dictionary of expected links with their corresponding English and German terms
        self.expected_links = {
            "Right of Withdrawal": ["Widerrufsrecht", "Right of Revocation"],
            "Imprint": ["Impressum", "Imprint"],
            "Data Protection Information": ["Datenschutzinformationen", "Datenschutz", "Data Protection Information", "Datenschutzerklärung", "Privacy Policy"],
            "Advertising Partners": ["Werbepartner", "Advertising Partners"]
        }

    async def check_newsletter_functionality(self):
        """
        This method checks the newsletter functionality on a given URL by verifying 
        the existence of expected links and their validity (HTTP status).
        """
        result = {} # Stores the result of the link check (True or False)
        feedback = {} # Stores detailed feedback about the status of each link
        detailed_feedback = []  # List to store results for detailed feedback (used for PDF generation)
        try:
         async with async_playwright() as p: 
            browser = await p.chromium.launch(headless=True) 
            page = await browser.new_page()

            # Special case handling for "loreal-paris.de"
            if "https://www.loreal-paris.de" in self.url:
                newsletter_url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
                print(f"Special case detected, redirecting to: {newsletter_url}")
                self.url = newsletter_url
            
            # Special case handling for "hansgrohe"
            if "https://www.hansgrohe.de" in self.url:
                newsletter_url = "https://www.hansgrohe.de/#interest-form"
                print(f"Special case detected, redirecting to: {newsletter_url}")
                self.url = newsletter_url

            # Special case handling for "tesa.com"
            if "https://www.tesa.com" in self.url:
                newsletter_url = "https://www.tesa.com/de-de/buero-und-zuhause/do-it-yourself-magazin/newsletter"
                print(f"Special case detected, redirecting to: {newsletter_url}")
                self.url = newsletter_url

            # direct rendering for vileda because the homepage blocks the webcrawler
            if "https://www.krombacher.de" in self.url:
                newsletter_url = "https://www.krombacher.de/die-brauerei/newsletter-anmeldung"
                print(f"Special case detected, redirecting to: {newsletter_url}")
                self.url = newsletter_url

            # Special case handling for "climeworks.com"
            if "https://www.climeworks.com" in self.url:
                newsletter_url = "https://info.climeworks.com/newsletter-subscription-form"
                print(f"Special case detected, redirecting to: {newsletter_url}")
                self.url = newsletter_url

            try: 
                print(f"Navigating to: {self.url}") # Navigate to the final URL after all redirection
                await page.goto(self.url, timeout=60000)  # Visit the URL and wait for the page to load
                await page.wait_for_load_state('networkidle')  # Ensure the page has finished loading

                # If the URL is already a newsletter page, check the links on it
                if any(phrase.lower() in self.url.lower() for phrase in ["newsletter", "subscribe", "email", "signup"]):
                    print("Detected as a newsletter page. Proceeding with the functionality check.")
                    result, feedback, detailed_feedback = await self.perform_functionality_check(page)

                else: # If the URL is not a newsletter page, search for dynamic links related to newsletters
                    print("Searching for relevant links to dynamic pages...")
                    links = await page.query_selector_all('a') # Get all <a> tags (links) on the page
                    for link in links:
                        try:
                            href = await link.get_attribute('href') # Get the href attribute of the link
                            if href:
                                full_url = urljoin(self.url, href) # Join the base URL with the href to get the full URL

                                #  Ignore imprint, privacy policy, and terms & conditions links.
                                ignore_keywords = ["impressum", "datenschutz", "agb", "privacy", "legal"]
                                if any(ignored in full_url.lower() for ignored in ignore_keywords):
                                     print(f" Ignoring irrelevant link: {full_url}")
                                     continue   # Skip this link and move on to the next one
                                
                                # If the link contains keywords related to newsletters, subscribe, or email, proceed with the check
                                if any(keyword in full_url.lower() for keyword in ["newsletter", "subscribe", "email", "signup", "newsletter-registrierung"]):
                                    print(f"Redirecting to dynamic newsletter-related page: {full_url}")
                                    await page.goto(full_url) # Navigate to the found newsletter-related page
                                    await page.wait_for_load_state('networkidle') # Wait for it to fully load
                                    result, feedback, detailed_feedback = await self.perform_functionality_check(page) # Check the links on this page
                                    break # Stop further searching for links since we've found a valid one
                        except Exception as e:
                            print(f"Error processing dynamic link: {e}") # If an error occurs, skip this link and continue
                            continue

                    # If no suitable links were found, process the main page
                    if not result:
                        print("No dynamic links found. Checking the main page.")
                        result, feedback, detailed_feedback = await self.perform_functionality_check(page)

            except Exception as e:
                feedback["error"] = f"Error loading the URL {self.url}: {str(e)}" # If there's an error while loading the page, store the error

        except Exception as e:
         feedback["error"] = f"Error while checking newsletter functionality: {str(e)}" # If an error occurs during the overall process, store the error

        # Format feedback for PDF
        formatted_feedback = self.format_feedback_for_pdf(detailed_feedback) # Format feedback for inclusion in a PDF
        return result, formatted_feedback # Return the result and formatted feedback


    async def perform_functionality_check(self, page):
       """
       This method performs the actual check of the newsletter-related links on the page.
       It looks for links matching the expected terms and verifies their validity by checking their HTTP status.
       """
       result = {} # Stores the overall result (True or False) for each expected link category
       feedback = {} # Stores detailed feedback for each expected link
       detailed_feedback = []  # Stores the results for detailed reporting (PDF generation)
       found_links = set()  # A set to track found links to avoid checking the same link multiple times

       for link_name, terms in self.expected_links.items():
           try:
               term_found = []  # List to store found links for the current term
               for term in terms:
                   print(f"Searching for links or content related to: {term}")

                   # Search for <a> or href tags containing the term directly in their text
                   link = await page.query_selector(f'a:has-text("{term}")') or await page.query_selector(f'a[href*="{term.lower()}"]')
                   if link:
                       href = await link.get_attribute("href") # Get the link's href attribute
                       link_text = await link.inner_text() # Get the text inside the link
                       if not href or "javascript:void" in href:
                        continue  # Skip invalid links (e.g., JavaScript-only links)

                       full_url = urljoin(self.url, href)   # Get the full URL by joining base URL with href

                       # Avoid duplicate links by checking if it has been found before
                       if full_url not in found_links:
                           found_links.add(full_url)  # Add to the set of found links
                           term_found.append({
                               "term": term,
                               "href": full_url,
                               "link_text": link_text
                           })

               # Check the found links for each term
               link_status = []
               for link_info in term_found:
                   href = link_info.get("href")
                   if href:
                       async with httpx.AsyncClient() as client:
                           try:
                               response = await client.get(href, timeout=10) # Make an HTTP GET request
                               status_code = response.status_code # Get the status code of the response
                               link_status.append({
                                   "term": link_info.get("term"),
                                   "link_text": link_info.get("link_text"),
                                   "href": href,
                                   "status": "Valid" if status_code == 200 else f"Invalid (HTTP {status_code})"
                               })
                           except Exception as e:
                               link_status.append({
                                   "term": link_info.get("term"),
                                   "link_text": link_info.get("link_text"),
                                   "href": href,
                                   "status": f"Error: {str(e)}"
                               })

               # Store the results of the check for this link
               if link_status:
                   result[link_name] = True
                   feedback[link_name] = link_status
                   detailed_feedback.append({
                       "link_name": link_name,
                       "results": link_status
                   })
               else:
                   result[link_name] = False
                   feedback[link_name] = f"No matching links found for {link_name}."
                   detailed_feedback.append({
                       "link_name": link_name,
                       "results": "No matching links found."
                   })

           except Exception as e:
               print(f"Error while checking '{link_name}': {e}") # Handle errors during the link check
               result[link_name] = False
               feedback[link_name] = f"Error while checking {link_name}: {str(e)}"
               detailed_feedback.append({
                   "link_name": link_name,
                   "results": f"Error while checking {link_name}: {str(e)}"
               })

       return result, feedback, detailed_feedback


    def format_feedback_for_pdf(self, detailed_feedback):
     """
     This method formats the detailed feedback to be included in a PDF report.
     It generates HTML content that can be later rendered into a PDF.
     """

     formatted_feedback = "<h2>Newsletter Functionality Check</h2>"
     for entry in detailed_feedback:
        link_name = entry["link_name"]
        results = entry["results"]

        formatted_feedback += f"<h3>{link_name}</h3>"
        if isinstance(results, list):
            for result in results:
                formatted_feedback += f"""
                <p style="margin: 0; padding: 2px 0; font-size: 12px;"><strong>Term:</strong> {result.get('term', 'N/A')}</p>
                <p style="margin: 0; padding: 2px 0; font-size: 12px;"><strong>Link Text:</strong> {result.get('link_text', 'N/A')}</p>
                <p style="margin: 0; padding: 2px 0; font-size: 12px;"><strong>URL:</strong> {result.get('href', 'N/A')}</p>
                <p style="margin: 0; padding: 2px 0; font-size: 12px;"><strong>Status:</strong> {result.get('status', 'N/A')}</p>
                <hr style="margin: 5px 0;">
                """
        else:
            formatted_feedback += f"<p style='margin: 0; padding: 2px 0; font-size: 12px;'>{results}</p><hr style='margin: 5px 0;'>"

     return formatted_feedback



"""Function to test the Newsletter Functionality exclusively"""
async def main():
    url = "https://www.climeworks.com"  # URL of the example page to be checked
    checker = NewsletterFunctionality(url)
    result, feedback = await checker.check_newsletter_functionality()

    print("\nResults of Newsletter Functionality Check:")
    print(f"Result: {result}")
    print(f"Feedback: {feedback}")


if __name__ == "__main__":
    asyncio.run(main())
