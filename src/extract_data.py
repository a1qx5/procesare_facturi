import re
from extract_full_text import extract_text_from_pdf

PATTERNS = {
    "id": [
        r'FACTURA\s+([A-Z0-9]+)',
        r'INVOICE\s+([A-Z0-9]+)',
    ],
    "issue_date": [
        r'Data emiterii[:\s]*([\d/]+)',
        r'Issue date[:\s]*([\d/]+)',
    ],
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
    extract_data(extract_text_from_pdf("mock-documents/invoice.pdf"))
