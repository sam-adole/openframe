"""
parse_manuals.py
Parse BO-VEST manuals (Nybyg, Simpel Sag, Renovering) PDF -> JSON
to match the exact structure of the bovest-nybyg.json reference schema.
"""

import re
import json
import argparse
from pathlib import Path
from utils import (
    clean_text,
    find_theme_pages,
    extract_description,
    extract_task_blocks,
    build_json_structure,
    save_json,
)

# Try to import pdfplumber first, fall back to PyPDF2
pdfplumber = None
PdfReader = None
try:
    import pdfplumber

    PDFLIB = "pdfplumber"
except Exception:
    from PyPDF2 import PdfReader

    PDFLIB = "pypdf2"


def extract_text_pages(pdf_path):
    """Return list of text per page."""
    pages = []
    if PDFLIB == "pdfplumber" and pdfplumber is not None:
        with pdfplumber.open(pdf_path) as pdf:
            for p in pdf.pages:
                pages.append(p.extract_text() or "")
    elif PDFLIB == "pypdf2" and PdfReader is not None:
        reader = PdfReader(str(pdf_path))
        for p in reader.pages:
            try:
                pages.append(p.extract_text() or "")
            except Exception:
                pages.append("")
    else:
        raise RuntimeError("No PDF library available.")
    return pages


def parse_manual(pdf_path, manual_meta):
    """Generate the JSON data for one manual."""
    print(f"Parsing {pdf_path} ({PDFLIB})...")
    pages = [clean_text(p) for p in extract_text_pages(pdf_path)]
    theme_pages = find_theme_pages(pages)
    description = extract_description(pages[0]) # Extract from first page
    manual_meta["description"] = description

    themes = []
    for t_idx, t in enumerate(theme_pages):
        theme_title = t["title"]
        start_page = t["page"] + 1
        chunk = "\n\n".join(pages[start_page : start_page + 40])
        theme_obj = extract_task_blocks(chunk, theme_title, manual_meta, start_page)
        theme_obj["sortOrder"] = t_idx + 1
        themes.append(theme_obj)

    return build_json_structure(manual_meta, themes)


def main(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = list(input_dir.glob("*.pdf"))
    if not pdfs:
        print("No PDFs found in input directory.")
        return

    # Metadata and URLs
    meta_map = {
        "NYBYG": {
            "id": "f7a3e8b2-9c4d-4f1a-8e5c-2d6b9a1c7f3e",
            "url_base": "https://storage.googleapis.com/custom-css/f7a3e8b2-9c4d-4f1a-8e5c-2d6b9a1c7f3e/B%C3%A6redygtighedsmanual%20-%20Nybyg.pdf",
        },
        "SIMPEL SAG": {
            "id": "f7a3b8e5-4c2d-4f1b-9e6a-3d8c7b2f1a5e",
            "url_base": "https://storage.googleapis.com/custom-css/f7a3b8e5-4c2d-4f1b-9e6a-3d8c7b2f1a5e/B%C3%A6redygtighedsmanual%20-%20Simpel%20sag.pdf",
        },
        "RENOVERING": {
            "id": "2b9d4e7c-6a1f-4d3b-8c5e-9f2a7b4d1c6e",
            "url_base": "https://storage.googleapis.com/custom-css/2b9d4e7c-6a1f-4d3b-8c5e-9f2a7b4d1c6e/B%C3%A6redygtighedsmanual%20-%20Renovering.pdf",
        },
    }

    for pdf_path in pdfs:
        name = pdf_path.stem.upper()
        if "NYBYG" in name:
            key = "NYBYG"
        elif "SIMP" in name or "SAG" in name:
            key = "SIMPEL SAG"
        elif "RENOV" in name:
            key = "RENOVERING"
        else:
            key = "UNKNOWN"

        meta = meta_map.get(key, {"id": "", "url_base": f"file://{pdf_path}"})
        manual_meta = {
            "id": meta["id"],
            "name": f"BO-VEST {key.title()}",
            "shortName": key.title(),
            "group": "bovest",
            "description": key.title(),
            "url_base": meta["url_base"],
        }

        data = parse_manual(pdf_path, manual_meta)
        outfile = output_dir / f"bovest-{key.lower().replace(' ', '-')}.json"
        save_json(data, outfile)
        print(f"✅ Wrote {outfile}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BO-VEST Manual Parser")
    parser.add_argument(
        "--input-dir", default="manuals/pdf", help="Folder with manuals (PDFs)"
    )
    parser.add_argument(
        "--output-dir", default="manuals/build", help="Destination for JSONs"
    )
    args = parser.parse_args()
    main(args.input_dir, args.output_dir)
