import networkx as nx
import pandas as pd
from openpyxl.formula.tokenizer import Tokenizer, Token
from openpyxl.utils import get_column_letter
from colorama import Fore, Style

class DependencyEngine:
    """
    The Logic Map.
    
    Responsibility:
    1. Parse Excel formulas to understand "Precedents" (Inputs) and "Dependents" (Outputs).
    2. Build a NetworkX Directed Graph where:
       - Nodes = Cells (e.g., 'Summary!B10')
       - Edges = Data Flow (Source -> Target)
    3. Detect Structural Risks (Circular References, Broken Chains).
    """

    def __init__(self, sheets_formulas: dict):
        self.raw_formulas = sheets_formulas
        self.graph = nx.DiGraph()
        self.node_count = 0

    def build_graph(self):
        """Iterates through every cell in every sheet to map dependencies."""
        print(f"{Fore.CYAN}[*] Building Dependency Graph...{Style.RESET_ALL}")
        
        for sheet_name, df in self.raw_formulas.items():
            # Iterate through the DataFrame (0-indexed)
            for row_idx, row in df.iterrows():
                for col_idx, cell_value in enumerate(row):
                    
                    # We only care about Formulas (strings starting with =)
                    if isinstance(cell_value, str) and cell_value.startswith("="):
                        target_node = self._get_node_id(sheet_name, row_idx, col_idx)
                        self._parse_formula(target_node, cell_value, sheet_name)
                        self.node_count += 1

        print(f"    > Graph Built. Total Calculation Nodes: {self.node_count}")
        print(f"    > Total Dependencies Mapped: {self.graph.number_of_edges()}")

    def _get_node_id(self, sheet, row_idx, col_idx):
        """Standardizes Node IDs: 'SheetName!A1'"""
        col_letter = get_column_letter(col_idx + 1)
        row_num = row_idx + 1
        return f"{sheet}!{col_letter}{row_num}"

    def _parse_formula(self, target_node, formula_str, current_sheet):
        """
        Uses OpenPyXL Tokenizer to find all precedents in a formula.
        Example: =SUM(PFNA!A1:A5) -> Creates edges from PFNA!A1...A5 to Target.
        """
        try:
            tok = Tokenizer(formula_str)
            
            for t in tok.items:
                if t.type == Token.OPERAND:
                    if t.subtype == Token.RANGE:
                        # This token is a reference (e.g., 'Sheet1!A1' or 'A1')
                        self._add_edge(target_node, t.value, current_sheet)
                        
        except Exception:
            # If tokenizer fails (complex array formulas), we flag the node but don't crash
            self.graph.add_node(target_node, status="parse_error")

    def _add_edge(self, target_node, source_ref, current_sheet):
        """
        Resolves the source reference (handling implied sheet names) and adds to Graph.
        """
        # 1. Handle External Links (Don't map, just tag)
        if "[" in source_ref and "]" in source_ref:
            self.graph.add_edge(f"EXT_LINK:{source_ref}", target_node)
            return

        # 2. Parse Sheet vs Cell
        if "!" in source_ref:
            source_sheet, source_range = source_ref.split("!")
            source_sheet = source_sheet.replace("'", "") # Clean quotes
        else:
            source_sheet = current_sheet
            source_range = source_ref

        # 3. Add Edge (Simplification: We link the Range String as the parent for now)
        # In a V2, we would expand 'A1:A5' into 5 distinct nodes. 
        # For now, linking the block is sufficient for logic tracing.
        source_node = f"{source_sheet}!{source_range}"
        self.graph.add_edge(source_node, target_node)

    def analyze_structure(self):
        """Returns high-level structural risks."""
        cycles = list(nx.simple_cycles(self.graph))
        return {
            "circular_references": len(cycles),
            "orphaned_calculations": [n for n, d in self.graph.out_degree() if d == 0 and self.graph.in_degree(n) > 0],
            "complexity_score": self.graph.number_of_edges() / (self.graph.number_of_nodes() + 1)
        }

# Unit Test
if __name__ == "__main__":
    # Mock data to test logic without loading full PEP model
    mock_data = {
        "Summary": pd.DataFrame([["=PFNA!A1 + 100", 50]]),
        "PFNA": pd.DataFrame([[100, 200]])
    }
    
    eng = DependencyEngine(mock_data)
    eng.build_graph()
    print(f"Cycles Detected: {eng.analyze_structure()['circular_references']}")