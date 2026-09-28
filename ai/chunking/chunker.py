import re
from typing import List, Dict


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150


# ---------------------------------------------------------
# Text Cleaning
# ---------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Normalize extracted page text while preserving
    meaningful paragraph boundaries.
    """

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Normalize spaces inside lines
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------
# Detect headings
# ---------------------------------------------------------

def is_heading(line: str) -> bool:
    """
    Detect common educational document headings.
    """

    line = line.strip()

    if not line:
        return False

    heading_patterns = [
        r"^Chapter\s+\d+",
        r"^\d+(\.\d+)*\s+.+",       # 1.1, 1.2, 2.1 etc.
        r"^Learning Objectives$",
        r"^Core Terminology$",
        r"^Examples?$",
        r"^Important Terms$",
        r"^Key Points$",
        r"^Summary$",
        r"^Conclusion$",
        r"^Questions?$",
        r"^Q&A$",
        r"^Comparisons?$",
    ]

    for pattern in heading_patterns:
        if re.match(pattern, line, re.IGNORECASE):
            return True

    return False


# ---------------------------------------------------------
# Split page into logical blocks
# ---------------------------------------------------------

def split_into_blocks(text: str) -> List[str]:
    """
    Split page text into paragraphs/sections.

    Headings are kept together with the following content
    instead of being randomly separated.
    """

    text = normalize_text(text)

    if not text:
        return []

    paragraphs = re.split(r"\n\s*\n", text)

    blocks = []
    current_block = ""

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        lines = paragraph.split("\n")

        for line in lines:

            line = line.strip()

            if not line:
                continue

            # Heading starts a new logical block
            if is_heading(line):

                if current_block:
                    blocks.append(current_block.strip())

                current_block = line

            else:

                if current_block:
                    current_block += " " + line
                else:
                    current_block = line

    if current_block:
        blocks.append(current_block.strip())

    return blocks


# ---------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------

def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences while keeping punctuation.
    """

    sentences = re.split(
        r"(?<=[.!?])\s+(?=[A-Z0-9])",
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


# ---------------------------------------------------------
# Create chunks from a logical block
# ---------------------------------------------------------

def split_large_block(
    block: str,
    chunk_size: int,
    chunk_overlap: int
) -> List[str]:

    sentences = split_into_sentences(block)

    if not sentences:
        return [block]

    chunks = []
    current = ""

    for sentence in sentences:

        # Normal case
        if len(current) + len(sentence) + 1 <= chunk_size:

            if current:
                current += " " + sentence
            else:
                current = sentence

        else:

            if current:
                chunks.append(current.strip())

            # Create overlap from previous sentences
            overlap_text = ""

            if chunk_overlap > 0:

                words = current.split()

                overlap_words = []

                current_length = 0

                for word in reversed(words):

                    if current_length + len(word) + 1 > chunk_overlap:
                        break

                    overlap_words.insert(0, word)

                    current_length += len(word) + 1

                overlap_text = " ".join(overlap_words)

            if overlap_text:
                current = overlap_text + " " + sentence
            else:
                current = sentence

    if current:
        chunks.append(current.strip())

    return chunks


# ---------------------------------------------------------
# Main chunking function
# ---------------------------------------------------------

def create_chunks_from_pages(
    pages: List[Dict],
    source_filename: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> List[Dict]:
    """
    Create semantic-ish chunks from page-aware PDF data.

    Each page is processed independently so that page metadata
    remains accurate.
    """

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be smaller than chunk_size."
        )

    all_chunks = []

    global_chunk_id = 0

    for page_data in pages:

        page_number = page_data["page"]
        page_text = page_data["text"]

        if not page_text.strip():
            continue

        blocks = split_into_blocks(page_text)

        page_chunks = []

        for block in blocks:

            # Small logical block
            if len(block) <= chunk_size:

                page_chunks.append(block)

            # Large logical block
            else:

                large_chunks = split_large_block(
                    block,
                    chunk_size,
                    chunk_overlap
                )

                page_chunks.extend(large_chunks)

        for page_chunk_index, chunk_text in enumerate(page_chunks):

            chunk_text = chunk_text.strip()

            if not chunk_text:
                continue

            all_chunks.append({
                "chunk_id": global_chunk_id,

                "text": chunk_text,

                "metadata": {
                    "source": source_filename,
                    "page": page_number,
                    "chunk_index": page_chunk_index
                }
            })

            global_chunk_id += 1

    return all_chunks


# ---------------------------------------------------------
# TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    from pathlib import Path
    from ai.ingestion.pdf_loader import load_pdf_pages


    pdf_file = "data/documents/operating_systems.pdf"

    pages = load_pdf_pages(pdf_file)

    chunks = create_chunks_from_pages(
        pages=pages,
        source_filename=Path(pdf_file).name,
        chunk_size=1000,
        chunk_overlap=150
    )


    print("=" * 60)
    print("STUDYMATE-AI — SEMANTIC CHUNKING TEST")
    print("=" * 60)

    print(f"\nTotal pages: {len(pages)}")
    print(f"Total chunks: {len(chunks)}")


    for chunk in chunks[:5]:

        print("\n" + "-" * 60)

        print(
            f"Chunk ID: {chunk['chunk_id']}"
        )

        print(
            f"Source: {chunk['metadata']['source']}"
        )

        print(
            f"Page: {chunk['metadata']['page']}"
        )

        print(
            f"Chunk Index: {chunk['metadata']['chunk_index']}"
        )

        print("-" * 60)

        print(chunk["text"])