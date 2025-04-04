import logging
import os
import time
import urllib.parse
from itertools import cycle
from pathlib import PurePosixPath

import requests
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
import pytz

# Import the RAGClient from your Pathway package for slide search
from pathway.xpacks.llm.question_answering import RAGClient

load_dotenv()

# ===================== Backend API CONFIGURATION =====================
API_HOST = os.environ.get("API_HOST", "localhost")
API_PORT = os.environ.get("API_PORT", 8000)
UPLOAD_ENDPOINT = f"http://{API_HOST}:{API_PORT}/upload"
PATIENT_DATA_ENDPOINT = f"http://{API_HOST}:{API_PORT}/patient"    # Endpoint to fetch patient data
QUERY_ENDPOINT = f"http://{API_HOST}:{API_PORT}/query"
DOC_LIST_ENDPOINT = f"http://{API_HOST}:{API_PORT}/documents"
DELETE_DOC_ENDPOINT = f"http://{API_HOST}:{API_PORT}/delete"
UPDATES_ENDPOINT = f"http://{API_HOST}:{API_PORT}/updates"           # Endpoint for guideline updates

# ===================== PATHWAY SLIDE SEARCH CONFIGURATION =====================
PATHWAY_HOST = os.environ.get("PATHWAY_HOST", "app")
PATHWAY_PORT = os.environ.get("PATHWAY_PORT", 8000)
conn = RAGClient(url=f"http://{PATHWAY_HOST}:{PATHWAY_PORT}")

file_server_base_url = os.environ.get("FILE_SERVER_URL", "http://localhost:8080/")
file_server_image_base_url = f"{file_server_base_url}images"
file_server_pdf_base_url = f"{file_server_base_url}documents"
internal_file_server_pdf_base_url = "http://nginx:8080/"

# ===================== UTILITY FUNCTIONS FOR SLIDE SEARCH =====================
def get_options_list(metadata_list: list[dict], opt_key: str) -> list:
    """Get all available options in a specific metadata key."""
    options = set(map(lambda x: x[opt_key], metadata_list))
    return list(options)

def parse_slide_id_components(slide_id: str) -> tuple[str, int, int]:
    stem = PurePosixPath(slide_id).stem
    (name_page, _, page_count) = stem.rpartition("_")
    (name, _, page) = name_page.rpartition("_")
    return (name, int(page), int(page_count))

def create_slide_url(name: str, page: int, page_count: int) -> str:
    return f"{file_server_image_base_url}/{name}_{page}_{page_count}.png"

def get_image_serve_url(metadata: dict) -> str:
    name, page, page_count = parse_slide_id_components(metadata["slide_id"])
    return create_slide_url(name, page, page_count)

def get_adjacent_image_urls(metadata: dict) -> list[str]:
    name, page, page_count = parse_slide_id_components(metadata["slide_id"])
    ret_images = []
    for p in range(page - 2, page + 3):
        if p < 0 or p >= page_count:
            continue
        ret_images.append(create_slide_url(name, p, page_count))
    return ret_images

def get_slide_link(file_name, page_num=None) -> str:
    filename_encoded = urllib.parse.quote(file_name)
    image_url = f"{file_server_pdf_base_url}/{filename_encoded}"
    if page_num is not None:
        image_url += f"#page={page_num}"
    return image_url

def get_all_index_files() -> list[str]:
    response = requests.get(internal_file_server_pdf_base_url + "/")
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        file_links = [a["href"] for a in soup.find_all("a", href=True)]
        file_links = [link for link in file_links if not link.endswith("/")]
    else:
        file_links = []
    return file_links

def get_ext_img_with_href(url, target_url, *args) -> str:
    width: int = 600
    margin = 20
    def get_img_html(dc):
        return f"""
        <div class="slider-item">
            <img src="{dc['url']}" width="90" />
        </div>"""
    slider_images = "\n".join([get_img_html(dc) for dc in args])
    html_code = f"""
        <a href="{target_url}">
            <img style="display: block; margin: {margin}px auto {margin}px auto" loading="lazy" src="{url}" width="{width}" />
        </a>
        <div class="slider-container">
            <div class="slider-wrapper">
                {slider_images}
            </div>
        </div>
    """
    return html_code

def log_rate_answer(event, idx, kwargs):
    logging.info({"_type": "rate_event", "rating": event, "rank": idx, **kwargs})

# ===================== STREAMLIT PAGE CONFIGURATION =====================
st.set_page_config(
    page_title="DocAssist Medical Portal",
    page_icon="🏥",
    layout="wide"
)

