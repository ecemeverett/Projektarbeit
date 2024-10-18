from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re
import sqlite3

app = Flask(__name__)

# Funktion zur Erstellung einer SQLite-Datenbank und Tabelle
def create_database():
    conn = sqlite3.connect('webseiten.db')  # Erstellt oder verbindet sich mit der Datenbank
    cursor = conn.cursor()

    # Tabelle erstellen (falls sie noch nicht existiert)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS webseiten (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            html_quelltext TEXT NOT NULL,
            cookie_banner TEXT,
            impressum TEXT,
            datenschutzerklaerung TEXT
        )
    ''')

    conn.commit()
    conn.close()

# Funktion zum Speichern des HTML-Quelltexts und der Konformitätsergebnisse in der Datenbank
def save_to_database(url, html_quelltext, results):
    conn = sqlite3.connect('webseiten.db')
    cursor = conn.cursor()

    # Daten in die Tabelle einfügen
    cursor.execute('''
        INSERT INTO webseiten (url, html_quelltext, cookie_banner, impressum, datenschutzerklaerung)
        VALUES (?, ?, ?, ?, ?)
    ''', (url, html_quelltext, results['Cookie-Banner'], results['Impressum'], results['Datenschutzerklärung']))

    conn.commit()
    conn.close()

# Funktion zum Herunterladen und Analysieren einer Webseite auf Datenschutzkonformität
def check_compliance(url):
    try:
        # HTML-Seite herunterladen
        response = requests.get(url)
        response.raise_for_status()  # Überprüft auf HTTP-Fehler
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = {}
        
        # 1. Cookie-Banner
        cookie_keywords = ["cookie", "einwilligung", "consent"]
        cookie_banner = any(keyword in response.text.lower() for keyword in cookie_keywords)
        results["Cookie-Banner"] = "Vorhanden" if cookie_banner else "Fehlt"
        
        # 2. Impressum
        impressum_link = soup.find("a", string=re.compile(r"impressum", re.I))
        results["Impressum"] = "Vorhanden" if impressum_link else "Fehlt"
        
        # 3. Datenschutzerklärung
        datenschutz_link = soup.find("a", string=re.compile(r"(datenschutz|privacy)", re.I))
        results["Datenschutzerklärung"] = "Vorhanden" if datenschutz_link else "Fehlt"
        
        # Ergebnisse ausgeben
        for item, status in results.items():
            print(f"{item}: {status}")
        
        # Speichern des HTML-Quelltexts und der Ergebnisse in der Datenbank
        save_to_database(url, response.text, results)
        
        return results
        
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Herunterladen der Seite: {e}")
        return None

# Route für die Startseite (Formular zur Eingabe der URL)
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']  # Die vom Benutzer eingegebene URL
        results = check_compliance(url)
        return render_template('index.html', results=results, url=url)
    return render_template('index.html')

if __name__ == '__main__':
    create_database()  # Erstellt die Datenbank, falls sie noch nicht existiert
    app.run(debug=True)