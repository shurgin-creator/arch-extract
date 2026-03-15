"""
Streamlit application for extracting architectural data from PDF plans.
Professional Project Management System with persistent storage.
"""

import gc
import streamlit as st
import os
import pandas as pd
import json
from io import BytesIO
from datetime import datetime
import time
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.pdf_processor import PDFProcessor  # noqa: E402
from src.gemini_api import GeminiDataExtractor  # noqa: E402
from src.supabase_client import get_supabase  # noqa: E402
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
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    /* ── Auth page hero ── */
    .auth-hero {
        text-align: center;
        padding: 48px 0 32px;
    }
    .auth-logo {
        font-size: 3rem;
        line-height: 1;
    }
    .auth-title {
        font-size: 2rem;
        font-weight: 700;
        color: #0068c9;
        margin: 8px 0 4px;
    }
    .auth-subtitle {
        font-size: 1rem;
        color: #666;
        margin-bottom: 32px;
    }
    .auth-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 32px;
        box-shadow: 0 4px 24px rgba(0,104,201,0.10);
        border: 1px solid #e8edf2;
    }

    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 6px;
        background: linear-gradient(90deg, #0068c9, #004fa3);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
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
    .validation-verified  { background-color: #d4edda; border-left: 4px solid #28a745; }
    .validation-conflict  { background-color: #f8d7da; border-left: 4px solid #dc3545; }
    .validation-warning   { background-color: #fff3cd; border-left: 4px solid #ffc107; }

    /* Metric boxes */
    .metric-box {
        background: linear-gradient(135deg, #0068c9 0%, #004fa3 100%);
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        color: white;
        box-shadow: 0 4px 12px rgba(0,104,201,0.25);
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
        border-radius: 6px;
        padding: 12px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        max-height: 300px;
        overflow-y: auto;
    }

    /* Table styling */
    table { width: 100% !important; }
    th    { background-color: #f0f2f6 !important; font-weight: 700 !important; }

    /* Tab list accent */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #eef2f7;
        border-radius: 8px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        font-weight: 600;
    }

    /* DataGrid card */
    .dataframe {
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }

    /* Sidebar styling */
    .sidebar-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin-top: 16px;
        margin-bottom: 8px;
        color: #1f1f2e;
        border-bottom: 2px solid #0068c9;
        padding-bottom: 6px;
    }

    .project-item {
        background-color: #eef2f7;
        padding: 10px;
        border-radius: 6px;
        margin: 6px 0;
        border-left: 4px solid #0068c9;
    }
</style>
""", unsafe_allow_html=True)



def _is_valid_bbox(bb) -> bool:
    """Return True for a single box [y,x,y,x] or a non-empty list of such boxes."""
    if not isinstance(bb, list) or len(bb) == 0:
        return False
    if isinstance(bb[0], (int, float)):
        return len(bb) == 4
    return all(isinstance(b, list) and len(b) == 4 for b in bb)


@st.dialog("Visual Trace", width="large")
def show_trace_dialog(field_code: str, field_data: dict, pdf_bytes: bytes, dpi: int):
    """Render the highlighted page in a modal dialog."""
    bb = field_data.get("bounding_box")
    if not _is_valid_bbox(bb):
        st.info("No spatial bounding box is available for this field.")
        return

    # Parse page number from "Page N" string
    page_ref = field_data.get("page_reference", "Page 1")
    try:
        page_num = int(str(page_ref).replace("Page", "").strip())
    except Exception:
        page_num = 1

    measure_name = field_data.get("measure_name", field_code)
    value = field_data.get("value", "—")
    unit_str = field_data.get("unit", "")

    # Determine box count for display
    box_count = len(bb) if isinstance(bb[0], list) else 1
    instances_label = f" &nbsp;|&nbsp; **Instances:** {box_count} highlighted" if box_count > 1 else ""

    st.markdown(f"**Field:** `{field_code}` — {measure_name}")
    st.markdown(
        f"**Value:** {value} {unit_str} &nbsp;|&nbsp; **Page:** {page_ref}"
        f"{instances_label}",
        unsafe_allow_html=True,
    )

    with st.spinner("Rendering page with highlight…"):
        try:
            processor = PDFProcessor(dpi=dpi, fmt="png")
            highlighted = processor.render_page_with_highlight(
                pdf_bytes, page_num, bb, dpi=dpi,
                overlay_vectors=st.session_state.get("show_cad_vectors", False),
            )
            st.image(highlighted, width="stretch")
        except Exception as e:
            st.error(f"Could not render highlight: {e}")


@st.dialog("PDF Required — Re-upload to Enable Trace", width="large")
def show_pdf_required_dialog(field_code: str, field_data: dict, dpi: int):
    """
    Shown when pdf_bytes is unavailable (old project not yet in Supabase storage).
    Lets the user re-upload the PDF, permanently fixes the storage gap, then renders the trace.
    """
    st.info(
        "This project was extracted before cloud PDF storage was enabled. "
        "Re-upload the original PDF once — it will be saved permanently so "
        "you won't need to do this again."
    )
    uploaded = st.file_uploader("Re-upload the PDF", type="pdf", key="reupload_pdf_dialog")
    if not uploaded:
        return

    pdf_bytes = uploaded.getvalue()
    st.session_state.pdf_bytes_for_refine = pdf_bytes

    # Permanently fix Supabase storage so future sessions work without re-uploading
    user = st.session_state.get("user")
    project_id = st.session_state.get("current_project_id")
    if user and project_id:
        try:
            sb = get_supabase()
            resp = sb.table("projects").select("filename").eq("id", project_id).single().execute()
            filename = (resp.data.get("filename") if resp.data else None) or uploaded.name
            storage_path = f"{user.id}/{filename}"
            sb.storage.from_("pdfs").upload(
                path=storage_path,
                file=pdf_bytes,
                file_options={"content-type": "application/pdf", "upsert": "true"},
            )
            st.success("PDF saved to cloud storage — Visual Trace will work automatically in all future sessions.")
        except Exception as e:
            st.warning(f"Cloud save failed (non-fatal): {e}")

    # Render trace inline (can't nest @st.dialog calls, so we render directly here)
    bb = field_data.get("bounding_box")
    if not _is_valid_bbox(bb):
        st.info("No bounding box available for this field.")
        return

    page_ref = field_data.get("page_reference", "Page 1")
    try:
        page_num = int(str(page_ref).replace("Page", "").strip())
    except Exception:
        page_num = 1

    st.markdown(f"**Field:** `{field_code}` — {field_data.get('measure_name', field_code)}")
    st.markdown(
        f"**Value:** {field_data.get('value', '—')} {field_data.get('unit', '')} &nbsp;|&nbsp; "
        f"**Page:** {page_ref}",
        unsafe_allow_html=True,
    )
    with st.spinner("Rendering trace…"):
        try:
            processor = PDFProcessor(dpi=dpi, fmt="png")
            highlighted = processor.render_page_with_highlight(
                pdf_bytes, page_num, bb, dpi=dpi,
                overlay_vectors=st.session_state.get("show_cad_vectors", False),
            )
            st.image(highlighted, width="stretch")
        except Exception as e:
            st.error(f"Could not render highlight: {e}")


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


def delete_project(project_id: str, filename: str):
    """
    Delete a project from Supabase:
      1. Remove the PDF file from the 'pdfs' storage bucket.
      2. Delete the project row from the 'projects' table.
    Raises on DB failure so the caller can show the error.
    """
    supabase = get_supabase()
    user = st.session_state.get("user")

    # Delete PDF from storage (non-fatal — file may not exist)
    if user and filename:
        try:
            storage_path = f"{user.id}/{filename}"
            supabase.storage.from_("pdfs").remove([storage_path])
        except Exception as storage_err:
            print(f"Storage delete warning (non-fatal): {storage_err}")

    # Delete the DB row — raises if it fails
    supabase.table("projects").delete().eq("id", project_id).execute()

    # If the deleted project was currently loaded, clear it from session state
    if st.session_state.get("current_project_id") == project_id:
        st.session_state.extraction_results = None
        st.session_state.current_project_id = None
        st.session_state.current_project_name = None
        st.session_state.pdf_processed = False


def show_project_history():
    """Display project history from Supabase in the sidebar."""
    st.markdown('<div class="sidebar-title">📁 Project History</div>', unsafe_allow_html=True)

    user = st.session_state.get("user")
    if not user:
        return

    try:
        supabase = get_supabase()
        resp = (
            supabase.table("projects")
            .select("id, project_name, filename, total_pages, updated_at, status")
            .eq("user_id", user.id)
            .order("updated_at", desc=True)
            .execute()
        )
        projects = resp.data or []
    except Exception as e:
        st.warning(f"Could not load project history: {e}")
        return

    if not projects:
        st.info("No projects saved yet. Upload a PDF to create one.")
        return

    for project in projects:
        col1, col2 = st.columns([4, 1])
        status_icon = "✅" if project.get("status") == "completed" else "⏳"
        updated = (project.get("updated_at") or "")[:10]

        with col1:
            if st.button(
                f"{status_icon} {project['project_name']}\n{updated} | {project.get('total_pages', '?')} pages",
                key=f"load_{project['id']}",
                use_container_width=True,
            ):
                st.session_state.selected_project_id = project["id"]
                st.session_state.load_project = True

        with col2:
            if st.button("🗑️", key=f"delete_{project['id']}", help="Delete this project"):
                try:
                    delete_project(project["id"], project.get("filename", ""))
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")


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

    # Cast mixed-type columns to str to prevent PyArrow ArrowInvalid crashes
    # (Gemini returns numeric or string values; Arrow infers the wrong dtype)
    for col in ("Value", "Unit", "Confidence Level", "Category", "Page Reference"):
        if col in df.columns:
            df[col] = df[col].astype(str)

    # Sort by category, then confidence descending; drop internal helper columns
    if not df.empty and "_confidence_numeric" in df.columns:
        df = df.sort_values(by=["Category", "_confidence_numeric"], ascending=[True, False])
        df = df.drop(columns=["_confidence_numeric", "_validation_status", "_field_code"], errors="ignore")

    print(f"Final DataFrame shape: {df.shape}")
    print(f"Final DataFrame columns: {list(df.columns)}")
    return df


def create_excel_export(results_df: pd.DataFrame, raw_results: dict) -> bytes:
    """Create an Excel file with formatted results including professional accuracy data."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Write summary sheet
        summary_data = {
            "Metric": ["Total Fields", "Fields Extracted", "Average Confidence", "High Confidence (>80%)", "Validation Issues", "Pages Processed"],
            "Value": [
                len(results_df),
                len(results_df[results_df["Value"] != "—"]),
                f"{results_df['Confidence Level'].str.rstrip('%').astype(float).mean():.1f}%",
                len(results_df[results_df["Confidence Level"].str.rstrip('%').astype(float) > 80]),
                len(results_df[results_df["Validation Status"].isin(["calculated_conflict", "sanity_check_failed", "scale_uncertain"])]),
                st.session_state.get("total_pages", "N/A")
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # Write results sheet with all professional columns
        results_df.to_excel(writer, sheet_name="Results", index=False)

        # Write raw JSON data for debugging/advanced analysis
        raw_df = pd.DataFrame([{"raw_json": json.dumps(raw_results, indent=2)}])
        raw_df.to_excel(writer, sheet_name="Raw_Data", index=False)

    # Extract bytes AFTER ExcelWriter closes so the buffer is fully flushed
    return output.getvalue()


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


def show_auth_page():
    """Full-page login/signup UI shown when the user is not authenticated."""
    # Hero section — centered, full width
    st.markdown("""
    <div class="auth-hero">
        <div class="auth-logo">📐</div>
        <div class="auth-title">Architectural PDF Data Extractor</div>
        <div class="auth-subtitle">AI-powered data extraction from architectural plans &amp; drawings</div>
    </div>
    """, unsafe_allow_html=True)

    try:
        supabase = get_supabase()
    except ValueError as e:
        st.error(f"⚠️ Supabase not configured: {e}")
        st.info("Add SUPABASE_URL and SUPABASE_KEY to your Streamlit secrets.")
        return

    # Center the auth card using columns
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

        with tab_login:
            email = st.text_input("Email", key="login_email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", key="login_password", placeholder="••••••••")
            if st.button("Log In", type="primary", use_container_width=True, key="login_btn"):
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    try:
                        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = response.user
                        st.session_state.supabase_access_token = response.session.access_token
                        st.session_state.supabase_refresh_token = response.session.refresh_token
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {str(e)}")

        with tab_signup:
            email_s = st.text_input("Email", key="signup_email", placeholder="you@example.com")
            password_s = st.text_input("Password (min 6 chars)", type="password", key="signup_password", placeholder="••••••••")
            if st.button("Create Account", type="primary", use_container_width=True, key="signup_btn"):
                if not email_s or not password_s:
                    st.error("Please fill in all fields.")
                else:
                    try:
                        supabase.auth.sign_up({"email": email_s, "password": password_s})
                        st.success("✅ Account created! Check your email to confirm, then log in.")
                    except Exception as e:
                        st.error(f"Sign-up failed: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    # Auth
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'supabase_access_token' not in st.session_state:
        st.session_state.supabase_access_token = None
    if 'supabase_refresh_token' not in st.session_state:
        st.session_state.supabase_refresh_token = None
    if 'extraction_results' not in st.session_state:
        st.session_state.extraction_results = None
    if 'pdf_processed' not in st.session_state:
        st.session_state.pdf_processed = False
    if 'extracted_images' not in st.session_state:
        st.session_state.extracted_images = []  # kept for compat; not bulk-loaded
    if 'pdf_bytes_for_refine' not in st.session_state:
        st.session_state.pdf_bytes_for_refine = None
    if 'pdf_dpi_for_refine' not in st.session_state:
        st.session_state.pdf_dpi_for_refine = 200
    if 'total_pages' not in st.session_state:
        st.session_state.total_pages = 0
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
    if 'quota_warning' not in st.session_state:
        st.session_state.quota_warning = None


def main():
    """Main Streamlit application - Professional Project Management System."""
    initialize_session_state()

    # ── Auth gate ──────────────────────────────────────────────────────────
    if not st.session_state.get("user"):
        show_auth_page()
        return

    # ── Load project from history ──────────────────────────────────────────
    if st.session_state.load_project and st.session_state.selected_project_id:
        try:
            supabase = get_supabase()
            resp = (
                supabase.table("projects")
                .select("*")
                .eq("id", st.session_state.selected_project_id)
                .single()
                .execute()
            )
            project = resp.data
            if project:
                # analysis_json is JSONB — already a dict from Supabase
                st.session_state.extraction_results = project["analysis_json"]
                st.session_state.current_project_id = project["id"]
                st.session_state.current_project_name = project["project_name"]
                st.session_state.pdf_processed = True
                st.session_state.load_project = False
                st.session_state.selected_project_id = None
                st.success(f"Loaded project: {project['project_name']}")
                st.rerun()
        except Exception as e:
            st.error(f"Failed to load project: {e}")
            st.session_state.load_project = False
            st.session_state.selected_project_id = None

    try:
        # Header
        st.markdown("<div class='main-header'>📐 Architectural PDF Data Extractor</div>", unsafe_allow_html=True)
        st.markdown("Professional Data Extraction System with Persistent Storage & Quality Control")
        st.divider()

        # Sidebar - Auth status + Project History + Configuration
        with st.sidebar:
            # User info & logout
            user = st.session_state.user
            st.markdown(f"👤 **{user.email}**")
            if st.button("Log Out", key="logout_btn"):
                try:
                    supabase = get_supabase()
                    supabase.auth.sign_out()
                except Exception:
                    pass
                for key in ["user", "supabase_client", "supabase_access_token",
                            "supabase_refresh_token", "extraction_results",
                            "current_project_id", "current_project_name"]:
                    st.session_state.pop(key, None)
                st.rerun()
            st.divider()

            # Project History (Supabase-backed)
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

            with st.expander("⚙️ Advanced Settings"):
                preprocess = st.checkbox(
                    "Enable image preprocessing",
                    value=True,
                    help=(
                        "Apply OpenCV CLAHE contrast enhancement, deskew, and "
                        "unsharp-mask sharpening before sending pages to Gemini. "
                        "Improves accuracy on scanned or low-contrast drawings. "
                        "Disable only for debugging or if pages look correct already."
                    ),
                )
                st.caption(
                    "Preprocessing is applied per-page inside the lazy extraction loop "
                    "and does not increase peak memory usage."
                )

                st.checkbox(
                    "[Beta] Show Raw CAD Vectors",
                    value=False,
                    key="show_cad_vectors",
                    help=(
                        "Overlay the exact vector geometry extracted from the PDF onto "
                        "the Visual Trace image. Cyan lines show raw CAD paths before "
                        "any rasterisation — useful for verifying bounding box alignment."
                    ),
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
                # Upload PDF to Supabase storage as soon as a file is selected
                # so _get_pdf_bytes() can retrieve it even across sessions.
                _upload_key = f"_uploaded_{uploaded_file.name}_{uploaded_file.size}"
                if _upload_key not in st.session_state:
                    _upload_user = st.session_state.get("user")
                    if _upload_user:
                        try:
                            _sb = get_supabase()
                            _storage_path = f"{_upload_user.id}/{uploaded_file.name}"
                            _sb.storage.from_("pdfs").upload(
                                path=_storage_path,
                                file=uploaded_file.getvalue(),
                                file_options={"content-type": "application/pdf", "upsert": "true"},
                            )
                        except Exception as _upload_err:
                            st.warning(
                                f"Could not pre-upload PDF to cloud storage "
                                f"(Visual Trace for history projects may be unavailable): {_upload_err}"
                            )
                    st.session_state[_upload_key] = True

                if st.button("Extract Data", type="primary", use_container_width=True):
                    print("Button clicked!")
                    print(f"Processing file: {uploaded_file.name}")
                    print(f"File size: {len(uploaded_file.getvalue())} bytes")
                    print(f"Selected categories: {selected_categories}")
                    print(f"DPI setting: {dpi}")

                    try:
                        # Get page count cheaply (no image rendering) for the spinner message
                        pdf_processor_temp = PDFProcessor(dpi=dpi, fmt="png")
                        pdf_bytes_preview = uploaded_file.read()
                        page_count = pdf_processor_temp.get_page_count(pdf_bytes_preview)
                        del pdf_bytes_preview  # Free immediately — only needed for count

                        # Reset file pointer so extract_data_from_pdf can read it
                        uploaded_file.seek(0)

                        estimated_minutes = max(1, page_count // 4)

                        with st.spinner(f"🔄 Analyzing {page_count} pages lazily with Gemini (~{estimated_minutes} min). Please do not refresh."):
                            extract_data_from_pdf(
                                uploaded_file,
                                selected_categories,
                                dpi,
                                preprocess,
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


def extract_data_from_pdf(uploaded_file, selected_categories: list, dpi: int, preprocess: bool = True):
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
        st.session_state.quota_warning = None

        # Initialize components
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Step 1: Parse PDF
        add_log_entry("Starting PDF processing...")
        status_text.text("📖 Processing PDF...")
        progress_bar.progress(20)

        pdf_processor = PDFProcessor(dpi=dpi, fmt="png", preprocess=preprocess)
        pdf_bytes = uploaded_file.read()

        # Count pages cheaply (no rendering) so we can show progress and use lazy iterator
        total_pages_count = pdf_processor.get_page_count(pdf_bytes)

        # Store pdf_bytes for on-demand rendering during field refinement
        st.session_state.pdf_bytes_for_refine = pdf_bytes
        st.session_state.pdf_dpi_for_refine = dpi
        st.session_state.total_pages = total_pages_count

        add_log_entry(f"PDF opened: {total_pages_count} pages (lazy processing — images never all in memory)")
        status_text.text(f"✓ PDF opened: {total_pages_count} page(s) — lazy mode active")
        progress_bar.progress(40)

        # ── Cloud storage upload ──────────────────────────────────────────
        user = st.session_state.get("user")
        supabase = get_supabase()
        project_name = uploaded_file.name.rsplit(".", 1)[0]

        if user:
            try:
                storage_path = f"{user.id}/{uploaded_file.name}"
                supabase.storage.from_("pdfs").upload(
                    path=storage_path,
                    file=pdf_bytes,
                    file_options={"content-type": "application/pdf", "upsert": "true"},
                )
                add_log_entry(f"PDF uploaded to cloud storage: pdfs/{storage_path}")
            except Exception as e:
                add_log_entry(f"Cloud storage upload warning (non-fatal): {e}")

        # ── Insert project row with status='processing' ───────────────────
        project_id = None
        if user:
            try:
                resp = supabase.table("projects").insert({
                    "project_name": project_name,
                    "filename": uploaded_file.name,
                    "user_id": user.id,
                    "total_pages": total_pages_count,
                    "analysis_json": {},
                    "status": "processing",
                }).execute()
                project_id = resp.data[0]["id"]
                st.session_state.current_project_id = project_id
                st.session_state.current_project_name = project_name
                add_log_entry(f"Project '{project_name}' created in Supabase (ID: {project_id})")
            except Exception as e:
                add_log_entry(f"Supabase project creation warning (non-fatal): {e}")

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
        add_log_entry(f"Starting lazy extraction of {total_pages_count} pages...")
        status_text.text("🔍 Extracting data lazily (one page at a time)...")
        progress_bar.progress(70)

        # Create progress tracking for paged extraction
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        # Progress callback for paged extraction
        def update_progress(page_num, total_pages):
            progress_percent = 70 + int((page_num / total_pages) * 15)  # 70% to 85%
            progress_bar.progress(progress_percent)
            progress_placeholder.text(f"📄 Processing page {page_num}/{total_pages}...")
            status_placeholder.text("Rate-limited API calls with 15s delays between pages...")
            add_log_entry(f"Completed page {page_num}/{total_pages}")

        # ── Incremental checkpoint callback ───────────────────────────────
        # Persists partial results to Supabase after every successful page.
        # If a 429 quota error fires mid-run, all completed pages are already
        # safely stored in the cloud.
        def checkpoint_to_supabase(page_num: int, partial_results: dict):
            if not project_id:
                return
            try:
                supabase.table("projects").update({
                    "analysis_json": partial_results,
                }).eq("id", project_id).execute()
                add_log_entry(f"Checkpoint saved to Supabase after page {page_num}")
            except Exception as ck_err:
                print(f"Supabase checkpoint warning (non-fatal): {ck_err}")

        # Lazy extraction: iter_pages yields one (image, text) tuple at a time,
        # each freed from memory before the next page is loaded.
        page_iter = pdf_processor.iter_pages(pdf_bytes)
        try:
            results, quota_warning = extractor.extract_data_from_multiple_pages(
                page_iter, fields_to_extract, update_progress, total_pages_count,
                checkpoint_callback=checkpoint_to_supabase,
            )
        except Exception as api_err:
            progress_placeholder.empty()
            status_placeholder.empty()
            add_log_entry(f"API extraction failed: {str(api_err)}")
            st.error(f"❌ Gemini API extraction failed: {str(api_err)}")
            st.info("Check the terminal/logs for the full exception traceback.")
            return

        if quota_warning:
            st.session_state.quota_warning = quota_warning
            add_log_entry(f"Quota warning: {quota_warning}")

        progress_placeholder.empty()
        status_placeholder.empty()
        add_log_entry("Lazy data extraction completed successfully")

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

        # Step 5: Mark project as completed in Supabase
        add_log_entry("Finalising project in Supabase...")
        if project_id:
            try:
                supabase.table("projects").update({
                    "analysis_json": results,
                    "status": "completed",
                }).eq("id", project_id).execute()
                add_log_entry(f"Project '{project_name}' marked completed in Supabase")
            except Exception as e:
                add_log_entry(f"Supabase finalisation warning (non-fatal): {e}")

        progress_bar.progress(100)
        status_text.text("✓ Data extraction & saving complete!")

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
        error_msg = str(e)
        add_log_entry(f"Error: {error_msg}")
        if "Daily API quota exhausted" in error_msg or "PerDay" in error_msg or "429" in error_msg:
            st.error("⚠️ Google Gemini API quota exceeded (free tier: 20 requests/day). Please wait until tomorrow or upgrade your API plan.")
            st.info("Your PDF was processed but the AI extraction step was blocked by the quota limit.")
        else:
            st.error(f"❌ Error during extraction: {error_msg}")
            st.exception(e)


def refine_field(field_code: str, field_row: pd.Series, user_feedback: str, results_df: pd.DataFrame):
    """Handle field refinement using targeted AI re-analysis."""
    add_log_entry(f"Starting refinement for field {field_code}...")
    
    try:
        # Get current project and images
        if not st.session_state.current_project_id:
            st.error("No active project. Please extract data first.")
            return

        if not st.session_state.get("pdf_bytes_for_refine"):
            st.error("PDF data not available for re-analysis. Please re-upload the PDF.")
            return

        # Show processing message
        with st.spinner(f"🔄 Re-analyzing {field_code} with your feedback..."):
            add_log_entry("Initializing Gemini API for refinement...")
            extractor = GeminiDataExtractor(api_key=st.secrets.get("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

            # Render images on-demand for refinement (not stored between runs)
            add_log_entry("Rendering PDF pages for re-analysis...")
            refine_processor = PDFProcessor(
                dpi=st.session_state.get("pdf_dpi_for_refine", 200), fmt="png"
            )
            refine_images = refine_processor.convert_pdf_bytes(st.session_state.pdf_bytes_for_refine)

            add_log_entry(f"Sending refinement request with user feedback...")
            refined_field = extractor.refine_field_value(
                images=refine_images,
                field_code=field_code,
                original_value=str(field_row["Value"]),
                user_feedback=user_feedback,
                original_reasoning=field_row["AI Reasoning / Source"]
            )

            # Free rendered images immediately after the API call
            del refine_images
            gc.collect()

            add_log_entry(f"Refinement completed for {field_code}")

            # Update the results in session state
            if field_code in st.session_state.extraction_results:
                st.session_state.extraction_results[field_code].update(refined_field)

            # Persist updated analysis_json back to Supabase
            pid = st.session_state.current_project_id
            if pid:
                try:
                    supabase = get_supabase()
                    supabase.table("projects").update({
                        "analysis_json": st.session_state.extraction_results,
                    }).eq("id", pid).execute()
                    add_log_entry(f"Refined analysis saved to Supabase (project {pid})")
                except Exception as save_err:
                    add_log_entry(f"Supabase refinement save warning (non-fatal): {save_err}")

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



def _get_pdf_bytes() -> bytes | None:
    """
    Return PDF bytes from session state, falling back to Supabase storage if missing.
    Returns None if unavailable.
    """
    pdf_bytes = st.session_state.get("pdf_bytes_for_refine")
    if pdf_bytes:
        return pdf_bytes

    # Try to fetch from Supabase storage using the current project's filename
    user = st.session_state.get("user")
    project_id = st.session_state.get("current_project_id")
    if not user or not project_id:
        return None

    try:
        supabase = get_supabase()
        # Look up the filename from the project row
        resp = supabase.table("projects").select("filename").eq("id", project_id).single().execute()
        filename = resp.data.get("filename") if resp.data else None
        if not filename:
            return None

        storage_path = f"{user.id}/{filename}"
        pdf_bytes = supabase.storage.from_("pdfs").download(storage_path)
        # Cache for the rest of this session
        st.session_state.pdf_bytes_for_refine = pdf_bytes
        return pdf_bytes
    except Exception as e:
        print(f"PDF fetch from Supabase warning: {e}")
        return None


def display_categorized_dataframe(results_df: pd.DataFrame):
    """
    Split results_df by Category via a selectbox, then render a custom
    row-by-row grid with a native 🔍 Trace button on every row that has a
    bounding box. Clicking Trace opens show_trace_dialog (or the PDF
    re-upload fallback dialog if the PDF is unavailable).
    """
    if results_df.empty:
        st.info("No data to display.")
        return

    categories = sorted(results_df["Category"].dropna().unique().tolist())
    if not categories:
        categories = ["All"]

    show_cols = [c for c in [
        "Code", "Key Measure", "Value", "Unit",
        "Confidence Level", "Page Reference", "AI Reasoning / Source",
    ] if c in results_df.columns]

    selected_category = st.selectbox(
        "Select Category to View",
        options=categories,
        key="category_select",
    )

    cat_df = results_df[results_df["Category"] == selected_category][show_cols].reset_index(drop=True)
    if cat_df.empty:
        st.info(f"No fields extracted for **{selected_category}**.")
        return

    results_raw = st.session_state.extraction_results or {}
    dpi = st.session_state.get("pdf_dpi_for_refine", 200)

    # ── Column widths: Code | Measure | Value | Unit | Confidence | Page | Reasoning | Trace ──
    WIDTHS = [0.7, 1.8, 0.8, 0.6, 0.7, 0.6, 3.5, 0.9]

    # Header row
    hdr = st.columns(WIDTHS)
    labels = ["Code", "Key Measure", "Value", "Unit", "Confidence", "Page", "AI Reasoning / Source", "Trace"]
    for col, lbl in zip(hdr, labels):
        col.markdown(f"**{lbl}**")
    st.markdown("<hr style='margin:4px 0 8px 0; border-color:#e0e0e0;'>", unsafe_allow_html=True)

    # Data rows
    for _, row in cat_df.iterrows():
        cols = st.columns(WIDTHS)
        cols[0].write(row.get("Code", ""))
        cols[1].write(row.get("Key Measure", ""))
        cols[2].write(str(row.get("Value", "")))
        cols[3].write(str(row.get("Unit", "")))

        # Confidence with inline color
        conf_str = str(row.get("Confidence Level", ""))
        try:
            conf_num = int(conf_str.rstrip("%").strip())
            if conf_num == 100:
                color = "#155724"; bg = "#d4edda"
            elif conf_num >= 80:
                color = "#856404"; bg = "#fff3cd"
            else:
                color = "#721c24"; bg = "#f8d7da"
            cols[4].markdown(
                f'<span style="background:{bg};color:{color};padding:2px 6px;'
                f'border-radius:4px;font-weight:bold;font-size:0.85em;">{conf_str}</span>',
                unsafe_allow_html=True,
            )
        except Exception:
            cols[4].write(conf_str)

        cols[5].write(str(row.get("Page Reference", "")))

        reasoning = str(row.get("AI Reasoning / Source", ""))
        cols[6].caption(reasoning[:160] + ("…" if len(reasoning) > 160 else ""))

        field_code = row.get("Code", "")
        field_data_raw = results_raw.get(field_code, {})
        has_bbox = _is_valid_bbox(field_data_raw.get("bounding_box"))
        # Sanitize key: replace spaces and special chars
        safe_key = f"trace_{selected_category}_{field_code}".replace(" ", "_").replace("/", "_")

        if has_bbox:
            if cols[7].button("🔍 Trace", key=safe_key, use_container_width=True):
                pdf_bytes = _get_pdf_bytes()
                if pdf_bytes:
                    show_trace_dialog(field_code, field_data_raw, pdf_bytes, dpi)
                else:
                    show_pdf_required_dialog(field_code, field_data_raw, dpi)
        else:
            cols[7].markdown("<span style='color:#aaa;font-size:0.85em;'>no trace</span>", unsafe_allow_html=True)

    st.caption(f"{len(cat_df)} field{'s' if len(cat_df) != 1 else ''} in **{selected_category}**")


def display_results():
    """Display extraction results in organized format with enhanced UI."""

    st.subheader("📊 Extraction Results")

    # Prominent quota warning — persists across reruns via session state
    if st.session_state.get("quota_warning"):
        st.warning(
            "⚠️ **Extraction paused due to API quota limits. "
            "Showing partial results up to the last completed page.** "
            f"\n\n{st.session_state.quota_warning}"
        )

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

    # ── Smart DataGrid: tabs by category + confidence color-coding ──────────
    st.markdown("### 📋 All Extracted Data — by Category")
    display_categorized_dataframe(results_df)

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


# =============================================================================
# STRATEGIC PLAN — PHASE NEXT: HYBRID VECTOR-LLM EXTRACTION ENGINE
# =============================================================================
#
# PROBLEM STATEMENT
# -----------------
# Gemini is a raster-based VLM: it receives a pixel image and estimates
# coordinates by visual pattern recognition. This works well for counting
# discrete objects (windows, doors) but fails for:
#   • Continuous linear elements (wall runs, roof edges, footings) — Gemini
#     cannot reliably trace every segment, so it either guesses a giant box
#     or skips the bounding box entirely.
#   • Precise measurements — pixel-level interpretation of a scale bar has
#     inherent ±2–5% error vs. reading the actual CAD vector geometry.
#   • Text values in dense title blocks — OCR on raster is less reliable
#     than reading embedded PDF text streams directly.
#
# CORE INSIGHT
# ------------
# Architectural PDFs generated by CAD software (AutoCAD, Revit, ArchiCAD)
# are NOT scanned images — they ARE vector documents. PyMuPDF (fitz) can
# extract the *exact* geometric primitives: line segments, polylines, arcs,
# text blocks with their bounding boxes, and fill/stroke colors.
#
# By combining:
#   (A) Gemini's semantic spatial awareness — "that cluster of line segments
#       is the exterior wall of the master bedroom wing"
#   (B) PyMuPDF's exact vector geometry — the actual pixel/point coordinates
#       of every line segment on the page
# …we can achieve near-CAD-precision bounding boxes snapped to real drawing
# lines, while retaining Gemini's ability to classify what those lines mean.
#
# IMPLEMENTATION PLAN — THREE PHASES
# ------------------------------------
#
# PHASE A: Vector Geometry Extraction (PDFProcessor additions)
# ─────────────────────────────────────────────────────────────
# Add a new method  PDFProcessor.extract_vector_geometry(pdf_bytes, page_num)
# that returns a structured dict:
#   {
#     "lines": [{"x0","y0","x1","y1","width","color"}, ...],  # raw line segs
#     "paths": [{"points": [...], "closed": bool, ...}, ...], # polylines/rects
#     "text_blocks": [{"text","x0","y0","x1","y1","size","font"}, ...],
#   }
# All coordinates are in fitz's default pt space (1/72 inch) which maps
# cleanly to any DPI via scale = dpi / 72.
#
# Implementation notes:
#   page = doc[page_num - 1]
#   paths = page.get_drawings()          # returns every vector path
#   text  = page.get_text("dict")        # returns text spans with bboxes
# Both are O(1) — no image rendering, instant results.
#
# PHASE B: Semantic Cluster Prompt (GeminiDataExtractor additions)
# ────────────────────────────────────────────────────────────────
# After Gemini returns a bounding_box for a field, send a SECOND lightweight
# prompt (no image, text-only) containing the vector geometry near that box:
#   "Here are the exact line segments within ±10% of the bounding box you
#    identified for WE_TOTAL. Group these segments into the wall runs they
#    belong to and return a revised list of bounding boxes, one per wall run."
# The response is a refined bounding_box list snapped to real geometry.
# This second call is cheap (no image tokens) — ~50 text tokens per field.
#
# PHASE C: Snap-to-Vector Post-Processing (PDFProcessor)
# ───────────────────────────────────────────────────────
# Even without a second LLM call, we can improve precision deterministically:
# Given Gemini's coarse bounding_box [y1,x1,y2,x2] (in 0-1000 space):
#   1. Convert to pt coordinates using page.rect dimensions.
#   2. Expand by a search_radius (e.g. 5% of box size).
#   3. Query extracted_lines for all segments whose endpoints fall within
#      the expanded box.
#   4. Return the tight convex hull (or axis-aligned bbox) of those segments
#      as the refined bounding box — snapped to actual CAD lines.
# This runs in microseconds (pure NumPy/geometry, no API call).
#
# CONFIDENCE BOOST
# ─────────────────
# Fields where snap-to-vector succeeds → mark validation_status = "vector_verified"
# and boost confidence to 99%.  Fields where no nearby vectors are found
# retain the original Gemini box and confidence score unchanged.
#
# DATA FLOW (end-to-end)
# ──────────────────────
#   PDF bytes
#     │
#     ├─► PyMuPDF iter_pages()  ──► raster image + text → Gemini extraction
#     │                                                         │
#     └─► PyMuPDF extract_vector_geometry()  ──────────────────┘
#                                                    │
#                                           snap_bbox_to_vectors()
#                                                    │
#                                        refined bounding boxes (vector_verified)
#                                                    │
#                                         render_page_with_highlight()
#
# SUPABASE SCHEMA CHANGE (future)
# ────────────────────────────────
# Add a "vector_geometry" JSONB column to the projects table to cache
# extracted geometry per page, avoiding re-extraction on every trace view.
#
# ESTIMATED PRECISION IMPROVEMENT
# ─────────────────────────────────
# Current (raster-only):  ±2–5% of page dimension (~10–25 px at 200 DPI)
# Phase C snap-to-vector: ±0.1% of page dimension (~0.5 px at 200 DPI) — CAD grade
# =============================================================================
