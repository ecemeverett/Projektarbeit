from flask import Flask, render_template, request, redirect, url_for, session, send_file
import requests
from bs4 import BeautifulSoup
import io
from xhtml2pdf import pisa
import sqlite3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import re
from difflib import SequenceMatcher
from datetime import datetime
from spellchecker import SpellChecker
from check_age_limitation import AgeLimitation
from check_newsletter_wording import NewsletterWording
from cookie_banner_visibility import CookieBannerVis
from cookie_banner_without_consent import WithoutConsentChecker
from cookie_options import CookieSelectionChecker
from cookie_banner_text import CookieBannerText
from check_clear_cta import ClearCTA
import asyncio


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Default templates
DEFAULT_TEMPLATES = {
    'impressum': "Default Impressum text...",
    'datenschutz': "Default Datenschutz text...",
    'cookie_policy': 'Auf unserer Webseite verwenden wir Cookies und ähnliche Technologien, um Informationen auf Ihrem Gerät (z.B. IP-Adresse, Nutzer-ID, Browser-Informationen) zu speichern und/oder abzurufen. Einige von ihnen sind für den Betrieb der Webseite unbedingt erforderlich. Andere verwenden wir nur mit Ihrer Einwilligung, z.B. um unser Angebot zu verbessern, ihre Nutzung zu analysieren, Inhalte auf Ihre Interessen zuzuschneiden oder Ihren Browser/Ihr Gerät zu identifizieren, um ein Profil Ihrer Interessen zu erstellen und Ihnen relevante Werbung auf anderen Onlineangeboten zu zeigen. Sie können nicht erforderliche Cookies akzeptieren ("Alle akzeptieren"), ablehnen ("Ohne Einwilligung fortfahren") oder die Einstellungen individuell anpassen und Ihre Auswahl speichern ("Auswahl speichern"). Zudem können Sie Ihre Einstellungen (unter dem Link "Cookie-Einstellungen") jederzeit aufrufen und nachträglich anpassen. Weitere Informationen enthalten unsere Datenschutzinformationen.',
    'newsletter' : 'Ja, hiermit willige ich in die Verarbeitung meiner o.g. Kontaktdaten zu Marketingzwecken im Wege der direkten Kontaktaufnahme durch [Marke] sowie die weiteren Marken der L’Oréal Deutschland GmbH ein. Um individuell auf meine Interessen zugeschnittene Informationen zu erhalten, willige ich außerdem ein, dass diese meine Reaktionen im Rahmen der Marketingaktionen sowie meine Interaktionen bei der Nutzung der Webservices der L’Oréal Deutschland GmbH  und ihrer Marken erhebt und in einem Interessenprofil speichert, nutzt sowie meine E-Mail-Adresse oder meine Telefonnummer (soweit angegeben) in verschlüsselter Form an unsere Werbepartner übermittelt, sodass mir auch bei der Nutzung der Webservices unserer Werbepartner entsprechende Informationen angezeigt werden.'
}

# IMPORTANT !
# In order to check a criteria, you should add the name and the function of the criteria into this dictionary.
# The function, that checks the criteria has to return False or True. Otherwise the dictionary won't get initialized correctly.
CRITERIA = {
    "Cookie Banner Visibility": "Check if the cookie banner is visible.",
    "Ohne Einwilligung Link": "Check for the presence of 'Ohne Einwilligung' link.",
    "Cookie Selection": "Check if all cookie options are available.",
    "Cookie Banner Text Comparison": "Compare website cookie banner text with the template.",
    "Clear CTA": "CTA must be recognizable and has to have a clear wording" ,
    "Age Limitation": "Check if the age limit is 18",
    "Newsletter wording": "Check if the wording of the newsletter is correct"
    """ 
    "Scrollbar": "Check if the banner has a scrollbar if it needs one.",
    "Links to Imprint and Privacy Policy": "Check links to Impressum and Datenschutzinformationen.",
    "Conform Design": "Check if the design conforms to the requirements.",
    "Button Size and Height": "Check if buttons are appropriately sized and aligned.",
    "Font Size": "Check if the font size is readable.",
    "Mobile Compatibility": "Check if the site is mobile-compatible.",
    "More Information Click": "Check for clickable 'More information' links.",
    "Cookie Lifetime": "Check cookie lifetime information.",
    "Clickable Datenschutzinformation": "Check if the Datenschutzinformation link is clickable.",
    "Cookie Description": "Check if every cookie has a description.",
    "No Unknown Cookies": "Check that there are no unknown cookies." 
    "Newsletter Consent Checkbox": Check if there is a consent checkbox in the newsletter",
    "Newsletter Functinality": Check if the functionality of the 4 Links in the Newsletter is correct",
    "Newsletter More Details": Check if the more Details Button is correct",
    """
}

# Function to get the templates
def get_templates():
    return session.get('templates', DEFAULT_TEMPLATES)  # This line should retrieve the default if not set

