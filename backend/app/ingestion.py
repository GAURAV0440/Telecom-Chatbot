from pathlib import Path
import json
from docx import Document
from docx.document import Document as _Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl


MAX_CHARS = 4000
OVERLAP_CHARS = 400


def iter_block_items(parent):
    """
    Yield paragraphs and tables in their original DOCX order.
    """
    if isinstance(parent, _Document):
        parent_element = parent.element.body
    else:
        parent_element = parent._tc

    for child in parent_element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def table_to_text(table: Table) -> str:
    """Convert a DOCX table into readable text."""
    rows = []

    for row in table.rows:
        cells = []

        for cell in row.cells:
            text = " ".join(
                paragraph.text.strip()
                for paragraph in cell.paragraphs
                if paragraph.text.strip()
            )

            if text:
                cells.append(text)

        if cells:
            rows.append(" | ".join(cells))

    return "\n".join(rows)


def extract_blocks(file_path: str) -> list[dict]:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    document = Document(path)

    blocks = []
    started = False
    paragraph_count = 0
    table_count = 0

    for block in iter_block_items(document):

        if isinstance(block, Paragraph):
            text = block.text.strip()

            if not text:
                continue

            style = block.style.name if block.style else "Normal"

            # Ignore cover/TOC material before Foreword.
            if text == "Foreword" and style == "Heading 1":
                started = True

            if not started:
                continue

            blocks.append(
                {
                    "type": "paragraph",
                    "text": text,
                    "style": style,
                    "index": paragraph_count,
                }
            )

            paragraph_count += 1

        elif isinstance(block, Table):
            if not started:
                continue

            text = table_to_text(block)

            if not text.strip():
                continue

            blocks.append(
                {
                    "type": "table",
                    "text": text,
                    "style": "Table",
                    "index": table_count,
                }
            )

            table_count += 1

    print(f"Paragraph blocks processed: {paragraph_count}")
    print(f"Table blocks processed: {table_count}")

    return blocks


def is_heading(style: str) -> bool:
    return style.startswith("Heading ")


def get_heading_level(style: str) -> int:
    try:
        return int(style.split()[-1])
    except (ValueError, IndexError):
        return 0


def build_chunks(blocks: list[dict]) -> list[dict]:
    chunks = []

    heading_stack: dict[int, str] = {}
    current_content: list[str] = []

    def flush_content():
        nonlocal current_content

        if not current_content:
            return

        text = "\n".join(current_content).strip()

        if not text:
            current_content = []
            return

        start = 0

        while start < len(text):
            end = min(start + MAX_CHARS, len(text))
            chunk_text = text[start:end].strip()

            if chunk_text:
                section_path = " > ".join(
                    heading_stack[level]
                    for level in sorted(heading_stack)
                )

                chunks.append(
                    {
                        "text": chunk_text,
                        "section_path": section_path,
                    }
                )

            if end >= len(text):
                break

            start = end - OVERLAP_CHARS

        current_content = []

    for block in blocks:
        text = block["text"]
        style = block["style"]

        if is_heading(style):
            flush_content()

            level = get_heading_level(style)

            for existing_level in list(heading_stack):
                if existing_level >= level:
                    del heading_stack[existing_level]

            heading_stack[level] = text

        else:
            current_content.append(text)

    flush_content()

    return chunks


def process_document(file_path: str) -> list[dict]:
    blocks = extract_blocks(file_path)
    chunks = build_chunks(blocks)

    metadata = {
        "specification": "TS 36.413",
        "version": "V19.2.0",
        "release": "19",
        "source_file": Path(file_path).name,
    }

    for index, chunk in enumerate(chunks):
        chunk["chunk_id"] = index
        chunk["specification"] = metadata["specification"]
        chunk["version"] = metadata["version"]
        chunk["release"] = metadata["release"]
        chunk["source_file"] = metadata["source_file"]

    return chunks


if __name__ == "__main__":
    document_path = "backend/data/documents/36413-j20.docx"

    chunks = process_document(document_path)

    output_path = Path("backend/data/processed/ts_36_413_chunks.json")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(chunks, file, ensure_ascii=False, indent=2)

    print(f"Total chunks: {len(chunks)}")
    print(f"Saved to: {output_path}")