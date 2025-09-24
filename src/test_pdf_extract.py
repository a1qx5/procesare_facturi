import pdfplumber


def extract_text_from_pdf(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"PDF has {len(pdf.pages)} pages")

            full_text = ""
            for page_num, page in enumerate(pdf.pages):
                print(f"\n--- Page {page_num + 1} ---")
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
                else:
                    print("No text found on this page")
            return full_text
    except Exception as e:
        print(f"Error reading pdf: {e}")


if __name__ == "__main__":
    pdf_file = r"mock-documents\invoice.pdf"
    text = extract_text_from_pdf(pdf_file)
    print(f"{text}")
    