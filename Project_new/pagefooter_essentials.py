import asyncio
import aiohttp
from bs4 import BeautifulSoup

class AsyncFooterValidator:
    def __init__(self):
        self.session = None

    async def fetch(self, url: str):
        """Fetch the HTML content of the given URL."""
        async with self.session.get(url) as response:
            return await response.text()

    async def check_link(self, page_url: str, keywords: list, href_patterns: list = None):
     """
    Check if a link exists on the page that matches the given keywords, href patterns, or onclick attributes.

    Args:
        page_url (str): The URL of the page to check.
        keywords (list): A list of keywords to match against the link text.
        href_patterns (list, optional): A list of substrings or regex patterns to match the href attribute.

    Returns:
        bool: True if a matching link is found, False otherwise.
    """
     html = await self.fetch(page_url)
     soup = BeautifulSoup(html, "html.parser")
     links = soup.find_all("a")

    # Debug: Log all found links
     print(f"Debug: Links found on {page_url}")

     for link in links:
        link_text = link.text.strip().lower()
        link_href = link.get("href", "").lower()
        link_onclick = link.get("onclick", "").lower()  # Fetch the onclick attribute

        # Check if the link text contains any of the keywords
        if any(keyword.lower() in link_text for keyword in keywords):
            # If href_patterns are provided, check if the href matches any of them
            if href_patterns:
                if any(pattern.lower() in link_href for pattern in href_patterns):
                    print(f"Debug: Match found via href for keyword: {link_text}")
                    return True
                elif link_onclick:  # If no href match, check if onclick exists
                    print(f"Debug: Match found via onclick for keyword: {link_text}")
                    return True
            else:
                print(f"Debug: Match found via text for keyword: {link_text}")
                return True
     print("Debug: No matching link found.")
     return False


    async def check_footer_links(self, base_url: str):
        """
        Check the presence of footer links (Imprint, privacy policy, Cookies) on the given page.

        Args:
            base_url (str): The base URL to check.

        Returns:
            dict: A dictionary with the results for each link.
        """
        async with aiohttp.ClientSession() as session:
            self.session = session

            # Define the keywords and href patterns for each type of link
            footer_checks = {
                "imprint": {
                    "keywords": ["impressum", "imprint"],
                    "href_patterns": ["/impressum", "impressum", "imprint"]
                },
                "privacy policy": {
                    "keywords": ["datenschutz", "privacy policy", "datenschutzerklärung"],
                    "href_patterns": ["/datenschutz", "privacy", "datenschutzerklärung"]
                },
                "cookie": {
                    "keywords": ["cookie", "cookie-einstellungen", "cookies", "Cookie Einstellungen", "cookie settings"],
                    "href_patterns": ["/cookies", "cookie", "optanon.toggleinfo", "#uc-central-modal-show"]
                }
            }

            # Create tasks for each check
            tasks = {
                name: self.check_link(base_url, data["keywords"], data["href_patterns"])
                for name, data in footer_checks.items()
            }

            # Run all tasks and gather results
            results = await asyncio.gather(*tasks.values())
            
            # Debug: Print the results
            for name, result in zip(tasks.keys(), results):
                print(f"Debug: {name.capitalize()} link presence: {result}")

            # Return results as a dictionary
            return {name: result for name, result in zip(tasks.keys(), results)}
