# BO-VEST JSON Extraction – Task Understanding Document

## 1. Project Overview

BO-VEST has provided three sustainability manuals:

1. **Bæredygtighedsmanual – Nybyg**
2. **Bæredygtighedsmanual – Simpel Sag**
3. **Bæredygtighedsmanual – Renovering**

The goal is to convert these manuals into **structured JSON files** following a predefined schema (`bovest-nybyg.json` provided as reference).  
Each JSON file will represent one manual and contain hierarchical data describing **themes, criteria, task groups, tasks, and task items**.

---

## 2. Core Objective

To extract and structure the content of each manual into a machine-readable JSON format with the following hierarchy:

```sh
Theme
└── Criterion
   └── Task group
      └── Task
         └── Task item
```

This enables BO-VEST’s platform to display and manage manual content digitally — for instance in an assessment or certification system.

---

## 3. Expected Deliverables

| **Deliverable**          | **Description**                                            |
| ------------------------ | ---------------------------------------------------------- |
| `bovest-nybyg.json`      | JSON output for the _Nybyg_ manual                         |
| `bovest-simpel-sag.json` | JSON output for the _Simpel Sag_ manual                    |
| `bovest-renovering.json` | JSON output for the _Renovering_ manual                    |
| `parse_manuals.py`       | Python script that parses all manuals into JSON            |
| `utils.py`               | Helper functions for extraction, cleaning, and structuring |
| `schema_example.json`    | Example of the expected JSON format                        |
| `README.md`              | Summary of task understanding and scope and Setup instructions for running the extraction scripts         |

---

## 4. JSON Structure Details

Each JSON file must conform to the following model:

```json
{
    "id": "manual-uuid",
    "name": "Manual Name",
    "shortName": "BDH",
    "group": "bovest",
    "description": "Manual description",
    "versions": [
        {
            "version": "1.0.0",
            "date": "2025-10-10T13:20:51.629Z",
            "themes": [
                {
                    "type": "theme",
                    "code": "DS",
                    "title": "Det Sociale",
                    "items": [
                        {
                            "type": "criterion",
                            "code": "DS1",
                            "title": "Livet Mellem Naboer",
                            "items": [
                                {
                                    "type": "task-group",
                                    "code": "DS1.1",
                                    "title": "Livet Mellem Naboer",
                                    "items": [
                                        {
                                            "type": "task",
                                            "code": "01",
                                            "title": "Det naturlige møde - fællesskab og naboskabskultur",
                                            "documentation": [],
                                            "items": [
                                                {
                                                    "type": "task-item",
                                                    "code": "01.1",
                                                    "definition": {
                                                        "type": "select-single",
                                                        "options": []
                                                    },
                                                    "text": "<strong>Beskrivelse</strong>..."
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}
```

---

## 5. Understanding of Content Hierarchy

| **Level** | **Description / Source** | **Example** |
|------------|---------------------------|--------------|
| **Theme** | The top-level sections from the manual’s table of contents. | “Det Sociale” |
| **Criterion** | Subsections under each theme (seen in the table of contents). | “Livet Mellem Naboer” |
| **Task Group** | Usually mirrors the criterion title (one per criterion). | “Livet Mellem Naboer” |
| **Task** | Individual items under the task group. Corresponds to numbered circles (e.g., “01”, “02”). | “Det naturlige møde - fællesskab og naboskabskultur” |
| **Task Item** | The descriptive and evaluative content of each task. Includes the “Beskrivelse”, “Dokumentationskrav”, and “Hvordan kan projektet bidrage” sections. | One per task. |

---

## 6. Manual-Specific Metadata

| **Manual** | **UUID** | **PDF URL** |
|-------------|-----------|--------------|
| Nybyg | `f7a3e8b2-9c4d-4f1a-8e5c-2d6b9a1c7f3e` | `https://storage.googleapis.com/custom-css/f7a3e8b2-9c4d-4f1a-8e5c-2d6b9a1c7f3e/B%C3%A6redygtighedsmanual%20-%20Nybyg.pdf` |
| Simpel Sag | `f7a3b8e5-4c2d-4f1b-9e6a-3d8c7b2f1a5e` | `https://storage.googleapis.com/custom-css/f7a3b8e5-4c2d-4f1b-9e6a-3d8c7b2f1a5e/B%C3%A6redygtighedsmanual%20-%20Simpel%20sag.pdf` |
| Renovering | `2b9d4e7c-6a1f-4d3b-8c5e-9f2a7b4d1c6e` | `https://storage.googleapis.com/custom-css/2b9d4e7c-6a1f-4d3b-8c5e-9f2a7b4d1c6e/B%C3%A6redygtighedsmanual%20-%20Renovering.pdf` |

---

## 7. Technical Implementation

- **Language:** Python 3.8+  
- **Libraries:**  
  - `pdfplumber` (preferred for text extraction)  
  - `PyPDF2` (fallback if pdfplumber unavailable)  
  - `json`, `re`, `argparse`, `pathlib` (standard library)  

### **Process Flow**

1. **Extract text per page**  
   → Use `pdfplumber` or `PyPDF2` to read all pages.

2. **Detect Themes**  
   → Identify TOC-like headings: “DET SOCIALE”, “INDEKLIMA”, “MATERIALER”.

3. **Find Criteria & Tasks**  
   → Use regex and line analysis to identify headings, numeric task codes, and section breaks.

4. **Extract Task Content**  
   → Pull “Beskrivelse”, “Dokumentationskrav”, and “Hvordan kan projektet bidrage” blocks.

5. **Assemble JSON structure**  
   → Use helper functions to build nested dictionaries matching the schema.

6. **Validate & Save**  
   → Write one validated JSON per manual.

---

## 8. Assumptions

- Manuals are text-based PDFs (not scanned images).  
- Each theme appears in the table of contents and has clear page references.  
- Each task contains one “task item”.  
- The color and style settings per theme follow the provided example.  
- “Options” in `task-item` always have three entries (values 1–3).

---

## 9. Output Expectations

- One JSON file per manual in UTF-8.  
- Each file should:
  - Match the schema of `bovest-nybyg.json`
  - Contain all hierarchy levels properly nested
  - Include correct UUIDs, URLs, and metadata
- Minor human review may be needed for:
  - Text formatting consistency
  - Correct mapping of page numbers and sections

---

## 10. Next Steps

1. Run the extraction script on the three provided manuals.  
2. Review and verify extracted structures and texts.  
3. Refine parsing rules if necessary.  
4. Deliver final JSON files along with the scripts.

## Data Flow Diagram

```sh
┌────────────────────┐
│  PDF Manuals       │
│  (Nybyg, etc.)     │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Text Extraction    │
│ (pdfplumber/PyPDF2)│
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Structure Parsing  │
│ (regex + heuristics)│
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ JSON Builder       │
│ (nested dicts)     │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Output JSON Files  │
│ bovest-*.json      │
└────────────────────┘

```
