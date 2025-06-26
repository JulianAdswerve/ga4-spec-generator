import streamlit as st
import pandas as pd
from openai import OpenAI
import io

# --- CONFIG ---
st.set_page_config(page_title="GA4 Data Layer Spec Generator", layout="centered")

# --- TITLE ---
st.title("GA4 Data Layer Spec Generator")
st.markdown("Upload your Tags CSV to get started.")

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Tags CSV", type=["csv"])

# --- LOAD DATA ---
def load_csv(file):
    return pd.read_csv(file)

# --- CALL OPENAI ---
def call_openai(prompt):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content

# --- GENERATE PROMPT ---
def build_prompt(event_name, parameters):
    base = f"""
You are a GA4 implementation expert. Given the event '{event_name}' and its parameter descriptions:

{parameters}

Generate a data layer spec in table format with the following columns:
- Key
- Description
- Data Type
- Example Value
- Source (e.g., dataLayer, JS variable, DOM scraping)
"""
    return base.strip()

# --- MAIN LOGIC ---
if uploaded_file:
    df = load_csv(uploaded_file)
    st.subheader("Preview: Tags CSV")
    st.dataframe(df.head())

    if "event_name" in df.columns:
        unique_events = df["event_name"].unique()
        selected_event = st.selectbox("Select an event to generate spec for:", unique_events)

        if st.button("Generate Spec"):
            param_rows = df[df["event_name"] == selected_event]
            param_descriptions = "\n".join(
                f"{row['parameter_name']}: {row['description']}"
                for _, row in param_rows.iterrows()
                if pd.notna(row['parameter_name']) and pd.notna(row['description'])
            )
            prompt = build_prompt(selected_event, param_descriptions)
            output = call_openai(prompt)
            st.subheader("Generated Data Layer Spec")
            st.code(output)
    else:
        st.warning("Your CSV must contain a column named 'event_name' to proceed.")