# ===================== CUSTOM CSS =====================
st.markdown("""
    <style>
        .vital-card {
            background: #1a1a1a;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #2A5C80;
        }
        .trend-up { color: #ff6b6b; }
        .trend-down { color: #8aff8a; }
        .medication-pill {
            display: inline-block;
            padding: 6px 12px;
            background: #2A5C80;
            border-radius: 20px;
            margin: 5px;
            font-size: 0.9em;
        }
        .imaging-card {
            background: #222;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            border: 1px solid #2A5C80;
        }
        .full-width { width: 100%; text-align: center; }
        .response-box { padding: 15px; border-radius: 8px; }
        .loading-animation {
            font-size: 20px;
            font-weight: bold;
            color: #16A085;
            text-align: center;
        }
        :root {
            --primary: #2A5C80;
            --secondary: #16A085;
            --accent: #E74C3C;
        }
        .diagnostic-section {
            background: white;
            border-radius: 10px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        }
        .timeline {
            border-left: 3px solid var(--primary);
            padding-left: 2rem;
            margin: 2rem 0;
        }
        .timeline-event {
            position: relative;
            padding: 1rem;
            margin: 1rem 0;
            background: var(--background);
            border-radius: 8px;
        }
        .timeline-event::before {
            content: '';
            position: absolute;
            left: -2.35rem;
            top: 1.2rem;
            width: 12px;
            height: 12px;
            background: var(--secondary);
            border-radius: 50%;
        }
        .metric-gauge {
            width: 100%;
            height: 120px;
            position: relative;
            margin: 1rem 0;
        }
        .interaction-card {
            transition: transform 0.2s;
            cursor: pointer;
        }
        .interaction-card:hover {
            transform: translateY(-3px);
        }
        /* CSS for slide image slider */
        .slider-container {
            margin-top: 20px;
        }
        .slider-item {
            float: left;
            margin: 10px;
            width: 120px;
            border: 1px solid #ccc;
            border-radius: 5px;
            cursor: pointer;
        }
        .slider-item img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 5px;
        }
        .slider-wrapper {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
        }
    </style>
""", unsafe_allow_html=True)

# ===================== HEADER SECTION =====================
st.image("path/to/logo.png", width=80)  # Replace with your logo path or URL
st.markdown(f"""
    <h1 style='border-bottom: 2px solid #2e86de; padding-bottom: 1rem;'>
        DocAssist Clinical Aid <span style='font-size: 1rem; color: #666;'>v1.0</span>
    </h1>
    <div style='display: flex; gap: 2rem; margin: 1rem 0;'>
        <div>🔴 Live Medical Intelligence</div>
        <div>⏱ Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
""", unsafe_allow_html=True)

# ===================== MAIN TABS =====================
tabs = st.tabs(["👨⚕ Patient Management", "🔍 Query Assistant", "📚 Update center"])

