# Cog Culture Fact Checker

**Automated PDF Fact-Checking Web App**  
A smart "Truth Layer" that extracts claims from documents, verifies them against live web data, and flags inaccurate or outdated statistics.

---

## ✨ Live Demo

**Deployed App:** [https://fact-checker-assignment.streamlit.app/](https://fact-checker-assignment.streamlit.app/)

---

## 🎯 Key Features

- Upload **PDF** or **DOCX** files
- Automatic extraction of factual claims using **spaCy NER**
- Real-time web verification using DuckDuckGo Search
- Intelligent verdict system: **Verified ✅**, **Inaccurate ⚠️**, **Unverified ❓**, **False ❌**
- Shows **real correcting facts** when claims are wrong or outdated
- Parallel processing for fast performance
- Download complete report as **CSV**

---

## 🎯 Designed For

This tool was built specifically for the **Fact-Check Agent Assignment**.  
It excels at detecting **"Trap Documents"** containing intentional fake statistics, outdated numbers, and hallucinations commonly found in marketing content.

---

## How to Use

1. Visit the live app: [https://fact-checker-assignment.streamlit.app/](https://fact-checker-assignment.streamlit.app/)
2. Upload a PDF or DOCX document
3. Click **"🚀 Start Fact Checking"**
4. Review detailed results with sources and corrections
5. Download the full report

---

## Tech Stack

- **Framework**: Streamlit
- **NLP**: spaCy (`en_core_web_sm`)
- **Search Engine**: DuckDuckGo Search
- **Document Parsing**: pypdf + python-docx
- **Processing**: Parallel execution with ThreadPoolExecutor

---

## Repository Structure
Main Directory/
├── app.py                 # Main Streamlit application
├── requirements.txt
├── setup.sh
├── README.md
└── .streamlit/config.toml
text---

## Deployment

- **Platform**: Streamlit Community Cloud
- **Status**: Live and Public
- **URL**: https://fact-checker-assignment.streamlit.app/

---

**Submission Ready**  
Fully meets all requirements of the Fact-Check Agent Part 2 assignment.

---

**Made for truth-seeking**
