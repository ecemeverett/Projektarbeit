from flask import Flask, render_template, request, redirect, url_for, session, send_file
import io
from xhtml2pdf import pisa
import sqlite3
from playwright.async_api import async_playwright
from datetime import datetime
import asyncio

# Importing various compliance checkers
from cookie_banner_visibility import CookieBannerVis
from cookie_banner_without_consent import WithoutConsentChecker
from cookie_options import CookieSelectionChecker
from cookie_banner_text import CookieBannerText
from cookie_banner_link_checker import CookieBannerLinkValidator
from cookie_banner_scrollbar import ScrollbarChecker
from cookie_banner_conform_design import ConformDesignChecker
from cookie_more_information import CookieInfoChecker
from cookie_preference_center_vis import CookiePreferenceVis
from cookie_preference_clickable_links import CookiePreferenceLinkValidator
from check_clear_cta import ClearCTA
from check_age_limitation import AgeLimitation
from check_newsletter_wording import NewsletterWording
from check_newsletter_functionality import NewsletterFunctionality
from check_newsletter_more_details import MoreDetails
from imprint_checker import ImprintChecker
from imprint_visibility_checker import AsyncImprintVisibilityChecker
from pagefooter import FooterLinkChecker
from pagefooter_essentials import AsyncFooterValidator

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key' 



# Default templates for compliance checks
DEFAULT_TEMPLATES = {
    'imprint': "No Default needed",
    'newsletterdetail': "Die Einwilligung umfasst, dass Ihre oben angegebene E-Mailadresse sowie ggf. weitere von Ihnen angegebene Kontaktdaten von der L’Oréal Deutschland GmbH, Johannstraße 1, 40476 Düsseldorf (im Folgenden L'Oréal), gespeichert und genutzt werden, um Sie per E-Mail, Telefon, Telefax, SMS, Briefpost persönlich und relevant über interessante Leistungen, Produkte und Aktionen von [Marke] sowie aus dem Angebot von L'Oréal und deren weiteren Marken zu informieren. Um Ihnen individuell auf Ihre Interessen zugeschnittene Informationen zukommen zu lassen, speichert L’Oréal auch die Daten zu Ihren Reaktionen auf die empfangenen Informationen und die weiteren Daten aus Ihrer Nutzung der Webservices von [Marke] und L'Oréal (insbesondere Daten zu Einkäufen und Gesamtumsatz, angesehenen und gekauften Warengruppen/Produkten, Produkten im Warenkorb und eingelöste Gutscheine sowie zu Ihren sonstigen Interaktionen im Rahmen der Webservices und Ihren Reaktionen auf unsere Kontaktaufnahmen und Angebote, inklusive besonderer Vorteils-Aktionen) und führt diese Daten mit Ihren Kontaktdaten innerhalb eines Interessenprofils zusammen. Diese Daten werden ausschließlich genutzt, um Ihnen Ihren Interessen entsprechende Angebote machen zu können. Um Ihnen auf den Plattformen unserer Werbepartner interessengerechte Informationen / Werbung anzeigen zu können, nutzen wir bestimmte Tools unserer Werbepartner (z.B. Facebook Custom Audiences und Google Customer Match) und übermitteln die von Ihnen bei der Anmeldung angegebene E-Mail-Adresse oder Telefonnummer in verschlüsselter (pseudonymisierter) Form an diese. Hierdurch wird es möglich, Sie beim Besuch der Plattformen unserer Werbepartner als Nutzer der Webservices von L'Oréal zu erkennen, um Ihnen maßgeschneiderte Informationen / Werbung anzuzeigen.",
    'cookie_policy': 'Auf unserer Webseite verwenden wir Cookies und ähnliche Technologien, um Informationen auf Ihrem Gerät (z.B. IP-Adresse, Nutzer-ID, Browser-Informationen) zu speichern und/oder abzurufen. Einige von ihnen sind für den Betrieb der Webseite unbedingt erforderlich. Andere verwenden wir nur mit Ihrer Einwilligung, z.B. um unser Angebot zu verbessern, ihre Nutzung zu analysieren, Inhalte auf Ihre Interessen zuzuschneiden oder Ihren Browser/Ihr Gerät zu identifizieren, um ein Profil Ihrer Interessen zu erstellen und Ihnen relevante Werbung auf anderen Onlineangeboten zu zeigen. Sie können nicht erforderliche Cookies akzeptieren ("Alle akzeptieren"), ablehnen ("Ohne Einwilligung fortfahren") oder die Einstellungen individuell anpassen und Ihre Auswahl speichern ("Auswahl speichern"). Zudem können Sie Ihre Einstellungen (unter dem Link "Cookie-Einstellungen") jederzeit aufrufen und nachträglich anpassen. Weitere Informationen enthalten unsere Datenschutzinformationen.',
    'newsletter' : 'Ja, hiermit willige ich in die Verarbeitung meiner o.g. Kontaktdaten zu Marketingzwecken im Wege der direkten Kontaktaufnahme durch [Marke] sowie die weiteren Marken der L’Oréal Deutschland GmbH ein. Um individuell auf meine Interessen zugeschnittene Informationen zu erhalten, willige ich außerdem ein, dass diese meine Reaktionen im Rahmen der Marketingaktionen sowie meine Interaktionen bei der Nutzung der Webservices der L’Oréal Deutschland GmbH  und ihrer Marken erhebt und in einem Interessenprofil speichert, nutzt sowie meine E-Mail-Adresse oder meine Telefonnummer (soweit angegeben) in verschlüsselter Form an unsere Werbepartner übermittelt, sodass mir auch bei der Nutzung der Webservices unserer Werbepartner entsprechende Informationen angezeigt werden.'
}

