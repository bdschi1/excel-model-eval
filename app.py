import streamlit as st
import os
import pandas as pd
import shutil
import time

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    import pathlib
    env_path = pathlib.Path(__file__).parent / '.env'
    load_dotenv(env_path, override=True)
except ImportError:
    pass  # python-dotenv not installed, use system env vars

from src.ingestion import ModelIngestor
from src.dependency import DependencyEngine
from src.auditor import ModelAuditor
from src.reporting import ReportGenerator
from src.llm_analyzer import analyze_findings_with_llm

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Hedge Fund Model Auditor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS STYLING ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f4e78;
    }
    .pass-card {
        background-color: #e8fdf5;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2ecc71;
    }
    .complexity-badge {
        font-size: 20px;
        font-weight: bold;
        padding: 10px;
        border-radius: 5px;
        color: white;
        text-align: center;
        margin-bottom: 10px;
    }
    .level-1 { background-color: #2ecc71; } /* Green */
    .level-2 { background-color: #3498db; } /* Blue */
    .level-3 { background-color: #f1c40f; color: black; } /* Yellow */
    .level-4 { background-color: #e67e22; } /* Orange */
    .level-5 { background-color: #c0392b; } /* Red */
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: HISTORY & SPECS ---
with st.sidebar:
    st.header("⚙️ System Architecture")
    st.info(
        """
        **1. Ingestion Layer**
        Dual-state load: Values (Math) & Formulas (Logic).

        **2. Graph Engine**
        Builds a Directed Acyclic Graph (DAG) of cell dependencies.

        **3. Auditor Module**
        Traverses the graph to find circular logic, plugs, and broken accounting.
        """
    )

    st.divider()
    st.caption("v2.2.0 | Hedge Fund Grade Evaluator")

# --- MAIN INTERFACE ---
st.title("📊 Hedge Fund Excel Model Auditor")
st.markdown(
    """
    **Forensic Analysis System** | Automated integrity checks for institutional financial models.
    """
)

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🚀 Run Audit", "📖 Interpretation Guide", "🧠 How it Works"])

with tab1:
    st.subheader("Upload Financial Model")

    # --- FILE UPLOADER WIDGET ---
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["xlsx", "xlsm", "xls", "csv"],
        help="Supported formats: .xlsx, .xlsm, .xls, .csv. (Note: CSVs will not contain formulas for logic auditing)"
    )

    # Initialize session state
    if 'audit_results' not in st.session_state:
        st.session_state.audit_results = None
    if 'llm_result' not in st.session_state:
        st.session_state.llm_result = None

    if uploaded_file:
        # Save File Temporarily
        os.makedirs("temp_data", exist_ok=True)
        temp_path = os.path.join("temp_data", uploaded_file.name)

        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.info(f"Ready to analyze: **{uploaded_file.name}**")

        if st.button("Start Forensic Audit", type="primary"):
            # Clear previous LLM result when starting new audit
            st.session_state.llm_result = None

            with st.spinner("Running forensic audit..."):
                try:
                    # --- PHASE 1: INGESTION ---
                    ingestor = ModelIngestor(temp_path)

                    if uploaded_file.name.lower().endswith('.csv'):
                        st.warning("⚠️ CSV file detected. Formula logic auditing will be skipped.")

                    if not ingestor.ingest():
                        st.error("Critical Failure: Could not ingest model.")
                        st.stop()

                    # --- PHASE 2: DEPENDENCY MAPPING ---
                    engine = DependencyEngine(ingestor.sheets_formulas)
                    engine.build_graph()
                    stats = engine.analyze_structure()

                    # --- PHASE 3: AUDITING ---
                    auditor = ModelAuditor(ingestor, engine)
                    issues = auditor.run_all_checks()

                    # --- PHASE 4: REPORTING ---
                    reporter = ReportGenerator(uploaded_file.name, issues, ingestor, engine)
                    pdf_path = reporter.generate_pdf()
                    excel_path = reporter.generate_excel()
                    reporter.update_log()

                    # Store results in session state
                    st.session_state.audit_results = {
                        'issues': issues,
                        'score': reporter.complexity_score,
                        'rationale': reporter.complexity_rationale,
                        'sheets_count': len(ingestor.sheets_values),
                        'node_count': engine.node_count,
                        'stats': stats,
                        'pdf_path': pdf_path,
                        'excel_path': excel_path,
                        'model_name': uploaded_file.name
                    }

                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
                    st.session_state.audit_results = None

        # Display results if available (persists across button clicks)
        if st.session_state.audit_results:
            results = st.session_state.audit_results
            issues = results['issues']
            score = results['score']

            st.success("Audit Complete!")
            st.divider()

            # 1. Complexity Score
            c_score, c_detail = st.columns([1, 3])
            with c_score:
                st.markdown(
                    f'<div class="complexity-badge level-{score}">Complexity Score: {score}/5</div>',
                    unsafe_allow_html=True
                )
            with c_detail:
                st.caption("Complexity Drivers:")
                st.write(f"**{results['rationale']}**")

            # 2. Key Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Sheets Scanned", results['sheets_count'])
            col2.metric("Formulas Mapped", f"{results['node_count']:,}")
            col3.metric("Critical Errors", len([i for i in issues if i['severity'] == 'Critical']))
            col4.metric("Cyclic Refs", results['stats'].get('circular_references', 0))

            st.divider()

            # 3. Downloadable Reports
            st.subheader("📥 Board Pack Downloads")
            d_col1, d_col2 = st.columns(2)

            pdf_path = results['pdf_path']
            excel_path = results['excel_path']

            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    d_col1.download_button(
                        label="📄 Download Executive Memo (PDF)",
                        data=f,
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf",
                        use_container_width=True
                    )

            if os.path.exists(excel_path):
                with open(excel_path, "rb") as f:
                    d_col2.download_button(
                        label="📊 Download Detailed Datatape (Excel)",
                        data=f,
                        file_name=os.path.basename(excel_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

            st.divider()

            # 4. Interactive Issue Explorer
            st.subheader("Interactive Findings Explorer")

            critical_issues = [i for i in issues if i['severity'] == 'Critical']
            high_issues = [i for i in issues if i['severity'] == 'High']
            medium_issues = [i for i in issues if i['severity'] == 'Medium']

            # Critical
            if critical_issues:
                st.error(f"🚨 {len(critical_issues)} CRITICAL INTEGRITY FAILURES")
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
                st.markdown('<div class="pass-card">✅ No Critical Integrity Failures Found</div>', unsafe_allow_html=True)
                st.write("")

            # High
            if high_issues:
                st.warning(f"⚠️ {len(high_issues)} HIGH RISK MODELING PRACTICES")
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
                st.info(f"ℹ️ {len(medium_issues)} Hygiene / Medium Risks")
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

            # --- LLM NARRATIVE ANALYSIS ---
            st.divider()
            st.subheader("🤖 AI-Powered Narrative Analysis")

            has_anthropic = os.getenv("ANTHROPIC_API_KEY") is not None
            has_openai = os.getenv("OPENAI_API_KEY") is not None

            if has_anthropic or has_openai:
                provider = "anthropic" if has_anthropic else "openai"
                st.caption(f"✓ API key detected for {provider.title()}")

                if st.button("Generate AI Analysis", type="secondary"):
                    with st.spinner(f"Generating narrative analysis with {provider.title()}..."):
                        try:
                            st.session_state.llm_result = analyze_findings_with_llm(
                                issues=issues,
                                model_name=results['model_name'],
                                complexity_score=score,
                                provider=provider
                            )
                            if st.session_state.llm_result is None:
                                st.error("LLM returned None - check API key configuration")
                        except Exception as e:
                            st.error(f"LLM Error: {e}")
                            st.session_state.llm_result = None

                # Display result if available
                if st.session_state.llm_result:
                    st.markdown("#### Executive Narrative")
                    st.markdown(st.session_state.llm_result["analysis"])

                    with st.expander("Analysis Metadata"):
                        st.json(st.session_state.llm_result["metadata"])

                    st.caption("⚠️ AI-generated analysis should be reviewed by a qualified professional. "
                               "See `eval/llm_rubrics/` for evaluation criteria.")
            else:
                st.info(
                    "💡 **Enable AI Analysis:** Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` "
                    "environment variable to unlock LLM-powered narrative summaries.\n\n"
                    "```bash\n"
                    "export ANTHROPIC_API_KEY=your_key_here\n"
                    "```"
                )

with tab2:
    st.header("How to Interpret Findings")

    st.markdown(r"""
    ### 🔴 Critical Severity (The "Showstoppers")
    **Definition:** Errors that invalidate the model's mathematical output.
    * **Accounting Mismatch:** Balance Sheet variance > $1.00. (Assets ≠ Liabs + Equity).
    * **Circular Logic:** Infinite calculation loops detected in the formula graph.

    ### 🟠 High Severity (The "Red Flags")
    **Definition:** Structural weaknesses that suggest manipulation or high fragility.
    * **Hard-coded Plug:** A hard number (e.g., `5.0%`) found inside a row of formulas. This often indicates a manual override to force a valuation result.
    * **Calculation Errors:** Active `#REF!`, `#DIV/0!`, or `#VALUE!` errors in the calculation chain.

    ### 🔵 Medium Severity (Hygiene)
    **Definition:** Issues that reduce portability or transparency.
    * **External Links:** Dependencies on files (`C:\Users\...\Budget.xlsx`) that are not present.
    * **Unused Inputs:** Assumptions that don't drive any output (orphaned nodes).
    """)

with tab3:
    st.header("Under the Hood: The Graph Approach")
    st.markdown("""
    Most model checkers just look at cell values (Is A1 > 0?).
    **We look at the structure.**

    1.  **Dual-State Ingestion**: We load the file twice using `openpyxl`.
        * *State A:* The calculated values (what you see).
        * *State B:* The formula strings (the logic).
    2.  **Tokenization**: We parse every formula to find its parents.
        * `=SUM(A1:A5)` -> Parents are A1, A2, A3, A4, A5.
    3.  **Graph Construction**: We build a **Directed Acyclic Graph (DAG)** where every cell is a node and every formula is an edge.
    4.  **Traversal Algorithms**:
        * To find **Circular References**, we look for "cycles" in the graph.
        * To find **Plugs**, we look for pattern breaks in the graph structure (e.g., a node with 0 parents in a row of nodes with 5 parents).
    """)

    st.info("This graph-based approach is what allows us to audit 50-tab models in seconds.")
