import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from audio_recorder_streamlit import audio_recorder
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

# Configuration
API_URL = "http://localhost:8000"

st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide")

st.title("💰 AI Expense Tracker")
st.markdown("Track expenses with voice or text - powered by local LLM")

# Tabs for different functions
tab1, tab2, tab3, tab4 = st.tabs([
    "➕ Add Expense", "📊 View Expenses", "📈 Monthly Summary", "📉 BI Dashboard"
])

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

# TAB 4: Adaptive BI-style Visualization (Power BI / Tableau–like)
with tab4:
    st.header("📉 Adaptive BI Dashboard")
    st.markdown("Interactive visualizations that adapt to your date range and data. Export for **Power BI** or **Tableau** below.")

    try:
        response = requests.get(f"{API_URL}/expenses", timeout=5)
        if response.status_code != 200:
            st.error("Failed to load expenses.")
            response = None
    except Exception:
        response = None
        st.error("Connection error: could not reach API.")

    if response and response.status_code == 200:
        expenses = response.json()
        if not expenses:
            st.info("No expenses yet. Add some in **Add Expense** or load sample data to see visualizations.")
        else:
            df = pd.DataFrame(expenses)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])
            if df.empty:
                st.warning("No valid dates in expenses.")
            else:
                # Date range filter
                min_date = df["date"].min().date()
                max_date = df["date"].max().date()
                col_a, col_b, col_c = st.columns([1, 1, 2])
                with col_a:
                    from_date = st.date_input(
                        "From",
                        value=min_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="viz_from",
                    )
                with col_b:
                    to_date = st.date_input(
                        "To",
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="viz_to",
                    )

                mask = (df["date"].dt.date >= from_date) & (df["date"].dt.date <= to_date)
                df_range = df.loc[mask].copy()

                if df_range.empty:
                    st.warning("No expenses in the selected date range.")
                else:
                    # KPIs
                    total = df_range["amount"].sum()
                    count = len(df_range)
                    n_months = max(1, (to_date - from_date).days / 30)
                    avg_monthly = total / n_months
                    top_cat = df_range.groupby("category")["amount"].sum().idxmax()
                    top_cat_amount = df_range.groupby("category")["amount"].sum().max()

                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Total spend", f"${total:,.2f}")
                    k2.metric("Transactions", count)
                    k3.metric("Avg monthly", f"${avg_monthly:,.2f}")
                    k4.metric("Top category", f"{top_cat} (${top_cat_amount:,.2f})")

                    st.divider()

                    # Charts row 1: Time series + Category breakdown
                    fig_ts = go.Figure()
                    daily = df_range.groupby(df_range["date"].dt.date)["amount"].sum().reset_index()
                    daily.columns = ["date", "amount"]
                    fig_ts.add_trace(
                        go.Scatter(
                            x=daily["date"],
                            y=daily["amount"],
                            mode="lines+markers",
                            name="Daily total",
                            line=dict(color="#3498db", width=2),
                        )
                    )
                    fig_ts.update_layout(
                        title="Spending over time",
                        xaxis_title="Date",
                        yaxis_title="Amount (USD)",
                        template="plotly_white",
                        height=320,
                        margin=dict(t=40, b=40, l=50, r=20),
                    )

                    by_cat = df_range.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=True)
                    fig_cat = px.bar(
                        by_cat,
                        x="amount",
                        y="category",
                        orientation="h",
                        title="Spending by category",
                        labels={"amount": "Amount (USD)", "category": "Category"},
                        color="amount",
                        color_continuous_scale="Blues",
                    )
                    fig_cat.update_layout(
                        showlegend=False,
                        template="plotly_white",
                        height=320,
                        margin=dict(t=40, b=40, l=80, r=20),
                        yaxis=dict(autorange="reversed"),
                    )

                    c1, c2 = st.columns(2)
                    c1.plotly_chart(fig_ts, use_container_width=True)
                    c2.plotly_chart(fig_cat, use_container_width=True)

                    # Row 2: Pie + Monthly comparison
                    fig_pie = px.pie(
                        by_cat,
                        values="amount",
                        names="category",
                        title="Share by category",
                        color_discrete_sequence=px.colors.sequential.Blues_r,
                    )
                    fig_pie.update_layout(template="plotly_white", height=340, margin=dict(t=40, b=20, l=20, r=20))

                    df_range["year_month"] = df_range["date"].dt.to_period("M").astype(str)
                    monthly = df_range.groupby("year_month")["amount"].sum().reset_index()
                    fig_month = px.bar(
                        monthly,
                        x="year_month",
                        y="amount",
                        title="Monthly total spending",
                        labels={"amount": "Amount (USD)", "year_month": "Month"},
                        color="amount",
                        color_continuous_scale="Teal",
                    )
                    fig_month.update_layout(
                        template="plotly_white",
                        height=340,
                        margin=dict(t=40, b=60, l=50, r=20),
                        xaxis_tickangle=-45,
                    )

                    c3, c4 = st.columns(2)
                    c3.plotly_chart(fig_pie, use_container_width=True)
                    c4.plotly_chart(fig_month, use_container_width=True)

                    # Export for Power BI / Tableau
                    st.divider()
                    st.subheader("Export for Power BI or Tableau")
                    export_df = df_range[["date", "category", "amount", "currency", "raw_text"]].copy()
                    export_df["date"] = export_df["date"].dt.strftime("%Y-%m-%d")

                    col_csv, col_xlsx, col_help = st.columns([1, 1, 2])
                    with col_csv:
                        buf_csv = io.BytesIO()
                        export_df.to_csv(buf_csv, index=False)
                        buf_csv.seek(0)
                        st.download_button(
                            "Download CSV",
                            data=buf_csv.getvalue(),
                            file_name="expenses_export.csv",
                            mime="text/csv",
                            key="dl_csv",
                        )
                    with col_xlsx:
                        buf_xlsx = io.BytesIO()
                        try:
                            export_df.to_excel(buf_xlsx, index=False, engine="openpyxl")
                            buf_xlsx.seek(0)
                            st.download_button(
                                "Download Excel",
                                data=buf_xlsx.getvalue(),
                                file_name="expenses_export.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="dl_xlsx",
                            )
                        except Exception:
                            st.caption("Install openpyxl for Excel export")
                    with col_help:
                        with st.expander("How to use in Power BI / Tableau"):
                            st.markdown("""
                            **Power BI**
                            1. Get data → Text/CSV or Excel → select the downloaded file.
                            2. Create reports with the same fields: date, category, amount, currency.

                            **Tableau**
                            1. Connect to Text file or Microsoft Excel → choose the downloaded file.
                            2. Use **date**, **category**, and **amount** for dimensions and measures.
                            """)
    else:
        st.info("Connect to the backend (run uvicorn) to see the BI dashboard.")

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
    - **BI Dashboard**: Plotly charts + export for Power BI / Tableau

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