# --------------------- TAB: Update Center ---------------------
with tabs[2]:
    st.subheader("Knowledge Management Hub")
    
    # Guideline Updates from backend
    with st.expander("🚨 Live Guideline Updates", expanded=True):
        try:
            response = requests.get(UPDATES_ENDPOINT)
            if response.status_code == 200:
                updates = response.json().get("updates", [])
                cols = st.columns(3)
                for i, update in enumerate(updates):
                    cols[i % 3].markdown(f"""
                        <div class="vital-card">
                            <strong>{update.get('source', 'Unknown')}</strong><br>
                            {update.get('message', '')}<br>
                            <small>{update.get('date', '')}</small>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("Error fetching guideline updates.")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    # Document Statistics (from backend)
    try:
        stats_response = requests.get(DOC_LIST_ENDPOINT)
        if stats_response.status_code == 200:
            docs_data = stats_response.json()
            documents = docs_data.get("documents", [])
            total_docs = len(documents)
            processing_time = docs_data.get("avg_processing_time", "N/A")
            data_freshness = docs_data.get("data_freshness", "N/A")
        else:
            total_docs, processing_time, data_freshness = "N/A", "N/A", "N/A"
    except Exception as e:
        total_docs, processing_time, data_freshness = "N/A", "N/A", "N/A"
    
    st.markdown("### Knowledge Base Analytics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Documents", total_docs)
    col2.metric("Avg. Processing Time", processing_time)
    col3.metric("Data Freshness", data_freshness)
    
    # Document List with deletion option
    if st.button("🔄 Refresh Document List"):
        try:
            response = requests.get(DOC_LIST_ENDPOINT)
            docs = response.json().get("documents", [])
            for doc in docs:
                with st.container():
                    status_class = "indexed" if doc.get('indexed') else "processing"
                    status_text = "INDEXED" if doc.get('indexed') else "PROCESSING"
                    st.markdown(f"""
                        <div class="document-item">
                            <div class="status-badge {status_class}">● {status_text}</div>
                            <strong>📄 {doc.get('filename')}</strong><br>
                            <small>Uploaded: {doc.get('timestamp')} | Pages: {doc.get('pages')}</small>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(
                        f"🗑", 
                        key=f"delete_{doc.get('filename')}",
                        help=f"Delete {doc.get('filename')}"
                    ):
                        del_response = requests.post(DELETE_DOC_ENDPOINT, json={"filename": doc.get("filename")})
                        if del_response.status_code == 200:
                            st.success(f"Deleted {doc.get('filename')}")
                            time.sleep(0.5)
                            st.experimental_rerun()
                        else:
                            st.error(f"Error deleting {doc.get('filename')}")
        except Exception as e:
            st.error(f"Error fetching document list: {str(e)}")

# --------------------- TAB: Query Assistant ---------------------
with tabs[1]:
    st.subheader("📚 Medical Document Support")
    question = st.text_input("🔍 Enter your medical query:", placeholder="Search medical books, diseases, or treatment guidelines...")
    
    # Sidebar for additional filtering using the slide metadata from Pathway
    st.sidebar.info("This demo uses Pathway slide search. Use the filters below.")
    # Retrieve document metadata list from the RAG client
    try:
        document_meta_list = conn.list_documents(keys=[])
        st.session_state["document_meta_list"] = document_meta_list
    except Exception as e:
        st.error(f"Error retrieving document metadata: {str(e)}")
        st.session_state["document_meta_list"] = []
    
    available_categories = get_options_list(st.session_state["document_meta_list"], "category")
    st.session_state["available_categories"] = available_categories
    available_languages = get_options_list(st.session_state["document_meta_list"], "language")
    st.session_state["available_languages"] = available_languages
    available_files = get_options_list(st.session_state["document_meta_list"], "path")
    
    cols = cycle(st.columns(2))
    with next(cols):
        cat_options = st.multiselect(
            "Filtered Categories",
            available_categories or [],
            [],
            key="cat_selection",
            label_visibility="hidden",
            placeholder="Filtered Categories",
        )
    with next(cols):
        language_options = st.multiselect(
            "Languages",
            available_languages or [],
            [],
            key="lang_selection",
            label_visibility="hidden",
            placeholder="Filtered Languages",
        )
    selected_categories = available_categories if len(cat_options) == 0 else cat_options
    selected_languages = available_languages if len(language_options) == 0 else language_options
    st.session_state.category_filter = selected_categories
    st.session_state.language_filter = selected_languages

    def get_category_filter(category: str) -> str:
        return f"contains(`{category}`, category)"
    def get_language_filter(lang: str) -> str:
        return f"contains(`{lang}`, language)"
    def combine_filters(*args: str | None) -> str:
        return " && ".join([arg for arg in args if arg is not None])
    
    if question:
        filter_ls = [get_category_filter(selected_categories), get_language_filter(selected_languages)]
        combined_query_filter = combine_filters(*filter_ls)
        st.markdown(f"**Searched for:** {question}")
        try:
            response = conn.answer(question, filters=combined_query_filter)
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            response = None
        
        if response:
            text_responses = [r["text"] for r in response]
            image_metadatas = [r["metadata"] for r in response]
            for idx, cur_metadata in enumerate(image_metadatas):
                file_name = cur_metadata["path"].split("/")[-1]
                select_page = cur_metadata["image_page"] + 1
                adjacent_urls = get_adjacent_image_urls(cur_metadata)
                args_list = [{"url": i} for i in adjacent_urls]
                image_html = get_ext_img_with_href(
                    get_image_serve_url(cur_metadata),
                    get_slide_link(file_name, select_page),
                    *args_list,
                )
                image_url = get_slide_link(file_name, select_page)
                slide_id = cur_metadata["slide_id"]
                st.markdown(f"Page `{select_page}` of [`{file_name}`]({image_url})")
                st.markdown(image_html, unsafe_allow_html=True)
                # Optionally log rating events if needed:
                log_rate_answer("display", idx, {
                    "slide_id": slide_id,
                    "filter": combined_query_filter,
                    "query": question,
                    "file_name": file_name,
                    "selected_cat": selected_categories,
                    "selected_lang": selected_languages,
                })
        else:
            st.markdown(f"""No results were found for search query: `{question}`
            and filter criteria: `{combined_query_filter}`""")
            
# --------------------- TAB: Patient Management ---------------------
with tabs[0]:
    st.markdown("### Enter New Patient Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        file_medical_history = st.file_uploader("Upload Medical History File", type=["pdf", "txt", "docx"])
    with col2:
        file_medicines = st.file_uploader("Upload Current Medicines File", type=["pdf", "txt", "docx"])
    with col3:
        file_reports = st.file_uploader("Upload Lab Scan Report", type=["png", "jpg", "jpeg"])

    if st.button("Submit Patient Data"):
        with st.spinner("Processing patient data..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            time.sleep(1)
            status_text.markdown("<div class='loading-animation'>📚 Fetching backend patient data...</div>", unsafe_allow_html=True)
            progress_bar.progress(20)
            time.sleep(2)
            status_text.markdown("<div class='loading-animation'>🧠 Analyzing patient records...</div>", unsafe_allow_html=True)
            progress_bar.progress(50)
            time.sleep(2)
            status_text.markdown("<div class='loading-animation'>🔎 Integrating lab and imaging results...</div>", unsafe_allow_html=True)
            progress_bar.progress(75)
            time.sleep(2)
            status_text.markdown("<div class='loading-animation'>📑 Finalizing patient dashboard...</div>", unsafe_allow_html=True)
            progress_bar.progress(100)
            time.sleep(2)
            progress_bar.empty()
            status_text.empty()

        try:
            response = requests.get(PATIENT_DATA_ENDPOINT)
            if response.status_code == 200:
                patient = response.json()
            else:
                st.error("Failed to fetch patient data.")
                patient = {}
        except Exception as e:
            st.error(f"Error fetching patient data: {str(e)}")
            patient = {}

        labs = patient.get("labs", {})
        imaging = patient.get("imaging", {})
        diagnostic_report = patient.get("diagnostic_report", "No diagnostic report available.")
        treatment_plan = patient.get("treatment_plan", "No treatment plan available.")
        conflicts = patient.get("conflicts", {})

        st.success("Additional patient information processed successfully!")
        st.subheader(f"Patient Dashboard: {patient.get('name', 'Unknown Patient')}")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"""
                <div class="vital-card">
                    <strong>🩺 AI-Generated Diagnostic Report</strong><br>
                    {diagnostic_report}
                </div>
            """, unsafe_allow_html=True)
        with col2:
            if conflicts:
                st.markdown("<div class='vital-card'><strong>⚠ Conflicting Medications</strong><br>", unsafe_allow_html=True)
                for med, reason in conflicts.items():
                    st.markdown(f"✔ <strong>{med}</strong>: {reason}<br>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='vital-card'><strong>✅ No Medication Conflicts Found</strong></div>", unsafe_allow_html=True)
                st.divider()
        
        st.markdown("## Patient Overview")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
                <div class="vital-card">
                    <strong>📌 Basic Info</strong><br>
                    ID: {patient.get('id', 'N/A')}<br>
                    Age: {patient.get('age', 'N/A')} • Gender: {patient.get('gender', 'N/A')}<br>
                    Condition: {patient.get('condition', 'N/A')}
                </div>
            """, unsafe_allow_html=True)
        with col2:
            medications = patient.get('medications', [])
            st.markdown(f"""
                <div class="vital-card">
                    <strong>💊 Current Medications</strong><br>
                    {' '.join([f'<span class="medication-pill">{med}</span>' for med in medications])}
                </div>
            """, unsafe_allow_html=True)
        st.markdown("### Clinical Metrics")
        cols = st.columns(4)
        vitals = patient.get("vitals", {"bp": "N/A", "hr": "N/A", "temp": "N/A", "spo2": "N/A"})
        vitals_info = [
            ("🩺 BP", vitals.get("bp", "N/A"), "120/80", "↑"),
            ("💓 HR", vitals.get("hr", "N/A"), "60-100", "↓"),
            ("🌡 Temp", vitals.get("temp", "N/A"), "36.5-37.5", "→"),
            ("🫁 SpO2", vitals.get("spo2", "N/A"), ">95%", "→")
        ]
        for i, (icon, value, normal, trend) in enumerate(vitals_info):
            cols[i].markdown(f"""
                <div class="vital-card">
                    {icon} {value}<br>
                    <small>Normal: {normal}</small><br>
                    <span class="trend-{'up' if '↑' in trend else 'down'}">{trend}</span>
                </div>
            """, unsafe_allow_html=True)
        st.markdown("### Diagnostic Results")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
                <div class="imaging-card">
                    <strong>🔬 Lab Results</strong><br>
                    Glucose: {labs.get('glucose', 'N/A')} mg/dL<br>
                    A1C: {labs.get('a1c', 'N/A')}%<br>
                    Creatinine: {labs.get('creatinine', 'N/A')} mg/dL<br>
                    LDL: {labs.get('ldl', 'N/A')} mg/dL
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="imaging-card">
                    <strong>🩻 Imaging Report</strong><br>
                    {imaging.get('type', 'N/A')} ({imaging.get('date', 'N/A')})<br>
                    Findings: {imaging.get('finding', 'N/A')}<br>
                    Impression: {imaging.get('impression', 'N/A')}
                </div>
            """, unsafe_allow_html=True)

# ===================== FOOTER =====================
st.divider()
st.markdown("""
    <footer>
        ⚠ Clinical Decision Support System v2.2 • Data updated every 5 minutes • For demonstration purposes only
    </footer>
""", unsafe_allow_html=True)
