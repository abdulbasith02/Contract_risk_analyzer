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


# ---------------- LOAD API KEY SAFELY ----------------
def load_api_key():
    """
    Loads API key from Streamlit secrets first,
    then environment variables.
    """
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.error(
            "❌ Gemini API key not found.\n\n"
            "Add it to `.streamlit/secrets.toml` OR Streamlit Cloud secrets."
        )
        st.stop()

    return api_key


api_key = load_api_key()

# Configure Gemini
genai.configure(api_key=api_key)


# ---------------- CACHE MODEL (VERY IMPORTANT) ----------------
@st.cache_resource
def get_model():
    """
    Cache prevents model reload on every UI interaction.
    Makes app MUCH faster.
    """
    try:
        models = genai.list_models()

        for m in models:
            if "generateContent" in m.supported_generation_methods:
                return genai.GenerativeModel(m.name)

    except Exception:
        return None

    return None


model = get_model()


# ---------------- FILE TEXT EXTRACTION ----------------
def extract_text(file):

    if file.name.endswith(".pdf"):
        text = ""

        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        return text

    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs)

    else:
        return file.read().decode("utf-8")


# ---------------- RULE-BASED RISK ----------------
def rule_based_risk(text):

    risks = []
    t = text.lower()

    if "terminate" in t:
        risks.append("Unilateral termination clause")

    if "indemnify" in t or "indemnity" in t:
        risks.append("Unlimited indemnity clause")

    if "jurisdiction" in t:
        risks.append("Foreign jurisdiction clause")

    level = (
        "High" if len(risks) >= 2
        else "Medium" if len(risks) == 1
        else "Low"
    )

    return risks, level


# ---------------- GEMINI ANALYSIS ----------------
def analyze_with_gemini(text):

    if not model:
        return "⚠️ AI analysis unavailable. Showing rule-based detection only."

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
        return "⚠️ AI analysis temporarily unavailable."


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
