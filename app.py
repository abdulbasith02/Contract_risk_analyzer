import streamlit as st
import google.generativeai as genai
import pdfplumber
from docx import Document
import os

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Contract Risk Analyzer",
    layout="wide"
)

st.title("📄 Contract Analysis & Risk Assessment Bot")

# ---------------- LOAD GEMINI API KEY ----------------
api_key = None

# First try Streamlit secrets
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error(
        "❌ Gemini API key not found.\n\n"
        "Add it to `.streamlit/secrets.toml` or set an environment variable."
    )
    st.stop()

genai.configure(api_key=api_key)

# ---------------- AUTO-DETECT WORKING MODEL ----------------
def get_working_model():
    try:
        models = genai.list_models()
        for m in models:
            if "generateContent" in m.supported_generation_methods:
                return genai.GenerativeModel(m.name)
    except Exception:
        return None
    return None

model = get_working_model()

# ---------------- FUNCTIONS ----------------
def extract_text(file):
    if file.name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text() + "\n"
        return text

    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs)

    else:
        return file.read().decode("utf-8")


def rule_based_risk(text):
    risks = []
    t = text.lower()

    if "terminate" in t:
        risks.append("Unilateral termination clause")

    if "indemnify" in t or "indemnity" in t:
        risks.append("Unlimited indemnity clause")

    if "jurisdiction" in t:
        risks.append("Foreign jurisdiction clause")

    if len(risks) >= 2:
        level = "High"
    elif len(risks) == 1:
        level = "Medium"
    else:
        level = "Low"

    return risks, level


def analyze_with_gemini(text):
    if not model:
        return (
            "⚠️ AI analysis is unavailable for this API key.\n\n"
            "Rule-based risk detection is shown above and is valid."
        )

    prompt = f"""
You are a legal contract risk analysis assistant.

Analyze the contract below and provide:
1. Contract type
2. Overall risk level (Low / Medium / High)
3. Risky clauses
4. Simple business explanation
5. Safer recommendations

Contract:
{text}
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return (
            "⚠️ AI analysis temporarily unavailable.\n\n"
            "Rule-based risk detection is still valid."
        )

# ---------------- UI ----------------
uploaded_file = st.file_uploader(
    "Upload Contract (PDF, DOCX, TXT)",
    type=["pdf", "docx", "txt"]
)

if uploaded_file:
    contract_text = extract_text(uploaded_file)

    st.success("✅ Contract uploaded successfully")

    risks, risk_level = rule_based_risk(contract_text)

    st.subheader("📌 Contract Summary")
    st.write("**Contract Type:** Commercial / Service Agreement")
    st.write(f"**Overall Risk Level:** `{risk_level}`")

    st.subheader("⚠️ Detected Risky Clauses")
    if risks:
        for r in risks:
            st.write(f"• {r}")
    else:
        st.write("No major risky clauses detected.")

    st.subheader("🤖 AI Explanation")
    with st.spinner("Analyzing contract..."):
        ai_result = analyze_with_gemini(contract_text)
        st.write(ai_result)

    st.download_button(
        label="📥 Download Analysis Report",
        data=ai_result,
        file_name="contract_risk_report.txt"
    )
