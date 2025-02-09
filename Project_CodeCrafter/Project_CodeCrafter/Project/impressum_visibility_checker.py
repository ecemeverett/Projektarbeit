import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright

class AsyncImpressumVisibilityChecker:

#This method attempts to locate the URL of the imprint page by analyzing the links on the given base URL. 
#It looks for keywords such as "impressum", "imprint", and "legal" in the href attributes of <a> tags.    
    def find_imprint_url(self, base_url):
        """
        Try to find the imprint URL on the base URL.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/'
            }
            response = requests.get(base_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract links on the page
            links = soup.find_all('a', href=True)
            high_priority_keywords = ['impressum', 'imprint', 'general-imprint']
            low_priority_keywords = ['terms', 'about', 'contact', 'legal', 'legal-information']

            parsed_base_url = urlparse(base_url)
            base_domain = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}"

            # Search for links with high priority
            for link in links:
                href = link['href'].lower()
                if any(keyword in href for keyword in high_priority_keywords):
                    if href.startswith('/'):  # Relative path
                        imprint_url = urljoin(base_url, href)
                        print(f"Found imprint URL (relativ): {imprint_url}")
                        return imprint_url
                    elif href.startswith(base_domain):  # Internal absolute link
                        print(f"Found imprint URL  (absolut): {href}")
                        return href
                    
                        # Search for links with low priority
            for link in links:
                href = link['href'].lower()
                if any(keyword in href for keyword in low_priority_keywords):
                    if href.startswith('/'):  # Relative path
                        return urljoin(base_url, href)
                    elif href.startswith('http'):  # External Link
                        return href        

        except requests.RequestException as e:
            print(f"Error retrieving the page: {e}")
        return None  # No imprint URL found
    
    async def check_scrollable(self, base_url):
        # Determine imprint URL
        imprint_url = self.find_imprint_url(base_url)
        
        if not imprint_url:
            feedback = f"<strong>Imprint Visibility Check for {base_url}</strong><br>"
            feedback += "- <strong>Error:</strong> No 'Imprint' link found on the main page.<br>"
            return False, feedback
        
        # Debug: Show imprint URL
        print(f"Imprint URL used: {imprint_url}")

        feedback = f"<strong>Imprint Visibility Check for {imprint_url}</strong><br>"
        is_compliant = True

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Go to the imprint URL
                await page.goto(imprint_url, timeout=60000)
                await page.wait_for_selector("body", timeout=10000)

                feedback += "- Navigated to the 'Imprint' page.<br>"

                # Check for horizontal scrollbars
                horizontal_scroll = await page.evaluate(
                    """() => {
                        const body = document.querySelector('body');
                        return body.scrollWidth > body.clientWidth;
                    }"""
                )

                if horizontal_scroll:
                    feedback += "- <strong>Warning:</strong> Horizontal scrollbar detected.<br>"
                    is_compliant = False
                else:
                    feedback += "- No horizontal scrollbar detected.<br>"

                # Calculate additional measured values
                page_height = await page.evaluate("document.body.scrollHeight")
                viewport_height = await page.evaluate("window.innerHeight")
   
                feedback += f"- <strong>Info:</strong> The total side height is {page_height} Pixel.<br>"
                feedback += f"- <strong>Info:</strong> The height of the viewport is {viewport_height} Pixel.<br>"

            finally:
                await browser.close()

        return is_compliant, feedback