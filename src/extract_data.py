import re
from extract_full_text import extract_text_from_pdf

PATTERNS = {
    "id": [
        r'FACTURA\s+([A-Z]+[0-9]+)',
        r'INVOICE\s*([A-Z]+[0-9]+)',
    ],
    "issue_date": [
        r'Data\s*emiterii[:\s]*([\d/]+)',
        r'Issue\s*date[:\s]*([\d/]+)',
    ],
    "cif": [
        r'CIF:\s*RO24386686\s*CIF[:\s]*([A-Z0-9]+)',
        r'VAT\s*CODE:\s*RO24386686\s*VAT\s*CODE[:\s]*([A-Z0-9]+)',
    ],
    "client": [
        r'ADVANCED\s*IDEAS\s*STUDIO\s*S\.R\.L\.\s*([^\n]+)',
    ],
    "currency": [
        r'-([Lei]{3})-',
        r'-([EUR]{3})-',
    ],
    "total_value": [
        r'TOTAL\s*PLATA\s*([0-9]+\.[0-9]+)',
        r'Total\s*value\s*([0-9]+\.[0-9]+)',
    ],
    "exchange_rate" : [
        r'Curs\s*1\s*EUR\s*=\s*([0-9]+\.[0-9]+)',
        r'Exchange\s*rate\s*1\s*EUR\s*=\s*([0-9]+\.[0-9]+)',
    ],
    "total_value_ron": [
        r'Total\s*value\s*[0-9]+\.[0-9]+\s*EUR\s*([0-9]+\.[0-9]+)\s*Lei',
    ]
}

def extract_data(text):
    results = {}
    for field, patterns in PATTERNS.items():
        value = None
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                value = match.group(1)
                break
        results[field] = value
    print(results)

if __name__ == "__main__":
    print("\n---Romanian invoice---\n")
    extract_data(extract_text_from_pdf("mock-documents/invoice.pdf"))

    print("\n---English Envoice---\n")
    extract_data(extract_text_from_pdf("mock-documents/invoice_eng.pdf"))
