import streamlit as st
import requests
import pandas as pd
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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "➕ Add", "📊 View", "📈 Summary", "📉 Dashboard", "🔔 Limits", "📧 Gmail"
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

    st.markdown("---")
    st.subheader("About")
    st.markdown("""
    **Stack**
    - Ollama (LLM) · Whisper (voice)
    - SQLite · FastAPI · Streamlit
    - BI: Plotly + Power BI export

    *Runs locally.*
    """)
