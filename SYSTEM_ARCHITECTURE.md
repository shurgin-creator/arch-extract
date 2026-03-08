# System Architecture - Professional Project Management System

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT WEB INTERFACE                       │
│  (app.py - 820 lines with enhanced UI/UX)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               SIDEBAR NAVIGATION                         │   │
│  │  • Project History (Load/Delete)                        │   │
│  │  • Configuration (Categories, DPI, API Status)          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              MAIN CONTENT AREA                          │   │
│  │  • Upload & Extract Section                            │   │
│  │  • Live Log Display                                    │   │
│  │  • Results with Professional Styling                   │   │
│  │  • Validation Issues & Low Confidence Warnings         │   │
│  │  • Challenge/Refine Mechanism                          │   │
│  │  • Export Options (CSV/Excel/JSON)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │          STREAMLIT SESSION STATE MANAGEMENT             │   │
│  │  • extraction_results, pdf_processed                   │   │
│  │  • extracted_images, current_project_id                │   │
│  │  • live_log, refining_field, etc.                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                           ↓↓↓
┌─────────────────────────────────────────────────────────────────┐
│                    DATA PROCESSING LAYER                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PDFProcessor (src/pdf_processor.py)                            │
│  ├─ Convert PDF to Images                                       │
│  ├─ Apply DPI settings (200 default)                           │
│  ├─ Generate PNG/JPG from each page                            │
│  └─ Return List[PIL.Image]                                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                           ↓↓↓
┌─────────────────────────────────────────────────────────────────┐
│                    AI/ML ANALYSIS LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  GeminiDataExtractor (src/gemini_api.py)                        │
│  ├─ extract_data_from_all_pages_consolidated()                 │
│  │  ├─ Sends all pages to Gemini at once                       │
│  │  ├─ Professional-grade system prompt                        │
│  │  ├─ Returns complete analysis with reasoning                │
│  │  └─ Includes validation status and AI confidence            │
│  │                                                              │
│  ├─ refine_field_value() [NEW]                                 │
│  │  ├─ Targeted re-analysis of one field                       │
│  │  ├─ Takes user feedback as input                            │
│  │  ├─ Focuses analysis on specific measurement               │
│  │  └─ Returns refined value with new reasoning                │
│  │                                                              │
│  └─ Built-in Error Handling                                     │
│     ├─ Exponential backoff (10s, 20s, 40s)                      │
│     ├─ Rate limit detection (429)                              │
│     └─ 3 retry attempts maximum                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                           ↓↓↓
┌─────────────────────────────────────────────────────────────────┐
│                    PERSISTENCE LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ExtractionDatabase (src/database.py)                           │
│  ├─ SQLite Manager (extraction_projects.db)                     │
│  │                                                              │
│  ├─ PROJECTS TABLE                                             │
│  │  ├─ Store complete extraction analysis                      │
│  │  ├─ Track project metadata                                  │
│  │  └─ Save refined analysis versions                          │
│  │                                                              │
│  ├─ EXTRACTION_HISTORY TABLE                                    │
│  │  ├─ Version control for projects                            │
│  │  ├─ Track refinements over time                             │
│  │  └─ Full audit trail maintained                             │
│  │                                                              │
│  ├─ FIELD_REFINEMENTS TABLE                                     │
│  │  ├─ Individual field change tracking                        │
│  │  ├─ Original vs. refined values                             │
│  │  └─ User feedback recorded                                  │
│  │                                                              │
│  └─ Operations (CRUD + Custom)                                  │
│     ├─ save_project() - Create/Update                           │
│     ├─ get_all_projects() - List all                            │
│     ├─ get_project() - Load specific                            │
│     ├─ delete_project() - Remove completely                     │
│     ├─ add_field_refinement() - Track changes                   │
│     └─ update_refined_analysis() - Save refinements             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                           ↓↓↓
                    extraction_projects.db
                     (SQLite Database)
```

---

## Data Flow Diagram

### Extraction Workflow

```
User Uploads PDF
        ↓
    ┌───────────────────────────┐
    │  PDF PROCESSING LAYER     │
    │  (src/pdf_processor.py)   │
    │  • Convert to images      │
    │  • Apply DPI settings     │
    │  • Return image list      │
    └───────────────────────────┘
        ↓
    ┌───────────────────────────────────────┐
    │  GEMINI CONSOLIDATED ANALYSIS         │
    │  (src/gemini_api.py)                  │
    │  • Send all pages to Gemini           │
    │  • Professional-grade prompts         │
    │  • Get complete analysis with         │
    │    - Values & confidence              │
    │    - AI reasoning                     │
    │    - Validation status                │
    │    - Page references                  │
    └───────────────────────────────────────┘
        ↓
    ┌───────────────────────────────────────┐
    │  DATABASE PERSISTENCE                 │
    │  (src/database.py)                    │
    │  • Save project (auto)                │
    │  • Record in history                  │
    │  • Store complete analysis            │
    └───────────────────────────────────────┘
        ↓
    ┌───────────────────────────────────────┐
    │  DISPLAY TO USER                      │
    │  (app.py)                             │
    │  • Format results                     │
    │  • Apply styling                      │
    │  • Show reasoning                     │
    │  • Highlight issues                   │
    └───────────────────────────────────────┘
        ↓
    User Reviews, Refines, or Exports
