import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from audio_recorder_streamlit import audio_recorder

# Configuration
API_URL = "http://localhost:8000"

st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide")

st.title("💰 AI Expense Tracker")
st.markdown("Track expenses with voice or text - powered by local LLM")

# Tabs for different functions
tab1, tab2, tab3 = st.tabs(["➕ Add Expense", "📊 View Expenses", "📈 Monthly Summary"])

# TAB 1: Add Expense
with tab1:
    st.header("Add New Expense")

    # Text input
    st.subheader("Option 1: Text Input")
    text_input = st.text_area(
        "Describe your expense",
        placeholder="e.g., Spent $45 on groceries yesterday\nPaid 2000 rupees for uber today\nBought coffee for 5 euros",
        height=100
    )

    if st.button("Add Text Expense", type="primary"):
        if text_input:
            with st.spinner("Processing..."):
                try:
                    response = requests.post(
                        f"{API_URL}/add-text-expense",
                        json={"text": text_input}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.success("✅ Expense added successfully!")
                        st.json(data)
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
        else:
            st.warning("Please enter an expense description")

    st.divider()

    # Audio input
    st.subheader("Option 2: Voice Input")
    st.info("🎤 Click to start recording, click again to stop")

    audio_bytes = audio_recorder(
        text="Click to record",
        recording_color="#e74c3c",
        neutral_color="#3498db",
        icon_size="2x"
    )

    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")

        if st.button("Process Audio Expense", type="primary"):
            with st.spinner("Transcribing and processing..."):
                try:
                    files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
                    response = requests.post(
                        f"{API_URL}/add-audio-expense",
                        files=files
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.success("✅ Expense added from voice!")
                        st.json(data)
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")

# TAB 2: View Expenses
with tab2:
    st.header("All Expenses")

    if st.button("🔄 Refresh Expenses"):
        st.rerun()

    try:
        response = requests.get(f"{API_URL}/expenses")

        if response.status_code == 200:
            expenses = response.json()

            if expenses:
                df = pd.DataFrame(expenses)
                df = df[['date', 'category', 'amount', 'currency', 'raw_text']]

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                # Summary stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Expenses", len(expenses))
                with col2:
                    st.metric("Categories", df['category'].nunique())
                with col3:
                    total = df['amount'].sum()
                    st.metric("Total Amount", f"${total:.2f}")
            else:
                st.info("No expenses recorded yet")
        else:
            st.error("Failed to fetch expenses")
    except Exception as e:
        st.error(f"Connection error: {str(e)}")

# TAB 3: Monthly Summary
with tab3:
    st.header("Monthly Analytics")

    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("Year", min_value=2020, max_value=2030, value=datetime.now().year)
    with col2:
        month = st.number_input("Month", min_value=1, max_value=12, value=datetime.now().month)

    if st.button("Generate Summary", type="primary"):
        with st.spinner("Analyzing expenses with AI..."):
            try:
                response = requests.post(
                    f"{API_URL}/monthly-summary",
                    json={"year": year, "month": month}
                )

                if response.status_code == 200:
                    data = response.json()

                    st.subheader(f"📅 {year}-{month:02d} Summary")
                    st.metric("Total Expenses", data["total_expenses"])

                    st.markdown("### 🤖 AI Insights")
                    st.write(data["summary"])

                    if data["expenses"]:
                        st.markdown("### 📋 Detailed Expenses")
                        df = pd.DataFrame(data["expenses"])
                        df = df[['date', 'category', 'amount', 'currency', 'raw_text']]
                        st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

# Sidebar
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    This app uses:
    - **Ollama** (llama3.1) for LLM
    - **Whisper** for speech-to-text
    - **SQLite** for storage
    - **FastAPI** backend
    - **Streamlit** frontend

    All processing happens locally!
    """)

    st.markdown("---")
    st.markdown("**API Status**")
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        if response.status_code == 200:
            st.success("✅ Connected")
        else:
            st.error("❌ API Error")
    except Exception:
        st.error("❌ Not Connected")
