# Cog Culture Fact Checker

**Automated Fact-Checking Web App**  
A smart tool that extracts claims from PDF/DOCX documents, verifies them against live web sources, and flags inaccurate or outdated statistics.

---

## ✨ Features

- **Upload PDF or DOCX** files
- **Automatic claim extraction** using spaCy (NER + sentence analysis)
- **Live web verification** using DuckDuckGo search
- **Smart classification** – detects Market Projections, Economic Impact, AGI timelines, etc.
- **Clear verdicts**: Verified ✅ | Inaccurate ⚠️ | Unverified ❓ | False ❌
- **Shows real facts** when claims are wrong or outdated
- **Parallel processing** for fast performance
- **Download full report** as CSV

---

## 🎯 Purpose

Built to act as a **"Truth Layer"** for marketing/sales documents that often contain hallucinated or outdated statistics.  
Especially effective against **"Trap Documents"** containing intentional fake claims.

---

## How to Use

1. Go to the live app
2. Upload a PDF or DOCX file
3. Click **"🚀 Start Fact Checking"**
4. Review results with sources and corrections

---

## Tech Stack

- **Frontend**: Streamlit
- **NLP**: spaCy (en_core_web_sm)
- **Search**: DuckDuckGo
- **PDF/DOCX**: pypdf + python-docx
- **Parallel Processing**: ThreadPoolExecutor

---

## Deployment

Deployed on **Streamlit Community Cloud**  
**Live URL**: `https://your-app-name.streamlit.app`

---

## Repository Structure
