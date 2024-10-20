from flask import Flask, render_template, request, redirect, url_for, session, send_file
import requests
from bs4 import BeautifulSoup
import io
from xhtml2pdf import pisa
import sqlite3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Default templates
DEFAULT_TEMPLATES = {
    'impressum': "Default Impressum text...",
    'datenschutz': "Default Datenschutz text...",
    'cookie_policy': "Default Cookie Policy text..."
}

CRITERIA = {
    "Cookie Banner Visibility": "Check if the cookie banner is visible.",
    "Ohne Einwilligung Link": "Check for the presence of 'Ohne Einwilligung' link.",
    "Cookie Selection": "Check if all cookie options are available."
    """ "Correct Text": "Check if the text in the cookie banner is correct.",
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
    "No Unknown Cookies": "Check that there are no unknown cookies." """
}

# Function to get the templates
def get_templates():
    return session.get('templates', DEFAULT_TEMPLATES)

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
    templates = get_templates()
    if request.method == 'POST':
        new_templates = {
            'impressum': request.form['impressum'],
            'datenschutz': request.form['datenschutz'],
            'cookie_policy': request.form['cookie_policy']
        }
        set_templates(new_templates)
        return redirect(url_for('check_compliance'))
    return render_template('templates.html', templates=templates)

@app.route('/check_compliance')
def check_compliance():
    url = session.get('url')
    if not url:
        return redirect(url_for('index'))  # Redirect if no URL is set

    # Run the compliance check
    conformity, pdf_content, criteria_results = run_compliance_check(url)

    # Save the criteria results in the session for later access in the results page
    session['criteria_results'] = criteria_results  

    # Save the result to the database
    save_result(url, conformity, pdf_content)

    # Redirect to the results page
    return redirect(url_for('results'))

