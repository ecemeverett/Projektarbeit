import asyncio
import aiohttp
from bs4 import BeautifulSoup


class FooterLinkChecker:
    def __init__(self):
        self.main_url = None
        self.visited_urls = set()
        self.footer_links = set()

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

    def extract_footer_links(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        footer = soup.find('footer', class_='footer')
        if footer:
            links = footer.find_all('a', href=True)
            for link in links:
                href = link['href']
                if href.startswith('/'):
                    href = self.main_url.rstrip('/') + href
                self.footer_links.add(href)

    async def get_all_subpages(self, session):
        html = await self.fetch_page(self.main_url, session)
        subpages = set()
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if href.startswith('/') and not href.startswith('//'):
                    subpages.add(self.main_url.rstrip('/') + href)
                elif href.startswith(self.main_url):
                    subpages.add(href)
        return subpages

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

    async def check_link(self, link, session):
        try:
            async with session.head(link, timeout=10) as response:
                if response.status >= 400:
                    return link, response.status
        except Exception as e:
            return link, str(e)
        return link, None

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
