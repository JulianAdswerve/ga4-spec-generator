# streamlit_app.py
import streamlit as st
import pandas as pd
import openai
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- SETUP ---
openai.api_key = st.secrets["OPENAI_API_KEY"]  # Add this to .streamlit/secrets.toml

def generate_prompt(event_name, parameters_text, notes=""):
    return f"""
    You are a GA4 implementation expert. Based on the following tagging plan row, generate a GA4-compatible data layer spec table.

    Event Name: {event_name}
    Web Event Parameters: {parameters_text}
    Notes: {notes}

    Output the spec as a table with columns:
    - parameter
    - scope (event-level or ecommerce.items[])
    - type
    - example_value
    - notes
    """

def call_openai(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a GA4 tagging and data layer specification assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )
    return response.choices[0].message.content

def upload_to_google_sheets(sheet_name, df):
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=credentials)
    spreadsheet = {
        'properties': {
            'title': sheet_name
        }
    }
    sheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
    sheet_id = sheet.get('spreadsheetId')

    # Prepare values
    values = [df.columns.tolist()] + df.values.tolist()
    body = {
        'values': values
    }
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Sheet1",
        valueInputOption="RAW",
        body=body
    ).execute()

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"

# --- STREAMLIT UI ---
st.title("GA4 Data Layer Spec Generator")
st.write("Upload your Tags CSV to get started.")

uploaded_file = st.file_uploader("Upload Tags CSV", type=["csv"])

if uploaded_file:
    df_tags = pd.read_csv(uploaded_file)
    st.subheader("Preview of Uploaded Tags")
    st.dataframe(df_tags.head())

    selected_rows = st.multiselect("Select rows to generate specs for (by row number):", df_tags.index)

    if st.button("Generate Spec") and selected_rows:
        all_results = []
        for idx in selected_rows:
            row = df_tags.loc[idx]
            event_name = row.get("Event Name", "")
            parameters = row.get("Web Event Parameters", "")
            notes = row.get("Notes", "")
            prompt = generate_prompt(event_name, parameters, notes)
            output = call_openai(prompt)
            st.markdown(f"### Spec for `{event_name}`")
            st.markdown(output)
            try:
                df_result = pd.read_csv(pd.compat.StringIO(output))
                all_results.append(df_result)
            except:
                st.warning(f"Could not parse structured output for {event_name}. Review response above.")

        if all_results:
            final_spec = pd.concat(all_results, ignore_index=True)
            if st.button("Upload to Google Sheets"):
                sheet_url = upload_to_google_sheets("GA4 Spec Output", final_spec)
                st.success(f"Uploaded to Google Sheets: [Open Sheet]({sheet_url})")
