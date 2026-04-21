import csv
import os
from datetime import datetime

import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos


class ReportGenerator:
    """
    The Communicator.
    Generates PDF memos, Excel datatapes, and calculates Complexity Scores.
    """
    def __init__(self, filename, issues, ingestor, dependency_engine):
        import hashlib
        import json

        self.filename = os.path.basename(filename).replace(os.sep, '_')
        self.issues = issues
        self.ingestor = ingestor
        self.graph = dependency_engine.graph if dependency_engine else None
        self.timestamp = datetime.now()

        # Initialize Output Directory (project-relative, not cwd)
        _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.results_dir = os.path.join(_project_root, "RESULTS")
        os.makedirs(self.results_dir, exist_ok=True)

        # Calculate Complexity
        self.complexity_score, self.complexity_rationale = self._calculate_complexity()

        # Report fingerprint: timestamp + first 8 chars of SHA-256 over the
        # issue list. Lets two runs of the same model be compared for drift —
        # identical issue sets produce identical sha8, regardless of run time.
        # The fingerprint is embedded in the PDF footer and Excel metadata.
        _issues_blob = json.dumps(
            [
                {
                    "type": str(i.get("type", "")),
                    "severity": str(i.get("severity", "")),
                    "location": str(i.get("location", "")),
                    "detail": str(i.get("detail", "")),
                }
                for i in (self.issues or [])
            ],
            sort_keys=True,
        ).encode("utf-8")
        _sha8 = hashlib.sha256(_issues_blob).hexdigest()[:8]
        self.fingerprint = f"{self.timestamp.strftime('%Y%m%d_%H%M%S')}-{_sha8}"

    def _calculate_complexity(self):
        """
        Calculates a 1-5 Complexity Score based on graph topology.
        """
        sheet_count = len(self.ingestor.sheets_values)
        node_count = self.graph.number_of_nodes() if self.graph else 0
        edge_count = self.graph.number_of_edges() if self.graph else 0
        
        # Heuristic Scoring
        score = 1
        rationale = []

        # Sheet Scale
        if sheet_count > 30: score += 2; rationale.append("High Sheet Count (>30)")
        elif sheet_count > 10: score += 1; rationale.append("Moderate Sheet Count (>10)")
        
        # Formula Density
        if node_count > 10000: score += 2; rationale.append("Massive Calculation Graph (>10k nodes)")
        elif node_count > 2000: score += 1; rationale.append("High Calculation Density")

        # Interconnectivity
        # Avoid division by zero
        if node_count > 0:
            if edge_count > (node_count * 1.5): score += 1; rationale.append("High Inter-dependency Ratio")

        # Cap at 5
        final_score = min(score, 5)
        return final_score, ", ".join(rationale)

    def generate_pdf(self):
        """Generates a professional PDF Memo."""
        pdf = FPDF()
        pdf.add_page()

        # Try to load a Unicode TTF font; fall back to core Helvetica
        _FONT_NAME = "Helvetica"
        _font_paths = []
        try:
            import matplotlib
            _mpl_ttf = os.path.join(
                matplotlib.get_data_path(), 'fonts', 'ttf', 'DejaVuSans.ttf')
            _font_paths.append(_mpl_ttf)
        except Exception:
            pass
        _font_paths.append(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'fonts', 'DejaVuSans.ttf'))
        for _fp in _font_paths:
            if os.path.isfile(_fp):
                try:
                    pdf.add_font("DejaVu", "", _fp)
                    _bold = _fp.replace("Sans.ttf", "Sans-Bold.ttf")
                    pdf.add_font("DejaVu", "B",
                                 _bold if os.path.isfile(_bold) else _fp)
                    _FONT_NAME = "DejaVu"
                except Exception:
                    pass
                break

        # Header
        pdf.set_font(_FONT_NAME, "B", 16)
        pdf.cell(0, 10, "ModelLens - Structural Audit Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.line(10, 20, 200, 20)
        pdf.ln(10)

        # Meta Data
        pdf.set_font(_FONT_NAME, "", 10)
        pdf.cell(0, 5, f"File Evaluated: {self.filename}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 5, f"Date: {self.timestamp.strftime('%Y-%m-%d %H:%M')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 5, f"Complexity Score: {self.complexity_score}/5", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 5, f"Complexity Drivers: {self.complexity_rationale}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)

        # Executive Summary
        pdf.set_font(_FONT_NAME, "B", 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 10, "Executive Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(2)

        critical = [i for i in self.issues if i['severity'] == 'Critical']
        high = [i for i in self.issues if i['severity'] == 'High']

        pdf.set_font(_FONT_NAME, "", 10)
        summary_text = (
            f"The model was evaluated for structural integrity, logical consistency, and best practices. "
            f"We detected {len(critical)} Critical Errors and {len(high)} High Risk Warnings. "
            f"The complexity rating is {self.complexity_score}/5."
        )
        pdf.multi_cell(0, 5, summary_text)
        pdf.ln(5)

        # High Priority Issues
        pdf.set_font(_FONT_NAME, "B", 12)
        pdf.cell(0, 10, "Top Red Flags", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(2)

        pdf.set_font(_FONT_NAME, "", 9)
        priority_issues = (critical + high)[:10]  # Show top 10 only
        
        if not priority_issues:
            pdf.cell(0, 5, "No Critical or High severity issues detected.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        for issue in priority_issues:
            # Color code severity tag (Text based in PDF)
            severity_tag = f"[{issue['severity'].upper()}]"
            pdf.set_font(_FONT_NAME, "B", 9)
            pdf.cell(30, 5, severity_tag)
            pdf.set_font(_FONT_NAME, "", 9)
            safe_loc = str(issue['location'])
            safe_type = str(issue['type'])
            safe_detail = str(issue['detail'])
            
            pdf.cell(0, 5, f"{safe_type} @ {safe_loc}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.multi_cell(0, 5, f"   Detail: {safe_detail}")
            pdf.ln(2)

        # Fingerprint footer — lets two runs of the same model be compared.
        pdf.ln(8)
        pdf.set_font(_FONT_NAME, "", 7)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(
            0, 4, f"fingerprint: {self.fingerprint}",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L",
        )
        pdf.set_text_color(0, 0, 0)

        ts = self.timestamp.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.results_dir, f"Audit_Summary_{self.filename}_{ts}.pdf")
        pdf.output(output_path)

        return output_path

    def generate_excel(self):
        """
        Generates an Excel file with grouped rows for large error lists.
        """
        ts = self.timestamp.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.results_dir, f"Audit_Details_{self.filename}_{ts}.xlsx")
        
        # Convert issues to DataFrame
        df = pd.DataFrame(self.issues)
        if df.empty:
            df = pd.DataFrame(columns=["severity", "type", "location", "detail"])

        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            workbook = writer.book

            # Fingerprint embedded in workbook metadata + as a custom property
            # so two runs of the same model can be compared for drift.
            workbook.set_properties({
                "title": f"ModelLens Audit - {self.filename}",
                "subject": "Structural audit report",
                "comments": f"fingerprint: {self.fingerprint}",
            })
            workbook.set_custom_property("fingerprint", self.fingerprint)

            # --- TAB 1: DASHBOARD ---
            ws_summary = workbook.add_worksheet("Executive Summary")
            header_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'bg_color': '#1f4e78', 'font_color': 'white'})

            ws_summary.write("B2", "Model Audit Dashboard", header_fmt)
            ws_summary.write("B4", f"Filename: {self.filename}")
            ws_summary.write("B5", f"Complexity Score: {self.complexity_score}/5")
            ws_summary.write("B6", f"Total Issues: {len(self.issues)}")
            ws_summary.write("B7", f"Fingerprint: {self.fingerprint}")
            
            # --- TAB 2: DETAILED FINDINGS ---
            if not df.empty:
                # Sort by Type so we can group them
                df_sorted = df.sort_values(by=['type', 'severity'])
                df_sorted.to_excel(writer, sheet_name="Findings", index=False, startrow=1)
                
                ws_data = writer.sheets['Findings']
                
                # Format Headers
                data_header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
                _COL_WIDTHS = [12, 20, 25, 50, 40, 40, 40]  # severity, type, location, detail, why, cause, fix
                for col_num, value in enumerate(df_sorted.columns.values):
                    ws_data.write(0, col_num, value, data_header_fmt)
                    width = _COL_WIDTHS[col_num] if col_num < len(_COL_WIDTHS) else 25
                    ws_data.set_column(col_num, col_num, width)

                # Logic to Group Rows (The "Dropdown" effect)
                current_type = None
                start_row = 1
                
                # Iterate rows to find blocks of same 'type'
                # Data starts at Excel row 2 (index 1)
                for row_num, type_val in enumerate(df_sorted['type']):
                    real_row = row_num + 1 # +1 because of header
                    
                    if type_val != current_type:
                        # If we just finished a block
                        if current_type is not None and (real_row - start_row) > 0:
                            # Group the previous block
                            # 'level': 1 adds the outline. 'hidden': True collapses it.
                            for r in range(start_row + 1, real_row):
                                ws_data.set_row(r, options={'level': 1, 'hidden': True})
                        
                        current_type = type_val
                        start_row = real_row
                
                # Handle the very last block
                if (len(df_sorted) + 1 - start_row) > 0:
                     for r in range(start_row + 1, len(df_sorted) + 1):
                         ws_data.set_row(r, options={'level': 1, 'hidden': True})

        return output_path

    def update_log(self):
        """Appends run details to a persistent CSV log."""
        log_path = os.path.join(self.results_dir, "audit_history.csv")
        file_exists = os.path.isfile(log_path)
        
        with open(log_path, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Filename", "Complexity_Score", "Critical_Errors", "Total_Issues"])
            
            crit_count = len([i for i in self.issues if i['severity'] == 'Critical'])
            writer.writerow([
                self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                self.filename,
                self.complexity_score,
                crit_count,
                len(self.issues)
            ])
            