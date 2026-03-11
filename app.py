"""
Streamlit application for extracting architectural data from PDF plans.
Professional Project Management System with persistent storage.
"""

import streamlit as st
import os
import pandas as pd
import json
from io import BytesIO
from datetime import datetime
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.pdf_processor import PDFProcessor  # noqa: E402
from src.gemini_api import GeminiDataExtractor  # noqa: E402
from src.database import get_db  # noqa: E402
from config.extraction_categories import EXTRACTION_CATEGORIES  # noqa: E402

# Page configuration
st.set_page_config(
    page_title="Architectural PDF Extractor - Pro",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced professional CSS styling
st.markdown("""
<style>
    /* General styling */
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 10px;
        background: linear-gradient(90deg, #2c3e50, #3498db);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Confidence badges */
    .confidence-high {
        background-color: #d4edda;
        color: #155724;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        display: inline-block;
    }
    
    .confidence-med {
        background-color: #fff3cd;
        color: #856404;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        display: inline-block;
    }
    
    .confidence-low {
        background-color: #f8d7da;
        color: #721c24;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        display: inline-block;
    }
    
    /* Validation status badges */
    .validation-verified {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
    }
    
    .validation-conflict {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
    }
    
    .validation-warning {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
    }
    
    /* Metric boxes */
    .metric-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Low confidence warning */
    .low-confidence-warning {
        background-color: #fff3cd;
        padding: 15px;
        border-left: 4px solid #ffc107;
        border-radius: 4px;
        margin: 10px 0;
    }
    
    /* Live log styling */
    .live-log {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 4px;
        padding: 12px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        max-height: 300px;
        overflow-y: auto;
    }

    /* Table styling for polished appearance */
    table {
        width: 100% !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    th {
        background-color: #f0f2f6 !important;
        font-weight: bold !important;
    }
    .refine-button {
        background-color: transparent;
        border: none;
        color: #3498db;
        cursor: pointer;
        font-size: 0.9rem;
    }
    
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #f0f2f6;
        border-radius: 8px;
    }
    
    /* Table styling */
    .dataframe {
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #3498db;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 8px 16px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #2980b9;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Sidebar styling */
    .sidebar-title {
        font-size: 1.2rem;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 10px;
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 8px;
    }
    
    .project-item {
        background-color: #ecf0f1;
        padding: 10px;
        border-radius: 4px;
        margin: 8px 0;
        border-left: 4px solid #3498db;
    }
</style>
""", unsafe_allow_html=True)


def get_confidence_color(confidence: int) -> str:
    """Get CSS class for confidence level styling."""
    if confidence >= 80:
        return "confidence-high"
    elif confidence >= 60:
        return "confidence-med"
    else:
        return "confidence-low"


def init_live_log():
    """Initialize live log in session state."""
    if "live_log" not in st.session_state:
        st.session_state.live_log = []


def add_log_entry(message: str):
    """Add a message to the live log."""
    init_live_log()
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.live_log.append(f"[{timestamp}] {message}")


def display_live_log():
    """Display the live log in a formatted box."""
    init_live_log()
    log_content = "\n".join(st.session_state.live_log[-20:])  # Show last 20 entries
    st.markdown(f"""<div class="live-log">{log_content}</div>""", unsafe_allow_html=True)


def show_project_history():
    """Display project history in sidebar."""
    st.markdown('<div class="sidebar-title">📁 Project History</div>', unsafe_allow_html=True)

    db = get_db()
    projects = db.get_all_projects()

    if not projects:
        st.info("No projects saved yet. Upload a PDF to create one.")
        return

    for project in projects:
        col1, col2 = st.columns([4, 1])

        with col1:
            # Create a clickable project item
            if st.button(
                f"📄 {project['project_name']}\n{project['updated_at'][:10]} | {project['total_pages']} pages",
                key=f"load_{project['id']}",
                use_container_width=True
            ):
                st.session_state.selected_project_id = project["id"]
                st.session_state.load_project = True

        with col2:
            # Delete button
            if st.button("🗑️", key=f"delete_{project['id']}", help="Delete this project"):
                if db.delete_project(project["id"]):
                    st.success(f"Deleted {project['project_name']}")
                    st.rerun()
                else:
                    st.error("Failed to delete project")


def display_confidence_badge(confidence: int) -> str:
    """Generate HTML for a confidence badge."""
    if confidence >= 80:
        return f'<span class="confidence-high">{confidence}%</span>'
    elif confidence >= 60:
        return f'<span class="confidence-med">{confidence}%</span>'
    else:
        return f'<span class="confidence-low">{confidence}%</span>'


def format_extraction_results(results: dict) -> pd.DataFrame:
    """Convert extraction results to a formatted DataFrame with professional accuracy features."""
    print("=== FORMATTING PROFESSIONAL RESULTS ===")
    print(f"Input results type: {type(results)}")
    print(f"Input results keys: {list(results.keys()) if isinstance(results, dict) else 'Not a dict'}")

    rows = []

    for field_code, field_data in results.items():
        print(f"Processing field: {field_code}, data: {field_data}")
        if isinstance(field_data, dict):
            # Extract confidence as numeric value for later filtering
            confidence_val = field_data.get("confidence", 0)
            confidence_str = f"{confidence_val}%"

            # Get validation status for color coding
            validation_status = field_data.get("validation_status", "unknown")

            rows.append({
                "Code": field_data.get("code", field_code),
                "Category": field_data.get("category", ""),
                "Key Measure": field_data.get("measure_name", field_code.replace("_", " ").title()),
                "Value": field_data.get("value", "—"),
                "Unit": field_data.get("unit", ""),
                "Confidence Level": confidence_str,
                "AI Reasoning / Source": field_data.get("reasoning", "No reasoning provided"),
                "Validation Status": validation_status,
                "Page Reference": field_data.get("page_reference", "N/A"),
                "_confidence_numeric": confidence_val,  # For sorting/filtering
                "_validation_status": validation_status,  # For color coding
                "_field_code": field_code,  # For refine tracking
            })

    print(f"Created {len(rows)} rows")
    df = pd.DataFrame(rows)

    # Sort by category, then by confidence level (descending)
    if not df.empty and "_confidence_numeric" in df.columns:
        df = df.sort_values(by=["Category", "_confidence_numeric"], ascending=[True, False])
        df = df.drop("_confidence_numeric", axis=1)

    print(f"Final DataFrame shape: {df.shape}")
    print(f"Final DataFrame columns: {list(df.columns)}")
    return df


def create_excel_export(results_df: pd.DataFrame, raw_results: dict) -> BytesIO:
    """Create an Excel file with formatted results including professional accuracy data."""
    with BytesIO() as output:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write summary sheet
            summary_data = {
                "Metric": ["Total Fields", "Fields Extracted", "Average Confidence", "High Confidence (>80%)", "Validation Issues", "Pages Processed"],
                "Value": [
                    len(results_df),
                    len(results_df[results_df["Value"] != "—"]),
                    f"{results_df['Confidence Level'].str.rstrip('%').astype(float).mean():.1f}%",
                    len(results_df[results_df["Confidence Level"].str.rstrip('%').astype(float) > 80]),
                    len(results_df[results_df["Validation Status"].isin(["calculated_conflict", "sanity_check_failed", "scale_uncertain"])]),
                    len(st.session_state.extracted_images) if hasattr(st.session_state, 'extracted_images') else "N/A"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

            # Write results sheet with all professional columns
            results_df.to_excel(writer, sheet_name="Results", index=False)

            # Write raw JSON data for debugging/advanced analysis
            raw_df = pd.DataFrame([{"raw_json": json.dumps(raw_results, indent=2)}])
            raw_df.to_excel(writer, sheet_name="Raw_Data", index=False)

        output.seek(0)
        return output


def get_validation_status_style(val):
    """Apply color coding based on validation status."""
    if pd.isna(val) or val == "unknown":
        return ""
    status = str(val).lower()
    if status in ["verified", "calculated_valid"]:
        return "background-color: #d4edda; color: #155724;"  # Green
    elif status in ["calculated_conflict", "sanity_check_failed"]:
        return "background-color: #f8d7da; color: #721c24;"  # Red
    elif status in ["scale_uncertain", "inferred"]:
        return "background-color: #fff3cd; color: #856404;"  # Yellow
    elif status == "not_found":
        return "background-color: #e2e3e5; color: #383d41;"  # Gray
    else:
        return "background-color: #d1ecf1; color: #0c5460;"  # Blue


def highlight_validation_status(df):
    """Apply styling to the Validation Status column."""
    if "Validation Status" in df.columns:
        return df.style.apply(lambda x: [get_validation_status_style(x.iloc[i]) if x.name == "Validation Status" else "" for i in range(len(x))], axis=0)
    return df.style


def get_low_confidence_items(results_df: pd.DataFrame) -> pd.DataFrame:
    """Get items with confidence below 70%."""
    confidence_nums = results_df["Confidence Level"].str.rstrip("%").astype(float)
    return results_df[confidence_nums < 70]


def initialize_session_state():
    """Initialize session state variables."""
    if 'extraction_results' not in st.session_state:
        st.session_state.extraction_results = None
    if 'pdf_processed' not in st.session_state:
        st.session_state.pdf_processed = False
    if 'extracted_images' not in st.session_state:
        st.session_state.extracted_images = []
    if 'current_project_id' not in st.session_state:
        st.session_state.current_project_id = None
    if 'current_project_name' not in st.session_state:
        st.session_state.current_project_name = None
    if 'selected_project_id' not in st.session_state:
        st.session_state.selected_project_id = None
    if 'load_project' not in st.session_state:
        st.session_state.load_project = False
    if 'refining_field' not in st.session_state:
        st.session_state.refining_field = None
    if 'feedback_idx' not in st.session_state:
        st.session_state.feedback_idx = None
    if 'row_feedback' not in st.session_state:
        st.session_state.row_feedback = {}
        st.session_state.refining_field = None
    if 'live_log' not in st.session_state:
        st.session_state.live_log = []


def main():
    """Main Streamlit application - Professional Project Management System."""
    initialize_session_state()

    # Handle loading a project from history
    if st.session_state.load_project and st.session_state.selected_project_id:
        db = get_db()
        project = db.get_project(st.session_state.selected_project_id)
        if project:
            # Complete load with JSON safety
            data = project['analysis_json']
            st.session_state.extraction_results = data if isinstance(data, (dict, list)) else json.loads(data)
            
            # Persistence
            st.session_state.current_project_id = project['id']
            st.session_state.current_project_name = project['project_name']
            st.session_state.pdf_processed = True
            st.session_state.load_project = False
            st.session_state.selected_project_id = None
            st.success(f"Loaded project: {project['project_name']}")
            # UI Trigger
            st.rerun()
        else:
            st.error("Project not found")
            st.session_state.load_project = False
            st.session_state.selected_project_id = None

    try:
        # Header
        st.markdown("<div class='main-header'>📐 Architectural PDF Data Extractor</div>", unsafe_allow_html=True)
        st.markdown("Professional Data Extraction System with Persistent Storage & Quality Control")
        st.divider()

        # Sidebar - Project History & Configuration
        with st.sidebar:
            # Project History Section
            show_project_history()
            st.divider()

            st.header("⚙️ Configuration")

            st.subheader("Extraction Categories")
            st.info("Categories are configured in `config/extraction_categories.py`")

            selected_categories = st.multiselect(
                "Select categories to extract:",
                options=list(EXTRACTION_CATEGORIES.keys()),
                default=list(EXTRACTION_CATEGORIES.keys()),
                help="Choose which data categories to extract from the PDF"
            )

            st.subheader("PDF Processing Settings")
            dpi = st.slider(
                "Resolution (DPI):",
                min_value=150,
                max_value=600,
                value=200,
                step=50,
                help="Higher DPI = better quality but slower processing"
            )

            st.subheader("API Status")
            api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                st.success("✓ Gemini API key configured")
            else:
                st.error("✗ Gemini API key missing. Add to Streamlit secrets or .env file")

        # Main content area
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📄 Upload PDF")
            uploaded_file = st.file_uploader(
                "Choose an architectural PDF file",
                type="pdf",
                help="Upload a PDF containing architectural plans"
            )

        with col2:
            st.subheader("🔄 Processing")
            if uploaded_file:
                if st.button("Extract Data", type="primary", use_container_width=True):
                    print("Button clicked!")
                    print(f"Processing file: {uploaded_file.name}")
                    print(f"File size: {len(uploaded_file.getvalue())} bytes")
                    print(f"Selected categories: {selected_categories}")
                    print(f"DPI setting: {dpi}")

                    try:
                        # First, quickly determine page count for dynamic messaging
                        pdf_processor_temp = PDFProcessor(dpi=dpi, fmt="png")
                        pdf_bytes = uploaded_file.read()
                        temp_images = pdf_processor_temp.convert_pdf_bytes(pdf_bytes)
                        page_count = len(temp_images)
                        
                        # Reset file pointer for actual processing
                        uploaded_file.seek(0)
                        
                        # Calculate estimated time (single API call, but longer processing time)
                        # Estimate ~2-3 minutes for consolidated analysis regardless of page count
                        estimated_minutes = 3
                        
                        with st.spinner(f"🔄 Analyzing all {page_count} pages with Gemini... this will take approx {estimated_minutes} minutes. Please do not refresh."):
                            extract_data_from_pdf(
                                uploaded_file,
                                selected_categories,
                                dpi
                            )
                    except Exception as e:
                        print(f"ERROR in button click: {str(e)}")
                        st.error(f"❌ Processing failed: {str(e)}")
                        import traceback
                        traceback.print_exc()
            else:
                st.info("Please upload a PDF file to begin extraction")

        st.divider()

        if st.session_state.extraction_results:
            st.write(f"Debug: Results found: {len(st.session_state.extraction_results) if st.session_state.extraction_results else 0}")
            display_results()

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.code(traceback.format_exc())


def extract_data_from_pdf(uploaded_file, selected_categories: list, dpi: int):
    """Extract data from uploaded PDF and save to database."""
    print("=== ENTERING extract_data_from_pdf ===")
    print(f"File: {uploaded_file.name if hasattr(uploaded_file, 'name') else 'No name'}")
    print(f"Selected categories: {selected_categories}")
    print(f"DPI: {dpi}")

    try:
        # Clear previous results to avoid conflicts
        st.session_state.extraction_results = None
        st.session_state.current_project_id = None
        st.session_state.current_project_name = None

        # Initialize components
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Step 1: Parse PDF
        add_log_entry("Starting PDF processing...")
        status_text.text("📖 Processing PDF...")
        progress_bar.progress(20)

        pdf_processor = PDFProcessor(dpi=dpi, fmt="png")
        pdf_bytes = uploaded_file.read()
        images = pdf_processor.convert_pdf_bytes(pdf_bytes)
        st.session_state.extracted_images = images

        add_log_entry(f"PDF converted to {len(images)} page(s)")
        status_text.text(f"✓ PDF converted to {len(images)} page(s)")
        progress_bar.progress(40)

        # Step 2: Initialize Gemini API
        add_log_entry("Connecting to Gemini API...")
        status_text.text("🤖 Connecting to Gemini API...")
        progress_bar.progress(50)

        extractor = GeminiDataExtractor(api_key=st.secrets.get("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        add_log_entry("Gemini API connected successfully")
        status_text.text("✓ Gemini API connected")
        progress_bar.progress(60)

        # Step 3: Get fields to extract based on selected categories (using codes)
        fields_to_extract = []
        selected_field_defs = {}
        for category_key in selected_categories:
            if category_key in EXTRACTION_CATEGORIES:
                category = EXTRACTION_CATEGORIES[category_key]
                for field in category["fields"]:
                    code = field["code"]
                    fields_to_extract.append(code)
                    selected_field_defs[code] = field

        # Step 4: Extract data
        add_log_entry(f"Starting paged analysis of {len(images)} pages...")
        status_text.text("🔍 Extracting data from images (page by page)...")
        progress_bar.progress(70)

        # Create progress tracking for paged extraction
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        # Progress callback for paged extraction
        def update_progress(page_num, total_pages):
            progress_percent = 70 + int((page_num / total_pages) * 15)  # 70% to 85%
            progress_bar.progress(progress_percent)
            progress_placeholder.text(f"📄 Processing page {page_num}/{total_pages}...")
            status_placeholder.text(f"Rate-limited API calls with 15s delays between pages...")
            add_log_entry(f"Completed page {page_num}/{total_pages}")

        # Use paged extraction method (one page at a time with delays)
        results = extractor.extract_data_from_multiple_pages(images, fields_to_extract, update_progress)
        add_log_entry("Paged data extraction completed successfully")

        # Clear progress indicators
        progress_placeholder.empty()
        status_placeholder.empty()

        # Debug: Print results to terminal
        print("=== AI EXTRACTION RESULTS ===")
        print(f"Number of results: {len(results)}")
        print(f"Result keys: {list(results.keys())}")
        print("=== END AI RESULTS ===")

        st.session_state.extraction_results = results
        st.session_state.pdf_processed = True

        progress_bar.progress(85)

        # Auto-refresh immediately after setting state
        # st.rerun()

        # Step 5: Save to database
        add_log_entry("Saving project to database...")
        db = get_db()
        project_name = uploaded_file.name.split(".")[0]  # Remove .pdf extension
        project_id = db.save_project(
            project_name=project_name,
            filename=uploaded_file.name,
            analysis_json=results,
            total_pages=len(images)
        )
        st.session_state.current_project_id = project_id
        st.session_state.current_project_name = project_name
        add_log_entry(f"Project '{project_name}' saved (ID: {project_id})")

        progress_bar.progress(100)
        status_text.text("✓ Data extraction & saving complete!")

        # Clear progress indicators after a moment
        import time
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()

        st.success("✅ Data extraction completed successfully!")

        # Force UI refresh to display results
        st.rerun()

    except ValueError as e:
        add_log_entry(f"Error: {str(e)}")
        st.error(f"⚠️ Configuration Error: {str(e)}")
        st.info("Please ensure GEMINI_API_KEY is set in Streamlit secrets or your .env file")
    except Exception as e:
        add_log_entry(f"Error: {str(e)}")
        st.error(f"❌ Error during extraction: {str(e)}")
        st.exception(e)


def refine_field(field_code: str, field_row: pd.Series, user_feedback: str, results_df: pd.DataFrame):
    """Handle field refinement using targeted AI re-analysis."""
    add_log_entry(f"Starting refinement for field {field_code}...")
    
    try:
        # Get current project and images
        if not st.session_state.current_project_id:
            st.error("No active project. Please extract data first.")
            return

        if not st.session_state.extracted_images:
            st.error("No PDF images available for re-analysis.")
            return

        # Show processing message
        with st.spinner(f"🔄 Re-analyzing {field_code} with your feedback..."):
            add_log_entry(f"Initializing Gemini API for refinement...")
            extractor = GeminiDataExtractor(api_key=st.secrets.get("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

            add_log_entry(f"Sending refinement request with user feedback...")
            refined_field = extractor.refine_field_value(
                images=st.session_state.extracted_images,
                field_code=field_code,
                original_value=str(field_row["Value"]),
                user_feedback=user_feedback,
                original_reasoning=field_row["AI Reasoning / Source"]
            )

            add_log_entry(f"Refinement completed for {field_code}")

            # Update the results in session state
            if field_code in st.session_state.extraction_results:
                st.session_state.extraction_results[field_code].update(refined_field)

            # Save refinement to database
            db = get_db()
            db.add_field_refinement(
                project_id=st.session_state.current_project_id,
                field_code=field_code,
                original_value=str(field_row["Value"]),
                refined_value=str(refined_field.get("value", "")),
                user_feedback=user_feedback
            )

            add_log_entry(f"Refinement saved to database for project {st.session_state.current_project_id}")

            st.success(f"✅ Field {field_code} refined successfully!")
            st.markdown("**New Value:**")
            st.info(f"{refined_field.get('value')} {refined_field.get('unit', '')}")
            st.markdown("**New Reasoning:**")
            st.markdown(f"```{refined_field.get('reasoning', 'No reasoning provided')}```")

            # Clear refining state
            st.session_state.refining_field = None

            # Rerun to show updated results
            st.rerun()

    except Exception as e:
        add_log_entry(f"Error during refinement: {str(e)}")
        st.error(f"❌ Refinement failed: {str(e)}")
        st.exception(e)


def display_results():
    """Display extraction results in organized format with enhanced UI."""

    st.subheader("📊 Extraction Results")

    if not st.session_state.extraction_results:
        st.info("No results to display. Please extract data from a PDF first.")
        return

    # Debug: Print results to terminal when displaying
    print("=== DISPLAYING RESULTS ===")
    print(f"Results type: {type(st.session_state.extraction_results)}")
    results = st.session_state.extraction_results
    keys = list(results.keys()) if isinstance(results, dict) else 'Not a dict'
    print(f"Results keys: {keys}")
    print("=== END DISPLAY DEBUG ===")

    # Raw data toggle
    show_raw = st.checkbox("🔍 Show Raw Gemini Output", help="Display the raw JSON response from Gemini for debugging")

    if show_raw:
        st.markdown("### 📄 Raw Gemini Response")
        st.json(st.session_state.extraction_results)
        st.divider()

    # Create result dataframe
    results_df = format_extraction_results(st.session_state.extraction_results)

    # Debug: Print dataframe info
    print(f"DataFrame shape: {results_df.shape}")
    print(f"DataFrame columns: {list(results_df.columns)}")
    print(f"DataFrame head:\n{results_df.head()}")

    if results_df.empty:
        st.warning("No data was extracted from the PDF.")
        return

    # Summary card above table
    st.markdown("### 📈 Extraction Summary")
    project_name = st.session_state.current_project_name or "(Unnamed)"
    total_measures = len(results_df)
    avg_confidence = results_df["Confidence Level"].str.rstrip("%").astype(float).mean()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Measures Extracted", total_measures)
    c2.metric("Average Confidence", f"{avg_confidence:.1f}%")
    c3.metric("Project Name", project_name)

    st.divider()

    # Professional Validation Issues Section
    validation_issues = results_df[results_df["Validation Status"].isin(["calculated_conflict", "sanity_check_failed", "scale_uncertain"])]
    if not validation_issues.empty:
        st.markdown("### ⚠️ Validation Issues Detected")
        st.warning(f"Found {len(validation_issues)} validation issues that require attention:")

        # Display validation issues in a table
        issues_display = validation_issues[["Code", "Key Measure", "Validation Status", "AI Reasoning / Source"]].copy()
        st.dataframe(
            issues_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Code": st.column_config.TextColumn("Code", width="small"),
                "Key Measure": st.column_config.TextColumn("Key Measure", width="medium"),
                "Validation Status": st.column_config.TextColumn("Validation Status", width="medium"),
                "AI Reasoning / Source": st.column_config.TextColumn("AI Reasoning / Source", width="extra-large"),
            }
        )
        st.divider()

    # Check for low confidence items
    low_conf_df = get_low_confidence_items(results_df)
    if not low_conf_df.empty:
        st.markdown("### ⚠️ Items with Low Confidence (< 70%)")
        st.markdown("""
        <div class="low-confidence-warning">
            The following extracted fields have low confidence scores. Please verify them manually.
        </div>
        """, unsafe_allow_html=True)

        # Display low confidence items
        low_conf_display = low_conf_df.copy()
        st.dataframe(
            low_conf_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Code": st.column_config.TextColumn("Code", width="small"),
                "Category": st.column_config.TextColumn("Category", width="small"),
                "Key Measure": st.column_config.TextColumn("Key Measure", width="large"),
                "Value": st.column_config.TextColumn("Value", width="medium"),
                "Unit": st.column_config.TextColumn("Unit", width="small"),
                "Confidence Level": st.column_config.TextColumn("Confidence Level", width="small"),
                "AI Reasoning / Source": st.column_config.TextColumn("AI Reasoning / Source", width="extra-large"),
                "Validation Status": st.column_config.TextColumn("Validation Status", width="medium"),
                "Page Reference": st.column_config.TextColumn("Page Reference", width="small"),
            }
        )
        st.divider()

    # Display all results table with clean, professional styling
    # Only keep required columns and rename for display
    display_df = results_df[["Code", "Key Measure", "Value", "Unit", "Confidence Level", "AI Reasoning / Source"]].copy()
    display_df = display_df.rename(columns={
        "Key Measure": "Measure Name",
        "Confidence Level": "Confidence",
        "AI Reasoning / Source": "Reasoning/Source"
    })

    st.markdown("### 📋 All Extracted Data")
    # Table headers with custom sizing
    header_cols = st.columns([1,2,1,1,1,3,1])
    headers = ["Code", "Measure Name", "Value", "Unit", "Confidence", "Reasoning/Source", "Action"]
    for hc, h in zip(header_cols, headers):
        hc.markdown(f"**{h}**")

    # Render each row manually to include badges, formatting, and feedback textarea
    for idx, row in display_df.iterrows():
        cols = st.columns([1,2,1,1,1,3,1])
        cols[0].write(row["Code"])
        cols[1].write(row["Measure Name"])
        # value with N/A fallback and centered bold
        val = row.get("Value", "")
        if not val or val == "—":
            val_html = "<span style='color:#888;'>N/A</span>"
        else:
            val_html = f"<div style='text-align:center;font-weight:bold;'>{val}</div>"
        cols[2].markdown(val_html, unsafe_allow_html=True)
        # unit centered bold
        unit = row.get("Unit", "")
        unit_html = f"<div style='text-align:center;font-weight:bold;'>{unit or ''}</div>"
        cols[3].markdown(unit_html, unsafe_allow_html=True)
        # confidence badge
        try:
            conf_val = int(str(row["Confidence"]).rstrip("%"))
        except Exception:
            conf_val = 0
        badge_color = "green" if conf_val > 90 else "orange" if conf_val >= 70 else "red"
        cols[4].markdown(
            f"<span style='background-color:{badge_color}; color:white; padding:2px 6px; border-radius:4px;'>{conf_val}%</span>",
            unsafe_allow_html=True
        )
        # reasoning with wrap
        reasoning = row.get("Reasoning/Source", "")
        cols[5].markdown(f"<div style='white-space:normal; word-wrap:break-word;'>{reasoning}</div>", unsafe_allow_html=True)
        # action column: refine button and optional checkmark
        status_val = results_df.loc[idx, "Validation Status"] if idx in results_df.index else ""
        if isinstance(status_val, str) and status_val.lower() == "verified":
            cols[6].write("✅")
        if cols[6].button("Refine", key=f"refine_btn_{idx}"):
            st.session_state.feedback_idx = idx
        # show textarea if this row is selected
        if st.session_state.feedback_idx == idx:
            cols[6].text_area("Feedback", key=f"feedback_{idx}", placeholder="Enter your comments here...")

    st.divider()

    # Refine/Challenge Mechanism
    st.markdown("### 🔧 Refine Results (Challenge Mechanism)")
    st.markdown("Found an error or want to challenge the AI? Provide feedback and we'll re-analyze just that field.")

    refine_col1, refine_col2 = st.columns([2, 1])

    with refine_col1:
        refine_field_code = st.selectbox(
            "Select a field to refine:",
            options=[row["Code"] for _, row in results_df.iterrows()],
            key="refine_field_select"
        )

    with refine_col2:
        if st.button("🔍 Refine This Field", use_container_width=True):
            st.session_state.refining_field = refine_field_code

    if st.session_state.refining_field:
        st.markdown(f"#### Refining: {st.session_state.refining_field}")

        # Get the current field data
        field_row = results_df[results_df["Code"] == st.session_state.refining_field].iloc[0]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Current Value:**")
            st.info(f"{field_row['Value']} {field_row['Unit']}")

        with col2:
            st.markdown("**Current Confidence:**")
            st.metric("", f"{field_row['Confidence Level']}")

        st.markdown("**AI Reasoning:**")
        st.markdown(f"```{field_row['AI Reasoning / Source']}```")

        # User feedback input
        user_feedback = st.text_area(
            "What's wrong with this extraction? Provide details:",
            placeholder="e.g., 'The value should be 50 ft, not 45 ft. I can see it clearly marked on the foundation plan.'",
            height=100,
            key="refine_feedback"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Submit Refinement", type="primary", use_container_width=True):
                if not user_feedback.strip():
                    st.error("Please provide feedback before refining.")
                else:
                    refine_field(refine_field_code, field_row, user_feedback, results_df)

        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.refining_field = None
                st.rerun()

    st.divider()

    # Export options
    st.markdown("### 💾 Export Results")

    col1, col2, col3 = st.columns(3)

    with col1:
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name="extraction_results.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        # Excel export
        try:
            excel_buffer = create_excel_export(results_df, st.session_state.extraction_results)
            st.download_button(
                label="📊 Download as Excel",
                data=excel_buffer,
                file_name="extraction_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Excel export unavailable: {str(e)}")

    with col3:
        json_str = st.session_state.extraction_results
        st.download_button(
            label="📄 Download as JSON",
            data=json.dumps(json_str, indent=2),
            file_name="extraction_results.json",
            mime="application/json",
            use_container_width=True
        )

    # Additional metadata
    st.divider()
    with st.expander("📌 Raw Data (JSON)"):
        st.json(st.session_state.extraction_results)


if __name__ == "__main__":
    main()
