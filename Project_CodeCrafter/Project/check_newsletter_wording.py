
import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from difflib import SequenceMatcher, ndiff
from spellchecker import SpellChecker
import re

class NewsletterWording:
    def __init__(self, url=None):
        self.url = url
        self.spell_checker = SpellChecker(language='de')

        # Custom words for spell checking
        self.spell_checker.word_frequency.load_words([
            "Drittunternehmen", "Einwilligungsbedürftige", "Datenschutzerklärung", "Rechtsgrundlagen",
            "Einwilligung", "Zweck", "ID", "Datenschutzinformationen", "zuzuschneiden", "Onlineangeboten",
            "Marketingbemühungen", "Auswertungsmöglichkeiten", "Schaltfläche", "Überwachungszwecken",
            "Rechtsbehelfsmöglichkeiten"
        ])

        self.checkbox_selector = 'input[type="checkbox"]'  # standard selector for checkboxes

    async def extract_text_after_checkbox(self, url, template_text):
     """Extracts text from the modal or checkboxes and performs a similarity comparison."""
     try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            print(f"Navigating to URL: {url}")
            await page.goto(url, timeout=60000)

            # Ensure we're on the newsletter page
            if 'newsletter' not in page.url.lower():
                print("Error: Not on the newsletter page. The URL is incorrect.")
                await browser.close()
                return "Error: No newsletter page found.", 0

            # List to store all found texts
            potential_texts = []

            # Now that we've reached the newsletter page, we extract text from the checkboxes first
            print("Proceeding to search for checkboxes on the newsletter page...")
            try:
                await page.wait_for_selector(self.checkbox_selector, timeout=30000)  # Wait for checkboxes on the newsletter page
                checkboxes = await page.query_selector_all(self.checkbox_selector)
                print(f"Found {len(checkboxes)} checkboxes on the page.")

                # Extract text associated with checkboxes
                for checkbox in checkboxes:
                    associated_text = await checkbox.evaluate(
                        '''(node) => {
                            let sibling = node.nextElementSibling;
                            let associatedTexts = [];
                            while (sibling) {
                                if (sibling.textContent.trim()) associatedTexts.push(sibling.textContent.trim());
                                sibling = sibling.nextElementSibling;
                            }
                            let label = document.querySelector(label[for='${node.id}']);
                            if (label && label.textContent.trim()) associatedTexts.push(label.textContent.trim());
                            return associatedTexts.join(" ");
                        }'''
                    )
                    if associated_text:
                        potential_texts.append(associated_text.strip())
            except Exception as e:
                print(f"No checkboxes found")

            # Fallback: If no checkboxes found, extract text from the entire body of the newsletter page
            if not potential_texts:
                print("No checkboxes found, extracting entire text from the body of the newsletter page.")
                try:
                    page_text = await page.inner_text('body')
                    potential_texts.extend(page_text.split('\n'))
                    print(f"Extracted page text from newsletter page.")
                except Exception as e:
                    print(f"Error extracting page text: {e}")

            print("Potential texts found:", potential_texts)

            # Searching for iframe texts
            print("Searching for text inside iframe...")
            try:
                # Find the iframe on the page
                iframe_element = await page.query_selector('iframe')
                if iframe_element:
                    # Wait for the iframe to load
                    iframe = await iframe_element.content_frame()

                    # Extract all text from the iframe (could be refined further for specific elements)
                    iframe_text = await iframe.inner_text('body')  # Extracting all text in the iframe body
                    print(f"Extracted text from iframe body: {iframe_text[:200]}...")  # Print a snippet for debugging
                    
                    # Add the iframe text to potential texts for similarity comparison
                    potential_texts.append(iframe_text.strip())
                else:
                    print("No iframe found on the page.")
            except Exception as e:
                print(f"Error accessing iframe: {e}")

            # If no texts are found, return feedback
            if not potential_texts:
                print("No relevant text found on the newsletter page.")
                return "No relevant text found.", 0

            # Step 1: Compare all potential texts and find the best match based on similarity
            best_match = max(potential_texts, key=lambda x: SequenceMatcher(None, template_text, x).ratio())
            best_similarity = SequenceMatcher(None, template_text, best_match).ratio() * 100

            print(f"Best match based on similarity: {best_match} (Similarity: {best_similarity:.2f}%)")

            # Step 2: Check for prioritized keywords in the best match
            priority_keywords = ["Kenntnis", "email", "bestätigen", "einverstanden", "Sign up", "informiert", "Registrierung", "Einwilligung", "persönliche Daten"]
            if any(keyword.lower() in best_match.lower() for keyword in priority_keywords):
                print("Prioritized text contains keywords, returning this match.")
                return best_match.strip(), best_similarity

            # Step 3: If the best match exceeds the similarity threshold, return it
            similarity_threshold = 50  # Minimum similarity threshold (can be adjusted)
            if best_similarity >= similarity_threshold:
                print("Best match passed threshold, returning:", best_match)
                return best_match.strip(), best_similarity

            # If no good match is found, return the best match anyway
            print("No prioritized text found, returning best match anyway.")
            return best_match.strip(), best_similarity

     except Exception as e:
        print(f"Error extracting text after checkbox: {e}")
        return f"Error extracting text after checkbox: {str(e)}", 0


    def show_diff(self, template_text, website_text):
        """Can be aktivated in case the user wants the differences word for word in the pdf."""
        diff = ndiff(template_text.split(), website_text.split())
        differences = []
        for change in diff:
            if change.startswith('- '):
                differences.append(f"Missing in website: {change[2:]}")
            elif change.startswith('+ '):
                differences.append(f"Extra in website: {change[2:]}")
        return differences

    async def check_newsletter_wording(self, url, template_text):
     try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Special handling for loreal-paris.de
            if "https://www.loreal-paris.de" in url:
                newsletter_url = "https://cloud.mail.lorealpartnershop.com/lorealprofessionnelparis-anmeldung-newsletter"
                print(f"Detected 'loreal-paris.de', redirecting to newsletter URL: {newsletter_url}")
                await page.goto(newsletter_url)
                await page.wait_for_load_state('networkidle')

                
                checkbox_text, similarity = await self.extract_text_after_checkbox(newsletter_url, template_text)
                if not checkbox_text or "No relevant text found" in checkbox_text:
                    feedback = "No relevant text found on the newsletter page."
                    await browser.close()
                    return False, 0, feedback

                # differences = self.show_diff(template_text, checkbox_text)  # the comment can be edited in case it is necessary for the user to know the differences
                feedback = f"""
                <strong>Template Text:</strong> {template_text}<br>
                <strong>Extracted Text:</strong> {checkbox_text}<br>
                <strong>Similarity:</strong> {similarity:.2f}%<br>
                """
                await browser.close()
                return True, similarity, feedback
            
            
            if "https://www.schwarzkopf.de" in self.url:
                print(f"Detected 'schwarzkopf.de', clicking 'ANMELDEN' for newsletter.")
    
                # Navigate to the homepage
                await page.goto(self.url)
                await page.wait_for_load_state('networkidle')

                # Wait for the "ANMELDEN" button and ensure it is visible
                sign_up_button = await page.query_selector('button.calltoaction__link.cta:has-text("ANMELDEN")')
                if sign_up_button:
                    print("Clicking 'ANMELDEN' button to trigger the modal.")
                    await sign_up_button.click()

                    # Wait for the modal container to become visible
                    try:
                        print("Waiting for modal to appear...")

                        # Wait for the modal to appear (using the wrapper or a more general modal container)
                        await page.wait_for_selector('div.calltoaction__wrapper.cta', state='visible', timeout=30000)

                        # Optionally, add a small delay to allow any dynamic content to fully load
                        await asyncio.sleep(3)

                        checkbox_text, similarity = await self.extract_text_after_checkbox(url, template_text)

                        if not checkbox_text or "No relevant text found" in checkbox_text:
                            feedback = "No relevant text found in the modal."
                            await browser.close()
                            return False, 0, feedback

                        feedback = f"""
                        <strong>Template Text:</strong> {template_text}<br>
                        <strong>Extracted Text:</strong> {checkbox_text}<br>
                        <strong>Similarity:</strong> {similarity:.2f}%<br>
                        """
                        await browser.close()
                        return True, similarity, feedback
                    except Exception as e:
                        print(f"Error or timeout waiting for modal: {str(e)}")
                        result = False
                        feedback = "Error: Modal did not appear or was not visible."
                        await browser.close()
                        return result, 0, feedback
                else:
                    print("Could not open pop-up modal.")
                    feedback = "Could not open pop-up modal."
                    await browser.close()
                    return False, 0, feedback
                    
            # redirecting for krombacher
            if "https://www.krombacher.de" in self.url:
                newsletter_url = "https://www.krombacher.de/die-brauerei/newsletter-anmeldung"
                print(f"Detected 'krombacher.de', redirecting to newsletter URL: {newsletter_url}")
                await page.goto(newsletter_url)
                await page.wait_for_load_state('networkidle')

                
                checkbox_text, similarity = await self.extract_text_after_checkbox(newsletter_url, template_text)
                if not checkbox_text or "No relevant text found" in checkbox_text:
                    feedback = "No relevant text found on the newsletter page."
                    await browser.close()
                    return False, 0, feedback

                # differences = self.show_diff(template_text, checkbox_text)  # the comment can be edited in case it is necessary for the user to know the differences
                feedback = f"""
                <strong>Template Text:</strong> {template_text}<br>
                <strong>Extracted Text:</strong> {checkbox_text}<br>
                <strong>Similarity:</strong> {similarity:.2f}%<br>
                """
                await browser.close()
                return True, similarity, feedback
            
            # Special handling for tesa.com
            if "https://www.tesa.com" in url:
                newsletter_url = "https://www.tesa.com/de-de/buero-und-zuhause/do-it-yourself-magazin/newsletter"
                print(f"Detected 'tesa.com', redirecting to newsletter URL: {newsletter_url}")
                await page.goto(newsletter_url)
                await page.wait_for_load_state('networkidle')

                
                checkbox_text, similarity = await self.extract_text_after_checkbox(newsletter_url, template_text)
                if not checkbox_text or "No relevant text found" in checkbox_text:
                    feedback = "No relevant text found on the newsletter page."
                    await browser.close()
                    return False, 0, feedback

                # differences = self.show_diff(template_text, checkbox_text)  # the comment can be edited in case it is necessary for the user to know the differences
                feedback = f"""
                <strong>Template Text:</strong> {template_text}<br>
                <strong>Extracted Text:</strong> {checkbox_text}<br>
                <strong>Similarity:</strong> {similarity:.2f}%<br>
                """
                await browser.close()
                return True, similarity, feedback
            
        
            
            # Special handling for hansgrohe
            if "https://www.hansgrohe.de" in url:
                newsletter_url = "https://www.hansgrohe.de/#interest-form"
                print(f"Detected 'hansgrohe.de', redirecting to newsletter URL: {newsletter_url}")
                await page.goto(newsletter_url)
                await page.wait_for_load_state('networkidle')

                
                checkbox_text, similarity = await self.extract_text_after_checkbox(newsletter_url, template_text)
                if not checkbox_text or "No relevant text found" in checkbox_text:
                    feedback = "No relevant text found on the newsletter page."
                    await browser.close()
                    return False, 0, feedback

                # differences = self.show_diff(template_text, checkbox_text)  # the comment can be edited in case it is necessary for the user to know the differences
                feedback = f"""
                <strong>Template Text:</strong> {template_text}<br>
                <strong>Extracted Text:</strong> {checkbox_text}<br>
                <strong>Similarity:</strong> {similarity:.2f}%<br>
                """
                await browser.close()
                return True, similarity, feedback
            

            # General case: Load the given URL
            try:
                await page.goto(url, timeout=60000)
                await page.wait_for_load_state('networkidle')
            except Exception as e:
                feedback = f"Error loading the URL: {url}, Details: {str(e)}"
                await browser.close()
                return False, 0, feedback
        
            # Check whether the URL is already a newsletter page
            if any(phrase.lower() in url.lower() for phrase in ["newsletter", "subscribe", "email", "signup"]):
                checkbox_text, similarity = await self.extract_text_after_checkbox(url, template_text)
                if not checkbox_text or "No relevant text found" in checkbox_text:
                    feedback = "No relevant text found on the newsletter page."
                    await browser.close()
                    return False, 0, feedback

                # differences = self.show_diff(template_text, checkbox_text)  # the comment can be edited in case it is necessary for the user to know the differences
                feedback = f"""
                <strong>Template Text:</strong> {template_text}<br>
                <strong>Extracted Text:</strong> {checkbox_text}<br>
                <strong>Similarity:</strong> {similarity:.2f}%<br>
                """
                await browser.close()
                return True, similarity, feedback

            # Search links on the page to get to the newsletter page
            links = await page.query_selector_all('a')
            for link in links:
                try:
                    href = await link.get_attribute('href')
                    if href:
                        full_url = urljoin(url, href)


                        # Ignore imprint, data protection and general terms and conditions links
                        ignore_keywords = ["impressum", "datenschutz", "agb", "privacy", "legal"]
                        if any(ignored in full_url.lower() for ignored in ignore_keywords):
                             print(f" Ignoring irrelevant link: {full_url}")
                             continue  # Skip irrelevant links

                        if any(keyword in full_url.lower() for keyword in ["newsroom", "press", "enews", "newsletter"]):
                            print(f"Found a relevant link: {full_url}")
                            await page.goto(full_url)
                            await page.wait_for_load_state('networkidle')

                            # Check on the linked page
                            checkbox_text, similarity = await self.extract_text_after_checkbox(full_url, template_text)
                            if not checkbox_text or "No relevant text found" in checkbox_text:
                                continue

                            # differences = self.show_diff(template_text, checkbox_text)  # the comment can be edited in case it is necessary for the user to know the differences
                            feedback = f"""
                            <strong>Template Text:</strong> {template_text}<br>
                            <strong>Extracted Text:</strong> {checkbox_text}<br>
                            <strong>Similarity:</strong> {similarity:.2f}%<br>
                            """
                            await browser.close()
                            return True, similarity, feedback
                except Exception:
                    continue

                
            # If no newsletter link is found, check the given URL directly
            print("No relevant newsletter link found, checking the given URL.")
            checkbox_text, similarity = await self.extract_text_after_checkbox(url, template_text)
            if not checkbox_text or "No relevant text found" in checkbox_text:
                feedback = "No relevant text found on the given URL."
                await browser.close()
                return False, 0, feedback

            feedback = f"""
            <strong>Template Text:</strong> {template_text}<br>
            <strong>Extracted Text:</strong> {checkbox_text}<br>
            <strong>Similarity:</strong> {similarity:.2f}%<br>
            """
            await browser.close()
            return True, similarity, feedback
            

     except Exception as e:
        print(f"Error during newsletter wording check: {e}")
        return False, 0, f"Error: {str(e)}"




