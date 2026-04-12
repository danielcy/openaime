import pdfplumber

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"--- Page {i+1} ---\n\n"
                text += page_text
                text += "\n\n"
    return text

if __name__ == "__main__":
    pdf_path = "2507.11988v2.pdf"
    text = extract_text_from_pdf(pdf_path)
    with open("2507.11988v2_extracted.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Extracted {len(text)} characters to 2507.11988v2_extracted.txt")
