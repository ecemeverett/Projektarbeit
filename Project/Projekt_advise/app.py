import io
import requests
from flask import Flask, render_template, request, send_file, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Konfiguration der SQLite-Datenbank
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reports.db'
db = SQLAlchemy(app)

# Datenbankmodell für gespeicherte PDFs
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    text1 = db.Column(db.String(500), nullable=False)
    text2 = db.Column(db.String(500), nullable=False)
    text3 = db.Column(db.String(500), nullable=False)
    pdf_data = db.Column(db.LargeBinary, nullable=False)


# Route für die Startseite mit URL-Eingabe
@app.route('/')
def index():
    return render_template('index.html')

# Route für die Texteingabe (Schritt 2)
@app.route('/step2', methods=['POST'])
def step2():
    url = request.form.get('url')
    return render_template('step2.html', url=url)

# Route für das Speichern der PDF und Weiterleitung zu Schritt 3
@app.route('/step3', methods=['POST'])
def step3():
    url = request.form.get('url')
    text1 = request.form.get('text1')
    text2 = request.form.get('text2')
    text3 = request.form.get('text3')

    # HTML-Quelltext abrufen und Textabgleich
    try:
        response = requests.get(url)
        page_source = response.text
    except requests.RequestException as e:
        return f"Fehler beim Abrufen der Seite: {e}"

    # Ergebnisse des Abgleichs
    results = {
        "text1_found": text1 in page_source,
        "text2_found": text2 in page_source,
        "text3_found": text3 in page_source
    }

    # PDF generieren
    pdf_buffer = io.BytesIO()
    p = canvas.Canvas(pdf_buffer, pagesize=A4)
    p.drawString(100, 750, f"URL: {url}")
    p.drawString(100, 720, "Impressum-Abgleich: " + ("Gefunden" if results["text1_found"] else "Nicht gefunden"))
    p.drawString(100, 700, "Datenschutz-Abgleich: " + ("Gefunden" if results["text2_found"] else "Nicht gefunden"))
    p.drawString(100, 680, "AGB-Abgleich: " + ("Gefunden" if results["text3_found"] else "Nicht gefunden"))
    p.showPage()
    p.save()

    pdf_buffer.seek(0)

    # PDF in der Datenbank speichern
    new_report = Report(url=url, text1=text1, text2=text2, text3=text3, pdf_data=pdf_buffer.read())
    db.session.add(new_report)
    db.session.commit()


    # Schritt 3 rendern (PDF ist in der Datenbank)
    return render_template('step3.html', report_id=new_report.id)

# Route für das Herunterladen der PDF (Schritt 4)
@app.route('/download/<int:report_id>')
def download_pdf(report_id):
    # Report aus der Datenbank abrufen
    report = Report.query.get_or_404(report_id)

    # PDF-Datei zum Herunterladen anbieten
    return send_file(io.BytesIO(report.pdf_data), as_attachment=True, download_name='report.pdf', mimetype='application/pdf')

# Route zum Anzeigen der gespeicherten PDFs (Admin-Ansicht)
@app.route('/admin')
def view_reports():
    reports = Report.query.all()
    return render_template('admin.html', reports=reports)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Datenbank initialisieren (nur beim ersten Start notwendig)
    app.run(debug=True)

