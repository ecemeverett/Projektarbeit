from flask import Flask, render_template, request
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import re

class ImpressumChecker:
    #Initializes the ImpressumChecker class and sets typical imprint paths that might be found on a website.
    def __init__(self):
        self.imprint_paths = ["/impressum", "/imprint", "/legal", "/legal-notice"]

    #This method attempts to find the URL of the imprint page on the base URL. It prioritizes links with keywords like "impressum", "imprint", and "legal". 
    #If no high-priority link is found, it looks for lower-priority keywords like "terms", "about", and "contact".
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
            mid_priority_keywords = ['terms', 'legal-notice', 'legal', 'legal-information']
            low_priority_keywords = ['about', 'contact', 'general']

            parsed_base_url = urlparse(base_url)
            base_domain = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}"

            # Search for links with high priority
            for link in links:
                href = link['href'].lower()
                if any(keyword in href for keyword in high_priority_keywords):
                    if href.startswith('/'):  # Relative path
                        return urljoin(base_url, href)
                    elif href.startswith('http') and base_domain in href:  # Check if link belongs to the same domain
                        return href

                                    # Search for links with mid priority
            for link in links:
                href = link['href'].lower()
                if any(keyword in href for keyword in mid_priority_keywords):
                    if href.startswith('/'):  # Relative path
                        return urljoin(base_url, href)
                    elif href.startswith('http'):  # External Link
                        return href 

            # Search for links with low priority
            for link in links:
                href = link['href'].lower()
                if any(keyword in href for keyword in low_priority_keywords):
                    if href.startswith('/'):  # Relative path
                        return urljoin(base_url, href)
                    elif href.startswith('http'):  # Allow only internal links
                        return href


        except requests.RequestException as e:
            print(f"Error retrieving the page: {e}")
        return None  # No imprint URL found

    def normalize_text(self, text):
        """
        Normalizes text for comparison (lower case, no special characters, no multiple spaces).
        """
        text = re.sub(r'\s+', ' ', text)  # Remove multiple spaces
        text = re.sub(r'[^\w\s]', '', text)  # Remove special characters
        return text.lower().strip()

    def check_terms(self, url, terms):
        """
        Checks whether certain terms are contained in the imprint text.
        """
        # Step 1: Find the imprint URL
        imprint_url = self.find_imprint_url(url)
        print(f"Found imprint URL: {imprint_url}")
        if not imprint_url:
            print(f"No imprint URL found for {url}.")
            return None, {}, False, False  # No imprint URL found

        try:
            # Step 2: Retrieve HTML of the imprint page
            response = requests.get(imprint_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract the entire text of the page
            page_text = soup.get_text(separator=' ').lower()
        except requests.RequestException as e:
            print(f"Error retrieving the imprint page {imprint_url}: {e}")
            return imprint_url, {}, False, False  # Error when retrieving the imprint page

        # Step 3: Check terms
        normalized_page_text = self.normalize_text(page_text)
        term_results = {}
        for term in terms:
            normalized_term = self.normalize_text(term)  # Normalize terms
            term_results[term] = normalized_term in normalized_page_text  # True/False depending on presence

            # Debug log for each term
            print(f"Check term '{term}' (normalized: '{normalized_term}') in the imprint: {'Found' if term_results[term] else 'Not found'}")


        # Return of the results
        return imprint_url, term_results, False, False
