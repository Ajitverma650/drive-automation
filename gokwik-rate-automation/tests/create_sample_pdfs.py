"""Create sample Agreement PDF and Rate Card PDF for testing."""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


def create_agreement_pdf(path="sample_agreement.pdf"):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(inch, h - inch, "Master Service Agreement (MSA)")

    c.setFont("Helvetica", 12)
    y = h - 1.8 * inch
    lines = [
        "This Master Service Agreement is entered into between",
        "GoKwik Technologies Pvt. Ltd. and Jaipur Masala Company.",
        "",
        "Agreement effective date: 01/03/2026",
        "",
        "The terms and conditions outlined herein shall govern",
        "the relationship between the parties for the provision",
        "of checkout optimization and payment services.",
        "",
        "Signed on behalf of both parties.",
        "",
        "Start date of services: 01/03/2026",
    ]

    for line in lines:
        c.drawString(inch, y, line)
        y -= 20

    c.save()
    print(f"Created: {path}")


def create_rate_pdf(path="sample_rate_card.pdf"):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(inch, h - inch, "TPPA Platform Fees - Rate Card")

    c.setFont("Helvetica", 11)
    c.drawString(inch, h - 1.6 * inch, "Merchant: Jaipur Masala Company")
    c.drawString(inch, h - 1.9 * inch, "Effective from: 01/03/2026")

    # Table header
    y = h - 2.6 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(inch, y, "Modes")
    c.drawString(4 * inch, y, "Commercials")
    y -= 5
    c.line(inch, y, 6 * inch, y)
    y -= 18

    # Rate data
    c.setFont("Helvetica", 11)
    rates = [
        ("UPI", "2.5%"),
        ("DC Below2K", "2.5%"),
        ("DC Above2K", "2.5%"),
        ("Credit Card", "2.5%"),
        ("CC EMI", "0%"),
        ("DC EMI", "2.5%"),
        ("Debit Card EMI", "0%"),
        ("Card Less EMI", "0%"),
        ("Amex", "3%"),
        ("UPI Credit Card (Rupay only)", "3%"),
        ("Net Banking", "2.5%"),
        ("Diners Credit Card", "2.5%"),
        ("Corporate Credit Card", "3%"),
        ("Wallets", "2.5%"),
        ("BNPL", "0%"),
        ("International CC", "0%"),
    ]

    for mode, rate in rates:
        c.drawString(inch, y, mode)
        c.drawString(4 * inch, y, rate)
        y -= 18

    c.save()
    print(f"Created: {path}")


if __name__ == "__main__":
    try:
        create_agreement_pdf()
        create_rate_pdf()
        print("\nSample PDFs created successfully!")
    except ImportError:
        print("reportlab not installed. Install with: pip install reportlab")
        print("Creating text-based PDFs instead...")

        # Fallback: use a simpler approach
        _create_simple_pdfs()


def _create_simple_pdfs():
    """Fallback using fpdf2 or just raw text files renamed to .pdf for testing."""
    try:
        from fpdf import FPDF

        # Agreement PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Master Service Agreement", ln=True)
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, "Agreement effective date: 01/03/2026", ln=True)
        pdf.cell(0, 10, "Start date: 01/03/2026", ln=True)
        pdf.output("sample_agreement.pdf")

        # Rate PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "TPPA Platform Fees", ln=True)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(80, 8, "Modes", border=1)
        pdf.cell(40, 8, "Commercials", border=1, ln=True)
        pdf.set_font("Helvetica", "", 11)
        for mode, rate in [
            ("UPI", "2.5%"), ("DC Below2K", "2.5%"), ("DC Above2K", "2.5%"),
            ("Credit Card", "2.5%"), ("CC EMI", "0%"), ("DC EMI", "2.5%"),
            ("Debit Card EMI", "0%"), ("Card Less EMI", "0%"), ("Amex", "3%"),
            ("UPI Credit Card (Rupay only)", "3%"), ("Net Banking", "2.5%"),
            ("Diners Credit Card", "2.5%"), ("Corporate Credit Card", "3%"),
            ("Wallets", "2.5%"), ("BNPL", "0%"), ("International CC", "0%"),
        ]:
            pdf.cell(80, 8, mode, border=1)
            pdf.cell(40, 8, rate, border=1, ln=True)
        pdf.output("sample_rate_card.pdf")

        print("Created sample PDFs with fpdf2!")
    except ImportError:
        print("Install reportlab or fpdf2: pip install reportlab")
