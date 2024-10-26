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
from datetime import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed



app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Default templates
DEFAULT_TEMPLATES = {
    'impressum': "Default Impressum text...",
    'datenschutz': "Default Datenschutz text...",
    'cookie_policy': "Default Cookie Policy text...",
    'newsletter' : "Default Newsletter text..."
}

# IMPORTANT !
# In order to check a criteria, you should add the name and the function of the criteria into this dictionary.
# The function, that checks the criteria has to return False or True. Otherwise the dictionary won't get initialized correctly.
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
            'impressum': request.form['impressum'],
            'datenschutz': request.form['datenschutz'],
            'cookie_policy': request.form['cookie_policy'],
            'newsletter': request.form['newsletter']
        }
        set_templates(new_templates)  # Save updated templates
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

        # Create a ThreadPoolExecutor for concurrent execution
        with ThreadPoolExecutor() as executor:
            # Submit tasks to the executor for each check
            future_to_criteria = {
                executor.submit(check_cookie_banner_with_playwright, url): "Cookie Banner Visibility",
                executor.submit(check_ohne_einwilligung_link, url): "Ohne Einwilligung Link",
                executor.submit(check_cookie_selection, url): "Cookie Selection"
                # Add more checks here as needed
        
            }

            # Process results as they complete
            for future in as_completed(future_to_criteria):
                criterion_name = future_to_criteria[future]
                try:
                    criteria_results[criterion_name] = future.result()
                    print(f"{criterion_name}: {criteria_results[criterion_name]}")  # Logging for debug
                except Exception as e:
                    print(f"{criterion_name} check generated an exception: {e}")
        
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
    Checks if a visible cookie or consent banner is present on the given webpage,
    including checks for iframes and specific selectors.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Launch browser in headful mode for debugging
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
        )
        page = context.new_page()

        # Common selectors for cookie banners
        common_selectors = [
            'div.sticky',  # The main sticky container of the cookie banner
            'div.hp__sc-yx4ahb-7',  # The main container of the cookie banner
            'p.hp__sc-hk8z4-0',  # Paragraphs containing cookie consent text
            'button.hp__sc-9mw778-1',  # Buttons for actions
            'div.cmp-container',
            'div.ccm-modal-inner',
            'div.ccm-modal--header',
            'div.ccm-modal--body',
            'div.ccm-widget--buttons',
            'button.ccm--decline-cookies',
            'button.ccm--save-settings',
            'button[data-ccm-modal="ccm-control-panel"]',
            'div.ccm-powered-by',
            'div.ccm-link-container',
            'div.ccm-modal',
            'div[class*="ccm-settings-summoner"]',
            'div[class*="ccm-control-panel"]',
            'div[class*="ccm-modal--footer"]',
            'button.ccm--button-primary',
            'div[data-testid="uc-default-wall"]',
            'div[role="dialog"]',
            'div.cc-banner',
            'section.consentDrawer',
            'div[class*="cookie"]', 
            'div[class*="consent"]', 
            'div[id*="banner"]', 
            'div[class*="cookie-banner"]',  
            'div[class*="cookie-notice"]',
            '[role="dialog"]', 
            '[aria-label*="cookie"]', 
            '[data-cookie-banner]', 
            'div[style*="bottom"]', 
            'div[style*="fixed"]',
            'div[data-borlabs-cookie-consent-required]',  # Selector for Borlabs Cookie
            'div#BorlabsCookieBox',  # Specific ID for Borlabs Cookie Box
            'div#BorlabsCookieWidget',  # Specific ID for Borlabs Cookie Widget
            'div.elementText',  # Selector for the custom cookie banner text container
            'h3:has-text("Datenschutzhinweis")',  # Check for the header text
           
        ]

        def is_visible_cookie_banner(page_or_frame):
            """Check for visible cookie banners in the given page or frame."""
            found_banners = []  # Store found banners for debugging
            for selector in common_selectors:
                elements = page_or_frame.query_selector_all(selector)
                for element in elements:
                    if element and element.is_visible():
                        box = element.bounding_box()
                        if box and box['width'] > 300 and box['height'] > 50:  # Minimum dimensions for a banner
                            # Get the text content of the element
                            element_text = element.evaluate("el => el.textContent").lower() or ""
                            found_banners.append({
                                'selector': selector,
                                'text': element_text,
                                'bounding_box': box
                            })

            # Debugging output for detected banners
            for banner in found_banners:
                print(f"Found banner with selector: '{banner['selector']}'")
                print(f"Element text: '{banner['text']}'")
                print(f"Element bounding box: {banner['bounding_box']}")

            # Check for keywords in the page content
             # Check if any found banner contains relevant keywords
            for banner in found_banners:
                keywords = ["cookie", "consent", "gdpr", "privacy", "tracking", "preferences"]
                if any(keyword in banner['text'] for keyword in keywords):
                    return True

            return False
        
        def check_cookieconsent_options(page):
            """Check if cookie consent options are present in the page context."""
            try:
                # Check if window.cookieconsent_options exists
                cookie_consent = page.evaluate("window.cookieconsent_options !== undefined")
                if cookie_consent:
                    print("Cookie consent options found.")
                    return True
            except Exception as e:
                print(f"Error checking cookie consent options: {e}")
            return False

        def check_script_inclusions(page):
            """Check if the specific Borlabs Cookie scripts are included."""
            try:
                scripts = page.query_selector_all("script[type='module']")
                for script in scripts:
                    script_src = script.get_attribute('src')
                    if 'borlabs-cookie' in script_src:
                        print("Borlabs Cookie script found: ", script_src)
                        return True
            except Exception as e:
                print(f"Error checking for Borlabs Cookie scripts: {e}")
            return False
        
        try:
            # Attempt to load the page with retries
            for attempt in range(5):
                try:
                    print(f"Attempting to load the page (Attempt {attempt + 1})...")
                    page.goto(url, timeout=60000)  # Set timeout for page loading
                    page.wait_for_load_state('networkidle')  # Wait until the network is idle
                    print("Page loaded successfully.")
                    break
                except PlaywrightTimeoutError:
                    print(f"Attempt {attempt + 1} failed. Retrying after 5 seconds...")
                    page.wait_for_timeout(5000)  # Wait before retrying
            else:
                print("Page failed to load after multiple attempts.")
                return False

            # Allow extra time for dynamic content (like cookie banners)
            page.wait_for_timeout(30000)  # Increased timeout for dynamic content

             # Check the main document for cookie banners
            if is_visible_cookie_banner(page) or check_cookieconsent_options(page) or check_script_inclusions(page):
                print("Cookie banner found in the main document.")
                return True  # Banner found in the main document

            # Check for cookie banner in iframes, specifically excluding the hidden ad iframe
            iframes = page.query_selector_all('iframe')
            for iframe in iframes:
                # Checking if the iframe is hidden or not
                iframe_src = iframe.get_attribute('src')
                if iframe_src and "doubleclick" not in iframe_src:
                    iframe_content = iframe.content_frame()
                    if iframe_content and is_visible_cookie_banner(iframe_content):
                        print("Cookie banner found in an iframe.")
                        return True  # Banner found in an iframe

            # Debugging output: log page content if no banners were found
            content = page.content().lower()
            print("Page content (for debugging):")
            print(content[:2000])  # Print first 2000 characters for debugging

            # Check for keywords in the page content
            keywords = ["cookie", "consent", "onetrust", "gdpr", "privacy", "banner", "tracking", "preferences"]
            exclude_keywords = ["recaptcha", "g-recaptcha", "captcha", "not a robot", "login", "signup"]

            if any(word in content for word in keywords) and not any(ex_kw in content for ex_kw in exclude_keywords):
                print("Cookie-related content found on the page, but no visible banner detected.")
                return False  # Don't falsely indicate a banner presence

            print("No visible cookie banner found.")
            return False

        except Exception as e:
            print(f"Error: {e}")
            return False  # Banner considered not present if an error occurs

        finally:
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

