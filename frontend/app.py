import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
from audio_recorder_streamlit import audio_recorder
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import os

# Configuration: backend URL (env or sidebar override)
_DEFAULT_API = os.environ.get("EXPENSE_API_URL", "http://127.0.0.1:8000")
if "api_url" not in st.session_state:
    st.session_state["api_url"] = _DEFAULT_API

st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide", initial_sidebar_state="expanded")

# ---- Dark mode: Blue & Black (trust, security, sophistication) ----
st.markdown("""
<style>
    /* Theme: Blue = trust/security, Black = sophistication/luxury */
    :root {
        --blue: #2563eb;
        --blue-light: #3b82f6;
        --blue-bright: #60a5fa;
        --blue-deep: #1e3a8a;
        --black: #0a0a0f;
        --black-elevated: #12121a;
        --black-card: #16161f;
        --surface: #1a1a24;
        --border: #2d2d3a;
        --text: #f1f5f9;
        --text-muted: #94a3b8;
        --radius: 12px;
        --shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
        --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.5);
    }
    /* Dark app background */
    .stApp {
        background: var(--black) !important;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }
    /* Headers: light text */
    .main h1, .main h2, .main h3 {
        color: var(--text) !important;
        font-weight: 600 !important;
        border-bottom: none !important;
    }
    .main h1 { font-weight: 700 !important; letter-spacing: -0.02em; margin-bottom: 0.25rem !important; }
    /* Tabs: black surface, blue selected */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: var(--black-card) !important;
        padding: 6px;
        border-radius: var(--radius);
        border: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 500;
        color: var(--text-muted) !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--blue) !important;
        color: white !important;
    }
    /* Cards / expanders */
    .stExpander {
        background: var(--black-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius);
    }
    /* Metrics: blue value, light label */
    [data-testid="stMetricValue"] {
        font-weight: 700 !important;
        color: var(--blue-bright) !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--text-muted) !important;
        font-weight: 500 !important;
    }
    /* Alerts: dark with blue/amber accents */
    .stAlert {
        border-radius: var(--radius);
        border: 1px solid var(--border);
        background: var(--black-card) !important;
    }
    [data-baseweb="notification"][kind="error"] {
        background: rgba(220, 38, 38, 0.15) !important;
        border-color: #dc2626 !important;
        color: #fca5a5 !important;
    }
    [data-baseweb="notification"][kind="warning"] {
        background: rgba(245, 158, 11, 0.15) !important;
        border-color: #f59e0b !important;
        color: #fcd34d !important;
    }
    [data-baseweb="notification"][kind="info"] {
        background: var(--black-card) !important;
        border-color: var(--blue) !important;
        color: var(--text-muted) !important;
    }
    /* Buttons */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="primary"] {
        background: var(--blue) !important;
        border: none !important;
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--blue-light) !important;
        box-shadow: 0 0 20px rgba(37, 99, 235, 0.4) !important;
        transform: translateY(-1px);
    }
    /* Sidebar: dark blue-black */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--black-elevated) 0%, var(--black) 100%) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
        color: var(--text-muted) !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
        color: var(--text) !important;
    }
    /* Dataframes: dark */
    .stDataFrame {
        border-radius: var(--radius);
        overflow: hidden;
        border: 1px solid var(--border);
    }
    .stDataFrame div[data-testid="stDataFrameResizable"] {
        background: var(--black-card) !important;
    }
    /* Hero */
    .hero-sub {
        color: var(--blue-bright);
        font-size: 1.05rem;
        margin-bottom: 0.5rem;
    }
    .hero-meta {
        font-size: 0.9rem;
        color: var(--text-muted);
    }
    /* Dividers */
    hr {
        border-color: var(--border) !important;
    }
    /* Labels and captions */
    .stCaption, .stCaptionContainer label, [data-testid="stCaptionContainer"] {
        color: var(--text-muted) !important;
    }
    label {
        color: var(--text-muted) !important;
    }
    /* Text inputs: dark */
    .stTextArea textarea, .stTextInput input {
        border-radius: 8px !important;
        border-color: var(--border) !important;
        background: var(--black-card) !important;
        color: var(--text) !important;
    }
    /* Number input */
    .stNumberInput input {
        background: var(--black-card) !important;
        border-color: var(--border) !important;
        color: var(--text) !important;
    }
    /* Selectbox */
    .stSelectbox div[data-baseweb="select"] {
        background: var(--black-card) !important;
        border-color: var(--border) !important;
    }
    /* Code blocks */
    .stCodeBlock code {
        background: var(--black-card) !important;
        color: var(--blue-bright) !important;
        border: 1px solid var(--border);
    }
    /* JSON expander */
    .stJson {
        background: var(--black-card) !important;
        border: 1px solid var(--border);
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


def get_api_url():
    return st.session_state.get("api_url", _DEFAULT_API).rstrip("/")

# ---- Header ----
st.title("💰 AI Expense Tracker")
st.markdown('<p class="hero-sub">Track expenses with voice or text — powered by your local LLM</p>', unsafe_allow_html=True)
st.markdown(f'<p class="hero-meta">🕐 {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>', unsafe_allow_html=True)
st.markdown("---")

# Fetch limit alerts for banner (near/over limit)
try:
    _status = requests.get(f"{get_api_url()}/limits/status", timeout=3)
    _alerts = _status.json().get("alerts", []) if _status.status_code == 200 else []
except Exception:
    _alerts = []

# Tabs for different functions
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14 = st.tabs([
    "➕ Add", "📊 View", "📈 Summary", "📉 Dashboard", "🔔 Limits", "📧 Gmail", "✏️ Review Queue", "🔄 Recurring", "📋 Insights", "🤖 Ask AI", "🎯 Goals", "💳 Affordability", "🔮 Simulator", "🏦 Wealth Hub"
])

if _alerts:
    with st.container():
        for a in _alerts:
            if a.get("alert_type") == "over":
                st.error(f"⚠️ **Over limit:** {a['category']} — ${a['spent']:.2f} / ${a['limit']:.2f} ({a['percent']}%)")
            else:
                st.warning(f"⚠️ **Near limit:** {a['category']} — ${a['spent']:.2f} / ${a['limit']:.2f} ({a['percent']}%)")
    st.divider()

# TAB 1: Add Expense
with tab1:
    st.header("Add New Expense")
    st.caption("Use text or voice to log an expense. The AI will extract amount, category, and date.")

    col_text, col_voice = st.columns([1, 1])
    with col_text:
        with st.container():
            st.subheader("📝 Text")
            text_input = st.text_area(
                "Describe your expense",
                placeholder="e.g., Spent $45 on groceries yesterday\nPaid 2000 rupees for uber today\nBought coffee for 5 euros",
                height=120,
                label_visibility="collapsed"
            )
            if st.button("Add from text", type="primary", key="btn_text"):
                if text_input:
                    with st.spinner("Processing..."):
                        try:
                            response = requests.post(
                                f"{get_api_url()}/add-text-expense",
                                json={"text": text_input}
                            )
                            if response.status_code == 200:
                                data = response.json()
                                st.success("✅ Expense added successfully!")
                                if data.get("is_verified") == 0 or (data.get("confidence_score") or 0) < 0.6:
                                    st.warning("⚠️ This expense was saved with **low confidence** and needs review. Check **Review Queue** to verify or correct.")
                                st.json(data)
                                st.rerun()
                            else:
                                st.error(f"Error: {response.text}")
                        except Exception as e:
                            st.error(f"Connection error: {str(e)}")
                else:
                    st.warning("Please enter an expense description")

    with col_voice:
        with st.container():
            st.subheader("🎤 Voice")
            st.caption("Click to record, then click again to stop.")
            audio_bytes = audio_recorder(
                text="Click to record",
                recording_color="#dc2626",
                neutral_color="#2563eb",
                icon_size="2x"
            )
            if audio_bytes:
                st.audio(audio_bytes, format="audio/wav")
                if st.button("Add from voice", type="primary", key="btn_voice"):
                    with st.spinner("Transcribing and processing..."):
                        try:
                            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
                            response = requests.post(
                                f"{get_api_url()}/add-audio-expense",
                                files=files
                            )
                            if response.status_code == 200:
                                data = response.json()
                                st.success("✅ Expense added from voice!")
                                if data.get("is_verified") == 0 or (data.get("confidence_score") or 0) < 0.6:
                                    st.warning("⚠️ This expense was saved with **low confidence** and needs review. Check **Review Queue** to verify or correct.")
                                st.json(data)
                                st.rerun()
                            else:
                                st.error(f"Error: {response.text}")
                        except Exception as e:
                            st.error(f"Connection error: {str(e)}")

# TAB 2: View Expenses
with tab2:
    st.header("All Expenses")
    st.caption("Your full expense list. Use **Refresh** after adding items here or via Telegram.")

    try:
        response = requests.get(f"{get_api_url()}/expenses", timeout=10)
        if response.status_code == 200:
            expenses = response.json()
            if expenses:
                df = pd.DataFrame(expenses)
                df = df[['date', 'category', 'amount', 'currency', 'raw_text']]
                total_amt = df['amount'].sum()
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Transactions", len(expenses))
                m2.metric("Categories", df['category'].nunique())
                m3.metric("Total", f"${total_amt:,.2f}")
                with m4:
                    st.write("")
                    if st.button("🔄 Refresh", type="primary"):
                        st.rerun()
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                if st.button("🔄 Refresh", type="primary"):
                    st.rerun()
                st.info("No expenses recorded yet. Add one in **Add Expense** or via Telegram.")
        else:
            st.error("Failed to fetch expenses")
    except Exception as e:
        st.error(f"Connection error: {str(e)}")

# TAB 3: Monthly Summary
with tab3:
    st.header("Monthly Analytics")
    st.caption("Pick a month and generate an AI summary with insights.")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        year = st.number_input("Year", min_value=2020, max_value=2030, value=datetime.now().year)
    with col2:
        month = st.number_input("Month", min_value=1, max_value=12, value=datetime.now().month)
    with col3:
        st.write("")
        st.write("")
        gen = st.button("Generate Summary", type="primary")

    if gen:
        with st.spinner("Analyzing expenses with AI..."):
            try:
                response = requests.post(
                    f"{get_api_url()}/monthly-summary",
                    json={"year": year, "month": month},
                    timeout=60
                )
                if response.status_code == 200:
                    data = response.json()
                    st.subheader(f"📅 {year}-{month:02d} Summary")
                    st.metric("Transactions", data["total_expenses"])
                    st.markdown("### 🤖 AI Insights")
                    st.write(data["summary"])
                    if data.get("expenses"):
                        st.markdown("### 📋 Detailed Expenses")
                        df = pd.DataFrame(data["expenses"])
                        df = df[['date', 'category', 'amount', 'currency', 'raw_text']]
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No expense records for this month.")
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

# TAB 4: BI Dashboard
with tab4:
    st.header("📉 BI Dashboard")
    st.caption("Interactive charts and exports for Power BI / Tableau. Upload a CSV if the backend is unreachable.")

    # 1) Try API
    expenses = None
    try:
        response = requests.get(f"{get_api_url()}/expenses", timeout=5)
        if response.status_code == 200:
            expenses = response.json()
    except Exception:
        pass

    # 2) Fallback: upload CSV when API unreachable
    if expenses is None:
        st.warning("Could not reach the backend API. Set **Backend API URL** in the sidebar (e.g. `http://127.0.0.1:8000`) or upload a CSV to see visualizations.")
        st.caption("Expected CSV columns: date, category, amount, currency (optional), raw_text (optional)")
        uploaded = st.file_uploader("Upload expenses CSV", type=["csv"], key="viz_upload")
        if uploaded:
            try:
                df_up = pd.read_csv(uploaded)
                df_up["date"] = pd.to_datetime(df_up["date"], errors="coerce")
                df_up = df_up.dropna(subset=["date"])
                if "amount" not in df_up.columns or "category" not in df_up.columns:
                    st.error("CSV must have columns: date, category, amount")
                else:
                    expenses = df_up.to_dict("records")
            except Exception as e:
                st.error(f"Could not read CSV: {e}")
                expenses = None
    elif not expenses:
        st.info("No expenses yet. Add some in **Add Expense** or load sample data. You can also upload a CSV above to visualize.")

    if expenses:
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
                # Budget Health (when API available)
                try:
                    r_h = requests.get(f"{get_api_url()}/insights/health-score", timeout=3)
                    if r_h.status_code == 200:
                        st.metric("Budget Health", f"{r_h.json().get('score', 0):.0f} / 100", "Insights tab for details")
                except Exception:
                    pass
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
                        line=dict(color="#2563eb", width=2),
                        marker=dict(size=6, color="#60a5fa"),
                    )
                )
                fig_ts.update_layout(
                    title="Spending over time",
                    xaxis_title="Date",
                    yaxis_title="Amount (USD)",
                    template="plotly_dark",
                    paper_bgcolor="rgba(22, 22, 31, 0.95)",
                    plot_bgcolor="rgba(22, 22, 31, 0.8)",
                    height=320,
                    margin=dict(t=40, b=40, l=50, r=20),
                    font=dict(color="#f1f5f9"),
                    xaxis=dict(gridcolor="rgba(45, 45, 58, 0.8)"),
                    yaxis=dict(gridcolor="rgba(45, 45, 58, 0.8)"),
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
                    color_continuous_scale=["#1e3a8a", "#2563eb", "#60a5fa"],
                )
                fig_cat.update_layout(
                    showlegend=False,
                    template="plotly_dark",
                    paper_bgcolor="rgba(22, 22, 31, 0.95)",
                    plot_bgcolor="rgba(22, 22, 31, 0.8)",
                    height=320,
                    margin=dict(t=40, b=40, l=80, r=20),
                    yaxis=dict(autorange="reversed", gridcolor="rgba(45, 45, 58, 0.8)"),
                    font=dict(color="#f1f5f9"),
                    xaxis=dict(gridcolor="rgba(45, 45, 58, 0.8)"),
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
                    color_discrete_sequence=["#1e3a8a", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd", "#bfdbfe"],
                )
                fig_pie.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(22, 22, 31, 0.95)",
                    height=340,
                    margin=dict(t=40, b=20, l=20, r=20),
                    font=dict(color="#f1f5f9"),
                )

                df_range["year_month"] = df_range["date"].dt.to_period("M").astype(str)
                monthly = df_range.groupby("year_month")["amount"].sum().reset_index()
                fig_month = px.bar(
                    monthly,
                    x="year_month",
                    y="amount",
                    title="Monthly total spending",
                    labels={"amount": "Amount (USD)", "year_month": "Month"},
                    color="amount",
                    color_continuous_scale=["#1e3a8a", "#2563eb", "#60a5fa"],
                )
                fig_month.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(22, 22, 31, 0.95)",
                    plot_bgcolor="rgba(22, 22, 31, 0.8)",
                    height=340,
                    margin=dict(t=40, b=60, l=50, r=20),
                    xaxis_tickangle=-45,
                    font=dict(color="#f1f5f9"),
                    xaxis=dict(gridcolor="rgba(45, 45, 58, 0.8)"),
                    yaxis=dict(gridcolor="rgba(45, 45, 58, 0.8)"),
                )

                c3, c4 = st.columns(2)
                c3.plotly_chart(fig_pie, use_container_width=True)
                c4.plotly_chart(fig_month, use_container_width=True)

                # Export for Power BI / Tableau
                st.divider()
                st.subheader("Download for Power BI Desktop")
                export_cols = [c for c in ["date", "category", "amount", "currency", "raw_text"] if c in df_range.columns]
                export_df = df_range[export_cols].copy()
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
                    with st.expander("How to use in Power BI Desktop"):
                        st.markdown("""
                        **Power BI Desktop**
                        1. Open Power BI Desktop → **Get data** → **Text/CSV** or **Excel**.
                        2. Select the downloaded file. Load the data.
                        3. Build visuals: use **date** (slicer/axis), **category** (legend/slicer), **amount** (values).
                        4. Publish to Power BI Service, then use **File → Embed → Publish to web** and paste the URL above to embed here.
                        """)

                # Power BI embed section
                st.divider()
                st.subheader("📊 Embed Power BI report")
                st.caption("Paste a Power BI 'Publish to web' embed URL to show your report below.")
                embed_url = st.text_input(
                    "Power BI embed URL",
                    placeholder="https://app.powerbi.com/view?r=...",
                    key="pbi_embed_url",
                    label_visibility="collapsed",
                )
                if embed_url and ("powerbi.com" in embed_url or "app.powerbi.com" in embed_url):
                    st.components.v1.iframe(embed_url, height=600, scrolling=True)
                elif embed_url:
                    st.caption("Enter a valid Power BI 'Publish to web' URL.")

# TAB 5: Limits & Alerts
LIMIT_CATEGORIES = ["total", "food", "transport", "shopping", "entertainment", "utilities", "healthcare", "other"]

with tab5:
    st.header("Limits & Alerts")
    st.caption("Set monthly limits per category or **total**. Alerts when you're near (80%+) or over.")

    try:
        status_resp = requests.get(f"{get_api_url()}/limits/status", timeout=5)
        if status_resp.status_code != 200:
            st.error("Could not load limits status.")
        else:
            status = status_resp.json()
            limits_list = status.get("limits", [])
            spending = status.get("spending", {})
            alerts = status.get("alerts", [])

            st.subheader("Set a limit")
            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a:
                limit_category = st.selectbox("Category", LIMIT_CATEGORIES, key="limit_cat")
            with col_b:
                limit_amount = st.number_input("Amount ($)", min_value=0.0, value=500.0, step=50.0, key="limit_amt")
            with col_c:
                st.write("")
                st.write("")
                if st.button("Save limit", type="primary"):
                    r = requests.post(f"{get_api_url()}/limits", json={"category": limit_category, "amount": limit_amount, "currency": "USD"}, timeout=5)
                    if r.status_code == 200:
                        st.success(f"Limit set: ${limit_amount:.0f} for {limit_category}")
                        st.rerun()
                    else:
                        st.error(r.text)

            st.divider()
            st.subheader("Current limits & this month")

            if not limits_list:
                st.info("No limits set yet. Set one above to get alerts.")
            else:
                for lim in limits_list:
                    cat = lim["category"]
                    amt = float(lim["amount"])
                    spent = spending.get(cat, 0.0)
                    pct = (spent / amt * 100) if amt else 0
                    cols = st.columns([2, 1, 1, 1, 1])
                    with cols[0]:
                        st.write(f"**{cat}**")
                    with cols[1]:
                        st.write(f"${amt:,.0f}")
                    with cols[2]:
                        st.write(f"${spent:,.2f}")
                    with cols[3]:
                        st.write(f"{pct:.1f}%")
                    with cols[4]:
                        if pct >= 100:
                            st.error("Over")
                        elif pct >= 80:
                            st.warning("Near")
                        else:
                            st.success("OK")
                        if st.button("Delete", key=f"del_{cat}"):
                            requests.delete(f"{get_api_url()}/limits/{cat}", timeout=5)
                            st.rerun()
                if alerts:
                    st.divider()
                    st.subheader("Active alerts")
                    for a in alerts:
                        if a.get("alert_type") == "over":
                            st.error(f"**{a['category']}**: ${a['spent']:.2f} / ${a['limit']:.2f} ({a['percent']}%) — over limit")
                        else:
                            st.warning(f"**{a['category']}**: ${a['spent']:.2f} / ${a['limit']:.2f} ({a['percent']}%) — near limit")

            st.divider()
            st.subheader("Forecast & predictive alerts")
            try:
                r_fc = requests.get(f"{get_api_url()}/forecast/month", params={"year": status.get("year"), "month": status.get("month")}, timeout=5)
                r_pred = requests.get(f"{get_api_url()}/alerts/predictive", params={"year": status.get("year"), "month": status.get("month")}, timeout=5)
                if r_fc.status_code == 200 and r_pred.status_code == 200:
                    fc = r_fc.json()
                    pred = r_pred.json()
                    proj_total = fc.get("projected_total", 0)
                    days_elapsed = fc.get("days_elapsed", 0)
                    days_in_month = fc.get("days_in_month", 30)
                    st.metric("Projected month-end total", f"${proj_total:,.2f}", f"Based on {days_elapsed}/{days_in_month} days")
                    if fc.get("by_category"):
                        st.caption("Projected by category")
                        df_fc = pd.DataFrame([{"Category": k, "Projected": f"${v:,.2f}"} for k, v in fc["by_category"].items()])
                        st.dataframe(df_fc, use_container_width=True, hide_index=True)
                    for a in pred.get("alerts", []):
                        st.warning(a.get("message", ""))
                    if not pred.get("alerts") and limits_list:
                        st.caption("No predictive over-limit alerts this month.")
                    r_fc_cat = requests.get(f"{get_api_url()}/forecast/categories", params={"year": status.get("year"), "month": status.get("month")}, timeout=5)
                    if r_fc_cat.status_code == 200:
                        fc_cat = r_fc_cat.json()
                        if fc_cat:
                            with st.expander("Category forecast (forecast/categories API)"):
                                if isinstance(fc_cat, dict):
                                    df_fcc = pd.DataFrame([{"Category": k, "Projected": f"${v:,.2f}"} for k, v in fc_cat.items()])
                                else:
                                    df_fcc = pd.DataFrame(fc_cat)
                                st.dataframe(df_fcc, use_container_width=True, hide_index=True)
                else:
                    st.caption("Forecast unavailable.")
            except Exception:
                st.caption("Forecast unavailable.")
    except Exception as e:
        st.error(f"Connection error: {e}")

# TAB 6: Gmail Sync
with tab6:
    st.header("Gmail → Expenses")
    st.caption("Sync expenses from Gmail: filter receipts and payments; the same LLM extracts and saves them.")

    try:
        status_resp = requests.get(f"{get_api_url()}/gmail/status", timeout=5)
        if status_resp.status_code != 200:
            st.warning("Could not check Gmail status.")
        else:
            gs = status_resp.json()
            if gs.get("configured"):
                st.success("✅ Gmail is configured. You can sync below.")
            else:
                st.info(
                    "**One-time setup:**\n"
                    "1. Google Cloud Console → enable Gmail API → create OAuth 2.0 credentials (Desktop).\n"
                    "2. Save the JSON as `backend/credentials.json`.\n"
                    "3. Run: `python backend/gmail_auth.py` and log in in the browser.\n"
                    "4. Refresh this page and sync."
                )
                if gs.get("error"):
                    st.caption(f"Error: {gs['error']}")

        st.subheader("Sync now")
        default_query = "newer_than:7d (from:paypal.com OR from:amazon.com OR from:uber.com OR subject:receipt OR subject:payment OR subject:order)"
        query = st.text_area(
            "Gmail search query",
            value=default_query,
            height=80,
            help="Use Gmail search syntax: from:..., subject:..., newer_than:7d, etc.",
        )
        max_results = st.number_input("Max emails to process", min_value=5, max_value=100, value=30)
        if st.button("🔄 Sync Gmail", type="primary"):
            with st.spinner("Fetching and processing emails…"):
                try:
                    r = requests.post(
                        f"{get_api_url()}/gmail/sync",
                        json={"query": query, "max_results": max_results},
                        timeout=120,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        added = data.get("added", 0)
                        errs = data.get("errors", [])
                        if added:
                            st.success(f"Added **{added}** expense(s) from Gmail.")
                        else:
                            st.info("No new expenses added (all matching emails already processed or none matched).")
                        if errs:
                            st.warning("Some messages had errors:")
                            for e in errs[:10]:
                                st.caption(e)
                    else:
                        st.error(r.text or f"Error {r.status_code}")
                except Exception as e:
                    st.error(str(e))
    except Exception as e:
        st.error(f"Connection error: {e}")

# TAB 7: Review Queue (low-confidence correction workflow)
with tab7:
    st.header("✏️ Review Queue")
    st.caption("Expenses that need verification (low confidence or not yet verified). Edit and verify or reject.")

    try:
        response = requests.get(f"{get_api_url()}/expenses/review", timeout=10)
        if response.status_code != 200:
            st.error("Failed to fetch review queue")
        else:
            items = response.json()
            if not items:
                st.info("No expenses in the review queue. All expenses are verified or confidence is high.")
            else:
                st.metric("Needs review", len(items))
                for ex in items:
                    eid = ex.get("id")
                    with st.expander(f"ID {eid} — {ex.get('date', '')} · {ex.get('category', '')} · {ex.get('amount')} {ex.get('currency', 'USD')}", expanded=True):
                        st.caption("Raw text")
                        st.text(ex.get("raw_text") or "")
                        c_score = ex.get("confidence_score")
                        st.caption(f"Confidence: {c_score if c_score is not None else 'N/A'}")
                        if ex.get("extracted_json"):
                            try:
                                st.json(json.loads(ex["extracted_json"]) if isinstance(ex["extracted_json"], str) else ex["extracted_json"])
                            except Exception:
                                st.text(ex.get("extracted_json"))
                        col_a, col_b = st.columns(2)
                        with col_a:
                            new_date = st.text_input("Date", value=ex.get("date") or "", key=f"rev_date_{eid}")
                            new_category = st.text_input("Category", value=ex.get("category") or "", key=f"rev_cat_{eid}")
                            new_subcategory = st.text_input("Subcategory", value=ex.get("subcategory") or "", key=f"rev_sub_{eid}")
                        with col_b:
                            new_amount = st.number_input("Amount", value=float(ex.get("amount") or 0), min_value=0.0, step=0.01, key=f"rev_amt_{eid}")
                            new_currency = st.text_input("Currency", value=ex.get("currency") or "USD", key=f"rev_cur_{eid}")
                            new_merchant = st.text_input("Merchant", value=ex.get("merchant") or "", key=f"rev_merchant_{eid}")
                        btn_col1, btn_col2, _ = st.columns([1, 1, 2])
                        with btn_col1:
                            if st.button("✓ Verify / Update", type="primary", key=f"verify_{eid}"):
                                payload = {
                                    "date": new_date,
                                    "category": new_category,
                                    "subcategory": new_subcategory if new_subcategory else None,
                                    "amount": new_amount,
                                    "currency": new_currency,
                                    "merchant": new_merchant.strip() if new_merchant else None,
                                }
                                r = requests.post(f"{get_api_url()}/expenses/{eid}/verify", json=payload, timeout=5)
                                if r.status_code == 200:
                                    st.success("Verified")
                                    st.rerun()
                                else:
                                    st.error(r.text or str(r.status_code))
                        with btn_col2:
                            if st.button("🗑 Reject (delete)", key=f"reject_{eid}"):
                                r = requests.delete(f"{get_api_url()}/expenses/{eid}", timeout=5)
                                if r.status_code == 200:
                                    st.success("Removed")
                                    st.rerun()
                                else:
                                    st.error(r.text or str(r.status_code))
    except Exception as e:
        st.error(f"Connection error: {e}")

# TAB 8: Recurring Expenses
with tab8:
    st.header("🔄 Recurring Expenses")
    st.caption("Detected subscriptions, rent, utilities, and other repeating bills. Recompute to refresh from your expense history.")

    try:
        if st.button("🔄 Recompute recurring", type="primary"):
            with st.spinner("Scanning expenses for patterns…"):
                r = requests.post(f"{get_api_url()}/insights/recurring/recompute", timeout=60)
                if r.status_code == 200:
                    data = r.json()
                    st.success(f"Found **{data.get('count', 0)}** recurring pattern(s).")
                    st.rerun()
                else:
                    st.error(r.text or str(r.status_code))

        response = requests.get(f"{get_api_url()}/insights/recurring", timeout=10)
        if response.status_code != 200:
            st.error("Failed to load recurring insights.")
        else:
            items = response.json()
            if not items:
                st.info("No recurring expenses detected yet. Add more expenses and click **Recompute recurring** to detect subscriptions, rent, utilities, etc.")
            else:
                st.metric("Recurring items", len(items))
                df = pd.DataFrame([{
                    "Merchant": (x.get("merchant") or x.get("category") or "—"),
                    "Category": x.get("category", "—"),
                    "Amount": f"{x.get('currency', 'USD')} {float(x.get('typical_amount', 0)):.2f}",
                    "Frequency": x.get("frequency_type", "—"),
                    "Confidence": f"{float(x.get('confidence_score') or 0):.0%}",
                    "Next expected": x.get("next_expected_date") or "—",
                    "Count": x.get("expense_count", 0),
                } for x in items])
                st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Connection error: {e}")

# TAB 9: Advanced Insights
with tab9:
    st.header("📋 Insights")
    st.caption("Structured behavioral insights from your expense history. Choose date range and view KPIs, trends, and anomalies.")

    try:
        from datetime import datetime, timedelta
        end_default = datetime.now()
        start_default = end_default - timedelta(days=30)
        col_d1, col_d2, col_d3 = st.columns([1, 1, 2])
        with col_d1:
            start_date = st.date_input("Start date", value=start_default.date(), key="ins_start")
        with col_d2:
            end_date = st.date_input("End date", value=end_default.date(), key="ins_end")
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        params = f"start_date={start_str}&end_date={end_str}"

        # Budget Health score
        try:
            r_health = requests.get(f"{get_api_url()}/insights/health-score", timeout=5)
            if r_health.status_code == 200:
                health = r_health.json()
                score = health.get("score", 0)
                st.subheader("Budget Health")
                st.metric("Health score", f"{score:.0f} / 100", "Based on adherence, overspend frequency, volatility, recurring burden, discretionary ratio, anomalies")
                with st.expander("Score breakdown"):
                    st.json(health.get("metrics") or {})
            else:
                st.caption("Health score unavailable.")
        except Exception:
            st.caption("Health score unavailable.")

        st.divider()
        # Overview
        r_overview = requests.get(f"{get_api_url()}/insights/overview?{params}", timeout=10)
        if r_overview.status_code != 200:
            st.error("Failed to load overview.")
        else:
            ov = r_overview.json()
            st.subheader("KPI cards")
            k1, k2, k3, k4, k5 = st.columns(5)
            with k1:
                st.metric("Total spend", f"${ov.get('total_spend', 0):,.2f}")
            with k2:
                st.metric("Transactions", ov.get("transaction_count", 0))
            with k3:
                st.metric("Avg transaction", f"${ov.get('average_transaction_amount', 0):,.2f}")
            with k4:
                delta = ov.get("spend_delta")
                delta_p = ov.get("spend_delta_percent")
                if delta is not None and delta_p is not None:
                    st.metric("Vs previous period", f"{delta_p:+.1f}%", delta=f"${delta:+,.2f}")
                else:
                    st.metric("Vs previous period", "—", "No prior period")
            with k5:
                burden = ov.get("recurring_burden_percent")
                st.metric("Recurring burden", f"{burden}%" if burden is not None else "—", "of spend")

            st.divider()
            st.subheader("Category breakdown")
            if ov.get("category_breakdown"):
                df_cat = pd.DataFrame(ov["category_breakdown"])
                st.dataframe(df_cat, use_container_width=True, hide_index=True)
            else:
                st.caption("No category data for this period.")
            r_ins_cat = requests.get(f"{get_api_url()}/insights/categories", params={"start_date": start_str, "end_date": end_str}, timeout=10)
            if r_ins_cat.status_code == 200:
                ins_cat = r_ins_cat.json()
                if ins_cat:
                    with st.expander("Category breakdown (insights/categories API)"):
                        if isinstance(ins_cat, list):
                            st.dataframe(pd.DataFrame(ins_cat), use_container_width=True, hide_index=True)
                        elif isinstance(ins_cat, dict):
                            st.json(ins_cat)
                        else:
                            st.write(ins_cat)

            if ov.get("biggest_category_increase"):
                b = ov["biggest_category_increase"]
                st.info(f"**Biggest category increase:** {b.get('category', '')} — ${b.get('delta', 0):+,.2f} ({b.get('delta_percent', 0):+.1f}%)")

            st.subheader("Weekday vs weekend")
            ww = ov.get("weekday_vs_weekend") or {}
            st.write(f"Weekday total: **${ww.get('weekday_total', 0):,.2f}** · Weekend total: **${ww.get('weekend_total', 0):,.2f}**")

            if ov.get("highest_spending_day"):
                h = ov["highest_spending_day"]
                st.caption(f"Highest spending day: **{h.get('date')}** — ${h.get('total', 0):,.2f}")

            st.subheader("Top merchants")
            if ov.get("top_merchants"):
                st.dataframe(pd.DataFrame(ov["top_merchants"]), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Trends (last 6 months)")
        r_trends = requests.get(f"{get_api_url()}/insights/trends?months=6", timeout=10)
        if r_trends.status_code == 200:
            tr = r_trends.json()
            if tr.get("trends"):
                df_t = pd.DataFrame([{"Month": t["label"], "Total": t["total_spend"], "Count": t["transaction_count"]} for t in tr["trends"]])
                st.dataframe(df_t, use_container_width=True, hide_index=True)
            else:
                st.caption("No trend data.")
        else:
            st.caption("Could not load trends.")

        st.divider()
        st.subheader("Month forecast")
        try:
            r_fc = requests.get(f"{get_api_url()}/forecast/month", timeout=5)
            r_pred = requests.get(f"{get_api_url()}/alerts/predictive", timeout=5)
            if r_fc.status_code == 200:
                fc = r_fc.json()
                proj = fc.get("projected_total", 0)
                so_far = fc.get("spend_so_far_total", 0)
                de, dm = fc.get("days_elapsed", 0), fc.get("days_in_month", 30)
                st.metric("Projected month-end total", f"${proj:,.2f}", f"Spend so far: ${so_far:,.2f} ({de}/{dm} days)")
                if r_pred.status_code == 200:
                    pred = r_pred.json()
                    for a in pred.get("alerts", []):
                        st.warning(a.get("message", ""))
            else:
                st.caption("Forecast unavailable.")
        except Exception:
            st.caption("Forecast unavailable.")

        st.divider()
        st.subheader("Recommendations")
        try:
            r_rec = requests.get(f"{get_api_url()}/insights/recommendations", timeout=5)
            if r_rec.status_code == 200:
                data = r_rec.json()
                recs = data.get("recommendations", [])
                if recs:
                    for r in recs:
                        with st.container():
                            st.markdown(f"**{r.get('title', '')}**")
                            st.caption(f"Metric: {r.get('metric_cited', '')} = {r.get('value')}")
                            st.write(r.get("suggestion", ""))
                            st.divider()
                else:
                    st.caption("No recommendations right now. Keep up the good work!")
            else:
                st.caption("Recommendations unavailable.")
        except Exception:
            st.caption("Recommendations unavailable.")

        st.divider()
        st.subheader("Anomalous expenses")
        r_anom = requests.get(f"{get_api_url()}/insights/anomalies?{params}", timeout=10)
        if r_anom.status_code == 200:
            an = r_anom.json()
            if an.get("anomalies"):
                df_a = pd.DataFrame(an["anomalies"])
                st.dataframe(df_a, use_container_width=True, hide_index=True)
            else:
                st.caption("No anomalies detected for this period.")
        else:
            st.caption("Could not load anomalies.")

        st.divider()
        st.subheader("AI narrative (optional)")
        if st.button("Generate AI narrative from insights", key="ins_narrative"):
            with st.spinner("Generating narrative with Ollama…"):
                r_nar = requests.get(f"{get_api_url()}/insights/narrative?{params}", timeout=60)
                if r_nar.status_code == 200:
                    data = r_nar.json()
                    st.markdown("### Summary")
                    st.write(data.get("narrative", ""))
                else:
                    st.error(r_nar.text or "Failed")
    except Exception as e:
        st.error(f"Connection error: {e}")

# TAB 10: Ask AI (natural language query)
with tab10:
    st.header("🤖 Ask AI")
    st.caption("Ask questions about your expense history in plain language. Answers are based only on your recorded data.")

    question = st.text_input(
        "Your question",
        placeholder="e.g. How much did I spend on coffee last month? Show Uber expenses above 20 dollars. Which month had the highest grocery spend?",
        key="ask_ai_question",
        label_visibility="collapsed",
    )
    if st.button("Ask", type="primary", key="ask_ai_btn") and question:
        with st.spinner("Querying…"):
            try:
                r = requests.post(f"{get_api_url()}/ask", json={"question": question.strip()}, timeout=30)
                if r.status_code != 200:
                    st.error(r.text or f"Error {r.status_code}")
                else:
                    data = r.json()
                    if data.get("refused"):
                        st.warning(data.get("answer_text", "Request refused."))
                    else:
                        st.markdown("### Answer")
                        st.markdown(data.get("answer_text", ""))
                    with st.expander("Parsed filters (transparency)"):
                        st.json(data.get("parsed_query") or {})
                    if data.get("rows"):
                        st.subheader("Supporting data")
                        df = pd.DataFrame(data["rows"])
                        display_cols = [c for c in ["date", "category", "amount", "currency", "merchant", "raw_text"] if c in df.columns]
                        st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
                    elif not data.get("refused") and not data.get("rows"):
                        st.caption("No matching transactions.")
            except Exception as e:
                st.error(f"Connection error: {e}")
    else:
        st.caption("Examples: _How much did I spend on coffee last month?_ · _Show Uber expenses above $20_ · _Which month had the highest grocery spend?_")

# TAB 11: Goals
with tab11:
    st.header("🎯 Financial Goals")
    st.caption("Define savings targets, spending reductions, or category caps. Track progress and suggested pace.")

    try:
        status_filter = st.selectbox("Status", ["active", "completed", "all"], key="goals_status")
        r = requests.get(f"{get_api_url()}/goals", params={"status": status_filter}, timeout=10)
        if r.status_code != 200:
            st.error(r.text or f"Error {r.status_code}")
        else:
            goals = r.json() if isinstance(r.json(), list) else []
            if goals:
                for g in goals:
                    gid = g.get("id")
                    with st.expander(f"{g.get('description') or g.get('goal_type', 'Goal')} — {g.get('goal_type', '')} (${g.get('current_amount', 0):,.2f} / ${g.get('target_amount', 0):,.2f})"):
                        dist = g.get("distance") or {}
                        if dist:
                            st.caption(f"Distance: {dist}")
                        if g.get("suggested_reduction_per_month") is not None:
                            st.caption(f"Suggested per month: ${g['suggested_reduction_per_month']:,.2f} · per week: ${g.get('suggested_reduction_per_week') or 0:,.2f}")
                        col_edit, col_del, _ = st.columns([1, 1, 4])
                        with col_edit:
                            if st.button("Edit", key=f"edit_goal_{gid}"):
                                st.session_state["editing_goal"] = g
                                st.rerun()
                        with col_del:
                            if st.button("Delete", key=f"del_goal_{gid}"):
                                try:
                                    dr = requests.delete(f"{get_api_url()}/goals/{gid}", timeout=10)
                                    if dr.status_code in (200, 204):
                                        st.success("Goal deleted.")
                                    else:
                                        st.error(dr.text or f"Error {dr.status_code}")
                                except Exception as ex:
                                    st.error(str(ex))
                                st.rerun()
                        with st.expander("Raw goal JSON"):
                            st.json(g)
            else:
                st.info("No goals yet. Create one below.")
    except Exception as e:
        st.error(f"Connection error: {e}")

    if st.session_state.get("editing_goal"):
        eg = st.session_state["editing_goal"]
        eg_id = eg.get("id")
        st.subheader("Edit goal")
        with st.form("edit_goal_form"):
            gt_choices = ["savings_target", "spending_reduction", "category_cap"]
            gt_index = gt_choices.index(eg["goal_type"]) if eg.get("goal_type") in gt_choices else 0
            edit_goal_type = st.selectbox("Goal type", gt_choices, index=gt_index, key="edit_goal_type")
            edit_target = st.number_input("Target amount", min_value=0.0, value=float(eg.get("target_amount", 0)), step=50.0, key="edit_goal_target")
            edit_current = st.number_input("Current amount", min_value=0.0, value=float(eg.get("current_amount", 0)), step=50.0, key="edit_goal_current")
            try:
                edit_date_val = datetime.strptime(eg["target_date"][:10], "%Y-%m-%d").date() if eg.get("target_date") else None
            except Exception:
                edit_date_val = None
            edit_date = st.date_input("Target date (optional)", value=edit_date_val, key="edit_goal_date")
            edit_category = st.text_input("Category (optional)", value=eg.get("category") or "", key="edit_goal_cat")
            edit_description = st.text_input("Description", value=eg.get("description") or "", key="edit_goal_desc")
            edit_status = st.selectbox("Status", ["active", "completed"], index=0 if (eg.get("status") or "active") == "active" else 1, key="edit_goal_status")
            col1, col2 = st.columns(2)
            with col1:
                submit_edit = st.form_submit_button("Save changes")
            with col2:
                cancel_edit = st.form_submit_button("Cancel")
        if submit_edit and eg_id is not None:
            try:
                payload = {
                    "goal_type": edit_goal_type,
                    "target_amount": float(edit_target),
                    "current_amount": float(edit_current),
                    "target_date": (edit_date.isoformat() if edit_date else None),
                    "category": edit_category.strip() or None,
                    "description": edit_description.strip() or None,
                    "status": edit_status,
                }
                r_put = requests.put(f"{get_api_url()}/goals/{eg_id}", json=payload, timeout=10)
                if r_put.status_code == 200:
                    st.success("Goal updated.")
                    del st.session_state["editing_goal"]
                    st.rerun()
                else:
                    st.error(r_put.text or f"Error {r_put.status_code}")
            except Exception as e:
                st.error(str(e))
        if cancel_edit:
            del st.session_state["editing_goal"]
            st.rerun()
        st.divider()

    st.subheader("Create goal")
    with st.form("create_goal_form"):
        goal_type = st.selectbox("Goal type", ["savings_target", "spending_reduction", "category_cap"], key="goal_type")
        target_amount = st.number_input("Target amount", min_value=0.0, value=1000.0, step=50.0, key="goal_target")
        current_amount = st.number_input("Current amount", min_value=0.0, value=0.0, step=50.0, key="goal_current")
        target_date = st.date_input("Target date (optional)", value=None, key="goal_date")
        category = st.text_input("Category (optional, for spending_reduction / category_cap)", value="", key="goal_cat")
        description = st.text_input("Description", value="", key="goal_desc")
        submitted = st.form_submit_button("Create goal")
        if submitted:
            try:
                payload = {
                    "goal_type": goal_type,
                    "target_amount": float(target_amount),
                    "current_amount": float(current_amount),
                    "target_date": target_date.isoformat() if target_date else None,
                    "category": category.strip() or None,
                    "description": description.strip() or None,
                }
                r = requests.post(f"{get_api_url()}/goals", json=payload, timeout=10)
                if r.status_code == 200:
                    st.success("Goal created.")
                    st.rerun()
                else:
                    st.error(r.text or f"Error {r.status_code}")
            except Exception as e:
                st.error(str(e))

# TAB 12: Affordability Check
with tab12:
    st.header("💳 Can I Afford This?")
    st.caption("Check whether a purchase fits your budget, limits, projected spend, and goals.")

    amount = st.number_input("Amount", min_value=0.0, value=50.0, step=1.0, key="aff_amount")
    category = st.text_input("Category", value="food", placeholder="e.g. food, transport", key="aff_cat")
    merchant = st.text_input("Merchant (optional)", value="", placeholder="e.g. Starbucks", key="aff_merchant")
    if st.button("Check affordability", type="primary", key="aff_btn"):
        try:
            payload = {"amount": float(amount), "category": category.strip() or None, "merchant": merchant.strip() or None}
            r = requests.post(f"{get_api_url()}/affordability/check", json=payload, timeout=10)
            if r.status_code != 200:
                st.error(r.text or f"Error {r.status_code}")
            else:
                data = r.json()
                if data.get("can_afford"):
                    st.success("✅ Yes — you can afford this purchase.")
                else:
                    st.error("❌ This purchase would exceed your limits or conflict with goals.")
                st.markdown("**Recommendation:** " + (data.get("recommendation_text") or ""))
                for reason in data.get("reasons", []):
                    st.caption(f"• {reason}")
                if data.get("projected_impact"):
                    with st.expander("Projected impact"):
                        st.json(data["projected_impact"])
                if data.get("budget_impact"):
                    with st.expander("Budget impact"):
                        st.json(data["budget_impact"])
                if data.get("goal_impact"):
                    with st.expander("Goal impact"):
                        st.json(data["goal_impact"])
        except Exception as e:
            st.error(f"Connection error: {e}")

# TAB 13: Simulator
with tab13:
    st.header("🔮 Scenario Simulator")
    st.caption("Test hypothetical changes without affecting real data. See how adjustments would impact projected spending, limits, and goals.")

    adjustments = []
    with st.expander("Adjustments", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            if st.checkbox("Reduce category spend by %", key="sim_reduce_pct"):
                rcat = st.text_input("Category", value="transport", key="sim_rcat")
                rval = st.slider("Percent to reduce", 0, 100, 20, key="sim_rpct")
                adjustments.append({"type": "reduce_category_percent", "category": rcat.strip() or "other", "value": float(rval)})
            if st.checkbox("Remove recurring subscription", key="sim_remove_rec"):
                rmerchant = st.text_input("Merchant name", value="", placeholder="e.g. Netflix", key="sim_rmerchant")
                if rmerchant.strip():
                    adjustments.append({"type": "remove_recurring_merchant", "merchant": rmerchant.strip()})
            if st.checkbox("Add one-time expense", key="sim_add_one"):
                acat = st.text_input("Category", value="travel", key="sim_acat")
                aamt = st.number_input("Amount", min_value=0.0, value=300.0, key="sim_aamt")
                adjustments.append({"type": "add_one_time_expense", "category": (acat or "other").strip(), "amount": float(aamt)})
        with c2:
            if st.checkbox("Change category cap", key="sim_cap"):
                cap_cat = st.text_input("Category", value="food", key="sim_cap_cat")
                cap_amt = st.number_input("New monthly cap", min_value=0.0, value=400.0, key="sim_cap_amt")
                adjustments.append({"type": "change_category_cap", "category": (cap_cat or "other").strip(), "amount": float(cap_amt)})
            if st.checkbox("Save fixed amount per week", key="sim_save"):
                save_val = st.number_input("Amount per week", min_value=0.0, value=50.0, key="sim_save_val")
                adjustments.append({"type": "save_fixed_per_week", "value": float(save_val)})

    if st.button("Run simulation", type="primary", key="sim_run"):
        if not adjustments:
            st.warning("Add at least one adjustment above, then run again.")
        else:
            try:
                r = requests.post(
                    f"{get_api_url()}/simulate",
                    json={"adjustments": adjustments},
                    timeout=15,
                )
                if r.status_code != 200:
                    st.error(r.text or f"Error {r.status_code}")
                else:
                    data = r.json()
                    base = data.get("baseline_summary") or {}
                    sim = data.get("simulated_summary") or {}
                    delta = data.get("delta_summary") or {}

                    st.subheader("Comparison")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Baseline projected", f"${base.get('projected_total', 0):,.2f}", "current month")
                    with col2:
                        st.metric("Simulated projected", f"${sim.get('projected_total', 0):,.2f}", "after adjustments")
                    with col3:
                        chg = delta.get("total_change", 0)
                        st.metric("Delta", f"${chg:,.2f}", "savings" if chg < 0 else "increase")

                    st.subheader("Before vs after by category")
                    by_cat_base = {k: v for k, v in (base.get("by_category") or {}).items() if k != "total"}
                    by_cat_sim = {k: v for k, v in (sim.get("by_category") or {}).items() if k != "total"}
                    if by_cat_base or by_cat_sim:
                        cats = sorted(set(by_cat_base.keys()) | set(by_cat_sim.keys()))
                        if cats:
                            fig = go.Figure()
                            fig.add_trace(go.Bar(name="Baseline", x=cats, y=[by_cat_base.get(c, 0) for c in cats], marker_color="#3b82f6"))
                            fig.add_trace(go.Bar(name="Simulated", x=cats, y=[by_cat_sim.get(c, 0) for c in cats], marker_color="#22c55e"))
                            fig.update_layout(barmode="group", xaxis_title="Category", yaxis_title="Amount", margin=dict(t=20), height=320)
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.caption("No category breakdown (add expenses or limits for categories).")

                    if data.get("projected_limit_changes"):
                        with st.expander("Limit impact"):
                            for lim in data["projected_limit_changes"]:
                                over_b = lim.get("baseline_over") or 0
                                over_s = lim.get("simulated_over") or 0
                                st.caption(f"**{lim.get('category', '')}** — Baseline over: ${over_b:,.2f} → Simulated over: ${over_s:,.2f}")
                            st.json(data["projected_limit_changes"])
                    if data.get("goal_impact"):
                        with st.expander("Goal impact"):
                            for g in data["goal_impact"]:
                                st.caption(f"**{g.get('description', '')}** — Simulated spend: ${g.get('simulated_projected_spend', 0):,.2f}; improves: {g.get('improves', 'N/A')}")
                            st.json(data["goal_impact"])
            except Exception as e:
                st.error(f"Connection error: {e}")

# TAB 14: Wealth Hub
with tab14:
    st.header("🏦 Wealth Hub")
    st.caption("Salary, investments, portfolio, cashflow, projections, and grounded suggestions.")
    wh_year = datetime.now().year
    wh_month = datetime.now().month
    wh_sub1, wh_sub2, wh_sub3, wh_sub4, wh_sub5, wh_sub6 = st.tabs([
        "💰 Salary", "📈 Investments", "📊 Portfolio", "💵 Cashflow", "🔮 Projections", "💡 Suggestions"
    ])

    with wh_sub1:
        st.subheader("Salary / Income")
        try:
            r = requests.get(f"{get_api_url()}/wealth/salary/summary", params={"year": wh_year, "month": wh_month}, timeout=10)
            if r.status_code == 200:
                sm = r.json()
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Net income (month)", f"${sm.get('net_income', 0):,.2f}", "")
                with c2:
                    st.metric("Bonus", f"${sm.get('bonus_total', 0):,.2f}", "")
                with c3:
                    st.metric("Records", sm.get('record_count', 0), "")
            else:
                st.caption("Could not load summary.")
        except Exception as e:
            st.caption(f"Error: {e}")
        with st.expander("Add salary record"):
            with st.form("salary_form"):
                s_date = st.text_input("Date", value=datetime.now().strftime("%Y-%m-%d"), key="salary_date")
                s_source = st.text_input("Source", value="Salary", key="salary_source")
                s_gross = st.number_input("Gross", min_value=0.0, value=5000.0, step=100.0, key="salary_gross")
                s_deductions = st.number_input("Deductions", min_value=0.0, value=0.0, step=50.0, key="salary_ded")
                s_bonus = st.number_input("Bonus", min_value=0.0, value=0.0, step=100.0, key="salary_bonus")
                s_notes = st.text_input("Notes", value="", key="salary_notes")
                if st.form_submit_button("Add"):
                    net = s_gross - s_deductions
                    payload = {"date": s_date[:10], "source": s_source, "gross_amount": s_gross, "deductions": s_deductions, "net_amount": net, "bonus_amount": s_bonus, "notes": s_notes or None}
                    try:
                        rr = requests.post(f"{get_api_url()}/wealth/salary", json=payload, timeout=10)
                        if rr.status_code == 200:
                            st.success("Added.")
                            st.rerun()
                        else:
                            st.error(rr.text)
                    except Exception as ex:
                        st.error(str(ex))
        try:
            r_list = requests.get(f"{get_api_url()}/wealth/salary", params={"year": wh_year, "month": wh_month}, timeout=10)
            if r_list.status_code == 200 and r_list.json():
                df_sal = pd.DataFrame(r_list.json())
                st.dataframe(df_sal, use_container_width=True, hide_index=True)
        except Exception:
            st.caption("No salary records or error loading.")

    with wh_sub2:
        st.subheader("Investment transactions")
        with st.expander("Add transaction"):
            with st.form("inv_form"):
                inv_ticker = st.text_input("Ticker", value="AAPL", key="inv_ticker")
                inv_name = st.text_input("Stock name (optional)", value="", key="inv_name")
                inv_type = st.selectbox("Type", ["BUY", "SELL", "DIVIDEND"], key="inv_type")
                inv_qty = st.number_input("Quantity", min_value=0.0, value=10.0, step=1.0, key="inv_qty")
                inv_price = st.number_input("Price", min_value=0.0, value=150.0, step=0.01, key="inv_price")
                inv_fees = st.number_input("Fees", min_value=0.0, value=0.0, step=0.01, key="inv_fees")
                inv_date = st.text_input("Date", value=datetime.now().strftime("%Y-%m-%d"), key="inv_date")
                inv_broker = st.text_input("Broker (optional)", value="", key="inv_broker")
                inv_notes = st.text_input("Notes", value="", key="inv_notes")
                if st.form_submit_button("Add"):
                    payload = {"ticker": inv_ticker.strip().upper(), "stock_name": inv_name.strip() or None, "transaction_type": inv_type, "quantity": inv_qty, "price": inv_price, "fees": inv_fees, "date": inv_date[:10], "broker": inv_broker.strip() or None, "notes": inv_notes.strip() or None}
                    try:
                        rr = requests.post(f"{get_api_url()}/wealth/investments", json=payload, timeout=10)
                        if rr.status_code == 200:
                            st.success("Added.")
                            st.rerun()
                        else:
                            st.error(rr.text)
                    except Exception as ex:
                        st.error(str(ex))
        try:
            r_inv = requests.get(f"{get_api_url()}/wealth/investments", timeout=10)
            if r_inv.status_code == 200 and r_inv.json():
                st.dataframe(pd.DataFrame(r_inv.json()), use_container_width=True, hide_index=True)
            else:
                st.caption("No transactions.")
        except Exception as e:
            st.caption(f"Error: {e}")

    with wh_sub3:
        st.subheader("Portfolio")
        try:
            r_port = requests.get(f"{get_api_url()}/wealth/portfolio", timeout=10)
            if r_port.status_code == 200:
                data = r_port.json()
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Current value", f"${data.get('total_current_value', 0):,.2f}", "")
                with m2:
                    st.metric("Total invested", f"${data.get('total_invested', 0):,.2f}", "")
                with m3:
                    st.metric("Realized P&L", f"${data.get('total_realized_pnl', 0):,.2f}", "")
                with m4:
                    st.metric("Unrealized P&L", f"${data.get('total_unrealized_pnl', 0):,.2f}", "")
                holdings = data.get("holdings") or []
                if holdings:
                    df_h = pd.DataFrame(holdings)
                    st.dataframe(df_h, use_container_width=True, hide_index=True)
                    if "ticker" in df_h.columns and "total_invested" in df_h.columns and df_h["total_invested"].sum() > 0:
                        fig = px.pie(df_h, values="total_invested", names="ticker", title="Allocation")
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No holdings. Add BUY transactions in Investments.")
            else:
                st.error(r_port.text or "Failed to load portfolio.")
        except Exception as e:
            st.error(f"Connection error: {e}")

    with wh_sub4:
        st.subheader("Cashflow")
        try:
            r_cf = requests.get(f"{get_api_url()}/wealth/cashflow", params={"year": wh_year, "month": wh_month}, timeout=10)
            if r_cf.status_code == 200:
                cf = r_cf.json()
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Income", f"${cf.get('total_income', 0):,.2f}", "")
                with c2:
                    st.metric("Expenses", f"${cf.get('total_expenses', 0):,.2f}", "")
                with c3:
                    st.metric("Invested", f"${cf.get('total_invested', 0):,.2f}", "")
                with c4:
                    st.metric("Free cash", f"${cf.get('free_cash', 0):,.2f}", "")
                st.caption(f"Savings ratio: {cf.get('savings_ratio', 0):.1f}% · Investment ratio: {cf.get('investment_ratio', 0):.1f}% · Expense ratio: {cf.get('expense_ratio', 0):.1f}%")
            else:
                st.caption("Could not load cashflow.")
        except Exception as e:
            st.caption(f"Error: {e}")

    with wh_sub5:
        st.subheader("Projections")
        mode = st.selectbox("Portfolio growth", ["no_growth", "conservative", "moderate", "aggressive"], index=2, key="proj_mode")
        try:
            r_proj = requests.get(f"{get_api_url()}/wealth/projections", params={"year": wh_year, "month": wh_month, "portfolio_growth_mode": mode}, timeout=10)
            if r_proj.status_code == 200:
                p = r_proj.json()
                st.metric("Projected EOM expenses", f"${p.get('projected_end_of_month_expenses', 0):,.2f}", "")
                st.metric("Projected monthly surplus", f"${p.get('projected_monthly_surplus', 0):,.2f}", "")
                st.metric("Projected yearly invested", f"${p.get('projected_yearly_invested', 0):,.2f}", "")
                pp = p.get("portfolio_projection") or {}
                st.caption(f"Portfolio projection: 6m ${pp.get('6m', 0):,.2f} · 1y ${pp.get('1y', 0):,.2f} · 3y ${pp.get('3y', 0):,.2f} ({mode})")
            else:
                st.caption("Could not load projections.")
        except Exception as e:
            st.caption(f"Error: {e}")

    with wh_sub6:
        st.subheader("Suggestions")
        try:
            r_sug = requests.get(f"{get_api_url()}/wealth/suggestions", params={"year": wh_year, "month": wh_month}, timeout=10)
            if r_sug.status_code == 200:
                sug_data = r_sug.json()
                suggestions_list = sug_data.get("suggestions") or []
                if suggestions_list:
                    for s in suggestions_list:
                        sev = s.get("severity", "medium")
                        if sev == "high":
                            st.error(f"**{s.get('title', '')}** — {s.get('message', '')}")
                        elif sev == "medium":
                            st.warning(f"**{s.get('title', '')}** — {s.get('message', '')}")
                        else:
                            st.info(f"**{s.get('title', '')}** — {s.get('message', '')}")
                else:
                    st.success("No suggestions; metrics look healthy.")
            else:
                st.caption("Could not load suggestions.")
        except Exception as e:
            st.caption(f"Error: {e}")

    st.divider()
    st.subheader("Stock lookup & affordability")
    ticker_lookup = st.text_input("Ticker", value="AAPL", key="stock_ticker")
    if st.button("Stock details", key="stock_btn"):
        try:
            r_stock = requests.get(f"{get_api_url()}/wealth/stock/details", params={"ticker": ticker_lookup.strip()}, timeout=10)
            if r_stock.status_code == 200:
                d = r_stock.json()
                st.json(d)
            else:
                st.error(r_stock.text)
        except Exception as ex:
            st.error(str(ex))
    qty_aff = st.number_input("Quantity (for affordability)", min_value=0.0, value=10.0, key="aff_qty")
    price_aff = st.number_input("Price per share", min_value=0.0, value=150.0, key="aff_price")
    if st.button("Can I buy this?", type="primary", key="aff_stock_btn"):
        try:
            r_aff = requests.post(f"{get_api_url()}/wealth/stock/affordability", json={"ticker": ticker_lookup.strip().upper(), "quantity": qty_aff, "price_per_share": price_aff}, timeout=10)
            if r_aff.status_code == 200:
                a = r_aff.json()
                if a.get("affordable"):
                    st.success(a.get("message", ""))
                else:
                    st.warning(a.get("message", ""))
                for reason in a.get("reasons", []):
                    st.caption(f"• {reason}")
            else:
                st.error(r_aff.text)
        except Exception as ex:
            st.error(str(ex))

# Sidebar
with st.sidebar:
    st.header("Settings")
    api_input = st.text_input(
        "Backend API URL",
        value=st.session_state.get("api_url", _DEFAULT_API),
        placeholder="http://127.0.0.1:8000",
        help="Change if the backend runs on another host or port.",
        key="api_url_input",
    )
    if api_input and api_input != st.session_state.get("api_url"):
        st.session_state["api_url"] = api_input.rstrip("/")
        st.rerun()

    st.markdown("---")
    st.subheader("Status")
    st.caption("Time")
    st.code(datetime.now().strftime("%Y-%m-%d %H:%M"), language=None)
    st.caption("API")
    try:
        response = requests.get(f"{get_api_url()}/", timeout=3)
        if response.status_code == 200:
            st.success("Connected")
        else:
            st.error("API Error")
    except Exception:
        st.error("Not connected")

    with st.expander("API endpoints check"):
        st.caption("Hit key backend routes to verify connectivity.")
        base = get_api_url()
        endpoints = [
            ("GET", "/"),
            ("GET", "/expenses"),
            ("GET", "/limits"),
            ("GET", "/limits/status"),
            ("GET", "/forecast/month"),
            ("GET", "/forecast/categories"),
            ("GET", "/insights/overview"),
            ("GET", "/insights/categories"),
            ("GET", "/insights/health-score"),
            ("GET", "/goals"),
            ("GET", "/gmail/status"),
            ("GET", "/wealth/salary/summary"),
            ("GET", "/wealth/portfolio"),
            ("GET", "/wealth/cashflow"),
            ("GET", "/wealth/suggestions"),
        ]
        for method, path in endpoints:
            try:
                r = requests.get(f"{base}{path}", timeout=3) if method == "GET" else None
                ok = r is not None and r.status_code == 200
                st.write(f"{'✅' if ok else '❌'} {method} {path}")
            except Exception:
                st.write(f"❌ {method} {path}")

    st.markdown("---")
    st.subheader("About")
    st.markdown("""
    **Stack**
    - Ollama (LLM) · Whisper (voice)
    - SQLite · FastAPI · Streamlit
    - BI: Plotly + Power BI export

    *Runs locally.*
    """)
