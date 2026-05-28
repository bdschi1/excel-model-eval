import os
import time
import uuid

import pandas as pd
import streamlit as st

# Load environment variables from .env file if present
try:
    import pathlib

    from dotenv import load_dotenv
    env_path = pathlib.Path(__file__).parent / '.env'
    load_dotenv(env_path, override=True)
except ImportError:
    pass  # python-dotenv not installed, use system env vars

from src.auditor import ModelAuditor
from src.dependency import DependencyEngine
from src.ingestion import ModelIngestor
from src.llm_analyzer import analyze_findings_with_llm
from src.reporting import ReportGenerator

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ModelLens",
    page_icon="\U0001f4ca",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    h1 { font-size: 2.4rem !important; font-weight: 600 !important; letter-spacing: -0.02em; color: #e2e8f0 !important; }
    h2 { font-size: 1.15rem !important; font-weight: 600 !important; color: #cbd5e1 !important; }
    h3 { font-size: 1.0rem !important; font-weight: 500 !important; color: #94a3b8 !important; }
    p, li, span { font-size: 0.875rem; color: #b0bec5; }

    /* captions */
    div[data-testid="stCaptionContainer"] { color: #8896a5 !important; }

    /* tighten Streamlit default block spacing */
    .block-container { padding-top: 1.5rem !important; padding-bottom: 0 !important; }
    .modellens-title { font-size: 3.2rem; font-weight: 700; letter-spacing: -0.03em; color: #e2e8f0; margin: 0 0 0.1rem 0; }
    div[data-testid="stMetric"] { background: #1e293b; border: 1px solid #334155; border-radius: 3px; padding: 10px 14px; }
    div[data-testid="stMetric"] label { font-size: 0.75rem !important; color: #94a3b8 !important; text-transform: uppercase; letter-spacing: 0.04em; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 1.25rem !important; color: #e2e8f0 !important; font-weight: 600 !important; }

    .metric-card {
        background-color: #1e293b;
        padding: 14px;
        border-radius: 3px;
        border-left: 3px solid #334155;
        color: #e2e8f0;
    }
    .metric-card label { color: #94a3b8; }
    .pass-card {
        background-color: #1a2e1a;
        padding: 14px;
        border-radius: 3px;
        border-left: 3px solid #6b8f71;
        font-size: 0.875rem;
        color: #a7c4a0;
    }
    .complexity-badge {
        font-size: 0.85rem;
        font-weight: 600;
        padding: 6px 14px;
        border-radius: 3px;
        color: white;
        text-align: center;
        margin-bottom: 8px;
        letter-spacing: 0.02em;
        display: inline-block;
    }
    .level-1 { background-color: #6b8f71; }
    .level-2 { background-color: #5b7fa5; }
    .level-3 { background-color: #a08c5b; }
    .level-4 { background-color: #b07a4f; }
    .level-5 { background-color: #9b4d4d; }

    /* tabs */
    button[data-baseweb="tab"] { font-size: 0.8rem !important; font-weight: 500 !important; letter-spacing: 0.02em; color: #94a3b8 !important; }

    /* expanders */
    details summary { font-size: 0.85rem !important; color: #cbd5e1 !important; }

    /* dataframes */
    .stDataFrame { font-size: 0.8rem; }

    /* download buttons */
    .stDownloadButton button { font-size: 0.8rem !important; border-radius: 3px !important; color: #cbd5e1 !important; }

    /* file uploader */
    div[data-testid="stFileUploader"] label { color: #94a3b8 !important; }
    </style>
""", unsafe_allow_html=True)

# --- AUTH ---
_required_pw = os.getenv("MODELLENS_PASSWORD")
if _required_pw:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("ModelLens")
        pw = st.text_input("Password", type="password")
        if pw == _required_pw:
            st.session_state.authenticated = True
            st.rerun()
        elif pw:
            st.error("Incorrect password")
        st.stop()

# --- MAIN INTERFACE ---
st.markdown('<div class="modellens-title">ModelLens</div>', unsafe_allow_html=True)
st.caption("Structural integrity analysis for institutional financial models — v2.2.0")
st.markdown(
    '<span style="font-size:0.78rem; color:#64748b;">'
    "Ingestion (values + formulas) &rarr; DAG construction &rarr; Audit (circular refs, plugs, broken accounting)"
    "</span>",
    unsafe_allow_html=True,
)

# --- CLEANUP STALE TEMP FILES ---
try:
    _temp_dir = "temp_data"
    if os.path.isdir(_temp_dir):
        _now = time.time()
        for _fname in os.listdir(_temp_dir):
            _fpath = os.path.join(_temp_dir, _fname)
            try:
                if os.path.isfile(_fpath) and (_now - os.path.getmtime(_fpath)) > 3600:
                    os.remove(_fpath)
            except OSError:
                pass
except OSError:
    pass

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["Audit", "History", "Guide", "Methodology"])

with tab1:
    uploaded_files = st.file_uploader(
        "Upload model(s)",
        type=["xlsx", "xlsm", "xls", "csv"],
        accept_multiple_files=True,
        help=".xlsx, .xlsm, .xls, .csv — CSVs lack formulas for logic auditing"
    )

    # Initialize session state (dict-based for multi-file)
    if 'audit_results' not in st.session_state:
        st.session_state.audit_results = {}
    if 'llm_result' not in st.session_state:
        st.session_state.llm_result = {}

    if uploaded_files:
        # Validate all files before audit
        for uploaded_file in uploaded_files:
            if uploaded_file.size > 50 * 1024 * 1024:
                st.error(f"{uploaded_file.name} exceeds 50 MB limit")
                st.stop()

        file_names = [f.name for f in uploaded_files]
        st.caption(f"Loaded: {', '.join(file_names)}")

        ticker_input = st.text_input(
            "Ticker (optional)",
            value="",
            max_chars=10,
            help="SEC ticker (e.g. NVDA). When provided, historical cells matching Core 6 GAAP line items are cross-checked against EDGAR.",
        ).strip().upper() or None

        if st.button("Run Audit", type="primary"):
            # Clear previous LLM results when starting new audit
            st.session_state.llm_result = {}
            st.session_state.audit_results = {}

            audit_id = uuid.uuid4().hex[:8]

            progress = st.progress(0)
            total = len(uploaded_files)

            for idx, uploaded_file in enumerate(uploaded_files):
                with st.spinner(f"Auditing {uploaded_file.name} ({idx + 1}/{total})..."):
                    try:
                        # Save file temporarily (basename prevents path traversal)
                        os.makedirs("temp_data", exist_ok=True)
                        safe_name = os.path.basename(uploaded_file.name)
                        temp_path = os.path.join("temp_data", safe_name)

                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        # --- PHASE 1: INGESTION ---
                        ingestor = ModelIngestor(temp_path, audit_id=audit_id)

                        is_csv = safe_name.lower().endswith('.csv')

                        if not ingestor.ingest():
                            st.error(f"Critical Failure: Could not ingest {uploaded_file.name}.")
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                            continue

                        # CSV empty/malformed check
                        if is_csv:
                            if (
                                not ingestor.sheets_values
                                or all(len(v) == 0 for v in ingestor.sheets_values.values())
                            ):
                                st.error("CSV appears empty or malformed")
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                                continue

                        # --- PHASE 2: DEPENDENCY MAPPING ---
                        if not is_csv:
                            engine = DependencyEngine(ingestor.sheets_formulas, audit_id=audit_id)
                            if ingestor.defined_names:
                                engine.set_defined_names(ingestor.defined_names)
                            engine.build_graph()
                            stats = engine.analyze_structure()
                        else:
                            engine = None
                            stats = {'circular_references': 0}

                        # --- PHASE 3: AUDITING ---
                        auditor = ModelAuditor(
                            ingestor, engine,
                            hidden_sheets=ingestor.hidden_sheets,
                            audit_id=audit_id,
                            ticker=ticker_input,
                        )
                        issues = auditor.run_all_checks()

                        # --- PHASE 4: REPORTING ---
                        reporter = ReportGenerator(uploaded_file.name, issues, ingestor, engine)
                        pdf_path = reporter.generate_pdf()
                        excel_path = reporter.generate_excel()
                        reporter.update_log()

                        # Store results keyed by filename
                        st.session_state.audit_results[uploaded_file.name] = {
                            'audit_id': audit_id,
                            'issues': issues,
                            'score': reporter.complexity_score,
                            'rationale': reporter.complexity_rationale,
                            'sheets_count': len(ingestor.sheets_values),
                            'node_count': engine.node_count if engine else 0,
                            'stats': stats,
                            'pdf_path': pdf_path,
                            'excel_path': excel_path,
                            'model_name': uploaded_file.name,
                            'is_csv': is_csv,
                            'load_errors': list(ingestor.load_errors),
                        }

                        # Clean up temp file
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                    except FileNotFoundError:
                        st.error(f"{uploaded_file.name}: File not found — re-upload and try again.")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except MemoryError:
                        st.error(f"{uploaded_file.name}: Too large to process.")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except Exception as e:
                        st.error(f"{uploaded_file.name}: Audit failed — {type(e).__name__}: {e}")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                progress.progress((idx + 1) / total)

            progress.empty()

        # Display results if available (persists across button clicks)
        if st.session_state.audit_results:
            multi = len(st.session_state.audit_results) > 1

            if len(st.session_state.audit_results) > 1:
                st.subheader("Batch Summary")
                summary_data = []
                for fname, r in st.session_state.audit_results.items():
                    summary_data.append({
                        "File": fname,
                        "Complexity": f"{r['score']}/5",
                        "Critical": len([i for i in r['issues'] if i['severity'] == 'Critical']),
                        "High": len([i for i in r['issues'] if i['severity'] == 'High']),
                        "Total Issues": len(r['issues']),
                    })
                st.dataframe(pd.DataFrame(summary_data), hide_index=True, use_container_width=True)

            for fname, results in st.session_state.audit_results.items():
                if multi:
                    container = st.expander(f"Results: {fname}", expanded=False)
                else:
                    container = st.expander(f"Results: {fname}", expanded=True)

                with container:
                    issues = results['issues']
                    score = results['score']

                    if results.get('is_csv'):
                        st.warning("CSV — formula logic auditing skipped")

                    for err in results.get('load_errors', []):
                        st.warning(err)

                    st.success("Audit complete")

                    # Complexity Score
                    st.markdown(
                        f'<div class="complexity-badge level-{score}">Complexity: {score}/5</div>',
                        unsafe_allow_html=True
                    )
                    st.caption(results['rationale'])

                    # Key Metrics
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Sheets", results['sheets_count'])
                    col2.metric("Formulas", f"{results['node_count']:,}")
                    col3.metric("Critical", len([i for i in issues if i['severity'] == 'Critical']))
                    col4.metric("Cyclic Refs", results['stats'].get('circular_references', 0))

                    # Unresolved table references warning
                    table_refs = results['stats'].get('unresolved_table_refs', [])
                    if table_refs:
                        st.warning(
                            f"{len(table_refs)} unresolved table reference(s) — "
                            "dependency chains through structured tables may be incomplete."
                        )
                        with st.expander("View Table References"):
                            for ref in table_refs[:50]:
                                st.text(ref)

                    # Reports
                    st.subheader("Downloads")
                    d_col1, d_col2 = st.columns(2)

                    pdf_path = results['pdf_path']
                    excel_path = results['excel_path']

                    if os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            d_col1.download_button(
                                label="Executive Memo (PDF)",
                                data=f,
                                file_name=os.path.basename(pdf_path),
                                mime="application/pdf",
                                use_container_width=True,
                                key=f"pdf_dl_{fname}"
                            )

                    if os.path.exists(excel_path):
                        with open(excel_path, "rb") as f:
                            d_col2.download_button(
                                label="Datatape (Excel)",
                                data=f,
                                file_name=os.path.basename(excel_path),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key=f"excel_dl_{fname}"
                            )

                    # Findings
                    st.subheader("Findings")

                    critical_issues = [i for i in issues if i['severity'] == 'Critical']
                    high_issues = [i for i in issues if i['severity'] == 'High']
                    medium_issues = [i for i in issues if i['severity'] == 'Medium']

                    # Critical
                    if critical_issues:
                        st.error(f"{len(critical_issues)} critical integrity failures")
                        for i in critical_issues:
                            with st.expander(f"**{i['type']}** @ {i['location']}"):
                                st.write(f"**Finding:** {i['detail']}")
                                if i.get('why'):
                                    st.markdown("---")
                                    st.markdown(f"**Why this matters:** {i['why']}")
                                if i.get('cause'):
                                    st.markdown(f"**Likely cause:** {i['cause']}")
                                if i.get('fix'):
                                    st.markdown(f"**How to fix:** {i['fix']}")
                    else:
                        st.markdown('<div class="pass-card">No critical integrity failures</div>', unsafe_allow_html=True)
                        st.write("")

                    # High
                    if high_issues:
                        st.warning(f"{len(high_issues)} high-risk modeling practices")
                        df_high = pd.DataFrame(high_issues)
                        if not df_high.empty:
                            issue_types = df_high['type'].unique()
                            for itype in issue_types:
                                subset = df_high[df_high['type'] == itype]
                                first_issue = subset.iloc[0]
                                with st.expander(f"{itype} ({len(subset)} instances)"):
                                    if first_issue.get('why'):
                                        st.info(f"**Why this matters:** {first_issue['why']}")
                                    if first_issue.get('cause'):
                                        st.markdown(f"**Likely cause:** {first_issue['cause']}")
                                    if first_issue.get('fix'):
                                        st.success(f"**How to fix:** {first_issue['fix']}")
                                    st.markdown("---")
                                    st.markdown("**Instances found:**")
                                    st.dataframe(subset[['location', 'detail']], hide_index=True)

                    # Medium (Hygiene)
                    if medium_issues:
                        st.info(f"{len(medium_issues)} hygiene issues")
                        with st.expander("View Hygiene Issues (Grouped)"):
                            df_med = pd.DataFrame(medium_issues)
                            if not df_med.empty:
                                type_counts = df_med['type'].value_counts().reset_index()
                                type_counts.columns = ['Issue Type', 'Count']
                                st.dataframe(type_counts, hide_index=True)

                                for itype in df_med['type'].unique():
                                    first_of_type = df_med[df_med['type'] == itype].iloc[0]
                                    if first_of_type.get('why'):
                                        st.markdown(f"**{itype}:** {first_of_type['why']}")
                                        if first_of_type.get('fix'):
                                            st.caption(f"Fix: {first_of_type['fix']}")

                                st.markdown("---")
                                st.caption("Detailed List:")
                                st.dataframe(df_med[['type', 'location', 'detail']], hide_index=True)

                    # LLM Narrative
                    st.subheader("Narrative Analysis")

                    has_anthropic = os.getenv("ANTHROPIC_API_KEY") is not None
                    has_openai = os.getenv("OPENAI_API_KEY") is not None

                    if "llm_in_progress" not in st.session_state:
                        st.session_state.llm_in_progress = False

                    if has_anthropic or has_openai:
                        provider = "anthropic" if has_anthropic else "openai"
                        st.caption(f"Provider: {provider.title()}")

                        if st.session_state.llm_in_progress:
                            st.warning("An analysis is already running — wait for it to complete.")
                        else:
                            if st.button("Generate AI Analysis", type="secondary", key=f"llm_btn_{fname}"):
                                st.session_state.llm_in_progress = True
                                try:
                                    with st.spinner(f"Generating narrative analysis with {provider.title()}..."):
                                        try:
                                            st.session_state.llm_result[fname] = analyze_findings_with_llm(
                                                issues=issues,
                                                model_name=results['model_name'],
                                                complexity_score=score,
                                                provider=provider,
                                                audit_id=results.get('audit_id')
                                            )
                                            if st.session_state.llm_result[fname] is None:
                                                st.error("LLM returned None - check API key configuration")
                                        except Exception as e:
                                            st.error(f"LLM Error: {e}")
                                            st.session_state.llm_result[fname] = None
                                finally:
                                    st.session_state.llm_in_progress = False

                        # Display result if available
                        if st.session_state.llm_result.get(fname):
                            llm_meta = st.session_state.llm_result[fname].get("metadata", {})
                            if llm_meta.get("prompt_truncated"):
                                st.warning(
                                    f"Analysis based on top {llm_meta.get('prompt_issue_count', 50)}"
                                    f" of {len(issues)} issues"
                                )

                            st.markdown("#### Executive Narrative")
                            st.markdown(st.session_state.llm_result[fname]["analysis"])

                            with st.expander("Analysis Metadata"):
                                st.json(llm_meta)

                            st.caption("AI-generated — review before distribution")
                    else:
                        st.caption(
                            "Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` to enable narrative analysis."
                        )

with tab2:
    _project_root = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(_project_root, "RESULTS", "audit_history.csv")
    if os.path.exists(log_path):
        df_log = pd.read_csv(log_path)

        # Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            files_in_log = ["All"] + sorted(df_log["Filename"].unique().tolist())
            sel_file = st.selectbox("Filter by file", files_in_log, key="hist_file_filter")
        with col_f2:
            sort_opts = {"Newest first": ("Timestamp", False), "Oldest first": ("Timestamp", True),
                         "Most issues": ("Total_Issues", False), "Highest complexity": ("Complexity_Score", False)}
            sel_sort = st.selectbox("Sort by", list(sort_opts.keys()), key="hist_sort")

        df_view = df_log.copy()
        if sel_file != "All":
            df_view = df_view[df_view["Filename"] == sel_file]
        sort_col, sort_asc = sort_opts[sel_sort]
        df_view = df_view.sort_values(by=sort_col, ascending=sort_asc)

        st.dataframe(df_view, hide_index=True, use_container_width=True)
        st.caption(f"{len(df_view)} of {len(df_log)} audit(s)")

        # Trend chart (if enough data)
        if len(df_log) >= 2:
            with st.expander("Trend"):
                df_chart = df_log.copy()
                df_chart["Timestamp"] = pd.to_datetime(df_chart["Timestamp"])
                st.line_chart(df_chart.set_index("Timestamp")[["Total_Issues", "Critical_Errors"]])

        # Clear log button
        if st.button("Clear history", type="secondary"):
            os.remove(log_path)
            st.rerun()
    else:
        st.caption("No audit history yet — run an audit to start logging.")

with tab3:
    st.markdown(r"""
    **Critical** — Errors that invalidate model output
    * *Accounting Mismatch:* Balance sheet variance > 0.1% of total assets, $1,000 floor (Assets ≠ Liabs + Equity)
    * *Circular Logic:* Infinite loops in the formula graph

    **High** — Structural weaknesses suggesting manipulation or fragility
    * *Hard-coded Plug:* Literal value embedded in a formula row, often a manual override
    * *Calculation Errors:* Active `#REF!`, `#DIV/0!`, or `#VALUE!` in the chain

    **Medium** — Hygiene issues reducing portability or transparency
    * *External Links:* Dependencies on absent files
    * *Unused Inputs:* Assumptions with no downstream impact
    """)

with tab4:
    st.markdown("""
    Most checkers inspect cell values. ModelLens inspects **structure**.

    1. **Dual-state ingestion** — load values (what you see) and formulas (the logic) separately via `openpyxl`
    2. **Tokenization** — parse each formula to identify parent cells
    3. **DAG construction** — every cell is a node, every formula reference is an edge
    4. **Graph traversal** — cycles = circular refs; pattern breaks = plugs (e.g., a literal in a row of formulas)

    This approach audits 50-tab models in seconds.
    """)
