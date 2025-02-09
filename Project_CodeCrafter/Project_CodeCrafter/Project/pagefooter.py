
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

#Initializes the FooterLinkChecker by setting main_url, visited_urls, and footer_links.
class FooterLinkChecker:
    def __init__(self):
        self.main_url = None
        self.visited_urls = set()
        self.footer_links = set()

#Fetches the HTML content of a URL asynchronously. Returns the HTML text or None on error.
    async def fetch_page(self, url, session):
        try:
            async with session.get(url, timeout=10) as response:
                if response.status >= 400:
                    print(f"Error fetching {url}: {response.status}")
                    return None
                return await response.text()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

#Extracts links from the page footer and adds valid ones to footer_links
    def extract_footer_links(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        # Search the footer flexibly
        footer = soup.find('footer') or soup.find(class_='footer') or soup.find(id='footer')
        if not footer and soup.body:
            footer = soup.body.find_all(recursive=False)[-1]

        if footer:
            links = footer.find_all('a', href=True)
            for link in links:
                href = urljoin(self.main_url, link['href'])

                # Filter irrelevant links
                if href.startswith(('tel:', 'javascript:', '#')) or len(href.strip()) == 0:
                    continue

                # Normalize URLs
                parsed_url = urlparse(href)
                if not parsed_url.scheme or not parsed_url.netloc:
                    continue

                self.footer_links.add(href)

#Collects all subpages from the main page up to the specified depth.
    async def get_all_subpages(self, session, depth=2):
        if depth == 0:
            return set()

        html = await self.fetch_page(self.main_url, session)
        subpages = set()
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            links = soup.find_all('a', href=True)
            for link in links:
                href = urljoin(self.main_url, link['href'])
                if href not in self.visited_urls and self.main_url in href:
                    subpages.add(href)
                    self.visited_urls.add(href)

            for subpage in list(subpages):
                subpages.update(await self.get_all_subpages(session, depth - 1))
        return subpages

#Checks all footer links for errors and returns a list of invalid links.
    async def check_links(self, session):
        invalid_links = []
        tasks = []
        for link in self.footer_links:
            tasks.append(self.check_link(link, session))

        results = await asyncio.gather(*tasks)
        for link, status in results:
            if status is not None:
                invalid_links.append((link, status))
        return invalid_links

#Checks if a link is reachable and returns the link with its status.
    async def check_link(self, link, session):
        try:
            async with session.get(link, timeout=10) as response:
                if response.status >= 400:
                    return link, response.status
        except Exception as e:
            return link, str(e)
        return link, None

#Runs the full process: collects subpages, extracts footer links, and checks their validity.
    async def check_footer_links_on_all_pages(self, url):
        self.main_url = url
        async with aiohttp.ClientSession() as session:
            subpages = await self.get_all_subpages(session)
            for subpage in subpages:
                if subpage not in self.visited_urls:
                    html = await self.fetch_page(subpage, session)
                    if html:
                        self.extract_footer_links(html)
                    self.visited_urls.add(subpage)

            invalid_links = await self.check_links(session)
            return [link for link, _ in invalid_links]
