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
from cookie_banner_visibility import CookieBannerVis
from cookie_banner_without_consent import WithoutConsentChecker
from cookie_options import CookieSelectionChecker
from cookie_banner_text import CookieBannerText
import asyncio


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Default templates
DEFAULT_TEMPLATES = {
    'impressum': "Default Impressum text...",
    'datenschutz': "Default Datenschutz text...",
    'cookie_policy': 'Auf unserer Webseite verwenden wir Cookies und ähnliche Technologien, um Informationen auf Ihrem Gerät (z.B. IP-Adresse, Nutzer-ID, Browser-Informationen) zu speichern und/oder abzurufen. Einige von ihnen sind für den Betrieb der Webseite unbedingt erforderlich. Andere verwenden wir nur mit Ihrer Einwilligung, z.B. um unser Angebot zu verbessern, ihre Nutzung zu analysieren, Inhalte auf Ihre Interessen zuzuschneiden oder Ihren Browser/Ihr Gerät zu identifizieren, um ein Profil Ihrer Interessen zu erstellen und Ihnen relevante Werbung auf anderen Onlineangeboten zu zeigen. Sie können nicht erforderliche Cookies akzeptieren ("Alle akzeptieren"), ablehnen ("Ohne Einwilligung fortfahren") oder die Einstellungen individuell anpassen und Ihre Auswahl speichern ("Auswahl speichern"). Zudem können Sie Ihre Einstellungen (unter dem Link "Cookie-Einstellungen") jederzeit aufrufen und nachträglich anpassen. Weitere Informationen enthalten unsere Datenschutzinformationen.',
    'newsletter' : "Default Newsletter text..."
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
    "Newsletter functinality": Check if the functionality of the 4 Links in the Newsletter is correct",
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

    # Initialize criteria results and feedback results
    criteria_results = {}
    feedback_results = {}

    try:
        # Perform cookie banner checks asynchronously
        tasks = [
            checker.check_visibility(url),
            checker2.check_ohne_einwilligung_link(url),
            checker3.check_cookie_selection(url),
            asyncio.to_thread(check_clear_cta, url),  
            asyncio.to_thread(check_age_limitation, url)  
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
        #cta_result, cta_feedback = results[3] if not isinstance(results[3], Exception) else (False, str(results[3]))
        #age_limitation_result, age_limitation_feedback = results[4] if not isinstance(results[4], Exception) else (False, str(results[4]))
        
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
            
        # Populate criteria results and feedback
        criteria_results = {
            "Cookie Banner Visibility": banner_result,
            "Ohne Einwilligung Link": ohne_einwilligung_result,
            "Cookie Selection": selection_result,
            "Cookie Banner Text Comparison": text_comparison_result,
           # "Clear CTA": cta_result,
           # "Age Limitation": age_limitation_result,
        }

        feedback_results = {
            "Cookie Banner Visibility": banner_feedback,
            "Ohne Einwilligung Link": ohne_feedback,
            "Cookie Selection": selection_feedback,
            "Cookie Banner Text Comparison": text_comparison_feedback,
           # "Clear CTA": cta_feedback,
           # "Age Limitation": age_limitation_feedback,
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


def check_clear_cta(url):

    # Ensure the URL starts with http or https; add https:// if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    criteria_met = False
    feedback = "CTA not found or not recognizable as a clear call-to-action."
    newsletter_phrases = ["subscribe now", "join our newsletter", "sign up", "get updates", "newsletter signup", "subscribe", "subscribe to our newsletter"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print(f"Checking URL: {url}")  # Debugging print

            page.goto(url)  # Page.goto expects a full URL (including http:// or https://)

            # Find CTA elements
            cta_elements = page.query_selector_all('a, button, input')
            for element in cta_elements:
                text = element.inner_text()  # Extract the text of the element
                if any(phrase.lower() in text.lower() for phrase in newsletter_phrases):
                    criteria_met = True
                    feedback = f"Found CTA: '{text}'"
                    break

            if not criteria_met:
                feedback = "No CTA found matching the expected phrases."

        except Exception as e:
            feedback = f"Error navigating to URL {url}: {str(e)}"
            print(feedback)

        browser.close()

    return criteria_met, feedback


def check_age_limitation(url):

    # Ensure the URL starts with http or https; add https:// if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # List of common phrases that indicate an age limitation (18+)
    age_restriction_phrases = [
        "You must be 18 or older",
        "18+",
        "You must be over 18",
        "Age verification",
        "Enter your birthdate",
        "Please confirm your age",
        "Restricted to users 18 and older",
        "DOB",
        "Date of Birth"
    ]
    
    # Default value for age limitation check (assume no age restriction)
    age_limitation_met = False
    feedback = "No age limitation found."

    try:
        # Fetch the HTML content of the page using Playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            page_content = page.content()
            browser.close()

        # Parse the page content
        soup = BeautifulSoup(page_content, 'html.parser')

        # Search for age limitation-related phrases in text elements
        age_verification_elements = soup.find_all(string=True)
        for element in age_verification_elements:
            text = element.strip().lower()  # Convert to lowercase for easier matching
            for phrase in age_restriction_phrases:
                if phrase.lower() in text:
                    age_limitation_met = True
                    feedback = f"Age limitation found: '{text}'"
                    break
            if age_limitation_met:
                break  # No need to continue once an age limitation is found

    except Exception as e:
        print(f"Error loading the page: {e}")
        feedback = f"Error during age limitation check: {str(e)}"

    return age_limitation_met, feedback



#def extract_brand_from_url(url):
  #  """Extract brand name from URL (e.g., 'loreal' from 'loreal.com')."""
   # domain = urlparse(url).netloc  # Get domain name from URL (e.g., 'loreal.com')
   # brand_name = domain.split('.')[0]  # Extract the first part of the domain (e.g., 'loreal')
    #brand_name = brand_name.capitalize()  # Capitalize the brand name
   # return brand_name

#def check_newsletter_wording(url, template_text=None):
    #"""Check if the newsletter wording matches the expected template."""

    # Default mustertext to use if no template is provided
   # default_mustertext = """By checking this box, I consent to the processing of my aforementioned contact details for marketing purposes by [Brand Name] and its affiliated companies. To receive information tailored to my interests, I also consent to the collection and storage of my interactions during marketing activities, as well as my use of [Brand Name]'s online services. Additionally, I agree that my email address or phone number (if provided) may be transmitted in encrypted form to third-party marketing partners, allowing relevant information to be displayed to me while using the online services of [Brand Name] and its partners."""

   # if not template_text:
     #   template_text = default_mustertext

    # Ensure the URL starts with http or https; add https:// if missing
   # if not url.startswith(('http://', 'https://')):
       # url = 'https://' + url

    # Extract brand name from the URL
   # brand_name = extract_brand_from_url(url)

    # Replace [Brand Name] with the actual brand name in the mustertext
   # template_text = template_text.replace("[Brand Name]", brand_name)

   # try:
        # Using Playwright for a better solution to handle dynamic content
       # with sync_playwright() as p:
          #  browser = p.chromium.launch(headless=True)  # Set headless=False to see what's happening

          #  page = browser.new_page()

            # Increase the timeout for waiting for the page to load
          #  page.goto(url, timeout=60000, wait_until="domcontentloaded")  # 60 seconds timeout, waits until DOM is loaded

            # Wait for the newsletter button or a similar element to appear
           # page.wait_for_selector('a[href*="newsletter"], a[href*="subscribe"], button, input[type="submit"]', timeout=60000)

            # Scrape all links from the homepage
          #  links = page.query_selector_all('a')  # Collect all links
          #  relevant_links = []

            # Look for any link that mentions 'newsletter', 'subscribe', 'join', etc.
           # for link in links:
              #  href = link.get_attribute('href')
              #  if href and any(keyword in href.lower() for keyword in ["newsletter", "subscribe", "sign up", "join", "receive updates"]):
                   # relevant_links.append(href)

          #  if not relevant_links:
                # If no links were found, we need to search within the page content
               # print("No direct newsletter links found. Searching for newsletter-related content on the page...")

                # Search within the page content for keywords like 'newsletter', 'subscribe', etc.
              #  page_content = page.content()
               # if any(keyword in page_content.lower() for keyword in ["newsletter", "subscribe", "sign up", "join", "receive updates"]):
                  #  relevant_links.append(url)  # Fallback to checking the homepage or starting page

            # Check the relevant pages for consent wording
          #  for relevant_link in relevant_links:
                # Make sure the link is complete (starts with http:// or https://)
               # if not relevant_link.startswith(('http://', 'https://')):
                  #  relevant_link = url + relevant_link  # Ensure it's a full URL

                # Go to the found relevant link (newsletter or subscribe page)
               # page.goto(relevant_link, wait_until="load")
               # page_content = page.content()  # Get the full page content after rendering

                # Use BeautifulSoup to parse the page content
              #  soup = BeautifulSoup(page_content, 'html.parser')

                # Get all visible text from the page and convert it to lowercase for easier matching
              #  page_text = ' '.join([element.get_text() for element in soup.find_all(['p', 'span', 'label'])])  # Check relevant elements
              #  page_text = page_text.lower()  # Convert all text to lowercase for easier matching

                # Debugging: Print a snippet of the extracted text
               # print(f"Extracted text from page: {page_text[:1000]}...")  # Print first 1000 chars

                # Define consent-related keywords and phrases
              #  consent_keywords = [
                 #   r"\bconsent\b",
                 #   r"\bagree\b",
                 ##   r"\baccept\b",
                 #   r"\bgive permission\b",
                 #   r"\bcheck this box\b",
                 #   r"\bsubscribe\b",
                 #   r"\bmarketing\b",
                 #   r"\bprocessing\b",
                 #   r"\bprivacy policy\b",  # Added privacy related terms to capture more cases
                #    r"\bterms and conditions\b"
              #  ]

                # Check if any of the consent keywords are in the extracted text
              #  if any(re.search(keyword, page_text) for keyword in consent_keywords):
                   # browser.close()
                  #  return True, f"Newsletter wording matches the template on {relevant_link}."

            # If no consent-related text is found
          #  browser.close()
          #  return False, "Newsletter wording does not match the expected template or cannot find a relevant page."

   # except Exception as e:
      #  browser.close()
        #return False, f"Error during check: {e}"



#def check_consent_checkbox(url):

     # Ensure the URL starts with http or https; add https:// if missing
  #  if not url.startswith(('http://', 'https://')):
    #    url = 'https://' + url

  #  consent_phrases = [
    #    "I agree to the terms and conditions",
     #   "I consent to the use of my data",
     #   "I accept the privacy policy",
     #   "I am over 18 years old"
  #  ]

   # try:
     #   response = requests.get(url)
      #  soup = BeautifulSoup(response.text, 'html.parser')

     #   checkboxes = soup.find_all('input', {'type': 'checkbox'})
      #  for checkbox in checkboxes:
        #    label = checkbox.find_next('label')
         #   if label and any(phrase.lower() in label.get_text().lower() for phrase in consent_phrases):
          #      return True, "Consent checkbox found with appropriate consent wording."
        
       # return False, "Consent checkbox with proper wording not found."
  #  except Exception as e:
      #  return False, f"Error during check: {e}"


"""

def check_newsletter_functionality(soup):
    # Check the functinality of all 4 links and if they have the correct text
    # Widerrufsrecht, Impressumslink, Datenschutzinformationen, Werbepartner

def check_newsletter_more_details (soup):
    # Check if there's a plus for more details on data privacy policy information
    #whole text is correct and link to the advertising partners

"""

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