# Define compliance criteria and their descriptions
# IMPORTANT !
# In order to check a criteria, you should add the name and the function of the criteria into this dictionary.
# The function, that checks the criteria has to return False or True. Otherwise the dictionary won't get initialized correctly.
CRITERIA = {
    "Cookie Banner Visibility": "Check if the cookie banner is visible.",
    "Continue Without Consent Link": "Check for the presence of 'Ohne Einwilligung' link.",
    "Cookie Selection": "Check if all cookie options are available.",
    "Cookie Banner Text Comparison": "Compare website cookie banner text with the template.",
    "Cookie Banner Links to Imprint and Privacy Policy": "Check if the cookie banner has links to imprint and privacy policy, if the links are structured as url+privacy-policy and url+imprint, and if the links are clickable.",
    "Cookie Banner Scrollbar": "Check if the cookie banner has a visible and functional scrollbar when content overflows, ensuring all content is accessible without obstruction.",
    "Conform Design": "Ensure the cookie banner design is correct: 'Cookie-Einstellungen' at the bottom-left, vertical cookie options, aligned buttons, readable font size, and responsive across devices.",
    "Cookie Preference Accessibility": "Check if the Preference Center is accessible by clicking on the relevant option in the cookie banner, ensuring users can manage their preferences.",
    "Cookie Preference Center Links to Imprint and Privacy Policy": "Check if the cookie preference center contains valid and clickable links to the Imprint ('Impressum') and Privacy Policy ('Datenschutzinformationen') pages. Ensure that the links are present within the preference center, clickable, and lead to valid URLs, considering language-specific variations.",
    "Cookie Prefence Center More Info": "Check if the consumer can click on '+' or 'More information' for each cookie category and verify that additional details become visible.",
    "Clear CTA": "CTA must be recognizable and has to have a clear wording" ,
    "Age Limitation": "Check if the age limit is 18",
    "Newsletter Wording": "Check if the wording of the newsletter is correct",
    "Imprint": "Check for the presence of imprint.",
    "Imprint Horizontal": "Check if theres a Horizontal Scrollbar",
    "Imprint Length": "Check if how long the Imprint is",
    "Footer cookie": "Check if the cookies are in the page footer",
    "Footer imprint": "Check if the imprint is in the page footer",
    "Footer privacy policy": "Check if the privacy policy is in the page footer",
    "Footer links": "Check if the links in the page footer work properly",
    "Newsletter Functionality" : "Check if the functionality of the 4 Links in the Newsletter is correct",
    "Newsletter More Details": "Check if the More Details Button is avaiable and if yes, check the wording of the additional text."
    
}

