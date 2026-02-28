import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from spellchecker import SpellChecker
from fpdf import FPDF
from supabase import create_client, Client
import time
import re

# --- 1. ENTERPRISE UI & CUSTOM CSS ---
st.set_page_config(page_title="BugHunter QA | Enterprise", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    /* Clean, Corporate Background */
    .stApp { background-color: #f4f6f9; font-family: 'Inter', sans-serif; }
    
    /* Premium Headers */
    h1 { color: #0f172a; font-weight: 800; letter-spacing: -1px; }
    h2, h3 { color: #1e293b; font-weight: 600; }
    
    /* Button Styling */
    .stButton>button { 
        background-color: #2563eb; 
        color: white; 
        border-radius: 8px; 
        height: 3.2em; 
        font-weight: 600; 
        transition: all 0.3s;
        border: none;
    }
    .stButton>button:hover { background-color: #1d4ed8; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); }
    
    /* Metric Cards */
    div[data-testid="metric-container"] {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Divider */
    hr { border-color: #cbd5e1; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE PDF ENGINE (BUSINESS IMPACT FOCUSED) ---
def create_pdf_report(results, base_url):
    pdf = FPDF()
    pdf.add_page()
    
    # Premium Header
    pdf.set_fill_color(15, 23, 42) # Slate 900
    pdf.rect(0, 0, 210, 45, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 22)
    pdf.cell(0, 20, "DIGITAL INFRASTRUCTURE AUDIT", ln=True, align="C")
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Target Asset: {base_url}", ln=True, align="C")
    
    # Executive Summary
    pdf.set_y(55)
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, "1. Executive Summary & Revenue Risk", ln=True)
    pdf.set_font("Arial", '', 11)
    
    total_issues = len(results)
    summary = (f"This automated Quality Assurance scan identified {total_issues} technical bottlenecks. "
                "These issues actively degrade user experience, penalize search engine rankings, "
                "and increase customer bounce rates. Below is a strategic breakdown of the technical faults "
                "and their direct impact on business operations.")
    pdf.multi_cell(0, 7, summary)
    pdf.ln(8)

    # Detailed Findings
    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, "2. Critical Findings & Business Impact", ln=True)
    pdf.ln(3)

    for item in results:
        # Category Badge
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(241, 245, 249) # Slate 100
        pdf.cell(0, 8, f" {item['Category'].upper()} PROTOCOL", ln=True, fill=True)
        
        # Issue Found
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 7, f"Diagnostic: {item['Issue Found']}", ln=True)
        
        # Business Impact (Red)
        pdf.set_text_color(220, 38, 38) # Red 600
        pdf.set_font("Arial", 'B', 10)
        safe_impact = str(item['Impact']).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, f"Business Impact: {safe_impact}")
        
        # Detail (Grey)
        pdf.set_text_color(100, 113, 128) # Slate 500
        pdf.set_font("Arial", '', 10)
        safe_detail = str(item['Specific Detail']).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, f"Technical Detail: {safe_detail}")
        pdf.ln(6)

    return pdf.output(dest='S').encode('latin-1')

# --- 3. QA AUDITOR LOGIC ---
def run_full_audit(base_url):
    spell = SpellChecker()
    results = []

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        start = time.time()
        response = requests.get(base_url, headers=headers, timeout=15)
        speed = round(time.time() - start, 2)
        
        # 1. Performance
        if speed > 2.5:
            results.append({
                "Category": "Performance", 
                "Issue Found": "Critical Load Time Degradation", 
                "Specific Detail": f"Server response time clocked at {speed}s.",
                "Impact": "A delay of over 2.5 seconds results in up to a 38% increase in bounce rate, directly costing you leads and revenue."
            })

        # 2. Security
        h = response.headers
        if 'X-Frame-Options' not in h:
            results.append({
                "Category": "Security", 
                "Issue Found": "Missing Anti-Clickjacking Headers", 
                "Specific Detail": "X-Frame-Options protocol is absent.",
                "Impact": "Your domain can be framed by malicious actors to steal user credentials, exposing you to severe liability and loss of brand trust."
            })

        # 3. SEO & DOM Analysis
        soup = BeautifulSoup(response.text, 'html.parser')
        imgs = soup.find_all('img')
        missing_alt = sum(1 for i in imgs if not i.get('alt'))
        if missing_alt > 0:
            results.append({
                "Category": "SEO & Accessibility", 
                "Issue Found": "Missing DOM Metadata (ALT Tags)", 
                "Specific Detail": f"{missing_alt} graphical assets lack descriptive text.",
                "Impact": "Search engines blindly index these assets, penalizing your domain's organic reach and reducing overall visibility against competitors."
            })

        # 4. Content Integrity (With Ugandan/Tech Whitelist)
        text = soup.get_text(separator=' ', strip=True)
        words = re.findall(r'\b[a-z]{5,}\b', text.lower())
        misspelled = spell.unknown(words)
        
        whitelist = {"wifi", "gdpr", "kasese", "kemrose", "uganda", "kampala", "https", "admin"}
        count = 0
        for word in misspelled:
            if count >= 3: break
            corr = spell.correction(word)
            if corr and corr != word and word not in whitelist:
                results.append({
                    "Category": "Content Quality", 
                    "Issue Found": f"Orthographical Error: '{word}'", 
                    "Specific Detail": f"Suggested algorithmic correction: '{corr}'",
                    "Impact": "Typographical errors subconsciously erode consumer trust and perceived brand professionalism, leading to lower conversion rates."
                })
                count += 1

        return results
    except Exception as e:
        st.error(f"Diagnostic Failure: {e}")
        return []

# --- 4. THE FRONTEND UI ---
# Hero Section
st.markdown("<h1 style='text-align: center;'>BugHunter AI Intelligence</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.2rem; margin-bottom: 2rem;'>Enterprise-grade website auditing, performance diagnostics, and SEO risk analysis.</p>", unsafe_allow_html=True)

# Main Input Form
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    target_url = st.text_input("Target URL", placeholder="https://www.example.com", label_visibility="collapsed")
    analyze_btn = st.button("Initialize Diagnostic Scan 🚀", use_container_width=True)

if "results" not in st.session_state:
    st.session_state.results = None

if analyze_btn:
    if not target_url.startswith("http"):
        st.warning("Protocol required. Please prepend URL with 'https://'")
    else:
        # Professional Progress Simulation
        with st.status("Running diagnostics...", expanded=True) as status:
            st.write("Establishing secure connection to domain...")
            time.sleep(1)
            st.write("Parsing HTML/DOM structure...")
            st.session_state.results = run_full_audit(target_url)
            status.update(label="Analysis Complete", state="complete", expanded=False)

# Results Dashboard
if st.session_state.results is not None:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### Executive Dashboard Overview")
    
    # Dashboard Metrics
    m1, m2, m3 = st.columns(3)
    issue_count = len(st.session_state.results)
    perf_issues = sum(1 for r in st.session_state.results if r['Category'] == 'Performance')
    sec_issues = sum(1 for r in st.session_state.results if r['Category'] == 'Security')
    
    m1.metric(label="Total Bottlenecks", value=issue_count, delta="-Needs Attention" if issue_count > 0 else "Perfect", delta_color="inverse")
    m2.metric(label="Performance Degradations", value=perf_issues)
    m3.metric(label="Security Vulnerabilities", value=sec_issues)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Dual-Column Layout for Data and Lead Capture
    data_col, lead_col = st.columns([1.5, 1])
    
    with data_col:
        st.markdown("#### High-Level Diagnostics")
        if issue_count == 0:
            st.success("Your digital infrastructure is highly optimized.")
        else:
            for idx, item in enumerate(st.session_state.results):
                with st.expander(f"⚠️ {item['Category']}: {item['Issue Found']}"):
                    st.write(f"**Detail:** {item['Specific Detail']}")
                    st.markdown(f"***Impact Hypothesis:*** *{item['Impact']}*")

    with lead_col:
        st.markdown("#### Export Executive Brief")
        st.info("Download the full, formatted PDF report outlining the complete technical breakdown and strategic recommendations.")
        
        client_email = st.text_input("Corporate Email Address:")
        
        if client_email and "@" in client_email and "." in client_email:
            try:
                # Background Lead Capture
                sb_url = st.secrets["SUPABASE_URL"]
                sb_key = st.secrets["SUPABASE_KEY"]
                supabase: Client = create_client(sb_url, sb_key)
                supabase.table("leads").insert({"email": client_email, "website_url": target_url, "raw_report": st.session_state.results}).execute()
            except Exception as e:
                pass # Fails silently so user isn't interrupted
                
            # Generate Document
            pdf_bytes = create_pdf_report(st.session_state.results, target_url)
            st.download_button(
                label="📥 Secure Download (PDF)",
                data=pdf_bytes,
                file_name=f"Audit_{urlparse(target_url).netloc}.pdf",
                mime="application/pdf",
                use_container_width=True
            )