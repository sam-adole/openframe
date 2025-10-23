"""
utils.py
Helper functions for parsing and generating JSON structures that match the BO-VEST
manual schema exactly as provided in the bovest-nybyg.json example.
"""

from pathlib import Path
import re
import json
from datetime import datetime
import pandas as pd
import pdfplumber


def clean_text(s: str) -> str:
    """Normalize whitespace and fix linebreaks in PDF text."""
    if not s:
        return ""
    s = s.replace("\r", "\n")
    s = re.sub(r"-\n\s*", "", s)  # remove hyphenated linebreaks
    s = re.sub(r"\n{2,}", "\n\n", s)
    return s.strip()


def code_from_title(title: str) -> str:
    """Map theme titles to their codes."""
    title_upper = title.upper()
    if "SOCIA" in title_upper:
        return "DS"
    if "INDE" in title_upper:
        return "IE"
    if "MATER" in title_upper:
        return "M"
    return "XX"


def find_manualen_page(pages, title="Manualen som Værktøj"):
    """
    Find the page number where the given title (default 'Manualen som Værktøj') appears.

    Args:
        pages (list[str]): List of text strings, one per page (from pdfplumber/PyPDF2 extraction).
        title (str): Title text to search for (case-insensitive).

    Returns:
        int: 1-based page number where the title was found, or -1 if not found.
    """
    # Normalize the target title for fuzzy matching
    title_pattern = re.sub(r"\s+", r"\\s*", title, flags=re.UNICODE)
    title_pattern = (
        title_pattern.replace("å", "[åa]").replace("æ", "[æa]").replace("ø", "[øo]")
    )
    regex = re.compile(title_pattern, re.IGNORECASE)

    for i, text in enumerate(pages, start=1):
        if not text:
            continue
        if regex.search(text):
            print(f"✅ Found '{title}' on page {i}")
            return i

    print(f"⚠️ Title '{title}' not found in document.")
    return -1


def extract_description(text):
    """
    Extracts the meaningful BO-VEST description from a noisy text block,
    removing headers like 'Bæredygtigheds Manual NYBYG' and footers like
    'Tegnestuen Vandkunsten Oktober 2023'.
    """
    # Normalize spaces and line breaks
    text = text.replace("\n", " ").strip()

    # Remove repeated letters (e.g., 'TTeeggnneessttuueenn' -> 'Tegnestuen')
    text = re.sub(r"(\w)\1+", r"\1", text)

    # Remove symbols like >>, //, etc.
    text = re.sub(r"[>/]+", "", text)

    # Find the sentence starting with "BO-VEST" (case-insensitive)
    match = re.search(
        r"(BO-?VEST\s+bæredygtighedsmanual[^.]*\.)", text, re.IGNORECASE | re.UNICODE
    )

    if match:
        description = match.group(1)
    else:
        # fallback if pattern not found
        description = text

    # Remove unwanted header/footer phrases
    description = re.sub(
        r"Bæredygtigheds\s*Manual\s*(NYBYG|RENOVERING|SIMPEL\s*SAG)?",
        "",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(
        r"Tegnestuen\s*Vandkunsten\s*Oktober\s*\d{4}",
        "",
        description,
        flags=re.IGNORECASE,
    )

    # Clean up excess spaces
    description = re.sub(r"\s{2,}", " ", description).strip()
    description = description.replace("BO-VEST", "BO-VEST bæredygtighedsmanual")

    return description


def find_theme_pages(pages):
    """
    Detects the three main themes ('Det Sociale', 'Indeklima, Energi og Miljø', 'Materialer')
    by scanning only the page that contains the title 'Manualen som Værktøj'.
    Returns a list of dicts: [{'title': theme_title, 'page': page_index}]
    """

    # --- Step 1: Find which page contains 'Manualen som Værktøj'
    manual_title_pattern = re.compile(r"MANUALEN\s*SOM\s*V[ÆA]RKT[ØO]J", re.IGNORECASE)
    manual_page_idx = None

    for i, text in enumerate(pages):
        if not text:
            continue
        if manual_title_pattern.search(text):
            manual_page_idx = i
            break

    if manual_page_idx is None:
        print(
            "⚠️ Could not find 'Manualen som Værktøj' page — scanning first 8 pages as fallback."
        )
        search_pages = pages[:8]
    else:
        search_pages = [pages[manual_page_idx]]

    # --- Step 2: Extract themes from that page
    combined_text = "\n".join(search_pages).upper()

    theme_keywords = {
        "Det Sociale": ["DET SOCIALE"],
        "Indeklima, Energi og Miljø": ["INDEKLIMA", "ENERGI", "MILJØ"],
        "Materialer": ["MATERIALER"],
    }

    themes = []
    for title, keys in theme_keywords.items():
        if any(k in combined_text for k in keys):
            # Use manual_page_idx + 1 to return 1-based PDF page numbering
            themes.append(
                {
                    "title": title,
                    "page": (manual_page_idx + 1 if manual_page_idx is not None else 1),
                }
            )

    # --- Step 3: Fallback if none found
    if not themes:
        print("⚠️ No themes detected on 'Manualen som Værktøj' page.")
        themes = [
            {"title": "Det Sociale", "page": 1},
            {"title": "Indeklima, Energi og Miljø", "page": 1},
            {"title": "Materialer", "page": 1},
        ]

    print(f"✅ Detected {len(themes)} themes from 'Manualen som Værktøj' page:", themes)
    return themes


# ---------- THEME CONSTRUCTION ----------


def build_theme(theme_title):
    """
    Build base theme object with styling and options.
    """
    theme_code = code_from_title(theme_title)
    theme_colors = {
        "DS": "#d96552",  # Det Sociale
        "IE": "#81a38b",  # Indeklima, Energi og Miljø
        "M": "#2c484d",  # Materialer
    }
    theme_secondary_colors = {"DS": "#e49386", "IE": "#a3b9a7", "M": "#839195"}
    primary = theme_colors.get(theme_code, "#000000")
    secondary = theme_secondary_colors.get(theme_code, "#000000")

    return {
        "type": "theme",
        "code": theme_code,
        "title": theme_title,
        "longFormTitle": theme_title,
        "style": {"primaryColor": primary, "secondaryColor": secondary},
        "sortOrder": 1,
        "options": {
            "hideCodeInReport": True,
            "hideFromBreadcrumbs": True,
            "hideFromDocumentTree": True,
        },
        "items": [],
    }


# ---------- CRITERION DETECTION ----------


def detect_criteria(text_chunk):
    """
    Detect possible criteria within the given text chunk using keyword matching.
    Returns a list of criterion names.
    """
    possible_criteria = []
    for line in text_chunk.split("\n"):
        if any(
            k in line.upper()
            for k in [
                "LIVET MELLEM NABOER",
                "BYGNINGER UNDERSTØTTER DET SOCIALE LIV",
                "STEDETS KVALITET",
                "ENERGI FORBRUG",
                "SUND BYGGERI OG INDEKLIMA",
                "DET GRØNNE",
                "CO2 UDLEDNING OG",
                "ANSVARLIGT MATERIALEFORBRUG",
            ]
        ):
            crit = line.strip().split(":")[0]
            if crit not in possible_criteria:
                possible_criteria.append(crit)
    if not possible_criteria:
        possible_criteria.append("")  # fallback
    return possible_criteria


# ---------- TEXT JOINING ----------
def join_all_texts_as_one(lines: list) -> pd.Series:
    """
    Join all non-empty lines into a single string and return as a Pandas Series.

    Parameters
    ----------
    lines : list of str
        List of text lines.

    Returns
    -------
    pd.Series
        Series with a single element containing all joined text.
    """
    rows = []
    buffer = ""
    for idx, line in enumerate(lines):
        buffer += line.strip() + " "
    if buffer:
        rows.append(buffer)

    # Return as a Series
    return pd.Series(rows)


# ---------- TABLE EXTRACTION ----------


def extract_table_from_pdf(pages, page_number: int) -> pd.DataFrame | None:
    """
    Extracts a table from a specific page of a PDF using pdfplumber.

    Args:
        pdf_path (str): Path to the PDF file.
        page_number (int): Page number to extract the table from (1-indexed).

    Returns:
        pd.DataFrame: Extracted table as a DataFrame, or None if no table is found.
    """
    page = pages[page_number - 1]

    table = page.extract_table(
        table_settings={
            "vertical_strategy": "lines",
            "horizontal_strategy": "text",
        }
    )

    if table:
        # Use first row as column headers
        df = pd.DataFrame(table[1:], columns=table[0])
        if (
            "dokumentationskrav" not in df.columns
            or "krav" not in df.columns
            or "niveau" not in df.columns
        ):
            return df
        df = df.drop("niveau", axis=1)
        # convert these columns to strings 'dokumentationskrav', 'krav'
        df["krav"] = join_all_texts_as_one(df["krav"].tolist())
        df["dokumentationskrav"] = join_all_texts_as_one(
            df["dokumentationskrav"].tolist()
        )
        df.dropna(inplace=True)
        return df
    else:
        return None


# ---------- TASK DOCUMENTATION CREATION ----------


def build_documentation(page_number: int, manual_meta) -> list:
    """
    Build the documentation section for a task.
    """
    pdf_url = f"{manual_meta['url_base']}?page={page_number}"
    table = extract_table_from_pdf(manual_meta["pages"], page_number)
    documentations = []
    if table is not None and "dokumentationskrav" in table.columns:
        documentations = [
            {
                "type": "text",
                "label": "Dokumentationskrav",
                "text": f"{idx}) {row.strip()}",
            }
            for idx, row in enumerate(table["dokumentationskrav"].tolist(), start=1)
            if row and str(row).strip()
        ]
    return [
        {
            "type": "pdf",
            "label": "Definition",
            "text": f"Manual (side {page_number})",
            "url": pdf_url,
        },
        *documentations,
    ]


# ---------- TASK ITEM CREATION ----------


def build_task_item(task_num: str, page_number: int, manual_meta) -> dict:
    """
    Build a single task item for a task.
    """
    table = extract_table_from_pdf(manual_meta["pages"], page_number)
    options = []
    if table is not None and "krav" in table.columns:
        options = [
            {"id": f"option.{idx}", "text": f"{row.strip()}", "value": idx}
            for idx, row in enumerate(table["krav"].tolist(), start=1)
            if row and str(row)
        ]
    text = manual_meta["pages"][page_number - 1].extract_text_simple()
    description_matches = re.findall(
        r"^(?:Beskrivelse|Arkitektonisk kvalitet|Drift og vedligehold)\s*\n([\s\S]*?)(?=\n(?:Beskrivelse|Arkitektonisk kvalitet|Drift og vedligehold|Hvordan kan projektet bidrage:|$))",
        text,
        re.MULTILINE,
    )
    descriptions = (
        "<strong>Beskrivelse</strong><br>(P1)"
        "<br><br><strong>Arkitektonisk kvalitet</strong><br>(P2)"
        "<br><br><strong>Drift og vedligehold</strong><br>(P3)"
    )
    for i, match in enumerate(description_matches, 1):
        descriptions = descriptions.replace(f"(P{i})", match.strip())
    return {
        "type": "task-item",
        "code": f"{task_num}.1",
        "definition": {
            "type": "select-single",
            "options": [{"id": "option.0", "text": "Ingen", "value": 0}, *options],
        },
        "options": {"excludeFromTargets": False},
        "description": descriptions,
    }


# ---------- TASK CREATION ----------


def build_task(
    index: int,
    task_num: str,
    task_title: str,
    manual_meta,
    page_number: int,
) -> dict:
    """
    Build a single task object including documentation and task item.
    """
    return {
        "type": "task",
        "valueCalculationStrategy": "count",
        "code": task_num,
        "title": task_title.strip(),
        "longFormTitle": task_title.strip(),
        "sortOrder": index,
        "options": {
            "breadcrumbTextFormat": ":code: :title:",
            "documentTreeFolderTextFormat": ":code: :title:",
            "showCodeAsIndicatorTaskViewTitle": False,
            "criteriaTreeElementTextFormat": ":code: :title:",
        },
        "documentation": build_documentation(page_number, manual_meta),
        "items": [build_task_item(task_num, page_number, manual_meta)],
    }


# ---------- TASK GROUP BUILDER ----------


def build_task_group(index, criterion: str, theme_code, page_texts, manual_meta, start_page):
    """
    Build a task group with multiple tasks for a given criterion (task group name).

    Pattern matched:
        <criterion>:
        <task_name>

    Example:
        LIVET MELLEM NABOER:
        Attraktive stueetager + kantzoner
    """
    tg_code = f"{theme_code}.{index+1}"
    task_group = {
        "type": "task-group",
        "code": tg_code,
        "title": criterion.capitalize(),
        "longFormTitle": criterion.capitalize(),
        "sortOrder": index,
        "items": [],
    }

    # --- Dynamic regex: only match the current criterion name ---
    pattern = re.compile(
        rf"^{re.escape(criterion)}\s*:\s*\r?\n(?P<task_name>[A-ZÆØÅa-zæøå0-9\s\-\+&/,()]+)(?=\r?\n\d{{1,2}}\b|\r?\nBeskrivelse|\r?\n[A-ZÆØÅ])",
        re.MULTILINE | re.IGNORECASE,
    )

    matches = pattern.finditer(page_texts)
    tasks = []

    def clean_task_name(text):
        # Remove everything from "Beskrivelse" onward
        index = text.find("Beskrivelse")
        if index != -1:
            text = text[:index].strip()

        # Split lines
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # Find the code (assume it is a line that is only digits)
        code = next((line for line in lines if re.fullmatch(r"\d+", line)), None)

        # Build title by joining all lines except the code
        title = " ".join([line for line in lines if line != code])

        # Create output JSON
        output = {"code": code, "title": title}

        return output

    for match in matches:
        task_name = match.group("task_name").strip()
        output = clean_task_name(task_name)
        task_name = output["title"]
        task_num = output["code"]
        tasks.append((task_num, task_name))

    # --- Build JSON tasks ---
    for idx, (task_num, task_title) in enumerate(tasks):
        page_number = start_page
        task = build_task(idx, task_num, task_title, manual_meta, page_number)
        task_group["items"].append(task)

    return task_group


# ---------- CRITERION BUILDER ----------


def build_criterion(criterion: str, c_idx, theme_code, manual_meta, start_page, pages=None):
    """
    Build a criterion object with one task group and its tasks.
    """
    crit_code = f"{theme_code}{c_idx+1}"
    criterion_obj = {
        "type": "criterion",
        "code": crit_code,
        "title": criterion.capitalize(),
        "longFormTitle": criterion.capitalize(),
        "sortOrder": c_idx,
        "options": {
            "hideCodeInReport": True,
            "hideFromBreadcrumbs": True,
            "hideFromDocumentTree": True,
            "criteriaTreeElementTextFormat": ":title:",
        },
        "items": [],
    }

    if pages is not None:
        start_page = 16
        counter = 0
        for page_number, page in enumerate(pages[start_page - 1 :], start_page):
            task_group = build_task_group(
                counter, criterion, crit_code, page, manual_meta, page_number
            )
            if len(task_group["items"]) > 0:
                criterion_obj["items"].append(task_group)
                counter += 1
    return criterion_obj


# ---------- MAIN ENTRY FUNCTION ----------


def extract_task_blocks(text_chunk, theme_title, manual_meta, start_page=1, pages=None):
    """
    Master function that orchestrates the building of:
    Theme → Criterion → Task Group → Task → Task Item
    """
    theme_obj = build_theme(theme_title)
    criteria = detect_criteria(text_chunk)

    for c_idx, criterion in enumerate(criteria):
        if criterion:
            criterion_obj = build_criterion(
                criterion, c_idx, theme_obj["code"], manual_meta, start_page, pages
            )
            if len(criterion_obj["items"]) > 0:
                theme_obj["items"].append(criterion_obj)

    return theme_obj


def build_json_structure(manual_meta, themes):
    """Construct full JSON file according to provided schema."""
    version_obj = {
        "version": "1.0.0",
        "date": datetime.utcnow().isoformat() + "Z",
        "themes": themes,
    }
    root = {
        "id": manual_meta.get("id", ""),
        "name": manual_meta.get("name", ""),
        "shortName": manual_meta.get("shortName", ""),
        "group": manual_meta.get("group", "bovest"),
        "description": manual_meta.get("description", ""),
        "versions": [version_obj],
    }
    return root


def save_json(obj, path):
    """Save a JSON file with UTF-8 and indentation."""
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return str(p)
