import streamlit as st
import re
import spacy
from pypdf import PdfReader
from docx import Document
from duckduckgo_search import DDGS   # ← Changed from ddgs
import time
from typing import List, Dict
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import sys

# Load spaCy model (improved for cloud)
@st.cache_resource
def load_nlp():
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        st.warning("Downloading spaCy model... (only first time)")
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
        return spacy.load("en_core_web_sm")

nlp = load_nlp()


# ========================== 1. CLEAN TEXT ==========================
def clean_text(text: str) -> str:
    text = re.sub(r'-\n', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()


def load_document(uploaded_file) -> str:
    if not uploaded_file:
        return ""
    text = ""
    if uploaded_file.name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    elif uploaded_file.name.endswith(".docx"):
        doc = Document(uploaded_file)
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n"
    return clean_text(text)


# ========================== 2. CLAIM EXTRACTION (spaCy NER) ==========================
def extract_claims(text: str) -> List[str]:
    if not text:
        return []

    doc = nlp(text)
    claims = []

    for sent in doc.sents:
        s = sent.text.strip()

        # Basic filters
        if len(s) < 15 or len(s) > 800:
            continue
        if s.isupper():
            continue
        if s.startswith(("Page", "Chapter", "Figure", "Table", "Source", "Note")):
            continue
        if s.endswith(":"):
            continue

        # Accept if: has a named entity, has a number, or has a factual keyword
        has_entity = len(sent.ents) > 0
        has_number = any(tok.like_num for tok in sent) or bool(re.search(r'\d', s)) or '%' in s or '$' in s
        has_fact_word = any(w in s.lower() for w in [
            "according to", "projected", "forecast", "research shows", "study shows",
            "will reach", "expected to", "contributed", "is the", "was the",
            "serves as", "elected", "appointed", "founded", "known as",
            "prime minister", "president", "capital", "billion", "trillion", "million"
        ])

        if has_entity or has_number or has_fact_word:
            claims.append(s)

    return claims


# ========================== 3. WEB SEARCH (with retry) ==========================
def search_web(claim: str) -> List[Dict]:
    all_results = []
    queries = [claim[:130], claim.split(".")[0][:100]]  # two different angle queries

    for q in queries:
        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(q, max_results=8))
                    all_results.extend(results)
                    time.sleep(0.5)
                break
            except Exception:
                time.sleep(1.5 * (attempt + 1))

    seen = set()
    unique = []
    for r in all_results:
        url = r.get("href", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)
    return unique[:12]


# ========================== 4. GROUP CLASSIFICATION ==========================
def categorize_claim(claim: str) -> str:
    s = claim.lower()
    if any(x in s for x in ["market", "billion", "trillion", "size", "projected to reach"]):
        return "Market Projection"
    elif any(x in s for x in ["fortune 500", "companies", "integrated", "adopted", "adoption"]):
        return "Adoption Rate"
    elif any(x in s for x in ["economy", "gdp", "contributed"]):
        return "Economic Impact"
    elif any(x in s for x in ["content creation", "cost", "reduce", "65%"]):
        return "Cost Reduction"
    elif any(x in s for x in ["agi", "artificial general intelligence", "commercially available"]):
        return "AGI Timeline"
    elif any(x in s for x in ["prime minister", "president", "capital", "known as", "settled", "founded"]):
        return "Current/Historical Fact"
    return "General Claim"


# ========================== 5. EXTRACT REAL FACT FROM RESULTS ==========================
def extract_real_fact(claim: str, search_results: List[Dict]) -> str:
    claim_keywords = set(re.findall(r'\b\w{4,}\b', claim.lower()))
    claim_numbers = re.findall(r'\d+\.?\d*', claim)

    best_snippet = ""
    best_score = 0

    for r in search_results:
        title = r.get("title", "")
        body = r.get("body", "") or ""
        combined = (title + " " + body).lower()

        snippet_words = set(re.findall(r'\b\w{4,}\b', combined))
        overlap = len(claim_keywords & snippet_words)

        snippet_numbers = re.findall(r'\d+\.?\d*', combined)
        has_different_number = any(n not in claim_numbers for n in snippet_numbers)
        if has_different_number:
            overlap += 2

        if overlap > best_score:
            best_score = overlap
            snippet = body[:220].strip()
            if snippet:
                best_snippet = f'"{snippet}..." — {r.get("href", "")}'

    return best_snippet if best_snippet else "No correcting source found."


