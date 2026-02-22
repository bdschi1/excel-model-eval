import os
import sys
from src.ingestion import ModelIngestor
from src.dependency import DependencyEngine
from src.auditor import ModelAuditor
from src.reporting import ReportGenerator

def main():
    # 1. Configuration
    TARGET_FILE = "pep model for ai eval test.xlsx"
    BASE_DIR = os.getcwd()
    DATA_DIR = os.path.join(BASE_DIR, "data")
    FILE_PATH = os.path.join(DATA_DIR, TARGET_FILE)

    # 2. Validation
    if not os.path.exists(FILE_PATH):
        print(f"[!] Error: Model file not found at {FILE_PATH}")
        print("    Please ensure 'pep model for ai eval test.xlsx' is in the 'data' folder.")
        sys.exit(1)

    # 3. Execution Pipeline
    
    # --- PHASE I: INGESTION ---
    # The Ingestor handles loading values and formulas
    ingestor = ModelIngestor(FILE_PATH)
    if not ingestor.ingest():
        print("[!] Ingestion failed. Exiting.")
        sys.exit(1)

    # --- PHASE II: LOGIC MAPPING ---
    # We pass the formula layers to the graph engine
    dependency_engine = DependencyEngine(ingestor.sheets_formulas)
    dependency_engine.build_graph()
    structure_stats = dependency_engine.analyze_structure()

    # --- PHASE III: AUDIT ---
    # The Auditor needs both the values (for math checks) and the graph (for logic checks)
    auditor = ModelAuditor(ingestor, dependency_engine)
    issues = auditor.run_all_checks()

    # --- PHASE IV: REPORTING ---
    # Generate the final output
    reporter = ReportGenerator(TARGET_FILE, issues, ingestor, dependency_engine)
    reporter.generate_pdf()
    reporter.generate_excel()
    reporter.update_log()

if __name__ == "__main__":
    main()