# Retrieve stored templates or use default values
def get_templates():
    return session.get('templates', DEFAULT_TEMPLATES)  # This line should retrieve the default if not set

# Store new templates in session
def set_templates(new_templates):
    session['templates'] = new_templates

@app.route('/', methods=['GET', 'POST'])
def index():
    """Landing page where users enter a URL for compliance checks."""
    if request.method == 'POST':
        url = request.form['url']
        session['url'] = url  # Store the URL in session
        return redirect(url_for('templates'))  # Redirect to templates page
    return render_template('index.html')

@app.route('/templates', methods=['GET', 'POST'])
def templates():
    """Page for users to review or modify compliance templates."""
    templates = get_templates()  # Load templates from session
    print("Loaded templates:  ",templates)
    if request.method == 'POST':
        additional_imprint = request.form.getlist('additional_imprint')  # Formulareingaben abholen
        print("Form Data Received:", request.form) 
        new_templates = {
            'imprint': request.form.get('imprint', DEFAULT_TEMPLATES['imprint']),
            'newsletterdetail': request.form.get('newsletterdetail', DEFAULT_TEMPLATES['newsletterdetail']),
            'cookie_policy': request.form.get('cookie_policy', DEFAULT_TEMPLATES['cookie_policy']),
            'newsletter': request.form.get('newsletter', DEFAULT_TEMPLATES['newsletter']),
            'additional_imprint': request.form.getlist('additional_imprint[]')   # Save additional terms
        }
        set_templates(new_templates)  # Save templates in session
        print("Debug (templates): Templates saved in session:", session['templates'])  # Debugging
        return redirect(url_for('check_compliance'))
    return render_template('templates.html', templates=templates, DEFAULT_TEMPLATES=DEFAULT_TEMPLATES)


