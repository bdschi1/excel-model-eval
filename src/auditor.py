import pandas as pd
from colorama import Fore, Style


# --- ISSUE EXPLANATIONS ---
# Educational context for each issue type: why it matters, what causes it, how to fix it

ISSUE_EXPLANATIONS = {
    "External Link": {
        "why": "External links create dependencies on files that may not exist on other machines, "
               "causing #REF! errors when the model is shared. They also introduce version control "
               "risks if the source file changes without the model being updated.",
        "cause": "Usually created when copying data from another workbook using paste-link, or when "
                 "formulas reference Bloomberg/FactSet/Capital IQ feeds directly.",
        "fix": "Convert external links to static values (Paste Special > Values) for historical data. "
               "For live feeds, document the source and create a dedicated 'Data Inputs' sheet."
    },
    "Calculation Error": {
        "why": "Excel errors propagate through the model — any cell referencing an error cell will "
               "also show an error. This can silently break valuation outputs and key metrics.",
        "cause": {
            "#REF!": "A formula references a cell that has been deleted, or a range that was invalidated.",
            "#NAME?": "Excel doesn't recognize a function name (typo) or a named range that doesn't exist.",
            "#VALUE!": "A formula has the wrong type of argument (e.g., text where a number is expected).",
            "#DIV/0!": "A formula is dividing by zero or an empty cell."
        },
        "fix": "Trace the error back to its source using Excel's 'Trace Error' feature (Formulas > Error Checking). "
               "Fix the root cause rather than wrapping in IFERROR, which can hide real problems."
    },
    "Hard-coded Plug": {
        "why": "A 'plug' is a hard-coded value inserted into a row of formulas to force a desired result. "
               "This is a major red flag in financial models because it breaks the logical flow — "
               "changes to assumptions won't flow through correctly, and the model may produce "
               "misleading outputs without any warning.",
        "cause": "Often inserted when a model doesn't balance or produce expected results. Instead of "
                 "fixing the underlying logic, an analyst may override a cell with a manual number. "
                 "Also common in rushed model updates or when inheriting someone else's model.",
        "fix": "1) Identify what the cell SHOULD be calculating. 2) Write the correct formula. "
               "3) If the formula produces unexpected results, trace upstream to find the real issue. "
               "Never use hard-coded values in projection periods unless they represent genuine assumptions."
    },
    "Accounting Mismatch": {
        "why": "The fundamental accounting equation (Assets = Liabilities + Equity) must hold in every period. "
               "An imbalance means the model has a structural error — cash flows aren't routing correctly, "
               "or a balance sheet account is missing its corresponding entry.",
        "cause": "Common causes: (1) Working capital changes not flowing to cash flow statement, "
                 "(2) Debt/equity issuances not hitting both cash and the liability/equity account, "
                 "(3) Retained earnings not linking to net income, (4) Circular reference breaking the iteration.",
        "fix": "Create a 'Balance Check' row that calculates Assets - Liabilities - Equity for each period. "
               "Find the first period where the imbalance appears and trace all entries in that period. "
               "Check that every cash movement has a corresponding balance sheet entry."
    },
    "Circular Reference": {
        "why": "Circular references occur when a formula refers back to itself (directly or through a chain). "
               "While Excel can resolve some circular refs through iteration, they make models fragile, "
               "slow, and prone to convergence failures. They also make auditing extremely difficult.",
        "cause": "Most common in financial models: Interest expense depends on average debt, which depends on "
                 "ending cash, which depends on net income, which includes interest expense. Also common "
                 "with revolver/credit facility modeling.",
        "fix": "Break the circularity by using beginning-of-period balances instead of averages, or by "
               "implementing a 'copy-paste values' macro that iterates until convergence. Document any "
               "intentional circular references clearly."
    }
}


def get_explanation(issue_type, error_value=None):
    """Returns the educational explanation for an issue type."""
    if issue_type not in ISSUE_EXPLANATIONS:
        return {"why": "", "cause": "", "fix": ""}

    explanation = ISSUE_EXPLANATIONS[issue_type].copy()

    # Handle specific error subtypes for Calculation Errors
    if issue_type == "Calculation Error" and error_value:
        causes = explanation["cause"]
        if isinstance(causes, dict):
            for err_code, err_cause in causes.items():
                if err_code in str(error_value):
                    explanation["cause"] = err_cause
                    break
            else:
                explanation["cause"] = "Unknown error type."

    return explanation