# Function to set new templates
def set_templates(new_templates):
    session['templates'] = new_templates

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        session['url'] = url  # Store the URL in session
        return redirect(url_for('templates'))  # Redirect to templates page
    return render_template('index.html')

@app.route('/templates', methods=['GET', 'POST'])
def templates():
    templates = get_templates()  # Retrieve templates from session
    if request.method == 'POST':
        new_templates = {
            'impressum': request.form.get('impressum',DEFAULT_TEMPLATES['impressum']),
            'datenschutz': request.form.get('datenschutz',DEFAULT_TEMPLATES['datenschutz']),
            'cookie_policy': request.form.get('cookie_policy', DEFAULT_TEMPLATES['cookie_policy']),  
            'newsletter': request.form.get('newsletter', DEFAULT_TEMPLATES['newsletter'])
        }
        set_templates(new_templates)  # Save updated templates
        return redirect(url_for('check_compliance'))
    return render_template('templates.html', templates=templates)

@app.route('/check_compliance')
async def check_compliance():
    url = session.get('url')
    if not url:
        return redirect(url_for('index'))
    
    start_time = datetime.now()  # Startzeit erfassen

    checker = CookieBannerVis()
    checker2 = WithoutConsentChecker()
    checker3 = CookieSelectionChecker()
    checker4 = CookieBannerText()
    checker5 = ClearCTA(url)
    checker6 = AgeLimitation(url)
    checker7 = NewsletterWording(url)
    #checker8 = MoreDetails(url)

    # Initialize criteria results and feedback results
    criteria_results = {}
    feedback_results = {}

    try:
        # Perform cookie banner checks asynchronously
        tasks = [
            checker.check_visibility(url),
            checker2.check_ohne_einwilligung_link(url),
            checker3.check_cookie_selection(url),
            checker5.check_clear_cta(),  
            checker6.check_age_limitation(),
           #checker8.check_newsletter_more_details(),
        ]

        # Wait for all tasks to complete concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Debug print
        for idx, result in enumerate(results):
            print(f"Task {idx} result: {result} (Type: {type(result)})")

        # Extract results safely
        banner_result, banner_feedback = results[0] if not isinstance(results[0], Exception) else (False, str(results[0]))
        ohne_einwilligung_result, ohne_feedback = results[1] if not isinstance(results[1], Exception) else (False, str(results[1]))
        selection_result, selection_feedback = results[2] if not isinstance(results[2], Exception) else (False, str(results[2]))
        cta_result, cta_feedback = results[3] if not isinstance(results[3], Exception) else (False, str(results[3]))
        age_limitation_result, age_limitation_feedback = results[4] if not isinstance(results[4], Exception) else (False, str(results[4]))
        
    
        
        # Perform text comparison
        try:
            templates = get_templates()  # Retrieve templates
            website_text = await checker4.extract_cookie_banner_text(url)
            cookie_policy_template = templates['cookie_policy']  # Access the 'cookie_policy' template
            text_comparison_result, similarity, text_comparison_feedback = checker4.compare_cookie_banner_text(
            website_text, cookie_policy_template
            )
        except Exception as e:
            text_comparison_result = False
            text_comparison_feedback = f"Error during text comparison: {e}"


        # Newsletter comparison
        try:
         templates = get_templates()
         newsletter_template = templates['newsletter']
         checkbox_text, similarity, conformity, feedback = await checker7.check_newsletter_wording(url, newsletter_template)

           # Ergebnisse aktualisieren
         newsletter_wording_result = conformity
         newsletter_wording_feedback = feedback  # Set feedback directly

         feedback_results["Newsletter Wording"] = feedback

        except Exception as e:
         # Initialisiere newsletter_wording_feedback für den Fehlerfall
         newsletter_wording_result = False
         newsletter_wording_feedback = f"<strong>Error during newsletter text check:</strong> {e}"

         feedback_results["Newsletter Wording"] = newsletter_wording_feedback



        # Populate criteria results and feedback
        criteria_results = {
            "Cookie Banner Visibility": banner_result,
            "Ohne Einwilligung Link": ohne_einwilligung_result,
            "Cookie Selection": selection_result,
            "Cookie Banner Text Comparison": text_comparison_result,
            "Clear CTA": cta_result,
            "Age Limitation": age_limitation_result,
            "Newsletter Wording": newsletter_wording_result,
        }

        feedback_results = {
            "Cookie Banner Visibility": banner_feedback,
            "Ohne Einwilligung Link": ohne_feedback,
            "Cookie Selection": selection_feedback,
            "Cookie Banner Text Comparison": text_comparison_feedback,
            "Clear CTA": cta_feedback,
            "Age Limitation": age_limitation_feedback,
            "Newsletter Wording": newsletter_wording_feedback,
        }


    except Exception as e:
        # Handle errors gracefully and populate default feedback
        print(f"Error during compliance check: {e}")
        criteria_results = {key: False for key in CRITERIA}
        feedback_results = {key: f"Error: {e}" for key in CRITERIA}

    # Determine conformity based on all criteria results
    conformity = "Yes" if all(criteria_results.values()) else "No"

    # Endzeit erfassen und Dauer berechnen
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Generate PDF
    date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf_content = generate_pdf(url, conformity, criteria_results, feedback_results, date_time,duration)

    # Save to database
    await asyncio.to_thread(save_result, url, conformity, pdf_content)  # Save to database in a thread

    return redirect(url_for('results'))

