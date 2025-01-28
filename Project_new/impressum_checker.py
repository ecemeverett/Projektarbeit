from flask import Flask, render_template, request
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import re

class ImpressumChecker:
    def __init__(self):
        # Typische Impressum-Pfade
        self.imprint_paths = ["/impressum", "/imprint", "/legal", "/legal-notice"]

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
            low_priority_keywords = ['terms', 'about', 'contact']

            parsed_base_url = urlparse(base_url)
            base_domain = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}"

            # Suche nach Links mit hoher Priorität
            for link in links:
                href = link['href'].lower()
                if any(keyword in href for keyword in high_priority_keywords):
                    if href.startswith('/'):  # Relativer Pfad
                        return urljoin(base_url, href)
                    elif href.startswith('http') and href.startswith(base_domain):  # Interner absoluter Link
                        return href

            # Suche nach Links mit niedriger Priorität
            for link in links:
                href = link['href'].lower()
                if any(keyword in href for keyword in low_priority_keywords):
                    if href.startswith('/'):  # Relativer Pfad
                        return urljoin(base_url, href)
                    elif href.startswith('http'):  # Externer Link
                        return href

        except requests.RequestException as e:
            print(f"Error retrieving the page: {e}")
        return None  # Keine Impressum-URL gefunden

    def normalize_text(self, text):
        """
        Normalisiert Text für den Vergleich (Kleinbuchstaben, keine Sonderzeichen, keine mehrfachen Leerzeichen).
        """
        text = re.sub(r'\s+', ' ', text)  # Mehrfache Leerzeichen entfernen
        text = re.sub(r'[^\w\s]', '', text)  # Sonderzeichen entfernen
        return text.lower().strip()

    def check_terms(self, url, terms):
        """
        Prüft, ob bestimmte Begriffe (terms) im Impressum-Text enthalten sind.
        """
        # Schritt 1: Finde die Impressum-URL
        imprint_url = self.find_imprint_url(url)
        if not imprint_url:
            print(f"No imprint URL found for {url}.")
            return None, {}, False, False  # Keine Impressum-Seite gefunden

        try:
            # Schritt 2: HTML der Impressum-Seite abrufen
            response = requests.get(imprint_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Gesamten Text der Seite extrahieren
            page_text = soup.get_text(separator=' ').lower()
        except requests.RequestException as e:
            print(f"Error retrieving the imprint page {imprint_url}: {e}")
            return imprint_url, {}, False, False  # Fehler beim Abrufen der Impressum-Seite

        # Schritt 3: Begriffe prüfen
        normalized_page_text = self.normalize_text(page_text)
        term_results = {}
        for term in terms:
            normalized_term = self.normalize_text(term)  # Begriffe normalisieren
            term_results[term] = normalized_term in normalized_page_text  # True/False je nach Vorhandensein

            # Debug-Log für jeden Begriff
            print(f"Check term '{term}' (normalized: '{normalized_term}') in the imprint: {'Found' if term_results[term] else 'Not found'}")


        # Rückgabe der Ergebnisse
        return imprint_url, term_results, False, False