class ModelAuditor:
    """
    The Analyst.

    Responsibility:
    1. Numerical Integrity: Checks if Balance Sheet balances.
    2. Logic Hygiene: Finds 'Plugs' (Hardcodes in formula rows).
    3. Structural Health: Flags Broken Links and External References.
    """

    def __init__(self, ingestor, dependency_engine):
        self.ingestor = ingestor
        self.graph = dependency_engine.graph
        self.issues = []

    def run_all_checks(self):
        """Orchestrates the full suite of audit tests."""
        print(f"{Fore.CYAN}[*] Running Hedge Fund Grade Audit...{Style.RESET_ALL}")

        self.check_external_links()
        self.detect_hardcoded_plugs()
        self.verify_balance_sheet_integrity()

        print(f"    > Audit Complete. Found {len(self.issues)} issues.")
        return self.issues

    def _add_issue(self, issue_type, severity, location, detail, error_value=None):
        """Helper to add an issue with its explanation."""
        explanation = get_explanation(issue_type, error_value)
        self.issues.append({
            "type": issue_type,
            "severity": severity,
            "location": location,
            "detail": detail,
            "why": explanation.get("why", ""),
            "cause": explanation.get("cause", ""),
            "fix": explanation.get("fix", "")
        })

    def check_external_links(self):
        """Scans for links to files outside this workbook (e.g., Bloomberg/FactSet)."""
        print("    > Checking for External Links & Broken Refs...")

        # 1. Check Graph for External Nodes
        external_nodes = [n for n in self.graph.nodes if "EXT_LINK" in n]
        for node in external_nodes:
            self._add_issue(
                issue_type="External Link",
                severity="Medium",
                location=node,
                detail="Dependency on external workbook/source detected."
            )

        # 2. Check Values for Excel Errors (#REF!, #NAME?)
        for sheet_name, df in self.ingestor.sheets_values.items():
            # Stack data to find errors efficiently
            errors = df.stack()
            # Filter for common Excel error strings
            error_cells = errors[errors.astype(str).str.contains(r"#REF!|#NAME\?|#VALUE!|#DIV/0!", regex=True)]

            for index, value in error_cells.items():
                row, col = index
                cell_ref = f"{sheet_name}!Row{row+1}:Col{col+1}"
                self._add_issue(
                    issue_type="Calculation Error",
                    severity="High",
                    location=cell_ref,
                    detail=f"Cell contains error value: {value}",
                    error_value=value
                )

    def detect_hardcoded_plugs(self):
        """
        Heuristic: If a row is 80% formulas, but contains a hardcoded number
        in the middle of the time series (not in label/historical columns), it's likely a 'Plug'.
        """
        print("    > Scanning for Hard-coded Plugs in Projections...")

        # Skip first N columns (typically: label column + 2-3 historical years)
        SKIP_COLS = 3

        for sheet_name, df_formulas in self.ingestor.sheets_formulas.items():
            # Skip likely data dumps (if sheet name implies raw data)
            if "raw" in sheet_name.lower() or "cache" in sheet_name.lower():
                continue

            for idx, row in df_formulas.iterrows():
                # Get the row as a list, SKIPPING the first N columns (labels + historicals)
                row_list = row.tolist()[SKIP_COLS:]

                # Identify cells that look like formulas vs values
                is_formula = [str(x).startswith('=') for x in row_list if pd.notna(x)]

                if not is_formula:
                    continue

                formula_count = sum(is_formula)
                total_items = len(is_formula)

                # If row is mostly formulas (>70%) but has interruptions
                if total_items > 5 and (formula_count / total_items) > 0.7:
                    # Simple check: If we have formulas, but some values are interspersed
                    if formula_count < total_items:
                        hardcode_count = total_items - formula_count
                        # Find which columns have the plugs (for better detail)
                        plug_positions = [i + SKIP_COLS + 1 for i, x in enumerate(row_list)
                                          if pd.notna(x) and not str(x).startswith('=')]
                        self._add_issue(
                            issue_type="Hard-coded Plug",
                            severity="High",
                            location=f"{sheet_name}!Row{idx+1}",
                            detail=f"Row has {formula_count} formulas and {hardcode_count} hardcodes in projection columns. Plug at col(s): {plug_positions}"
                        )

    def verify_balance_sheet_integrity(self):
        """
        Locates Total Assets and Total Liabs+Equity and ensures variance is 0.
        """
        print("    > Verifying Balance Sheet Logic...")

        bs_sheet = None
        # Smart search for the Balance Sheet tab
        for name in self.ingestor.sheets_values.keys():
            if "balance" in name.lower() or "bs" in name.lower():
                bs_sheet = name
                break

        if not bs_sheet:
            return  # No BS found

        df = self.ingestor.sheets_values[bs_sheet]

        # Locate the rows (Case insensitive search in first column)
        row_assets = None
        row_liabs_eq = None

        for col_idx in [0, 1]:  # Check first two columns for labels
            for idx, val in df.iloc[:, col_idx].items():
                val_str = str(val).lower()
                if "total assets" in val_str:
                    row_assets = idx
                if "total liabilities" in val_str and "equity" in val_str:
                    row_liabs_eq = idx

        if row_assets is not None and row_liabs_eq is not None:
            # Extract the time series data (assumes data is to the right)
            assets_vals = pd.to_numeric(df.iloc[row_assets, 2:], errors='coerce').fillna(0)
            liabs_vals = pd.to_numeric(df.iloc[row_liabs_eq, 2:], errors='coerce').fillna(0)

            # Calculate Variance
            variance = assets_vals - liabs_vals

            if variance.abs().sum() > 1.0:  # Tolerance of $1 for rounding
                # Find which periods are out of balance
                problem_periods = variance[variance.abs() > 0.01].index.tolist()
                self._add_issue(
                    issue_type="Accounting Mismatch",
                    severity="Critical",
                    location=bs_sheet,
                    detail=f"Balance Sheet does not balance. Total Variance: ${variance.abs().sum():,.2f}. "
                           f"Out-of-balance periods: {problem_periods[:5]}{'...' if len(problem_periods) > 5 else ''}"
                )