@app.route('/check_compliance') 
async def check_compliance():
    """Asynchronously checks the website's compliance based on selected criteria."""
    url = session.get('url')
    if not url:
        return redirect(url_for('index'))

    start_time = datetime.now()  # Record start time for performance measurement



    # Instantiate compliance checkers
    checker = CookieBannerVis()
    checker2 = WithoutConsentChecker()
    checker3 = CookieSelectionChecker()
    checker4 = CookieBannerText()
    checker5 = CookieBannerLinkValidator()
    checker_scrollbar = ScrollbarChecker()
    checker_conform_design = ConformDesignChecker()
    checker_cookie_more_info = CookieInfoChecker()
    preference_center_vis = CookiePreferenceVis()
    preference_center_link_validator = CookiePreferenceLinkValidator()
    checkern1 = ClearCTA(url)
    checkern2 = AgeLimitation(url)
    checkern3 = NewsletterWording(url)
    checkern5 = NewsletterFunctionality(url)
    checkerm1 = ImprintChecker()
    checkerm2 = AsyncImprintVisibilityChecker()
    checkerm3 = FooterLinkChecker()
    checkerm4 = AsyncFooterValidator()

    # Initialize criteria results and feedback results
    criteria_results = {}
    feedback_results = {}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Run various compliance checks asynchronously
            tasks = [
                checker.check_visibility(url),
                checker2.check_ohne_einwilligung_link(url),
                checker3.check_cookie_selection(url),
                checker5.check_banner_and_links(url),
                checker_scrollbar.check_cookie_banner_with_scrollbar(url),
                preference_center_vis.check_visibility_and_preference_center(url),
                preference_center_link_validator.check_preference_links(url),
                checker_cookie_more_info.find_more_info_buttons(browser, url),  # Pass the browser here
                checkern1.check_clear_cta(),  
                checkern2.check_age_limitation(),
                checkerm2.check_scrollable(url), 
                checkern5.check_newsletter_functionality(),
                checkerm3.check_footer_links_on_all_pages(url),
                checkerm4.check_footer_links(url)
            ]
    
            footer_failed_links = await checkerm3.check_footer_links_on_all_pages(url)
    
            # Sync check for ImprintChecker (not asynchronous)
            templates = get_templates()
            additional_imprint = templates.get('additional_imprint', [])
            
            print("Debug (check_compliance): Loaded additional_imprint:", additional_imprint)  # Debugging
    
            # Check whether terms are available
            if not additional_imprint:
                print("No additional Imprint terms found.")
            imprint_url, term_results, _, _ = checkerm1.check_terms(url, additional_imprint)
            print("Debug (check_compliance): Term Results from checkerM1:", term_results)
    
            # Feedback for the Imprint
            imprint_feedback = f"Imprint found at {imprint_url}." if imprint_url else "No valid Imprint link found."
    
            # Populate criteria results
            criteria_results["Imprint URL"] = True if imprint_url else False
            feedback_results["Imprint URL"] = imprint_feedback or "No feedback available"
    
    
            # Debug: Output of the imprint results
            print(f"Imprint URL: {imprint_url}")
            print(f"Imprint Terms Results: {term_results}")
    
            # Checking the footer links
            if footer_failed_links:
                criteria_results["Footer Links"] = False

                feedback_results["Footer Links"] = f"The following footer links do not work: {', '.join(footer_failed_links)}"
            else:
                criteria_results["Footer Links"] = True
                feedback_results["Footer Links"] = "All footer links work properly."
    
    
            # Wait for all asynchronous tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Debug print
            for idx, result in enumerate(results):
                print(f"Task {idx} result: {result} (Type: {type(result)})")
    
            # Process asynchronous results
            banner_result, banner_feedback = results[0] if not isinstance(results[0], Exception) else (False, str(results[0]))
            ohne_einwilligung_result, ohne_feedback = results[1] if not isinstance(results[1], Exception) else (False, str(results[1]))
            selection_result, selection_feedback = results[2] if not isinstance(results[2], Exception) else (False, str(results[2]))
            imprint_privacy_result, imprint_privacy_feedback = results[3] if not isinstance(results[3], Exception) else (False, str(results[3]))
            cookie_banner_scrollbar_result, cookie_banner_scrollbar_feedback = results[4] if not isinstance(results[4], Exception) else (False, str(results[4]))
            preference_center_vis_result, preference_center_vis_feedback = results[5] if not isinstance(results[5], Exception) else (False, str(results[5]))
            preference_center_links_result, preference_center_links_feedback = results[6] if not isinstance(results[6], Exception) else (False, str(results[6]))
            cookie_banner_more_info_result, cookie_banner_more_info_feedback = results[7] if not isinstance(results[7], Exception) else (False, str(results[7]))
            cta_result, cta_feedback = results[8] if not isinstance(results[8], Exception) else (False, str(results[8]))
            age_limitation_result, age_limitation_feedback = results[9] if not isinstance(results[9], Exception) else (False, str(results[9]))
            imprint_visibility_result, imprint_visibility_feedback = results[10] if not isinstance(results[10], Exception) else (False, str(results[10]))
            newsletter_functionality_result, newsletter_functionality_feedback = results[11] if not isinstance(results[11], Exception) else ({}, "Error during newsletter functionality check.")
            footer_results = results[-1] if not isinstance(results[-1], Exception) else {"imprint": False, "privacy policy": False, "cookie": False}

            # Perform text comparison
            try:
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
             checkern3 = NewsletterWording(url)
             templates = get_templates()
             newsletter_template = templates['newsletter']

             # Execute the verification
             conformity, similarity, feedback = await checkern3.check_newsletter_wording(url, newsletter_template)
    
             
             newsletter_wording_result = conformity
             newsletter_wording_feedback = feedback  
             
             criteria_results["Newsletter Wording"] = conformity
             feedback_results["Newsletter Wording"] = feedback
             
            except Exception as e:
             
             newsletter_wording_result = False
             newsletter_wording_feedback = f"<strong>Error during newsletter text check:</strong> {e}"
    
             feedback_results["Newsletter Wording"] = newsletter_wording_feedback
    
    
            # More Details Check
            try:
             checkern4 = MoreDetails(url)
             templates = get_templates()
             newsletter_more_details_template = templates['newsletterdetail']
    
            # Execute the verification
             conformity, similarity, feedback = await checkern4.check_newsletter_more_details(expected_text=newsletter_more_details_template)
            
             newsletter_details_result = conformity
             newsletter_details_feedback = feedback  
    
             feedback_results["Newsletter More Details"] = feedback
    
            except Exception as e:
             
             newsletter_details_result = False
             newsletter_details_feedback = f"<strong>Error during More Details check:</strong> {e}"
    
             feedback_results["Newsletter More Details"] = newsletter_details_feedback
            
            # Conform Design Check    
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    # Perform the "Conform Design" check using the `checker_conform_design` instance
                    # This checks if the cookie banner follows a predefined layout and styling rules
                    conform_design_result, conform_design_feedback = await checker_conform_design.check_all_conformity(browser, url)
                # Ensure the browser is properly closed after the check is completed
                await browser.close()
            except Exception as e:
                print(f"Error during checks: {e}")
                # Store the failure in the results dictionary
                criteria_results["Conform Design"] = False  # Indicate that the check failed
                # Provide error feedback to be included in the final report
                feedback_results["Conform Design"] = f"Error: {e}"
    
    
            # Populate criteria results
            criteria_results = {
                "Cookie Banner Visibility": banner_result,
                "Continue Without Consent Link": ohne_einwilligung_result,
                "Cookie Selection": selection_result,
                "Cookie Banner Text Comparison": text_comparison_result,
                "Cookie Banner Links to Imprint and Privacy Policy": imprint_privacy_result,
                "Cookie Banner Scrollbar": cookie_banner_scrollbar_result,
                "Conform Design":conform_design_result,
                "Cookie Preference Accessibility": preference_center_vis_result,
                "Cookie Preference Center Links to Imprint and Privacy Policy": preference_center_links_result,
                "Cookie Prefence Center More Info": cookie_banner_more_info_result,
                "Clear CTA": cta_result,
                "Age Limitation": age_limitation_result,
                "Newsletter Wording": newsletter_wording_result,
                "Newsletter Functionality": all(newsletter_functionality_result.values()) if isinstance(newsletter_functionality_result, dict) else False,
                "Newsletter More Details" : newsletter_details_result,
                "Imprint URL": imprint_url or "Not found",       
                "Imprint Visibility": imprint_visibility_result,
                "Footer Links": not bool(footer_failed_links),
                "Footer Imprint": footer_results.get("imprint", False),
                "Footer privacy policy": footer_results.get("privacy policy", False),
                "Footer cookie settings": footer_results.get("cookie", False)

            }
            
    
            # Add detailed imprint terms check
            for term, found in term_results.items():
                criteria_results[f"Imprint Term: {term}"] = found
    
            # Populate feedback results
            feedback_results = {
                "Cookie Banner Visibility": banner_feedback,
                "Continue Without Consent Link": ohne_feedback,
                "Cookie Selection": selection_feedback,
                "Cookie Banner Text Comparison": text_comparison_feedback,
                "Cookie Banner Links to Imprint and Privacy Policy": imprint_privacy_feedback,
                "Cookie Banner Scrollbar": cookie_banner_scrollbar_feedback,
                "Conform Design":conform_design_feedback,
                "Cookie Preference Accessibility": preference_center_vis_feedback,
                "Cookie Preference Center Links to Imprint and Privacy Policy": preference_center_links_feedback,
                "Cookie Prefence Center More Info": cookie_banner_more_info_feedback,
                "Clear CTA": cta_feedback,
                "Age Limitation": age_limitation_feedback,
                "Newsletter Wording": newsletter_wording_feedback,
                "Newsletter Functionality": newsletter_functionality_feedback,
                "Newsletter More Details": newsletter_details_feedback,
                "Imprint Check": imprint_feedback,         
                "Imprint Visibility" : imprint_visibility_feedback,
                "Footer Links": f"The following footer links do not work: {', '.join(footer_failed_links)}" 
                        if footer_failed_links else "All footer links work properly.",
                "Footer Imprint": "Imprint-Link found." if footer_results.get("imprint") else "Imprint link missing!",
                "Footer privacy policy": "Privacy policy link found." if footer_results.get("privacy policy") else "privacy policy link is missing!",
                "Footer cookie settings": "Cookie settings link found." if footer_results.get("cookie") else "Cookie settings link missing!"

            }
    
            # Add feedback for imprint terms
            for term, found in term_results.items():
              feedback_results[f"Imprint Term: {term}"] = (
              f"Term '{term}' was found." if found else f"Term '{term}' was not found."
            )
    
            # Debug: Output of criteria and feedback results
            print(f"Criteria Results: {criteria_results}")
            print(f"Feedback Results: {feedback_results}")

    except Exception as e:
        # Handle errors gracefully and populate default feedback
        print(f"Error during compliance check: {e}")
        criteria_results = {key: False for key in CRITERIA}
        feedback_results = {key: f"Error: {e}" for key in CRITERIA}

    # Determine conformity based on all criteria results
    conformity = "Yes" if all(criteria_results.values()) else "No"

    # Capture end time and calculate duration
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Generate PDF
    date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf_content = generate_pdf(
        url,
        conformity,
        criteria_results,
        feedback_results,
        date_time,
        duration
    )

    # Save to database
    await asyncio.to_thread(save_result, url, conformity, pdf_content)  # Save to database in a thread

    return redirect(url_for('results'))

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
        ''')
        
        # Insert new results
        cursor.execute('''
            INSERT INTO compliance (url, conformity, conformity_details)
            VALUES (?, ?, ?)
        ''', (url, conformity, pdf_content))

        conn.commit()  # Save changes
    except sqlite3.Error as e:
        print(f"An error occurred while saving to database: {e}")
    finally:
        conn.close()

def generate_pdf(url, conformity, criteria_results, feedback_results, date_time, duration):
    """
    Generates a compliance report as a PDF document.

    Parameters:
    - url (str): The URL of the website being evaluated.
    - conformity (str): The overall conformity result (Yes/No).
    - criteria_results (dict): Dictionary storing the pass/fail status of each compliance criterion.
    - feedback_results (dict): Dictionary storing detailed feedback for each criterion.
    - date_time (str): Timestamp when the report was generated.
    - duration (float): Time taken to generate the report.

    Returns:
    - bytes: PDF file content in memory (if successful), otherwise None.
    """
    html_content = ""  # Ensure variable initialization to avoid errors
    templates = session.get('templates', {})
    additional_imprint = templates.get('additional_imprint', [])

    # Construct the HTML structure for the PDF report
    html_content += f'''
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
    # Check if Imprint URL is part of the results and add it separately
    if "Imprint URL" in criteria_results:
        imprint_feedback = feedback_results.get("Imprint Check", "No feedback available.")
        
        # If no additional terms were defined for the Imprint check, notify the user
        if not additional_imprint:
            imprint_feedback += " Note: No terms were defined for the imprint check. The check could therefore not take place."

        html_content += f'''
        <tr>
            <td style="padding: 10px;">Imprint URL</td>
            <td style="padding: 10px; text-align: center; vertical-align: middle; font-size: 20px;">{'✔️' if criteria_results['Imprint URL'] else '❌'}</td>
            <td style="padding: 10px;">{imprint_feedback}</td>
        </tr>
        '''   

    # Loop through other criteria and add them to the PDF
    for criterion, met in criteria_results.items():
        if criterion == "Imprint URL":
            continue # Skip Imprint URL since it was handled separately
        status = "✔️" if met else "❌"
        feedback = feedback_results.get(criterion, "No feedback available.")
    
        # Debugging: Output of individual criteria and their feedback
        print(f"Adding to PDF -> Criterion: {criterion}, Status: {status}, Feedback: {feedback}")
    

        html_content += f'''
        <tr>
        <td style="padding: 10px;">{criterion}</td>
        <td style="padding: 10px; text-align: center; vertical-align: middle; font-size: 20px;">{status}</td>
        <td style="padding: 10px;">{feedback}</td>
        </tr>
        '''

    html_content += '</table>' # Close the table

    # Generate the PDF from the HTML content
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
    
    # Check if PDF generation was successful
    if pisa_status.err:
        print("Error generating PDF")  # Log the error
        return None # Return None in case of failure

    pdf_buffer.seek(0) # Move buffer position to start before returning
    return pdf_buffer.read()


@app.route('/results')
def results():
    """
    Retrieves the most recent compliance check result from the database and renders the results page.

    Returns:
    - Renders 'results.html' template with the latest compliance check details.
    """
    conn = sqlite3.connect('compliance.db')
    cursor = conn.cursor()
    # Query the latest compliance check result from the database
    cursor.execute('SELECT id, date, url, conformity FROM compliance ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    # Store the result in a dictionary for template rendering
    if row:
        result = {
            'id': row[0],
            'date':row[1],
            'url': row[2],
            'conformity': row[3],
        }
    else:
        result = {} # No results found, return empty dictionary

    return render_template('results.html', result=result)

@app.route('/download/<int:id>')
def download(id):
    """
    Allows users to download a previously generated compliance report as a PDF.

    Parameters:
    - id (int): The database ID of the compliance report.

    Returns:
    - The PDF file for download, or a 404 error if not found.
    """
    conn = sqlite3.connect('compliance.db')
    cursor = conn.cursor()
    # Retrieve the compliance report PDF content by its ID
    cursor.execute('SELECT conformity_details FROM compliance WHERE id = ?', (id,))
    pdf_content = cursor.fetchone()
    
    # Check if the PDF exists in the database
    if pdf_content is None:
        return "No PDF found.", 404  # Handle the case where no PDF exists for the ID
    
    pdf_content = pdf_content[0]  # Get the actual bytes from the tuple
    conn.close()
    
    # Serve the PDF file as a downloadable attachment
    return send_file(
        io.BytesIO(pdf_content),
        download_name='compliance_report.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )

def execute_query(query, params=()):
    """
    Executes an SQL query and returns the results.

    Parameters:
    - query (str): The SQL query string.
    - params (tuple): Optional parameters for the SQL query.

    Returns:
    - list: Query results as a list of tuples.
    """
    conn = sqlite3.connect('compliance.db') # Connect to SQLite database
    cursor = conn.cursor()
    # Execute the provided query with optional parameters
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results # Return the query results

@app.route('/reset_templates', methods=['POST'])
def reset_templates():
    # Set templates to default values
    session['templates'] = DEFAULT_TEMPLATES
    return '', 204  # Return: No content, just success status



@app.route('/database', methods=['GET'])
def database():
    page = request.args.get('page', 1, type=int)  # Query the current page
    selected_url = request.args.get('url', 'all', type=str)  # Filtered URL
    per_page = 10  # Number of entries per page
    offset = (page - 1) * per_page  # Calculation of the offset
    
    # Retrieve customer URLs for the dropdown
    customers_query = "SELECT DISTINCT url FROM compliance"
    customers = execute_query(customers_query)

    # Database query based on the filtering
    if selected_url == 'all':
        query = "SELECT * FROM compliance ORDER BY id DESC LIMIT ? OFFSET ?"
        params = (per_page, offset)
    else:
        query = "SELECT * FROM compliance WHERE url = ? ORDER BY id DESC LIMIT ? OFFSET ?"
        params = (selected_url, per_page, offset)

    # Execute the query
    compliance = execute_query(query, params)

    # Get the total number of entries
    total_records_query = "SELECT COUNT(*) FROM compliance"
    total_records = execute_query(total_records_query)[0][0]

    # Calculate the total number of pages
    total_pages = (total_records + per_page - 1) // per_page

    # Pagination logic
    max_pages_to_show = 5
    if total_pages > max_pages_to_show:
        page_links = range(max(1, page - 2), min(page + 2, total_pages) + 1)
        if page > 3:
            page_links = ['1', '...'] + list(page_links)
        if page < total_pages - 2:
            page_links = list(page_links) + ['...', str(total_pages)]
    else:
        page_links = range(1, total_pages + 1)

    # Render the template and pass the variables
    return render_template(
        'database.html',
        records=compliance,  # Table contents
        page=page,  # Current page
        total_pages=total_pages,  # Total number of pages
        page_links=page_links,  # Pagination links
        customers=customers,  # Customer URLs for the dropdown
        selected_url=selected_url  # Currently selected URL
    )


if __name__ == '__main__':
    app.run(debug=True)
