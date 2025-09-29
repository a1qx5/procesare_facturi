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
    # "total_value": [
    #     r'TOTAL\s*PLATA\s*([0-9]+\.[0-9]+)',
    #     r'Total\s*value\s*([0-9]+\.[0-9]+)',
    # ],
    "exchange_rate": [
        r'Curs\s*1\s*EUR\s*=\s*([0-9]+\.[0-9]+)',
        r'Exchange\s*rate\s*1\s*EUR\s*=\s*([0-9]+\.[0-9]+)',
    ],
    # "total_value_ron": [
    #     r'Total\s*value\s*[0-9]+\.[0-9]+\s*EUR\s*([0-9]+\.[0-9]+)\s*Lei',
    # ]
}

def extract_global_data(text):
    results = {}
    for field, patterns in PATTERNS.items():
        value = None
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                value = match.group(1)
                break
        results[field] = value
    return results

def extract_IQID_list(text):
    IQID_list = []
    start_pos = 0
    while True:
        IQID_match = re.search(r'IQID\s*:\s*([^\n]+)', text[start_pos:], re.IGNORECASE)
        if IQID_match == None:
            break
        IQID_list.append(IQID_match.group(1))
        start_pos += IQID_match.end()
    return IQID_list

def extract_products(text):
    product_list = []
    start_pos = 0
    IQID_list = extract_IQID_list(text)
    counter = 0
    while True:
        product_values_match = re.search(r'buc\s+\d+\s+\d+(?:\s\d+)*\.?\d*\s+(\d+(?:\s\d+)*\.?\d*)\s+(\d+(?:\s\d+)*\.?\d*)', text[start_pos:], re.IGNORECASE)
        if product_values_match == None:
            break
        
        product = extract_global_data(text)

        product['IQID'] = IQID_list[counter]
        counter += 1

        product['value_without_vat'] = product_values_match.group(1).replace(' ', '')

        product['vat_value'] = product_values_match.group(2).replace(' ', '')

        product['total_value'] = float(product['value_without_vat']) + float(product['vat_value'])

        product['total_value_ron'] = round(product['total_value'], 2) if product['currency'] == "Lei" else round(float(product['total_value']) * float(product['exchange_rate']), 2)

        print(product)

        product_list.append(product)

        start_pos += product_values_match.end()

    return product_list
        

if __name__ == "__main__":
    print("\n---Romanian invoice---\n")
    extract_products(extract_text_from_pdf("mock-documents/invoice.pdf"))

    print("\n---English Envoice---\n")
    extract_products(extract_text_from_pdf("mock-documents/invoice_eng.pdf"))