# ========================== 6. VERIFICATION LOGIC ==========================
def classify_claim(claim: str, search_results: List[Dict]) -> tuple:
    if not search_results:
        return "False", "No relevant web results found", "No web results found for this claim."

    positive = 0
    negative = 0
    outdated = 0
    domains = set()

    claim_numbers = re.findall(r'\d+\.?\d*', claim)

    # ---- FIXED: removed short common phrases that cause false positives ----
    conf_words = {
        "according to", "official", "confirmed", "verified", "statista", "idc",
        "mckinsey", "gartner", "report", "study shows", "research shows", "industry reports"
    }
    contra_words = {
        "debunked", "false claim", "misinformation", "fact check: false",
        "no evidence", "misleading", "hoax", "myth", "fabricated",
        "fact-checked", "inaccurate claim", "disinformation", "not accurate"
    }
    outdated_words = {"outdated", "no longer", "old data", "previously", "was true until"}

    # spaCy NER on the claim for entity-level matching
    claim_doc = nlp(claim)
    claim_entities = [e.text.lower() for e in claim_doc.ents]

    for r in search_results:
        text = (r.get("title", "") + " " + r.get("body", "")).lower()
        url = r.get("href", "").lower()

        try:
            domain = url.split("/")[2]
            domains.add(domain)
        except Exception:
            pass

        # Contra words — only fire on strong, specific phrases now
        if any(w in text for w in contra_words):
            negative += 1

        # Confirmation signals
        if any(w in text for w in conf_words):
            positive += 2 if any(rep in url for rep in ["statista", "idc", "mckinsey", "gartner", ".gov"]) else 1

        # Outdated signals
        if any(w in text for w in outdated_words):
            outdated += 1

        # Authoritative domain bonus
        if any(x in url for x in [".gov", ".edu", "who.int", "un.org", "bbc.com", "reuters.com", "apnews.com"]):
            positive += 2

        # Number match bonus
        if claim_numbers:
            for num in claim_numbers:
                if num in text:
                    positive += 2

        # ---- NEW: NER entity match bonus ----
        for ent in claim_entities:
            if ent in text:
                positive += 2

    unique_sources = len(domains)
    total_positive = positive

    # Verdict logic
    if unique_sources == 0:
        return "False", "No supporting evidence found in web results", "No web results found."

    if negative >= 4 or (negative >= 3 and total_positive <= 4):
        verdict = "Inaccurate (real but outdated data)"
        reason = "Claim contradicted by specific fact-check sources"
    elif outdated >= 2:
        verdict = "Inaccurate (real but outdated data)"
        reason = f"Data appears outdated ({outdated} signals)"
    elif total_positive >= 8 and unique_sources >= 4:
        verdict = "Verified"
        reason = f"Strong confirmation from {unique_sources} reliable sources"
    elif total_positive >= 6 and unique_sources >= 5:
        verdict = "Verified"
        reason = f"Broad consensus across {unique_sources} sources"
    elif positive >= 5 and negative >= 2:
        verdict = "Unverified"
        reason = "Mixed signals from sources"
    elif unique_sources >= 7 and total_positive >= 4:
        verdict = "Verified"
        reason = "Good support from multiple sources"
    else:
        verdict = "Unverified"
        reason = f"Insufficient consensus ({unique_sources} sources)"

    real_fact = extract_real_fact(claim, search_results) if verdict != "Verified" else "—"
    return verdict, reason, real_fact


# ========================== 7. PARALLEL PROCESSING ==========================
def process_all_claims(claims: List[str]) -> List[Dict]:
    results = []
    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    total = len(claims)

    def process_claim(claim: str):
        search_results = search_web(claim)
        verdict, reason, real_fact = classify_claim(claim, search_results)
        category = categorize_claim(claim)
        return {
            "claim": claim,
            "category": category,
            "verdict": verdict,
            "reason": reason,
            "real_fact": real_fact,
            "sources_found": len(search_results),
            "raw_results": search_results[:4]
        }

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_idx = {executor.submit(process_claim, c): i for i, c in enumerate(claims)}

        for idx, future in enumerate(as_completed(future_to_idx), 1):
            result = future.result()
            results.append(result)
            progress = idx / total
            progress_bar.progress(progress)
            status_placeholder.caption(f"✅ Processed {idx}/{total} claims • {progress:.0%}")

    status_placeholder.empty()
    return sorted(results, key=lambda x: claims.index(x["claim"]))


