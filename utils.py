"""
utils.py
Helper functions for parsing and generating JSON structures that match the BO-VEST
manual schema exactly as provided in the bovest-nybyg.json example.
"""

from pathlib import Path
import re
import json
from datetime import datetime

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
        return "MA"
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
    title_pattern = title_pattern.replace("å", "[åa]").replace("æ", "[æa]").replace("ø", "[øo]")
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
    text = text.replace('\n', ' ').strip()

    # Remove repeated letters (e.g., 'TTeeggnneessttuueenn' -> 'Tegnestuen')
    text = re.sub(r'(\w)\1+', r'\1', text)

    # Remove symbols like >>, //, etc.
    text = re.sub(r'[>/]+', '', text)

    # Find the sentence starting with "BO-VEST" (case-insensitive)
    match = re.search(r'(BO-?VEST\s+bæredygtighedsmanual[^.]*\.)', text, re.IGNORECASE | re.UNICODE)

    if match:
        description = match.group(1)
    else:
        # fallback if pattern not found
        description = text

    # Remove unwanted header/footer phrases
    description = re.sub(
        r'Bæredygtigheds\s*Manual\s*(NYBYG|RENOVERING|SIMPEL\s*SAG)?',
        '',
        description,
        flags=re.IGNORECASE
    )
    description = re.sub(
        r'Tegnestuen\s*Vandkunsten\s*Oktober\s*\d{4}',
        '',
        description,
        flags=re.IGNORECASE
    )

    # Clean up excess spaces
    description = re.sub(r'\s{2,}', ' ', description).strip()
    description = description.replace('BO-VEST', 'BO-VEST bæredygtighedsmanual')

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
        print("⚠️ Could not find 'Manualen som Værktøj' page — scanning first 8 pages as fallback.")
        search_pages = pages[:8]
    else:
        search_pages = [pages[manual_page_idx]]

    # --- Step 2: Extract themes from that page
    combined_text = "\n".join(search_pages).upper()

    theme_keywords = {
        "Det Sociale": ["DET SOCIALE"],
        "Indeklima, Energi og Miljø": ["INDEKLIMA", "ENERGI", "MILJØ"],
        "Materialer": ["MATERIALER"]
    }

    themes = []
    for title, keys in theme_keywords.items():
        if any(k in combined_text for k in keys):
            # Use manual_page_idx + 1 to return 1-based PDF page numbering
            themes.append({"title": title, "page": (manual_page_idx + 1 if manual_page_idx is not None else 1)})

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

def extract_task_blocks(text_chunk, theme_title, manual_meta, start_page=1):
    """
    Build a single theme block according to schema:
    Theme → Criterion → Task Group → Task → Task Item
    Uses heuristics to find tasks, fills out required JSON fields.
    """
    theme_code = code_from_title(theme_title)
    theme_color_dict = {
        "DS": "#d96552",
        "IE": "#81a38b",
        "MA": "#2c484d",
    }
    # make theme color 10% lighter for secondary color
    # simple approach: increase each RGB component by 10% towards 255
    # This is a naive approach and may not be perfect for all colors
    def lighten_color(hex_color, amount=0.1):
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r + (255 - r) * amount)
        g = int(g + (255 - g) * amount)
        b = int(b + (255 - b) * amount)
        return f"#{r:02x}{g:02x}{b:02x}" 

    theme_obj = {
        "type": "theme",
        "code": theme_code,
        "title": theme_title,
        "longFormTitle": theme_title,
        "style": {"primaryColor": theme_color_dict.get(theme_code, "#000000"), "secondaryColor": lighten_color(theme_color_dict.get(theme_code, "#000000"))},
        "sortOrder": 1,
        "options": {
            "hideCodeInReport": True,
            "hideFromBreadcrumbs": True,
            "hideFromDocumentTree": True,
        },
        "items": [],
    }

    # Criteria detection (simple pattern)
    possible_criteria = []
    for line in text_chunk.split("\n"):
        if any(
            k in line.upper()
            for k in [
                "LIVET MELLEM",
                "BYGNINGER",
                "ENERGI",
                "SUNDT BYGGERI",
                "MATERIALER",
            ]
        ):
            crit = line.strip().split(":")[0]
            if crit not in possible_criteria:
                possible_criteria.append(crit)
    if not possible_criteria:
        possible_criteria.append("Livet Mellem Naboer")

    for c_idx, criterion in enumerate(possible_criteria[:5]):
        crit_code = f"{theme_code}{c_idx+1}"
        criterion_obj = {
            "type": "criterion",
            "code": crit_code,
            "title": criterion,
            "longFormTitle": criterion,
            "sortOrder": c_idx + 1,
            "options": {
                "hideCodeInReport": True,
                "hideFromBreadcrumbs": True,
                "hideFromDocumentTree": True,
                "criteriaTreeElementTextFormat": ":title:",
            },
            "items": [],
        }

        # Task group
        tg_code = f"{crit_code}.1"
        task_group = {
            "type": "task-group",
            "code": tg_code,
            "title": criterion,
            "longFormTitle": criterion,
            "sortOrder": 1,
            "items": [],
        }

        # Find tasks (01, 02, 03...) – simplified heuristic
        tasks = re.findall(r"\b(0?\d{1,2})\b\s*[-–]?\s*(.{5,80})", text_chunk)
        if not tasks:
            tasks = [("01", f"{criterion} - Eksempelopgave")]

        for t_idx, (task_num, task_title) in enumerate(tasks[:10]):
            task_code = task_num.zfill(2)
            page_number = start_page + t_idx
            pdf_url = f"{manual_meta['url_base']}?page={page_number}"

            task = {
                "type": "task",
                "valueCalculationStrategy": "count",
                "code": task_code,
                "title": task_title.strip(),
                "longFormTitle": task_title.strip(),
                "sortOrder": t_idx + 1,
                "options": {
                    "breadcrumbTextFormat": ":code: :title:",
                    "documentTreeFolderTextFormat": ":code: :title:",
                    "showCodeAsIndicatorTaskViewTitle": False,
                    "criteriaTreeElementTextFormat": ":code: :title:",
                },
                "documentation": [
                    {
                        "type": "pdf",
                        "label": "Definition",
                        "text": f"Manual (side {page_number})",
                        "url": pdf_url,
                    },
                    {
                        "type": "text",
                        "label": "Dokumentationskrav",
                        "text": "Planudsnit / fotodokumentation, og beskrivelser i tekst",
                    },
                ],
                "items": [
                    {
                        "type": "task-item",
                        "code": f"{task_code}.1",
                        "definition": {
                            "type": "select-single",
                            "options": [
                                {
                                    "id": "option.0",
                                    "text": "Der er etableret 1-2 typer af rumlige situationer...",
                                    "value": 1,
                                },
                                {
                                    "id": "option.1",
                                    "text": "I tillæg hertil er der attraktive og inviterende stueetager...",
                                    "value": 2,
                                },
                                {
                                    "id": "option.2",
                                    "text": "Derudover kan der identificeres mindst 3 invitationer...",
                                    "value": 3,
                                },
                            ],
                        },
                        "options": {"excludeFromTargets": False},
                        "text": "<strong>Beskrivelse</strong>\n(Extracted description)",
                    }
                ],
            }
            task_group["items"].append(task)

        criterion_obj["items"].append(task_group)
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
