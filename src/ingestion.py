import openpyxl
import pandas as pd
import os
import warnings
from colorama import Fore, Style

# Suppress warnings for "extension is not supported" often found in complex financial models
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

class ModelIngestor:
    """
    The Gateway for the Excel Audit Tool.
    
    Responsibility: 
    1. Load the target workbook in two modes: Values (Math) and Formulas (Logic).
    2. Convert every tab into a high-fidelity DataFrame.
    3. Handle 'External Link' errors gracefully (e.g., FactSet/Bloomberg links).
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        
        # Dual-State Storage
        self.wb_values = None     # Holds calculated numbers (e.g., 150.5)
        self.wb_formulas = None   # Holds logic strings (e.g., =SUM(A1:A5))
        
        # Dictionary Store: { "SheetName": pd.DataFrame }
        self.sheets_values = {}
        self.sheets_formulas = {}
        
        # Error Tracking
        self.load_errors = []

    def ingest(self) -> bool:
        """
        Orchestrates the full loading process. 
        Returns True if the critical mass of the model is loaded.
        """
        print(f"{Fore.CYAN}[*] Starting Ingestion for: {self.filename}{Style.RESET_ALL}")
        
        if not os.path.exists(self.file_path):
            print(f"{Fore.RED}[!] File not found: {self.file_path}{Style.RESET_ALL}")
            return False

        try:
            # 1. Load Values (Numerical Layer)
            print(f"    > Loading Numerical Layer (Values)...")
            self.wb_values = openpyxl.load_workbook(
                self.file_path, data_only=True, read_only=False, keep_vba=False
            )
            
            # 2. Load Logic (Formula Layer)
            print(f"    > Loading Logic Layer (Formulas)...")
            self.wb_formulas = openpyxl.load_workbook(
                self.file_path, data_only=False, read_only=False, keep_vba=False
            )
            
            # 3. Process Sheets
            self._process_all_sheets()
            
            return True

        except Exception as e:
            print(f"{Fore.RED}[!] CRITICAL INGESTION FAILURE: {str(e)}{Style.RESET_ALL}")
            return False

    def _process_all_sheets(self):
        """Iterates through all sheets and converts them to DataFrames."""
        # We assume sheet names are identical in both load modes
        sheet_names = self.wb_values.sheetnames
        print(f"    > Processing {len(sheet_names)} sheets...")

        for sheet in sheet_names:
            try:
                # Extract Values
                df_val = self._sheet_to_df(self.wb_values[sheet])
                self.sheets_values[sheet] = df_val
                
                # Extract Formulas
                df_form = self._sheet_to_df(self.wb_formulas[sheet])
                self.sheets_formulas[sheet] = df_form

            except Exception as e:
                # Log error but do not crash the program
                error_msg = f"Failed to parse sheet '{sheet}': {str(e)}"
                self.load_errors.append(error_msg)
                print(f"{Fore.YELLOW}    [!] Warning: {error_msg}{Style.RESET_ALL}")

    def _sheet_to_df(self, worksheet) -> pd.DataFrame:
        """
        Converts an openpyxl worksheet to a Pandas DataFrame.
        Does NOT use the first row as header automatically to preserve structure.
        """
        data = list(worksheet.values)
        if not data:
            return pd.DataFrame()
        
        # Create DataFrame with 0-based integer index/columns (A=0, B=1...)
        # This aligns perfectly with the Dependency Graph's (row, col) coordinate system.
        df = pd.DataFrame(data)
        return df

    def get_ingestion_report(self):
        """Returns a summary of what was loaded and any errors encountered."""
        return {
            "total_sheets": len(self.sheets_values),
            "sheet_names": list(self.sheets_values.keys()),
            "errors": self.load_errors,
            "status": "Success" if not self.load_errors else "Partial Success"
        }

# For testing this module in isolation
if __name__ == "__main__":
    # Test on the local file assuming standard dir structure
    test_path = os.path.join(os.getcwd(), "data", "pep model for ai eval test.xlsx")
    ingestor = ModelIngestor(test_path)
    if ingestor.ingest():
        report = ingestor.get_ingestion_report()
        print(f"\n{Fore.GREEN}[SUCCESS] Ingestion Complete.{Style.RESET_ALL}")
        print(f"Loaded Sheets: {report['total_sheets']}")
        if report['errors']:
            print(f"Errors: {report['errors']}")