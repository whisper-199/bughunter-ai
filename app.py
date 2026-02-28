import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from spellchecker import SpellChecker
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from fpdf import FPDF
from supabase import create_client, Client
import time
import re

# --- 1. WEB APP SETUP ---
st.set_page_config(page_title="BugHunter AI Pro", page_icon="🛡️", layout="wide")

# Custom CSS for a professional look
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ BugHunter AI: Enterprise Website Auditor")
st.markdown("Generate professional-grade QA reports for businesses in seconds.")

# --- 2. PROFESSIONAL PDF ENGINE ---
def create_pdf_report(results, base_url):
    pdf = FPDF()
    pdf.add_page()
    
    # Header Branding
    pdf.set_fill_color(0, 51, 102) # Dark Navy Blue
    pdf.rect(0, 0, 210, 45, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 24)
    pdf.cell(0, 25, "AUDIT REPORT", ln=True, align="C")
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 5, f"Domain: {base_url}", ln=True, align="C")
    
    # Executive Summary Section
    pdf.set_y(55)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "1. Executive Summary", ln=True)
    pdf.set_font("Arial", '', 11)
    
    total_issues = len(results)
    severity = "HIGH" if any(r['Category'] in ['Security', 'Technical'] for r in results) else "MODERATE"
    
    summary = (f"This automated audit identified {total_issues} issues. "
                f"The overall technical risk is rated as {severity}. "
                "Fixing these items will improve SEO ranking and user trust.")
    pdf.multi_cell(0, 7, summary)
    pdf.ln(5)

    # Detailed Results
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "2. Detailed Findings", ln=True)
    pdf.ln(2)

    for item in results:
        # Category Bar
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 8, f" CATEGORY: {item['Category'].upper()}", ln=True, fill=True)
        
        # Issue and Detail
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 7, f"Issue: {item['Issue Found']}", ln=True)
        pdf.set_font("Arial", '', 10)
        
        # Safe encoding for African names/technical terms
        detail_text = str(item['Specific Detail']).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, f"Details: {detail_text}")
        pdf.ln(4)

    return pdf.output(dest='S').encode('latin-1')

# --- 3. AUDITOR LOGIC ---
def run_full_audit(base_url):
    spell = SpellChecker()
    analyzer = SentimentIntensityAnalyzer()
    results = []

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
        start = time.time()
        response = requests.get(base_url, headers=headers, timeout=15)
        speed = round(time.time() - start, 2)
        results.append({"Category": "Performance", "Issue Found": "Page Load Speed", "Specific Detail": f"{speed} seconds"})

        # Security Headers
        h = response.headers
        if 'X-Frame-Options' not in h:
            results.append({"Category": "Security", "Issue Found": "Missing X-Frame-Options", "Specific Detail": "Vulnerable to Clickjacking."})

        soup = BeautifulSoup(response.text, 'html.parser')

        # SEO & Images
        imgs = soup.find_all('img')
        missing_alt = sum(1 for i in imgs if not i.get('alt'))
        if missing_alt > 0:
            results.append({"Category": "Accessibility", "Issue Found": "Missing Alt Text", "Specific Detail": f"{missing_alt} images lack descriptions."})

        # IMPROVED NLP SPELL CHECK
        # We only check words that are likely to be real English errors
        text = soup.get_text(separator=' ', strip=True)
        words = re.findall(r'\b[a-z]{5,}\b', text.lower()) # Only check words 5+ letters to avoid names/codes
        
        misspelled = spell.unknown(words)
        for word in list(misspelled)[:10]: # Limit to top 10 to keep report clean
            corr = spell.correction(word)
            # Only log if the correction is significantly different and not a common false positive
            if corr and corr != word and word not in ["wifi", "gdpr", "kasese", "kemrose"]:
                results.append({"Category": "Content", "Issue Found": f"Possible Typo: {word}", "Specific Detail": f"Suggest: {corr}"})

        return results
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return []

# --- 4. INTERFACE ---
url_input = st.text_input("Enter Website URL:", "https://")

if "results" not in st.session_state:
    st.session_state.results = None

if st.button("Start Enterprise Audit"):
    with st.spinner("Analyzing site architecture..."):
        st.session_state.results = run_full_audit(url_input)
        if st.session_state.results:
            st.success(f"Audit Complete! {len(st.session_state.results)} issues detected.")

if st.session_state.results:
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Results Preview")
        st.table(pd.DataFrame(st.session_state.results).head(5))
        
    with col2:
        st.subheader("Export Report")
        email = st.text_input("Business Email to Unlock PDF:")
        if email and "@" in email:
            # Supabase Integration
            try:
                sb_url = st.secrets["SUPABASE_URL"]
                sb_key = st.secrets["SUPABASE_KEY"]
                supabase = create_client(sb_url, sb_key)
                supabase.table("leads").insert({"email": email, "website_url": url_input}).execute()
            except:
                pass # Silently fail if DB is busy, allow download

            pdf_data = create_pdf_report(st.session_state.results, url_input)
            st.download_button("📥 Download PDF Report", pdf_data, "Website_Audit.pdf", "application/pdf")