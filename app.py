import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from spellchecker import SpellChecker
import time
import re
import io

# --- 1. WEB APP SETUP ---
st.set_page_config(page_title="BugHunter AI", page_icon="🕷️", layout="wide")
st.title("🕷️ BugHunter AI: Full-Stack Auditor")
st.markdown("Enter a website URL below to run a complete Quality Assurance, Security, and SEO audit.")

# --- 2. CORE AUDITOR LOGIC ---
def run_full_audit(base_url):
    domain = urlparse(base_url).netloc
    spell = SpellChecker()
    results = []

    def log_result(category, issue, detail=""):
        results.append({"Category": category, "Issue Found": issue, "Specific Detail": detail})

    try:
        # User Agents
        desktop_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
        mobile_headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'}

        # --- A. PERFORMANCE & MOBILE RESPONSIVENESS ---
        st.write("⚡ Testing Desktop & Mobile performance...")
        start_time = time.time()
        response = requests.get(base_url, headers=desktop_headers, timeout=15)
        desk_speed = round(time.time() - start_time, 2)
        log_result("Performance", "Desktop Load Time", f"{desk_speed} seconds")

        start_mobile = time.time()
        requests.get(base_url, headers=mobile_headers, timeout=15)
        mob_speed = round(time.time() - start_mobile, 2)
        log_result("Performance", "Mobile Load Time", f"{mob_speed} seconds")

        # --- B. CYBERSECURITY HEADERS ---
        st.write("🛡️ Scanning Security Headers...")
        headers = response.headers
        if 'Strict-Transport-Security' not in headers:
            log_result("Security", "Missing HSTS", "Site is not forcing secure HTTPS connections.")
        if 'X-Frame-Options' not in headers:
            log_result("Security", "Missing X-Frame-Options", "Vulnerable to Clickjacking attacks.")
        if 'X-Content-Type-Options' not in headers:
            log_result("Security", "Missing Content-Type-Options", "Vulnerable to MIME-sniffing.")

        soup = BeautifulSoup(response.text, 'html.parser')

        # --- C. SEO & ACCESSIBILITY ---
        st.write("🕵️‍♂️ Running SEO & Accessibility checks...")
        title_tag = soup.find('title')
        if not title_tag or not title_tag.text.strip():
            log_result("SEO", "Missing Title Tag", "Essential for Google ranking.")
        
        missing_alt = sum(1 for img in soup.find_all('img') if not img.get('alt') or not img.get('alt').strip())
        if missing_alt > 0:
            log_result("Accessibility", "Missing Image ALT Text", f"{missing_alt} images need descriptions.")

        # --- D. NLP SPELL CHECK ---
        st.write("✍️ Checking for typos (AI NLP)...")
        text_content = soup.get_text(separator=' ', strip=True)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text_content.lower())
        unique_words = set(words)
        misspelled = spell.unknown(unique_words)
        
        typo_count = 0
        for word in misspelled:
            correction = spell.correction(word)
            if correction and correction != word:
                log_result("Content Quality", "Typo Found", f"'{word}' -> Did you mean '{correction}'?")
                typo_count += 1
                if typo_count >= 5: # Cap at 5 for the web view
                    break

        # --- E. BROKEN LINKS (Light Check for speed) ---
        st.write("🔗 Checking internal links...")
        links = soup.find_all('a', limit=20) # Limit to 20 for fast web testing
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

        return pd.DataFrame(results)

    except Exception as e:
        st.error(f"Error connecting to website: {e}")
        return pd.DataFrame()

# --- 3. WEB INTERFACE CONTROLS ---
target_url = st.text_input("Target Website (e.g., https://example.com):", "https://example.com")

if st.button("Run Full Audit 🚀"):
    if not target_url.startswith("http"):
        st.warning("Please include 'https://' in the URL.")
    else:
        with st.spinner("Our AI is auditing the website. Please wait..."):
            df_results = run_full_audit(target_url)
            
            if not df_results.empty:
                st.success("✅ Audit Complete!")
                
                # Display the results as a beautiful web table
                st.dataframe(df_results, use_container_width=True)
                
                # Create an Excel file in memory for download
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False, sheet_name='Audit Report')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 Download Professional Excel Report",
                    data=excel_data,
                    file_name="BugHunter_Audit.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )