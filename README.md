# YottaFlex.ai Employee Lifecycle Workflow Challenge

A Python project that generates deterministic synthetic employee onboarding
and offboarding data, stores it in CSV/JSON and SQLite, injects seven labelled
edge cases, and validates workflow rules.

## What it generates

The default baseline in `config.json` contains:

- 500 employees across 8 departments, with 50 managers and 12 roles
- 500 onboarding cases and 4,000 task instances with prerequisite links
- 600 assets, 261 asset assignments, and 300 access requests
- Access approvals/provisioning, exit cases, explicit access revocations,
  asset-return and access-removal tasks, department history, and audit events
- Seven deliberate exceptions, labelled separately in `ground_truth/`

People and records are fictional. All generated email addresses use the
reserved `.test` domain.

## Run on Windows

Install Python 3.10+ and open PowerShell in this project folder:

```powershell
python -m pip install -r requirements.txt
python generate.py
python validate.py
python -m pytest -q
```

Alternatively, double-click `RUN_ME.bat`, which installs the listed
dependencies, generates the outputs, validates them, and runs tests.

`python generate.py` writes the output files and prints table row counts plus
the validation result. `python validate.py` reruns validation and writes the
JSON and CSV reports. The test suite checks baseline volumes, validation
results, and deterministic exported-data/ground-truth checksums.

## Main project files

- `config.json` — fixed seed, as-of date, baseline scale, and anomaly counts
- `src/generator.py` — deterministic data generation, exports, SQLite loading,
  and SQL seed export
- `src/validator.py` — relational, workflow, lifecycle, anomaly, and SLA checks
- `database/schema.sql` — current SQLite schema, constraints, and indexes
- `database/seed_data.sql` — self-contained SQLite schema and generated seed
  rows; regenerated with `python generate.py`
- `schemas/data_dictionary.md` — entities, fields, types, keys, cardinalities,
  enum values, and validation rules
- `tests/test_project.py` — automated project tests

## Generated outputs

- `data/*.csv` and `data/*.json` — generated entity tables
- `data/source_manifest.json` — seed, as-of date, and synthetic-data provenance
- `database/yottaflex.db` — SQLite database
- `database/seed_data.sql` — reproducible SQL schema/data dump
- `ground_truth/ground_truth.csv` and `.json` — seven labelled anomalies,
  separate from the entity tables
- `reports/validation_summary.csv` and `.json` — check results and metrics,
  including completion rate, overdue count, late completions, and SLA breaches
- `reports/ACCEPTANCE_MATRIX.md` — challenge requirement-to-implementation map
- `reports/build_verification.json` — result of the recorded local verification

## Workflow and validation

The generator creates master data before dependent records and uses
deterministic IDs. Onboarding tasks use task templates, including role/location
specific variants; dependencies are stored in a bridge table. Access approval
and provisioning dates are explicit, and the validator checks provisioning
does not precede approval. Offboarding creates access-removal and asset-recovery
tasks for each terminated employee and records completed access revocations.

The seven intentional cases cover: task completed before its prerequisite,
missing manager, duplicate active asset assignment, start before background
verification, active access after exit, overdue task, and a department change
during onboarding. The validator checks the expected anomalies against
`ground_truth`, as well as IDs, references, dependency acyclicity, task/date
rules, role/department consistency, approval history, offboarding coverage,
and SQL foreign-key integrity.

SLA metrics are derived from the configured as-of date and task due/completion
dates: open overdue tasks and tasks completed after their due date. No external
SLA policy was provided, so these metrics describe the generated workflow and
are not a production service-level commitment.

## Reproducibility

The generator seeds Python `random` and Faker using the configured seed. Running
`python generate.py` with unchanged configuration reproduces the CSV/JSON and
ground-truth files. The reproducibility test compares their SHA-256 checksums.
SQLite binary bytes are not used for cross-platform checksum comparison;
`database/seed_data.sql` is regenerated from the SQLite database.

To adjust the seed, as-of date, or data scale, edit `config.json`. The default
values match the challenge's requested baseline. If changing scale, keep the
configured values mutually feasible (for example, onboarding cases cannot
exceed employees).

## Challenge submission note

This project and its tests run locally. Per the challenge page, the candidate
still needs to push the project to a **public GitHub repository** and submit
that repository URL before the deadline. This repository folder does not
itself confirm that the upload or submission has happened.

## Limitations

This is a synthetic workflow/data challenge, not a production HR platform. It
does not connect to HRIS, identity providers, ticketing, email, or asset
management systems. The labelled anomalies are intentional test records, not
real employee events. The local validator passing does not guarantee a
particular hidden-grader score.

## Suggested reviewer walkthrough

1. Review `config.json` and `schemas/data_dictionary.md`.
2. Run `python generate.py`, then `python validate.py` and `python -m pytest -q`.
3. Inspect the CSV/JSON outputs and `database/yottaflex.db`.
4. Review the separate `ground_truth/` labels and validation report.
5. Import `database/seed_data.sql` into a clean SQLite database to inspect the
   portable schema/data export.

Do not add real personal data, credentials, or production secrets.