def run_compliance_check(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        criteria_results = {criterion: False for criterion in CRITERIA}  # Initialize results

        # Perform checks and update criteria_results
        criteria_results["Cookie Banner Visibility"] = check_cookie_banner_with_playwright(url)  # Make sure this returns the correct value
        print("Cookie Banner Visibility:", criteria_results["Cookie Banner Visibility"])  # Add this line
        criteria_results["Ohne Einwilligung Link"] = check_ohne_einwilligung_link(url)
        print("Ohne Einwilligung Link:", criteria_results["Ohne Einwilligung Link"])
        criteria_results["Cookie Selection"] = check_cookie_selection(url)
        """criteria_results["Correct Text"] = check_correct_text(soup)
        criteria_results["Scrollbar"] = check_scrollbar(soup)
        criteria_results["Links to Imprint and Privacy Policy"] = check_links_to_imprint_privacy(soup)
        criteria_results["Conform Design"] = check_conform_design(soup)
        criteria_results["Button Size and Height"] = check_button_size_height(soup)
        criteria_results["Font Size"] = check_font_size(soup)
        criteria_results["Mobile Compatibility"] = check_mobile_compatibility(soup)
        criteria_results["More Information Click"] = check_more_information_click(soup)
        criteria_results["Cookie Lifetime"] = check_cookie_lifetime(soup)
        criteria_results["Clickable Datenschutzinformation"] = check_clickable_datenschutz(soup)
        criteria_results["Cookie Description"] = check_cookie_description(soup)
        criteria_results["No Unknown Cookies"] = check_no_unknown_cookies(soup)"""

        # Determine conformity status
        issues = [name for name, met in criteria_results.items() if not met]
        conformity = "Yes" if not issues else "No"
        pdf_content = generate_pdf(url, conformity, criteria_results)

        return conformity, pdf_content, criteria_results

    except Exception as e:
        pdf_content = generate_pdf(url, "No", {})
        return "No", pdf_content, {}

# Automatic pop-up
def check_cookie_banner_with_playwright(url):
    """
    Checks if there is a cookie or consent banner present on the given webpage.
    """
    keywords = ["banner", "cookie", "consent", "onetrust", "gdpr", "privacy"]  # Relevant keywords

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Set headless to False for debugging
        page = browser.new_page()

        try:
            page.goto(url, timeout=30000)  # Wait for the page to fully load
            print("Page loaded successfully.")

            # Look for common IDs or classes indicating cookie banners
            for keyword in keywords:
                selector = f'div[id*="{keyword}"], div[class*="{keyword}"]'
                try:
                    page.wait_for_selector(selector, timeout=5000)  # Wait for the banner
                    print(f"Cookie banner found with '{selector}'")
                    return True  # Banner found
                except TimeoutError:
                    continue  # Try the next keyword if not found

            # If no specific banner is found, check the page content for relevant words
            content = page.content()
            if any(word in content.lower() for word in keywords):
                print("Cookie-related content found on the page.")
                return True

            print("No cookie banner found.")
            return False

        except Exception as e:
            print(f"Error: {e}")
            return False  # Banner considered not present if an error occurs

        finally:
            # Ensure the browser is closed
            page.close()  # Always close the page
            browser.close()  # Always close the browser
        
# Link "Ohne Einwilligung"
def check_ohne_einwilligung_link(url):
    """
    Checks if a cookie banner is present on the given webpage
    and whether the link or button "Ohne Einwilligung" or "Ohne Einwilligung fortfahren" can be clicked.
    """
    keywords = ["Ohne Einwilligung", "Ohne Einwilligung fortfahren"]  # Keywords for search
    selectors = [
        'button:has-text("Ohne Einwilligung")',
        'a:has-text("Ohne Einwilligung")',
        'button:has-text("Ohne Einwilligung fortfahren")',
        'a:has-text("Ohne Einwilligung fortfahren")'
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Set to False for debugging
        page = browser.new_page()

        try:
            # Load the page and wait for the cookie banner
            page.goto(url, timeout=30000)  # Wait for the page to fully load
            print("Page loaded successfully.")

            # Use a single wait for the cookie banner to be present
            page.wait_for_selector('div[id^="onetrust-banner"], div[class*="cookie-banner"]', timeout=10000)
            print("Cookie banner loaded.")

            # Check for the presence of the 'Ohne Einwilligung' button/link
            for selector in selectors:
                element = page.query_selector(selector)
                if element and element.is_visible() and element.is_enabled():
                    print(f"'{element.inner_text()}' found and is clickable.")
                    return True  # Button/link is clickable
                elif element:
                    print(f"'{element.inner_text()}' found, but it is not clickable.")

            print("No clickable 'Ohne Einwilligung' link or button found.")
            return False

        except TimeoutError:
            print("Error: Timeout while loading the page.")
            return False
        except Exception as e:
            print(f"General error: {e}")
            return False
        finally:
            browser.close()  # Ensure the browser is closed
            
def check_cookie_selection(url):
    """
    Check if the OneTrust cookie banner on the provided URL contains 
    the required four German cookie categories as toggle options.
    """
    # Expected German cookie categories
    expected_options = [
        "Leistungs-Cookies", 
        "Funktionelle Cookies", 
        "Werbe-Cookies", 
        "Social-Media-Cookies"
    ]

    # Set up Selenium with ChromeDriver
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    driver.get(url)

    try:
        # Wait for the OneTrust banner to appear
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "onetrust-banner-sdk"))
        )
        print("OneTrust cookie banner found.")

        # Click the settings button to open preferences
        settings_button = driver.find_element(By.CSS_SELECTOR, 'button#onetrust-pc-btn-handler')
        settings_button.click()

        # Wait for the settings menu to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "onetrust-pc-sdk"))
        )

        # Use JavaScript to extract all visible label text
        script = """
            return Array.from(document.querySelectorAll(
                'input[type="checkbox"] + label, div.ot-checkbox-label span, div.ot-checkbox-label'
            )).map(element => element.innerText || element.textContent).filter(text => text.trim());
        """
        # Execute the script to get options
        available_options = driver.execute_script(script)
        
        # Clean the list: Remove duplicates and unwanted entries
        available_options = list(set(option.strip() for option in available_options if option.strip() in expected_options))
        
        print("Available options:", available_options)

        # Check if all required options are present
        if all(option in available_options for option in expected_options):
            print("All required cookie options are present.")
            return True
        else:
            print("Some required cookie options are missing.")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False

    finally:
        driver.quit()  # Ensure the browser is closed