# Check 4 Cookie Options and if they're preselected
def check_cookie_selection(url):
    """
    Check if the OneTrust cookie banner on the provided URL contains 
    the required four German cookie categories as toggle options, 
    and verifies that they are not preselected.
    """
    # Expected German cookie categories
    expected_options = [
        "Leistungs-Cookies", 
        "Funktionelle Cookies", 
        "Werbe-Cookies", 
        "Social-Media-Cookies"
    ]

    # Set up Selenium with ChromeDriver in headless mode
    options = Options()
    options.add_argument('--headless')  # Run in headless mode
    options.add_argument('--no-sandbox')  # Bypass OS security model
    options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    try:
        driver.get(url)

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

        # Use JavaScript to extract all visible label text and check if toggles are selected
        script = """
            return Array.from(document.querySelectorAll(
                'input[type="checkbox"] + label, div.ot-checkbox-label span, div.ot-checkbox-label'
            )).map(element => {
                const checkbox = element.previousElementSibling; // Get the associated checkbox
                return {
                    text: element.innerText || element.textContent,
                    checked: checkbox ? checkbox.checked : false // Check if the checkbox is selected
                };
            }).filter(item => item.text.trim() && item.checked !== undefined);
        """
        # Execute the script to get options and their checked status
        available_options = driver.execute_script(script)

        # Create a dictionary for easy access
        option_status = {option['text'].strip(): option['checked'] for option in available_options}

        # Filter options based on expected categories
        available_options = {key: option_status[key] for key in expected_options if key in option_status}

        print("Available options with checked status:", available_options)

        # Check if all required options are present and not preselected
        if (len(available_options) == 4 and all(not available_options[option] for option in expected_options)):
            print("All required cookie options are present and none are preselected.")
            return True
        else:
            print("Some required cookie options are missing or some are preselected.")
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
                date DATETIME DEFAULT CURRENT_TIMESTAMP,
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
