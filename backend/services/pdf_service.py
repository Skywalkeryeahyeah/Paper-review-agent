import pymupdf


def parse_pdf(file_path):
    doc = pymupdf.open(file_path)

    pages = []

    for i, page in enumerate(doc):
        text = page.get_text()

        pages.append({
            "page": i + 1,
            "text": text
        })

    page_count = len(doc)

    doc.close()

    return {
        "page_count": page_count,
        "pages": pages
    }