```

### Refinement Workflow

```
User Selects Field to Refine
        ↓
    View Current Data
    • Value, confidence, reasoning
        ↓
    Provide User Feedback
    • Explain what's wrong
        ↓
    ┌───────────────────────────────────────┐
    │  TARGETED RE-ANALYSIS                 │
    │  (src/gemini_api.refine_field_value)  │
    │  • Use all PDF images                 │
    │  • Focus on specific field            │
    │  • Include user feedback as hint      │
    │  • Re-analyze with context            │
    └───────────────────────────────────────┘
        ↓
    ┌───────────────────────────────────────┐
    │  UPDATE DATABASE                      │
    │  (src/database.py)                    │
    │  • Record refinement                  │
    │  • Update project analysis            │
    │  • Add to history                     │
    │  • Track field change                 │
    └───────────────────────────────────────┘
        ↓
    ┌───────────────────────────────────────┐
    │  REFRESH UI                           │
    │  (app.py)                             │
    │  • Show new value                     │
    │  • Display new reasoning              │
    │  • Update confidence                  │
    └───────────────────────────────────────┘
        ↓
    User Sees Updated Result
```

---

## Component Interaction Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                           APP.PY                                      │
│                      (Main Interface)                                 │
│                                                                       │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │  Sidebar       │  │  Main Area   │  │  Session State       │    │
│  │  ├─ History    │→ │  ├─ Upload   │  │  ├─ results          │    │
│  │  ├─ Config     │  │  ├─ Extract  │→ │  ├─ images           │    │
│  │  └─ Settings   │  │  ├─ Display  │  │  ├─ project_id       │    │
│  └────────────────┘  │  ├─ Refine   │  │  └─ live_log         │    │
│         ↓            │  └─ Export   │  └──────────────────────┘    │
│    Database.py       └──────────────┘        ↓                      │
│   (Persistence)                       Gemini API.py                  │
│                                      (AI Analysis)                   │
│   get_db()                                  ↓                        │
│   ├─ get_all_projects()            pdf_processor.py                 │
│   ├─ get_project()                 (Image Processing)               │
│   ├─ save_project()                                                 │
│   ├─ delete_project()                                               │
│   ├─ add_field_refinement()                                         │
│   └─ update_refined_analysis()                                      │
└──────────────────────────────────────────────────────────────────────┘
                           ↓ All Persist To
                   extraction_projects.db
                      (3 SQLite Tables)
```

---

## Module Dependencies

```
app.py (Main Entry Point)
├─ Imports: streamlit, pandas, json, datetime
├─ Imports: src.pdf_processor
├─ Imports: src.gemini_api
├─ Imports: src.database  [NEW]
├─ Imports: config.extraction_categories
│
├─ Uses: PDFProcessor.convert_pdf_bytes()
│
├─ Uses: GeminiDataExtractor
│   ├─ extract_data_from_all_pages_consolidated()
│   └─ refine_field_value()  [NEW]
│
├─ Uses: ExtractionDatabase (via get_db())
│   ├─ save_project()
│   ├─ get_all_projects()
│   ├─ get_project()
│   ├─ delete_project()
│   ├─ add_field_refinement()
│   └─ update_refined_analysis()
│
└─ Functions:
   ├─ initialize_session_state()
   ├─ show_project_history()  [NEW]
   ├─ add_log_entry()  [NEW]
   ├─ display_live_log()  [NEW]
   ├─ format_extraction_results()  [ENHANCED]
   ├─ extract_data_from_pdf()  [ENHANCED]
   ├─ refine_field()  [NEW]
   ├─ display_results()  [ENHANCED]
   └─ main()

src/database.py  [NEW - 230 lines]
├─ Imports: sqlite3, json, datetime
├─ Class: ExtractionDatabase
│   ├─ init_db()
│   ├─ save_project()
│   ├─ get_all_projects()
│   ├─ get_project()
│   ├─ get_project_by_name()
│   ├─ delete_project()
│   ├─ add_field_refinement()
│   ├─ update_refined_analysis()
│   └─ get_field_refinements()
│
└─ Function: get_db()
   └─ Returns singleton ExtractionDatabase

src/gemini_api.py  [ENHANCED - 100 lines added]
├─ Class: GeminiDataExtractor
│   ├─ extract_data_from_all_pages_consolidated()
│   ├─ extract_data_from_image()
│   ├─ refine_field_value()  [NEW - Targeted re-analysis]
│   ├─ _build_consolidated_system_prompt()
│   ├─ _build_consolidated_system_prompt()  [PROFESSIONAL]
│   ├─ _parse_response()
│   └─ _aggregate_results()

src/pdf_processor.py  [Unchanged]
└─ Class: PDFProcessor
   └─ convert_pdf_bytes()

config/extraction_categories.py  [Unchanged]
└─ EXTRACTION_CATEGORIES dictionary
```

