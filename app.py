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
st.set_page_config(page_title="BugHunter AI", page_icon="🕷️", layout="wide")
st.title("🕷️ BugHunter AI: Premium Website Auditor")
st.markdown("Run a complete Quality Assurance, SEO, and AI Content audit to identify critical bugs and capture leads.")

# --- 2. PDF GENERATION LOGIC ---
def create_pdf_report(results, base_url):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Premium QA & SEO Audit", ln=True, align="C")
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, f"Target Website: {base_url}", ln=True, align="C")
    pdf.ln(10)
    
    # Body
    for item in results:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f"[{item['Category']}] {item['Issue Found']}", ln=True)
        pdf.set_font("Arial", '', 11)
        
        # Prevent PDF from crashing on special characters
        safe_detail = str(item['Specific Detail']).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, f"Detail: {safe_detail}")
        pdf.ln(5)
        
    # Return as bytes for Streamlit download
    return bytes(pdf.output(dest='S'))

# --- 3. CORE AUDITOR LOGIC ---
def run_full_audit(base_url):
    domain = urlparse(base_url).netloc
    spell = SpellChecker()
    analyzer = SentimentIntensityAnalyzer()
    results = []

    def log_result(category, issue, detail=""):
        results.append({"Category": category, "Issue Found": issue, "Specific Detail": detail})

    try:
        desktop_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
        mobile_headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605.1.15'}

        # A. PERFORMANCE
        start_time = time.time()
        response = requests.get(base_url, headers=desktop_headers, timeout=15)
        desk_speed = round(time.time() - start_time, 2)
        log_result("Performance", "Desktop Load Time", f"{desk_speed} seconds")

        start_mobile = time.time()
        requests.get(base_url, headers=mobile_headers, timeout=15)
        mob_speed = round(time.time() - start_mobile, 2)
        log_result("Performance", "Mobile Load Time", f"{mob_speed} seconds")

        # B. CYBERSECURITY
        headers = response.headers
        if 'Strict-Transport-Security' not in headers:
            log_result("Security", "Missing HSTS", "Site is not forcing secure HTTPS connections.")
        if 'X-Frame-Options' not in headers:
            log_result("Security", "Missing X-Frame-Options", "Vulnerable to Clickjacking attacks.")

        soup = BeautifulSoup(response.text, 'html.parser')

        # C. SEO & ACCESSIBILITY
        title_tag = soup.find('title')
        if not title_tag or not title_tag.text.strip():
            log_result("SEO", "Missing Title Tag", "Essential for Google ranking.")
        
        missing_alt = sum(1 for img in soup.find_all('img') if not img.get('alt') or not img.get('alt').strip())
        if missing_alt > 0:
            log_result("Accessibility", "Missing Image ALT Text", f"{missing_alt} images need descriptions.")

        # D. AI SENTIMENT & SPELL CHECK
        text_content = soup.get_text(separator=' ', strip=True)
        
        sentiment_score = analyzer.polarity_scores(text_content)
        tone = "Neutral"
        if sentiment_score['compound'] >= 0.05: tone = "Positive/Welcoming"
        elif sentiment_score['compound'] <= -0.05: tone = "Negative/Aggressive"
        log_result("AI Intelligence", "Website Tone Analysis", f"The brand's tone is detected as: {tone} (Score: {sentiment_score['compound']})")

        words = re.findall(r'\b[a-zA-Z]{4,}\b', text_content.lower())
        unique_words = set(words)
        misspelled = spell.unknown(unique_words)
        typo_count = 0
        for word in misspelled:
            correction = spell.correction(word)
            if correction and correction != word:
                log_result("Content Quality", "Typo Found", f"'{word}' -> Did you mean '{correction}'?")
                typo_count += 1
                if typo_count >= 5: break

        # E. BROKEN LINKS
        links = soup.find_all('a', limit=20)
        for link in links:
            href = link.get('href')
            if href and href.startswith('/'):
                full_url = urljoin(base_url, href)
                try:
                    res = requests.head(full_url, headers=desktop_headers, timeout=3)
                    if res.status_code >= 400:
                        log_result("Technical", "Broken Link", f"{full_url} (Status {res.status_code})")
                except:
                    pass

        return results

    except Exception as e:
        st.error(f"Error connecting to website: {e}")
        return []

# --- 4. WEB INTERFACE & STATE MANAGEMENT ---
target_url = st.text_input("Enter Target Website (e.g., https://example.com):", "https://example.com")

if "audit_done" not in st.session_state:
    st.session_state.audit_done = False
if "results" not in st.session_state:
    st.session_state.results = []

if st.button("Run Full AI Audit 🚀"):
    if not target_url.startswith("http"):
        st.warning("Please include 'https://' in the URL.")
    else:
        with st.spinner("Our AI is scanning the website. Please wait..."):
            st.session_state.results = run_full_audit(target_url)
            if st.session_state.results:
                st.session_state.audit_done = True
                st.success(f"✅ Audit Complete! We found {len(st.session_state.results)} potential issues.")

# --- 5. LEAD CAPTURE FUNNEL & DATABASE ---
if st.session_state.audit_done:
    st.divider()
    st.subheader("📥 Unlock Your Free PDF Report")
    st.write("We've compiled the exact bugs, security flaws, and AI insights into a professional document.")
    
    client_email = st.text_input("Enter your email address to download the full report:")
    
    if client_email and "@" in client_email and "." in client_email:
        # Connect to Supabase Securely
        try:
            url: str = st.secrets["SUPABASE_URL"]
            key: str = st.secrets["SUPABASE_KEY"]
            supabase: Client = create_client(url, key)
            
            # Save the lead to the database
            lead_data = {
                "email": client_email,
                "website_url": target_url,
                "bug_count": len(st.session_state.results),
                "raw_report": st.session_state.results
            }
            supabase.table("leads").insert(lead_data).execute()
            
            st.success("Email verified and report secured! You can now download your document.")
            
        except Exception as e:
            st.error("There was a small issue saving your data, but you can still download your report!")
            # Print to terminal for debugging, user won't see this on the web
            print(f"Database error: {e}") 

        # Generate and provide the PDF Download
        pdf_bytes = create_pdf_report(st.session_state.results, target_url)
        st.download_button(
            label="📄 Download Professional PDF Report",
            data=pdf_bytes,
            file_name="Premium_Website_Audit.pdf",
            mime="application/pdf"
        )