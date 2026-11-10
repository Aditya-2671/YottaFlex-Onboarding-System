from src.validator import validate

if __name__ == '__main__':
    report = validate()
    print(report['summary'])
    for check in report['checks']:
        print(f"[{check['status']}] {check['check']} - {check['detail']}")
    raise SystemExit(1 if report['summary']['failed'] else 0)
