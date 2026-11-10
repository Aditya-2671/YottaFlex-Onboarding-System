from src.generator import generate, checksums
from src.validator import validate

def test_generator_creates_expected_volumes():
    tables, gt = generate()
    assert len(tables["employees"]) == 500
    assert len(tables["departments"]) == 8
    assert len(tables["managers"]) == 50
    assert len(tables["roles"]) == 12
    assert len(tables["onboarding_cases"]) == 500
    assert len(tables["task_instances"]) == 4000
    assert len(tables["assets"]) == 600
    assert len(tables["access_requests"]) == 300
    assert len(tables["offboarding_cases"]) == 10
    assert len(tables["offboarding_tasks"]) == 20
    assert len(tables["access_revocations"]) == 9
    assert len(gt) == 7

def test_validation_report_has_checks():
    generate()
    report = validate()
    assert report["summary"]["total_checks"] >= 40
    assert report["summary"]["failed"] == 0
    assert report["metrics"]["sla_breach_count"] > 0
    assert report["metrics"]["offboarding_task_count"] == 20

def test_fixed_seed_is_reproducible():
    generate()
    first = checksums()
    generate()
    second = checksums()
    assert first == second
