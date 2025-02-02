import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright

class AsyncImpressumVisibilityChecker:
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

            # Links auf der Seite extrahieren
            links = soup.find_all('a', href=True)
            high_priority_keywords = ['impressum', 'imprint', 'legal']

            parsed_base_url = urlparse(base_url)
            base_domain = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}"

            # Suche nach Links mit hoher Priorität
            for link in links:
                href = link['href'].lower()
                if any(keyword in href for keyword in high_priority_keywords):
                    if href.startswith('/'):  # Relativer Pfad
                        imprint_url = urljoin(base_url, href)
                        print(f"Found imprint URL (relativ): {imprint_url}")
                        return imprint_url
                    elif href.startswith(base_domain):  # Interner absoluter Link
                        print(f"Found imprint URL  (absolut): {href}")
                        return href

        except requests.RequestException as e:
            print(f"Error retrieving the page: {e}")
        return None  # Keine Impressum-URL gefunden

    async def check_scrollable(self, base_url):
        # Impressum-URL ermitteln
        imprint_url = self.find_imprint_url(base_url)
        
        if not imprint_url:
            feedback = f"<strong>Impressum Visibility Check for {base_url}</strong><br>"
            feedback += "- <strong>Error:</strong> No 'Impressum' link found on the main page.<br>"
            return False, feedback
        
        # Debug: Impressum-URL anzeigen
        print(f"Imprint URL used: {imprint_url}")

        feedback = f"<strong>Impressum Visibility Check for {imprint_url}</strong><br>"
        is_compliant = True

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Gehe zur Impressum-URL
                await page.goto(imprint_url, timeout=60000)
                await page.wait_for_selector("body", timeout=10000)

                feedback += "- Navigated to the 'Impressum' page.<br>"

                # Prüfe auf horizontalen Scrollbalken
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

                # Vertikale Scrollprüfung mit zusätzlichen Messwerten
                scroll_step = 600  # Fester Scroll-Schritt
                max_scrolls = 3  # Maximal 3 Scroll-Schritte
                impressum_visible = False  # Standardwert: nicht sichtbar

                # Locator für "Impressum"
                impressum_locator = page.locator("xpath=//*[contains(text(), 'Impressum')]")

                # Zusätzliche Messwerte berechnen
                page_height = await page.evaluate("document.body.scrollHeight")
                viewport_height = await page.evaluate("window.innerHeight")
   
                feedback += f"- <strong>Info:</strong> The total side height is {page_height} Pixel.<br>"
                feedback += f"- <strong>Info:</strong> The height of the viewport is {viewport_height} Pixel.<br>"

            finally:
                await browser.close()

        return is_compliant, feedback