def generate_pdf(url, conformity, criteria_results, feedback_results,date_time,duration):
    html_content = f'''
    <h1>Compliance Report</h1>
    <p><strong>Date and Time:</strong> {date_time}</p>
    <p><strong>URL:</strong> {url}</p>
    <p><strong>Conformity:</strong> {conformity}</p>
    <p><strong>Time taken to generate this PDF:</strong> {duration} seconds</p>
    <h2>Criteria Results</h2>
    <table border="1" style="width: 100%; border-collapse: collapse;">
    <tr>
        <th style="padding: 10px; width: 25%;">Criterion</th>
        <th style="padding: 10px; width: 25%;">Status</th>
        <th style="padding: 10px; width: 50%;">Feedback</th>
    </tr>
    '''
    
    # Iterate over the criteria_results and feedback_results to generate rows for the PDF table
    for criterion in criteria_results.keys():
        met = criteria_results.get(criterion, False)  # Get the status safely
        status = "✔️" if met else "❌"  # Use checkmark for True, cross for False
        feedback = feedback_results.get(criterion, "No feedback available.")  # Get feedback, default if not available
        
        html_content += f'''
        <tr>
            <td style="padding: 10px;">{criterion}</td>
            <td style="padding: 10px;">{status}</td>
            <td style="padding: 10px;">{feedback}</td>
        </tr>
        '''
    
    html_content += '''
    </table>
    '''
    
    # Create a BytesIO buffer to hold the PDF
    pdf_buffer = io.BytesIO()
    
    # Convert HTML to PDF
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
    
    # Check for errors during PDF generation
    if pisa_status.err:
        print("Error generating PDF")
        return None

    # Return the PDF content as bytes
    pdf_buffer.seek(0)  # Reset buffer position to the beginning
    return pdf_buffer.read()


def save_result(url, conformity, pdf_content):
    try:
        conn = sqlite3.connect('compliance.db')
        cursor = conn.cursor()
        
        # Create the table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compliance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATETIME DEFAULT (datetime('now', 'localtime')),
                url TEXT NOT NULL,
                conformity TEXT NOT NULL,
                conformity_details BLOB NOT NULL
            )
        ''')  # Ensure the PDF content can be stored as a BLOB
        
        # Insert the new result into the database
        cursor.execute('''
            INSERT INTO compliance (url, conformity, conformity_details)
            VALUES (?, ?, ?)
        ''', (url, conformity, pdf_content))
        
        conn.commit()  # Commit the transaction
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")  # Log the error for debugging
    finally:
        conn.close()  # Ensure the database connection is closed



@app.route('/results')
def results():
    conn = sqlite3.connect('compliance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, date, url, conformity FROM compliance ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()

    if row:
        result = {
            'id': row[0],
            'date':row[1],
            'url': row[2],
            'conformity': row[3],
        }
    else:
        result = {}

    return render_template('results.html', result=result)

@app.route('/download/<int:id>')
def download(id):
    conn = sqlite3.connect('compliance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT conformity_details FROM compliance WHERE id = ?', (id,))
    pdf_content = cursor.fetchone()
    
    # Check if pdf_content is retrieved
    if pdf_content is None:
        return "No PDF found.", 404  # Handle the case where no PDF exists for the ID
    
    pdf_content = pdf_content[0]  # Get the actual bytes from the tuple
    conn.close()

    return send_file(
        io.BytesIO(pdf_content),
        download_name='compliance_report.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )

def execute_query(query, params=()):
    conn = sqlite3.connect('compliance.db') 
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results

@app.route('/database', methods=['GET'])
def database():
    page = request.args.get('page', 1, type=int)
    selected_url = request.args.get('url', 'all', type=str)
    per_page = 10
    offset = (page - 1) * per_page
    
    # Kunden-URLs abrufen für das Dropdown
    customers_query = "SELECT DISTINCT url FROM compliance"
    customers = execute_query(customers_query)

    if selected_url == 'all':
        query = "SELECT * FROM compliance ORDER BY id DESC LIMIT ? OFFSET ?"
        params = (per_page, offset)
    else:
        query = "SELECT * FROM compliance WHERE url = ? ORDER BY id DESC LIMIT ? OFFSET ?"
        params = (selected_url, per_page, offset)

    compliance = execute_query(query, params)

    total_records_query = "SELECT COUNT(*) FROM compliance"
    total_records = execute_query(total_records_query)[0][0]

    total_pages = (total_records + per_page - 1) // per_page

    return render_template('database.html', records=compliance, page=page, total_pages=total_pages, customers=customers, selected_url=selected_url)

if __name__ == '__main__':
    app.run(debug=True)