"""def check_correct_text(soup):
    # Replace with actual expected text from your compliance standard
    expected_text = "Expected cookie consent text"
    actual_text = soup.get_text()
    return expected_text in actual_text

def check_scrollbar(soup):
    # Check if the cookie banner has overflow property
    cookie_banner = soup.select_one('.cookie-banner')  # Update the selector as needed
    if cookie_banner:
        return 'overflow' in cookie_banner.attrs and cookie_banner.attrs['overflow'] == 'auto'
    return False

def check_links_to_imprint_privacy(soup):
    imprint_link = soup.find('a', string="Impressum")
    privacy_link = soup.find('a', string="Datenschutzinformationen")
    return (imprint_link is not None and 
            privacy_link is not None and
            imprint_link.is_displayed() and 
            privacy_link.is_displayed())


def check_conform_design(soup):
    # Check for required design conformity
    cookie_settings = soup.select_one('.cookie-settings')  # Example selector, adjust as needed
    cookie_options = soup.select('.cookie-option')  # Example selector, adjust as needed
    return cookie_settings is not None and len(cookie_options) >= 4  # At least 4 options should be present

def check_button_size_height(soup):
    # Check button size and height
    buttons = soup.select('.cookie-button')  # Example selector, adjust as needed
    return len(buttons) >= 2  # Check if both buttons exist

def check_font_size(soup):
    # Check font size is appropriate
    cookie_banner = soup.select_one('.cookie-banner')  # Update the selector as needed
    return cookie_banner and 'font-size' in cookie_banner.attrs  # Check for font-size property

def check_mobile_compatibility(soup):
    # Check for mobile responsiveness
    meta_viewport = soup.find('meta', attrs={'name': 'viewport'})
    return meta_viewport is not None

def check_more_information_click(soup):
    # Check if "more information" is available and clickable
    more_info = soup.find('a', string="More information")
    return more_info is not None and more_info.has_attr('href')

def check_cookie_lifetime(soup):
    # Placeholder check for cookie lifetime information
    # Update with actual checks based on your needs
    return True  # Assuming it meets the criteria for now

def check_clickable_datenschutz(soup):
    # Check if the Datenschutzinformationen link is clickable
    datenschutz = soup.find('a', string="Datenschutzinformationen")
    return datenschutz is not None and datenschutz.has_attr('href')

def check_cookie_description(soup):
    # Check for descriptions of each cookie
    cookie_descriptions = soup.select('.cookie-description')  # Adjust selector as needed
    return len(cookie_descriptions) > 0  # Check if there is at least one description

def check_no_unknown_cookies(soup):
    # Check that all cookies are assigned to a category
    cookie_categories = soup.select('.cookie-category')  # Adjust selector as needed
    return len(cookie_categories) > 0  # Check if there are no unknown cookies """

def generate_pdf(url, conformity, criteria_results):
    html_content = f'''
    <h1>Compliance Report</h1>
    <p><strong>URL:</strong> {url}</p>
    <p><strong>Conformity:</strong> {conformity}</p>
    <h2>Criteria Results</h2>
    <table border="1" style="width: 100%; border-collapse: collapse;">
        <tr>
            <th style="padding: 10px;">Criterion</th>
            <th style="padding: 10px;">Status</th>
        </tr>
    '''
    
    # Iterate over the criteria_results dictionary to generate rows for the PDF table
    for criterion in criteria_results.keys():
        met = criteria_results.get(criterion, False)  # Get the status safely
        status = "✔️" if met else "❌"  # Use checkmark for True, cross for False
        html_content += f'''
        <tr>
            <td style="padding: 10px;">{criterion}</td>
            <td style="padding: 10px;">{status}</td>
        </tr>
        '''
    
    html_content += '''
    </table>
    '''
    
    # Create a BytesIO buffer to hold the PDF
    pdf_buffer = io.BytesIO()
    
    # Convert HTML to PDF
    pisa_status = pisa.CreatePDF(io.StringIO(html_content), dest=pdf_buffer)
    
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
    cursor.execute('SELECT id, url, conformity FROM compliance ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()

    if row:
        result = {
            'id': row[0],
            'url': row[1],
            'conformity': row[2],
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
    
if __name__ == '__main__':
    app.run(debug=True)
