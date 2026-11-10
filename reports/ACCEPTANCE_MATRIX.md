# Challenge Acceptance Matrix

Assessment is based on the visible requirements in the supplied challenge
screenshots. “Verified” means the current local generator, validator, or test
suite provides evidence; it does not guarantee a hidden-grader score.

| Challenge requirement | Implementation | Evidence / status |
|---|---|---|
| Coordinate HR, IT, facilities, and managers; track dependencies and access removal | Onboarding task templates, manager ownership, task dependencies, access revocations, offboarding tasks | Verified by generated rows and validator |
| Generate master/reference data first | Departments, roles, managers, employees, onboarding cases | Generated in parent-before-child order |
| Generate dependent transactions with valid parent IDs | Task instances, assignments, requests, approvals, exits, history, audit | CSV/JSON exported; SQLite FK check passes |
| Core entities and relational schema | Department, Role, Manager, Employee, OnboardingCase, TaskTemplate/Instance, Asset, AccessRequest, Approval, AuditEvent and workflow history | `database/schema.sql`; field-level definitions in `schemas/data_dictionary.md` |
| Primary/foreign keys and relationship/cardinality documentation | PK/FK constraints and bridge table for task prerequisites | Schema plus data dictionary; SQLite foreign-key check passes |
| Deterministic IDs and fixed seed | Stable entity IDs, seed `20261022` | `config.json`, generator, repeat checksum test |
| Requested baseline volumes | 500 employees, 8 departments, 50 managers, 12 roles, 500 cases, 4,000 tasks, 600 assets, 300 access requests | Configured-volume validator check and test |
| Realistic workforce variation | Remote/on-site, permanent/contractor, future urgent start, terminated employees | `Required workforce variation` validator check |
| Role/location task templates and dependencies | Role/location-specific laptop templates and prerequisite bridge records | `Role/location task template coverage` and dependency/DAG checks |
| Access approval before provisioning | Approval decision date and access provisioned date | Provisioning and request/approval consistency checks |
| Late approvals | Request and decision dates | `Late approvals represented` check |
| Offboarding access revocation and asset recovery | Offboarding cases, revocation records, and two explicit tasks per exit | Coverage and workflow outcome checks; one labelled access exception remains open |
| Preserve state changes and traceability | Audit events, department history, revocation history | State-change audit check |
| Seven required negative/edge cases | One labelled case for each listed anomaly category | Ground-truth labels align with validator checks |
| Derived values and SLA metrics | Task status/date relationships, completion rate, overdue and late-completion counts | Metrics in `reports/validation_summary.json`; SLA reconciliation check |
| CSV, JSON, SQLite, SQL seed, README, schema, data dictionary, source manifest, validation summary | Generator exports all requested formats and provenance | Generated and cross-checked locally |
| Repeat generation and compare checksums | Checksums cover generated data and ground-truth exports | `test_fixed_seed_is_reproducible` |
| Tests and reproducible local run instructions | pytest suite, `RUN_ME.bat`, Python commands | Latest local run: 3 tests passed, 48 validator checks passed |
| Public GitHub repository and submission | Candidate action outside the local project files | **Not verified here; candidate must publish and submit the repository URL** |

## Latest local verification

- `python generate.py`: generated the configured baseline and current SQL seed.
- `python validate.py`: 48 checks passed, 0 failed.
- `python -m pytest -q`: 3 tests passed.
- Generated CSV headers match SQLite table columns; SQLite foreign-key check
  reported no violations.

Run the commands again after modifying code or configuration. The build report
is a snapshot of a local verification, not proof of public repository
submission or hidden-grader acceptance.
