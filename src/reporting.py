import pandas as pd
import os
import csv
from datetime import datetime
from fpdf import FPDF

class ReportGenerator:
    """
    The Communicator.
    Generates PDF memos, Excel datatapes, and calculates Complexity Scores.
    """
    def __init__(self, filename, issues, ingestor, dependency_engine):
        self.filename = filename
        self.issues = issues
        self.ingestor = ingestor
        self.graph = dependency_engine.graph
        self.timestamp = datetime.now()
        
        # Initialize Output Directory
        self.results_dir = os.path.join(os.getcwd(), "RESULTS")
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Calculate Complexity
        self.complexity_score, self.complexity_rationale = self._calculate_complexity()

    def _calculate_complexity(self):
        """
        Calculates a 1-5 Complexity Score based on graph topology.
        """
        sheet_count = len(self.ingestor.sheets_values)
        node_count = self.graph.number_of_nodes()
        edge_count = self.graph.number_of_edges()
        
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
        
        # Header
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Hedge Fund Excel Model Audit Report", ln=True, align="C")
        pdf.line(10, 20, 200, 20)
        pdf.ln(10)

        # Meta Data
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, f"File Evaluated: {self.filename}", ln=True)
        pdf.cell(0, 5, f"Date: {self.timestamp.strftime('%Y-%m-%d %H:%M')}", ln=True)
        pdf.cell(0, 5, f"Complexity Score: {self.complexity_score}/5", ln=True)
        pdf.cell(0, 5, f"Complexity Drivers: {self.complexity_rationale}", ln=True)
        pdf.ln(5)

        # Executive Summary
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 10, "Executive Summary", ln=True, fill=True)
        pdf.ln(2)
        
        critical = [i for i in self.issues if i['severity'] == 'Critical']
        high = [i for i in self.issues if i['severity'] == 'High']
        
        pdf.set_font("Arial", "", 10)
        summary_text = (
            f"The model was evaluated for structural integrity, logical consistency, and best practices. "
            f"We detected {len(critical)} Critical Errors and {len(high)} High Risk Warnings. "
            f"The complexity rating is {self.complexity_score}/5."
        )
        pdf.multi_cell(0, 5, summary_text)
        pdf.ln(5)

        # High Priority Issues
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Top Red Flags", ln=True, fill=True)
        pdf.ln(2)

        pdf.set_font("Arial", "", 9)
        priority_issues = (critical + high)[:10]  # Show top 10 only
        
        if not priority_issues:
            pdf.cell(0, 5, "No Critical or High severity issues detected.", ln=True)
        
        for issue in priority_issues:
            # Color code severity tag (Text based in PDF)
            severity_tag = f"[{issue['severity'].upper()}]"
            pdf.set_font("Arial", "B", 9)
            pdf.cell(30, 5, severity_tag)
            pdf.set_font("Arial", "", 9)
            # Sanitise text to avoid unicode errors in FPDF (Latin-1 limitation)
            safe_loc = str(issue['location']).encode('latin-1', 'replace').decode('latin-1')
            safe_type = str(issue['type']).encode('latin-1', 'replace').decode('latin-1')
            safe_detail = str(issue['detail']).encode('latin-1', 'replace').decode('latin-1')
            
            pdf.cell(0, 5, f"{safe_type} @ {safe_loc}", ln=True)
            pdf.multi_cell(0, 5, f"   Detail: {safe_detail}")
            pdf.ln(2)

        output_path = os.path.join(self.results_dir, f"Audit_Summary_{self.filename}.pdf")
        try:
            pdf.output(output_path)
        except Exception as e:
            print(f"PDF Generation Warning: {e}")
            
        return output_path

    def generate_excel(self):
        """
        Generates an Excel file with grouped rows for large error lists.
        """
        output_path = os.path.join(self.results_dir, f"Audit_Details_{self.filename}.xlsx")
        
        # Convert issues to DataFrame
        df = pd.DataFrame(self.issues)
        if df.empty:
            df = pd.DataFrame(columns=["severity", "type", "location", "detail"])

        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # --- TAB 1: DASHBOARD ---
            ws_summary = workbook.add_worksheet("Executive Summary")
            header_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'bg_color': '#1f4e78', 'font_color': 'white'})
            
            ws_summary.write("B2", "Model Audit Dashboard", header_fmt)
            ws_summary.write("B4", f"Filename: {self.filename}")
            ws_summary.write("B5", f"Complexity Score: {self.complexity_score}/5")
            ws_summary.write("B6", f"Total Issues: {len(self.issues)}")
            
            # --- TAB 2: DETAILED FINDINGS ---
            if not df.empty:
                # Sort by Type so we can group them
                df_sorted = df.sort_values(by=['type', 'severity'])
                df_sorted.to_excel(writer, sheet_name="Findings", index=False, startrow=1)
                
                ws_data = writer.sheets['Findings']
                
                # Format Headers
                data_header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
                for col_num, value in enumerate(df_sorted.columns.values):
                    ws_data.write(0, col_num, value, data_header_fmt)
                    ws_data.set_column(col_num, col_num, 25) # Widen columns

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
        log_path = "audit_history.csv"
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
            