# ========================== 8. SHOW SUMMARY ==========================
def show_summary(results: List[Dict], start_time: float):
    if not results:
        return

    elapsed = time.time() - start_time

    df = pd.DataFrame([{
        "Claim": r["claim"][:280] + "..." if len(r["claim"]) > 280 else r["claim"],
        "Category": r["category"],
        "Verdict": r["verdict"],
        "Reason": r["reason"],
        "Real Fact / Correction": r["real_fact"],
        "Sources": r["sources_found"]
    } for r in results])

    total = len(results)
    verified = sum(1 for r in results if r["verdict"] == "Verified")
    inaccurate = sum(1 for r in results if "Inaccurate" in r["verdict"])
    false_count = sum(1 for r in results if r["verdict"] == "False")
    unverified = total - verified - inaccurate - false_count

    st.subheader("📊 Fact Check Overview")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Claims", total)
    col2.metric("Verified ✅", verified)
    col3.metric("Inaccurate ⚠️", inaccurate)
    col4.metric("False ❌", false_count)
    col5.metric("Unverified ❓", unverified)
    col6.metric("Processing Time", f"{elapsed:.1f} sec")

    st.markdown("<h3 style='text-align: center;'>📊 Grouped Summary</h3>", unsafe_allow_html=True)
    grouped = df.groupby(["Category", "Verdict"]).size().unstack(fill_value=0)
    grouped = grouped.reset_index()
    st.dataframe(grouped, use_container_width=True, hide_index=True)

    st.markdown("<h3 style='text-align: center;'>Fact-Check Results</h3>", unsafe_allow_html=True)

    def color_verdict_text(val):
        if val == "Verified":
            return 'color: #28a745; font-weight: bold;'
        elif "Inaccurate" in str(val):
            return 'color: #ffc107; font-weight: bold;'
        elif val == "False":
            return 'color: #dc3545; font-weight: bold;'
        elif val == "Unverified":
            return 'color: #6c757d; font-weight: bold;'
        return ''

    styled_df = df.style.map(color_verdict_text, subset=['Verdict'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False)
    st.download_button("Download Full Report as CSV", csv, file_name="fact_check_report.csv", mime="text/csv", use_container_width=True)


# ========================== MAIN APP ==========================
def main():
    st.set_page_config(page_title="Cog Culture Fact Checker", page_icon="🔎", layout="wide")
    st.title("Cog Culture Fact Checker")
    st.caption("PDF/DOCX + Raw Text | spaCy NER | Parallel Processing")

    col_left, col_right = st.columns([1, 2])

    uploaded_file = None
    raw_text = ""

    with col_left:
        st.subheader("📤 Input Source")

        tab_file, tab_text = st.tabs(["📄 Upload File (PDF/DOCX)", "✍️ Paste Raw Text"])

        with tab_file:
            uploaded_file = st.file_uploader("Choose PDF or DOCX file", type=["pdf", "docx"], key="file_uploader")

        with tab_text:
            raw_text = st.text_area("Paste your raw text / paragraphs here",
                                    height=300,
                                    placeholder="Enter claims or full text here for quick testing...",
                                    key="raw_text_area")

        run_clicked = st.button("🚀 Start Fact Checking", type="primary", use_container_width=True)

    with col_right:
        st.subheader("📋 Extracted Claims Preview")
        preview_claims = []
        if st.session_state.get("raw_text_area", "").strip():
            preview_claims = extract_claims(clean_text(st.session_state.raw_text_area))
        elif uploaded_file is not None:
            preview_claims = extract_claims(load_document(uploaded_file))

        if preview_claims:
            for i, claim in enumerate(preview_claims):
                st.write(f"**{i+1}.** {claim}")
            st.caption(f"**Total claims: {len(preview_claims)}**")
        else:
            st.info("Paste text in the left tab or upload a file to preview claims.")

    st.divider()

    if run_clicked:
        start_time = time.time()

        if raw_text and raw_text.strip():
            text = clean_text(raw_text)
            source = "Raw Text"
        elif uploaded_file is not None:
            with st.spinner("Loading document..."):
                text = load_document(uploaded_file)
            source = "Uploaded File"
        else:
            st.warning("Please either paste text or upload a file.")
            st.stop()

        with st.spinner("Extracting claims..."):
            claims = extract_claims(text)

        st.success(f"Extracted {len(claims)} claims from {source} — Starting parallel verification...")

        results = process_all_claims(claims)
        show_summary(results, start_time)

        st.subheader("🔍 Detailed Search Results")
        for i, res in enumerate(results):
            if res["raw_results"]:
                with st.expander(f"View Search Results - Claim {i+1} ({res['category']})", expanded=False):
                    if res["verdict"] != "Verified" and res["real_fact"] != "—":
                        st.markdown(f"**🔎 Real Fact / Correction:** {res['real_fact']}")
                        st.divider()
                    for item in res["raw_results"]:
                        st.write(f"**{item.get('title', 'No Title')}**")
                        st.write(item.get('href', ''))
                        st.caption((item.get('body', '') or '')[:300] + "...")
                        st.divider()

    st.divider()
    st.caption("Modular • Transparent • spaCy NER • Fast Parallel Processing • Trap Document Ready")


if __name__ == "__main__":
    main()