async def main():
    url = "https://www.loreal-paris.de"
    template_text = (
        "Ja, hiermit willige ich in die Verarbeitung meiner o.g. Kontaktdaten zu Marketingzwecken im Wege der direkten Kontaktaufnahme durch [Marke] sowie die weiteren Marken der L’Oréal Deutschland GmbH ein."
        "Um individuell auf meine Interessen zugeschnittene Informationen zu erhalten, willige ich außerdem ein, dass diese meine Reaktionen im Rahmen der Marketingaktionen sowie meine Interaktionen bei der Nutzung der Webservices der L’Oréal Deutschland GmbH "
        "und ihrer Marken erhebt und in einem Interessenprofil speichert, nutzt sowie meine E-Mail-Adresse oder meine Telefonnummer (soweit angegeben) in verschlüsselter Form an unsere Werbepartner übermittelt, "
        "sodass mir auch bei der Nutzung der Webservices unserer Werbepartner entsprechende Informationen angezeigt werden."
    )

    checker = NewsletterWording(url)

    
    conformity, similarity, feedback = await checker.check_newsletter_wording(url, template_text)

    
    print("\nResults:")
    print("Conformity:", conformity)
    print("Similarity:", f"{similarity:.2f}%")
    print("Feedback:", feedback)

if __name__ == "__main__":
    asyncio.run(main())
