from src.generator import generate
from src.validator import validate

if __name__ == "__main__":
    tables, anomalies = generate()
    print("Dataset generation complete.")
    print("Table counts:")
    for name, rows in tables.items():
        print(f"  {name}: {len(rows)}")
    print(f"Ground-truth anomalies: {len(anomalies)}")
    report = validate()
    print(f"Validation: {report['summary']['passed']}/{report['summary']['total_checks']} checks passed.")
    if report["summary"]["failed"]:
        raise SystemExit("Some validation checks failed. Review reports/validation_summary.json")