---

## Database Schema Details

### projects Table

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_pages INTEGER,
    analysis_json TEXT NOT NULL,
    user_feedback TEXT,
    refined_analysis_json TEXT
);
```

**Relationships**:
- One-to-many with extraction_history (versions)
- One-to-many with field_refinements (changes)

### extraction_history Table

```sql
CREATE TABLE extraction_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    analysis_json TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    refinement_reason TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
```

**Purpose**: Version control and audit trail

### field_refinements Table

```sql
CREATE TABLE field_refinements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    field_code TEXT NOT NULL,
    original_value TEXT,
    refined_value TEXT,
    user_feedback TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
```

**Purpose**: Track individual field corrections

---

## Deployment Architecture (Future Ready)

```
Current (Local)                    Future (Cloud Ready)
─────────────────                 ──────────────────

app.py                            app.py (same code!)
  ↓                                  ↓
StreamLit                          Streamlit Cloud / Self-Hosted
  ↓                                  ↓
extraction_projects.db       →     PostgreSQL / MySQL
  ├─ projects                       ├─ projects
  ├─ extraction_history            ├─ extraction_history
  └─ field_refinements             └─ field_refinements
  
PDF Processing                     PDF Processing
  ├─ Local storage          →      ├─ Cloud Storage (S3/GCS)
  └─ Memory-based                  └─ Distributed processing

Gemini API                         Gemini API
  └─ (same)                        └─ (same)

Authentication                     Authentication
  └─ None needed (local)    →      ├─ OAuth
                                   ├─ SAML
                                   └─ API Keys

Scaling                            Scaling
  └─ Single machine         →      ├─ Load balancer
                                   ├─ DB replication
                                   ├─ Cache layer
                                   └─ Message queues
```

---

## Class Hierarchy & Design Patterns

### Singleton Pattern (Database)

```python
@st.cache_resource
def get_db():
    if "db" not in st.session_state:
        st.session_state.db = ExtractionDatabase()
    return st.session_state.db

# Usage anywhere in app:
db = get_db()  # Same instance every time
db.save_project(...)
```

### State Management Pattern

```python
# Session state holds all user context
st.session_state.extraction_results  # Current analysis
st.session_state.extracted_images    # PDF pages in memory
st.session_state.current_project_id  # Active project
st.session_state.refining_field      # Currently refining

# Persists across Streamlit reruns
# Survives page refreshes
# Lost when browser tab closes
```

### Factory Pattern (Extractors)

```python
# App creates appropriate extractor based on need
extractor = GeminiDataExtractor()  # Full extraction
refined = extractor.extract_data_from_all_pages_consolidated(...)

# Or for refinement:
refined_field = extractor.refine_field_value(...)
```

---

## Performance Optimization Strategy

```
┌─ Initial Load
│  ├─ Database initialized once (cached)
│  ├─ Session state created once
│  └─ CSS loaded once

├─ During Extraction
│  ├─ Images held in memory (for quick access)
│  ├─ Gemini API called once (consolidated)
│  ├─ Results saved to DB (single transaction)
│  └─ UI updates efficiently

├─ During Display
│  ├─ Results formatted once
│  ├─ DataFrames created efficiently
│  ├─ CSS applied client-side
│  └─ Live log shows last 20 (not all)

└─ During Refinement
   ├─ Only one field sent to Gemini
   ├─ Quick targeted re-analysis
   ├─ Images still in memory (fast)
   └─ Single DB update
```

---

## Security & Data Flow

```
User Input                          Protected
─────────────────────────────────────────────

PDF Upload
  ├─ Validated: .pdf only
  ├─ Processed: PDF2Image
  ├─ Memory: Kept in session state
  └─ DB: Not stored (JSON of results only)

API Keys
  ├─ Source: .env file only
  ├─ Protected: Never logged or displayed
  └─ Scope: Gemini API only

Extracted Data
  ├─ Stored: SQLite (local only currently)
  ├─ Protected: Foreign key relationships
  ├─ Backed up: Via database file copy
  └─ Exported: User controls format

User Feedback
  ├─ Input: Text area with max length
  ├─ Stored: In field_refinements table
  ├─ Used: As hint to Gemini only
  └─ Logged: Complete audit trail

Deletion
  ├─ Cascading: All related records deleted
  ├─ Permanent: No undo capability
  └─ Logged: Could be tracked in audit
```

---

## Summary

**Architecture Philosophy**: 
- Modular (each component independent)
- Scalable (cloud-ready design)
- Reliable (error handling built-in)
- Maintainable (clear separation of concerns)
- User-centric (intuitive interfaces)

**Key Innovation**:
- Challenge mechanism with targeted re-analysis
- Full traceability of every value
- Professional quality control system
- Persistent project management
- Cloud migration path preserved

**Ready For**: 
- ✅ Local deployment (now)
- ✅ Team use (same machine)
- 🔄 Cloud deployment (architecture prepped)
- 🔄 API layer (modular design allows)
- 🔄 Advanced analytics (data model ready)
