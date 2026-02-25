import argparse
import os
import sys
from src.ingestion import ModelIngestor
from src.dependency import DependencyEngine
from src.auditor import ModelAuditor
from src.reporting import ReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Structural audit of Excel-based financial models"
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=os.path.join("sample_models", "BOBWEIR_Model.xlsx"),
        help="Path to Excel model (.xlsx or .xlsm). Defaults to sample_models/BOBWEIR_Model.xlsx",
    )
    args = parser.parse_args()

    file_path = args.file
    if not os.path.exists(file_path):
        print(f"[!] Error: Model file not found at {file_path}")
        sys.exit(1)

    # --- PHASE I: INGESTION ---
    ingestor = ModelIngestor(file_path)
    if not ingestor.ingest():
        print("[!] Ingestion failed. Exiting.")
        sys.exit(1)

    # --- PHASE II: LOGIC MAPPING ---
    dependency_engine = DependencyEngine(ingestor.sheets_formulas)
    dependency_engine.build_graph()
    structure_stats = dependency_engine.analyze_structure()

    # --- PHASE III: AUDIT ---
    auditor = ModelAuditor(ingestor, dependency_engine)
    issues = auditor.run_all_checks()

    # --- PHASE IV: REPORTING ---
    target_name = os.path.basename(file_path)
    reporter = ReportGenerator(target_name, issues, ingestor, dependency_engine)
    reporter.generate_pdf()
    reporter.generate_excel()
    reporter.update_log()


if __name__ == "__main__":
    main()
