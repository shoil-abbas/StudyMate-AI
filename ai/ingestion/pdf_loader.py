import re
from pathlib import Path

from pypdf import PdfReader


PAGE_NUMBER = re.compile(
    r"\bPage\s+\d+\b",
    re.IGNORECASE
)


def clean_page_text(text: str, page_number: int) -> str:
    """
    Clean extracted text from a single PDF page.
    """

    # Remove page numbers such as "Page 1", "Page 2", etc.
    text = PAGE_NUMBER.sub("", text)

    # Normalize tabs
    text = text.replace("\t", " ")

    # Normalize Windows line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Normalize multiple spaces
    text = re.sub(r"[ ]{2,}", " ", text)

    # Preserve paragraph boundaries
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Join PDF-wrapped lines inside paragraphs.
    # Do not join headings, questions, answers, or list items.
    lines = text.split("\n")

    cleaned_lines = []

    for line in lines:

        line = line.strip()

        if not line:
            cleaned_lines.append("")
            continue

        if not cleaned_lines:
            cleaned_lines.append(line)
            continue

        previous = cleaned_lines[-1]

        if not previous:
            cleaned_lines.append(line)
            continue

        # Preserve likely headings
        if (
            re.match(r"^\d+(\.\d+)*\s+", line)
            or line.startswith("Chapter ")
            or line.startswith("Q:")
            or line.startswith("A:")
            or line.startswith("Learning Objectives")
            or line.startswith("Core Terminology")
            or line.startswith("Examples")
            or line.startswith("Example")
        ):
            cleaned_lines.append(line)
            continue

        # Preserve list items
        if re.match(r"^[•\-]\s+", line):
            cleaned_lines.append(line)
            continue

        # Join normal wrapped lines
        cleaned_lines[-1] = previous + " " + line

    text = "\n".join(cleaned_lines)

    # Clean excessive spaces again
    text = re.sub(r"[ ]{2,}", " ", text)

    # Clean excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def load_pdf_pages(pdf_path: str) -> list[dict]:
    """
    Extract and clean PDF text while preserving page numbers.

    Returns:
        [
            {
                "page": 1,
                "text": "..."
            },
            ...
        ]
    """

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    reader = PdfReader(str(path))

    pages = []

    for page_index, page in enumerate(reader.pages):

        text = page.extract_text()

        if not text:
            continue

        page_number = page_index + 1

        cleaned = clean_page_text(
            text,
            page_number
        )

        if cleaned:
            pages.append({
                "page": page_number,
                "text": cleaned
            })

    return pages


def load_pdf(pdf_path: str) -> str:
    """
    Backward-compatible PDF loader.

    Returns all cleaned text as one string.
    """

    pages = load_pdf_pages(pdf_path)

    return "\n\n".join(
        page["text"]
        for page in pages
    )


if __name__ == "__main__":

    pdf_file = "data/documents/operating_systems.pdf"

    pages = load_pdf_pages(pdf_file)

    print("=" * 60)
    print("STUDYMATE-AI — PDF EXTRACTION TEST")
    print("=" * 60)

    print(f"\nExtracted pages: {len(pages)}")

    total_characters = sum(
        len(page["text"])
        for page in pages
    )

    print(
        f"Extracted characters: {total_characters}"
    )

    for page in pages[:3]:

        print("\n" + "-" * 60)
        print(f"PAGE {page['page']}")
        print("-" * 60)

        print(page["text"][:2000])