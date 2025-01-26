import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright
import httpx


class NewsletterFunctionality:
    def __init__(self, url=None):
        self.url = url
        # Expected terms (English and German)
        self.expected_links = {
            "Right of Withdrawal": ["Widerrufsrecht", "Right of Revocation"],
            "Imprint": ["Impressum", "Imprint"],
            "Data Protection Information": ["Datenschutzinformationen", "Data Protection Information"],
            "Advertising Partners": ["Werbepartner", "Advertising Partners"]
        }

    async def check_newsletter_functionality(self):
        """
        Check the newsletter functionality by verifying the existence and validity of expected links.
        """
        result = {}
        feedback = {}
        detailed_feedback = []  # For PDF generation
        try:
         async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Special case handling for "loreal-paris.de"
            if "loreal-paris.de" in self.url:
                newsletter_url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
                print(f"Special case detected, redirecting to: {newsletter_url}")
                self.url = newsletter_url

            try:
                print(f"Navigating to: {self.url}")
                await page.goto(self.url, timeout=60000)
                await page.wait_for_load_state('networkidle')

                # Check if the URL is already a newsletter page
                if any(phrase.lower() in self.url.lower() for phrase in ["newsletter", "subscribe", "email", "signup"]):
                    print("Detected as a newsletter page. Proceeding with the functionality check.")
                    result, feedback, detailed_feedback = await self.perform_functionality_check(page)
                else:
                    # Search for dynamic links such as "newsroom", "press", or "newsletter"
                    print("Searching for relevant links to dynamic pages...")
                    links = await page.query_selector_all('a')
                    for link in links:
                        try:
                            href = await link.get_attribute('href')
                            if href:
                                full_url = urljoin(self.url, href)
                                if any(keyword in full_url.lower() for keyword in ["newsroom", "press", "enews", "newsletter"]):
                                    print(f"Redirecting to dynamic newsletter-related page: {full_url}")
                                    await page.goto(full_url)
                                    await page.wait_for_load_state('networkidle')
                                    result, feedback, detailed_feedback = await self.perform_functionality_check(page)
                                    break
                        except Exception as e:
                            print(f"Error processing dynamic link: {e}")
                            continue

                    # If no suitable links were found, process the main page
                    if not result:
                        print("No dynamic links found. Checking the main page.")
                        result, feedback, detailed_feedback = await self.perform_functionality_check(page)

            except Exception as e:
                feedback["error"] = f"Error loading the URL {self.url}: {str(e)}"

        except Exception as e:
         feedback["error"] = f"Error while checking newsletter functionality: {str(e)}"

        # Format feedback for PDF
        formatted_feedback = self.format_feedback_for_pdf(detailed_feedback)
        return result, formatted_feedback

    async def perform_functionality_check(self, page):
       """
       Perform the functionality check for the expected links on the page.
       """
       result = {}
       feedback = {}
       detailed_feedback = []  # For detailed results in PDF
       for link_name, terms in self.expected_links.items():
           try:
               found_links = []
               for term in terms:
                   print(f"Searching for links or content related to: {term}")

                   # Search for <a> tags containing the term directly in their text
                   link = await page.query_selector(f'a:has-text("{term}")')
                   if link:
                       href = await link.get_attribute("href")
                       link_text = await link.inner_text()
                       found_links.append({"term": term, "href": href, "link_text": link_text})

               # Check the found links
               link_status = []
               for link_info in found_links:
                   href = link_info.get("href")
                   if href:
                       async with httpx.AsyncClient() as client:
                           try:
                               response = await client.get(href, timeout=10)
                               status_code = response.status_code
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

               # Save results for this term
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
               print(f"Error while checking '{link_name}': {e}")
               result[link_name] = False
               feedback[link_name] = f"Error while checking {link_name}: {str(e)}"
               detailed_feedback.append({
                   "link_name": link_name,
                   "results": f"Error while checking {link_name}: {str(e)}"
               })

       return result, feedback, detailed_feedback

    def format_feedback_for_pdf(self, detailed_feedback):
        """
        Format the feedback for inclusion in the PDF report.
        """
        formatted_feedback = "<h2>Newsletter Functionality Check</h2>"
        for entry in detailed_feedback:
            link_name = entry["link_name"]
            results = entry["results"]

            formatted_feedback += f"<h3>{link_name}</h3>"
            if isinstance(results, list):
                for result in results:
                    formatted_feedback += f"""
                    <p><strong>Term:</strong> {result.get('term', 'N/A')}</p>
                    <p><strong>Link Text:</strong> {result.get('link_text', 'N/A')}</p>
                    <p><strong>URL:</strong> {result.get('href', 'N/A')}</p>
                    <p><strong>Status:</strong> {result.get('status', 'N/A')}</p>
                    <hr>
                    """
            else:
                formatted_feedback += f"<p>{results}</p><hr>"

        return formatted_feedback


 


# Example usage of the class
async def main():
    url = "https://www.pg.com"  # URL of the page to be checked
    checker = NewsletterFunctionality(url)
    result, feedback = await checker.check_newsletter_functionality()

    print("\nResults of Newsletter Functionality Check:")
    print(f"Result: {result}")
    print(f"Feedback: {feedback}")


if __name__ == "__main__":
    asyncio.run(main())
