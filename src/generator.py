
from __future__ import annotations

import csv
import json
import random
import sqlite3
import hashlib
from pathlib import Path
from datetime import date, timedelta

from faker import Faker


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads(
    (ROOT / "config.json").read_text(encoding="utf-8")
)

SEED = int(CONFIG["seed"])
AS_OF = date.fromisoformat(CONFIG["as_of_date"])

DEPARTMENTS = [
    "Engineering", "Human Resources", "Finance", "IT",
    "Facilities", "Sales", "Operations", "Marketing"
]

ROLES = [
    ("Software Engineer", "Engineering"),
    ("Data Analyst", "Engineering"),
    ("Product Manager", "Engineering"),
    ("HR Specialist", "Human Resources"),
    ("Recruiter", "Human Resources"),
    ("Accountant", "Finance"),
    ("IT Support Engineer", "IT"),
    ("Systems Administrator", "IT"),
    ("Facilities Coordinator", "Facilities"),
    ("Sales Executive", "Sales"),
    ("Operations Analyst", "Operations"),
    ("Marketing Specialist", "Marketing")
]

TASKS = [
    ("Sign employment documents", "Human Resources", None),
    ("Complete background verification", "Human Resources", None),
    ("Create corporate account", "IT", "Complete background verification"),
    ("Provision role access", "IT", "Approve access request"),
    ("Approve access request", "Manager", None),
    ("Prepare laptop", "IT", "Sign employment documents"),
    ("Prepare workspace", "Facilities", "Sign employment documents"),
    ("Complete HR orientation", "Human Resources", "Sign employment documents")
]

SYSTEMS = [
    "Email", "HRIS", "CRM", "Source Control",
    "VPN", "Finance Portal"
]


def deterministic_id(prefix: str, number: int, width: int = 6) -> str:
    return f"{prefix}{number:0{width}d}"


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def generate():
    random.seed(SEED)

    fake = Faker()
    Faker.seed(SEED)

    scale = CONFIG["scale"]

    data_dir = ROOT / "data"
    gt_dir = ROOT / "ground_truth"

    data_dir.mkdir(parents=True, exist_ok=True)
    gt_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # 1. Departments
    # --------------------------------------------------

    if not 1 <= scale["departments"] <= len(DEPARTMENTS):
        raise ValueError(f"departments must be between 1 and {len(DEPARTMENTS)}.")

    departments = [
        {
            "department_id": f"DEPT-{i + 1:03d}",
            "department_name": name
        }
        for i, name in enumerate(DEPARTMENTS[:scale["departments"]])
    ]

    # --------------------------------------------------
    # 2. Roles
    # --------------------------------------------------

    available_roles = [
        (name, dept) for name, dept in ROLES
        if dept in {department["department_name"] for department in departments}
    ]
    if not 1 <= scale["roles"] <= len(available_roles):
        raise ValueError(
            f"roles must be between 1 and {len(available_roles)} "
            "for the configured departments."
        )

    roles = [
        {
            "role_id": f"ROLE-{i + 1:03d}",
            "role_name": name,
            "department_id": next(
                d["department_id"]
                for d in departments
                if d["department_name"] == dept
            )
        }
        for i, (name, dept) in enumerate(available_roles[:scale["roles"]])
    ]

    # --------------------------------------------------
    # 3. Managers
    # --------------------------------------------------

    managers = []

    for i in range(scale["managers"]):
        dept = departments[i % len(departments)]

        managers.append({
            "manager_id": f"MGR-{i + 1:04d}",
            "manager_name": fake.name(),
            "department_id": dept["department_id"],
            "email": f"manager{i + 1}@example.test"
        })

    if not managers:
        raise ValueError("At least one manager is required.")

    # --------------------------------------------------
    # 4. Employees
    # --------------------------------------------------

    employees = []

    for i in range(scale["employees"]):
        role = roles[i % len(roles)]
        manager = managers[i % len(managers)]

        start = AS_OF + timedelta(days=random.randint(-100, 30))

        employees.append({
            "employee_id": deterministic_id("EMP-", i + 1),
            "employee_name": fake.name(),
            "email": f"employee{i + 1}@example.test",
            "department_id": role["department_id"],
            "role_id": role["role_id"],
            "manager_id": manager["manager_id"],
            "employment_type": random.choice(
                ["Permanent", "Contractor"]
            ),
            "work_location": random.choice(["Remote", "On-site"]),
            "start_date": start.isoformat(),
            "employment_status": (
                "Active" if start <= AS_OF else "Preboarding"
            )
        })

    for employee in employees[-min(10, len(employees)):]:
        employee["start_date"] = (AS_OF - timedelta(days=60)).isoformat()
        employee["employment_status"] = "Active"

    if len(employees) > 10:
        employees[5]["start_date"] = (AS_OF + timedelta(days=3)).isoformat()
        employees[5]["employment_status"] = "Preboarding"

    # --------------------------------------------------
    # 5. Onboarding cases
    # --------------------------------------------------

    if scale["onboarding_cases"] > len(employees):
        raise ValueError(
            "Onboarding case count cannot exceed employee count."
        )

    cases = [
        {
            "case_id": f"ONB-2026-{i + 1:06d}",
            "employee_id": employees[i]["employee_id"],
            "created_date": (
                date.fromisoformat(employees[i]["start_date"])
                - timedelta(days=14)
            ).isoformat(),
            "case_status": "In Progress"
        }
        for i in range(scale["onboarding_cases"])
    ]

    if not cases:
        raise ValueError("At least one onboarding case is required.")

    # --------------------------------------------------
    # 6. Task templates
    # --------------------------------------------------

    templates = []

    for i in range(8):
        task = TASKS[i]

        templates.append({
            "template_id": f"TPL-{i + 1:03d}",
            "task_name": task[0],
            "department_owner": task[1],
            "required_role": None,
            "required_location": None,
            "sequence_number": i + 1
        })

    for role in roles:
        for location in ("Remote", "On-site"):
            templates.append({
                "template_id": f"TPL-{len(templates) + 1:03d}",
                "task_name": "Prepare laptop",
                "department_owner": "IT",
                "required_role": role["role_id"],
                "required_location": location,
                "sequence_number": 6
            })

    # --------------------------------------------------
    # 7. Task instances and dependencies
    # --------------------------------------------------

    task_rows = []
    dependencies = []
    case_statuses = {}

    for i in range(scale["tasks"]):

        case_idx = i % len(cases)
        case = cases[case_idx]

        task_no = i // len(cases) + 1

        # Keep the same task sequence for every onboarding case.
        template = templates[(task_no - 1) % len(TASKS)]
        if (task_no - 1) % len(TASKS) == 5:
            employee = employees[case_idx]
            tailored_template = next(
                (
                    candidate for candidate in templates[len(TASKS):]
                    if candidate["required_role"] == employee["role_id"]
                    and candidate["required_location"] == employee["work_location"]
                ),
                None
            )
            if tailored_template:
                template = tailored_template

        task_id = (
            f"TASK-ONB-{case['case_id']}-{task_no:03d}"
        )

        due = (
            date.fromisoformat(case["created_date"])
            + timedelta(days=task_no * 2 + 4)
        )

        completed = None
        previous_task = None
        previous_status = None

        if task_no > 1:
            previous_task = (
                f"TASK-ONB-{case['case_id']}-{task_no - 1:03d}"
            )
            previous_status = case_statuses.get(case["case_id"], {}).get(previous_task)

        # Background verification must be completed for the
        # baseline employees, before their employment start date.
        if (
            template["task_name"] == "Complete background verification"
            and (task_no == 1 or previous_status == "Completed")
        ):
            employee_start = date.fromisoformat(
                employees[case_idx]["start_date"]
            )

            candidate_completion = min(due - timedelta(days=1), employee_start)
            if candidate_completion <= AS_OF:
                completed = candidate_completion

        elif task_no > 1 and previous_status != "Completed":
            completed = None

        elif random.random() < 0.62 and due - timedelta(days=1) <= AS_OF:
            completed = due - timedelta(days=1)

        status = (
            "Completed"
            if completed
            else ("Overdue" if due < AS_OF else "Pending")
        )

        task_rows.append({
            "task_id": task_id,
            "case_id": case["case_id"],
            "template_id": template["template_id"],
            "owner_manager_id": employees[case_idx]["manager_id"] or next(
                (
                    manager["manager_id"] for manager in managers
                    if manager["department_id"] == employees[case_idx]["department_id"]
                ),
                managers[0]["manager_id"]
            ),
            "task_status": status,
            "due_date": due.isoformat(),
            "completed_date": completed.isoformat() if completed else ""
        })

        case_statuses.setdefault(case["case_id"], {})[task_id] = status

        if task_no > 1:
            dependencies.append({
                "task_id": task_id,
                "prerequisite_task_id": previous_task
            })

    # --------------------------------------------------
    # 8. Assets
    # --------------------------------------------------

    assets = []

    for i in range(scale["assets"]):
        asset_type = [
            "Laptop", "Monitor", "Phone", "Access Card"
        ][i % 4]

        assets.append({
            "asset_id": f"AST-{asset_type[:3].upper()}-{i + 1:06d}",
            "asset_type": asset_type,
            "serial_number": f"SERIAL-{i + 1:07d}",
            "asset_status": "Available"
        })

    # --------------------------------------------------
    # 9. Access requests
    # --------------------------------------------------

    access = []

    for i in range(scale["access_requests"]):
        emp = employees[i % len(employees)]

        access.append({
            "request_id": f"ACCREQ-2026-{i + 1:06d}",
            "employee_id": emp["employee_id"],
            "system_name": SYSTEMS[i % len(SYSTEMS)],
            "request_status": "Approved" if i % 3 else "Pending",
            "request_date": (
                AS_OF - timedelta(days=random.randint(1, 60))
            ).isoformat(),
            "provisioned_date": ""
        })

    # --------------------------------------------------
    # 10. Asset assignments
    # --------------------------------------------------

    assignments = []

    for i in range(min(250, len(assets), len(employees))):
        assignments.append({
            "assignment_id": f"ASSIGN-{i + 1:06d}",
            "asset_id": assets[i]["asset_id"],
            "employee_id": employees[i]["employee_id"],
            "assigned_date": AS_OF.isoformat(),
            "returned_date": ""
        })

        assets[i]["asset_status"] = "Assigned"

    offboarding_count = min(10, len(employees))
    exiting_employees = (
        employees[-offboarding_count:] if offboarding_count else []
    )
    for i in range(min(offboarding_count, len(assets) - len(assignments))):
        employee = exiting_employees[-(i + 1)]
        asset = assets[len(assignments)]
        assignments.append({
            "assignment_id": f"ASSIGN-{len(assignments) + 1:06d}",
            "asset_id": asset["asset_id"],
            "employee_id": employee["employee_id"],
            "assigned_date": (AS_OF - timedelta(days=30)).isoformat(),
            "returned_date": ""
        })
        asset["asset_status"] = "Assigned"

    # --------------------------------------------------
    # 11. Approvals
    # --------------------------------------------------

    approvals = []

    for i, req in enumerate(access):
        approvals.append({
            "approval_id": f"APR-{i + 1:06d}",
            "request_id": req["request_id"],
            "task_id": "",
            "approver_id": managers[i % len(managers)]["manager_id"],
            "decision": (
                "Approved"
                if req["request_status"] == "Approved"
                else "Pending"
            ),
            "decision_date": (
                min(
                    AS_OF,
                    date.fromisoformat(req["request_date"])
                    + timedelta(days=random.randint(1, 10))
                ).isoformat()
                if req["request_status"] == "Approved"
                else ""
            )
        })

        if req["request_status"] == "Approved":
            req["provisioned_date"] = approvals[-1]["decision_date"]

    # --------------------------------------------------
    # 12. Offboarding
    # --------------------------------------------------

    offboarding = []

    for i in range(offboarding_count):
        emp = employees[-(i + 1)]

        emp["employment_status"] = "Terminated"

        offboarding.append({
            "offboarding_id": f"OFF-{i + 1:06d}",
            "employee_id": emp["employee_id"],
            "exit_date": AS_OF.isoformat(),
            "case_status": "In Progress"
        })

    # Give every exiting employee an access and asset recovery workflow.
    for i, employee in enumerate(exiting_employees):
        request = access[-(i + 1)]
        request["employee_id"] = employee["employee_id"]
        request["request_status"] = "Approved"
        request["request_date"] = (AS_OF - timedelta(days=10)).isoformat()
        request["provisioned_date"] = (AS_OF - timedelta(days=5)).isoformat()

        approval = next(
            approval for approval in approvals
            if approval["request_id"] == request["request_id"]
        )
        approval["decision"] = "Approved"
        approval["decision_date"] = (AS_OF - timedelta(days=5)).isoformat()

        # Assets issued to exiting employees are recovered at the exit date.
        assignment = next(
            assignment for assignment in assignments
            if assignment["employee_id"] == employee["employee_id"]
        )
        assignment["returned_date"] = AS_OF.isoformat()
        assets_by_id = {asset["asset_id"]: asset for asset in assets}
        assets_by_id[assignment["asset_id"]]["asset_status"] = "Available"

    # Keep one labelled offboarding-access anomaly while revoking all other exits.
    access_revocations = []
    if offboarding_count:
        anomaly_employee_id = employees[-1]["employee_id"]
        for request in access[-offboarding_count:]:
            if request["employee_id"] != anomaly_employee_id:
                request["request_status"] = "Revoked"
                access_revocations.append({
                    "revocation_id": f"REVOKE-{len(access_revocations) + 1:06d}",
                    "request_id": request["request_id"],
                    "employee_id": request["employee_id"],
                    "revoked_date": AS_OF.isoformat(),
                    "reason": "Employee offboarding"
                })

    # --------------------------------------------------
    # 13. Department history and audit
    # --------------------------------------------------

    dept_history = []
    audit = []

    for i, emp in enumerate(employees):
        audit.append({
            "audit_id": f"AUD-{AS_OF.strftime('%Y%m%d')}-{i + 1:06d}",
            "entity_type": "Employee",
            "entity_id": emp["employee_id"],
            "event_type": "EmployeeCreated",
            "event_timestamp": AS_OF.isoformat() + "T09:00:00",
            "actor_id": "SYSTEM",
            "details": "Synthetic baseline record created"
        })

    # --------------------------------------------------
    # 14. Deliberately labelled anomalies
    # --------------------------------------------------

    ground_truth = []

    # ANOM-001: Completed task before its prerequisite.
    if len(task_rows) > len(cases):
        prerequisite = task_rows[0]
        dependent = task_rows[len(cases)]

        prerequisite["task_status"] = "Pending"
        prerequisite["completed_date"] = ""

        dependent["task_status"] = "Completed"
        dependent["completed_date"] = (
            date.fromisoformat(dependent["due_date"])
            - timedelta(days=3)
        ).isoformat()

        ground_truth.append({
            "anomaly_id": "ANOM-001",
            "issue_type": "task_before_prerequisite",
            "entity_id": dependent["task_id"],
            "expected_detection": (
                "Completed task has an incomplete prerequisite"
            )
        })

    # ANOM-002: Missing manager.
    if len(employees) > 1:
        employees[1]["manager_id"] = ""

        ground_truth.append({
            "anomaly_id": "ANOM-002",
            "issue_type": "missing_manager",
            "entity_id": employees[1]["employee_id"],
            "expected_detection": "Employee manager is missing"
        })

    # ANOM-003: Duplicate active asset assignment.
    if assignments and len(employees) > 2:
        assignments.append({
            "assignment_id": "ASSIGN-ANOM-001",
            "asset_id": assignments[0]["asset_id"],
            "employee_id": employees[2]["employee_id"],
            "assigned_date": AS_OF.isoformat(),
            "returned_date": ""
        })

        ground_truth.append({
            "anomaly_id": "ANOM-003",
            "issue_type": "duplicate_asset_assignment",
            "entity_id": assignments[0]["asset_id"],
            "expected_detection": (
                "Asset has overlapping active assignments"
            )
        })

    # ANOM-004: Employee starts before background verification completes.
    if len(employees) > 3 and len(cases) > 3:
        employees[3]["start_date"] = (
            AS_OF - timedelta(days=1)
        ).isoformat()

        bg_task = task_rows[3 + len(cases)]

        bg_task["task_status"] = "Completed"
        bg_task["completed_date"] = AS_OF.isoformat()

        ground_truth.append({
            "anomaly_id": "ANOM-004",
            "issue_type": "start_before_background_check",
            "entity_id": employees[3]["employee_id"],
            "expected_detection": (
                "Start date precedes background verification completion"
            )
        })

    # ANOM-005: Terminated employee retains approved access.
    if employees and access and approvals:
        terminated = employees[-1]

        access[0]["employee_id"] = terminated["employee_id"]
        access[0]["request_status"] = "Approved"
        access[0]["request_date"] = (AS_OF - timedelta(days=10)).isoformat()
        access[0]["provisioned_date"] = (AS_OF - timedelta(days=5)).isoformat()
        approvals[0]["decision"] = "Approved"
        approvals[0]["decision_date"] = (
            AS_OF - timedelta(days=5)
        ).isoformat()

        ground_truth.append({
            "anomaly_id": "ANOM-005",
            "issue_type": "offboarding_active_access",
            "entity_id": terminated["employee_id"],
            "expected_detection": (
                "Terminated employee retains approved access"
            )
        })

    # ANOM-006: Open task past its due date.
    if task_rows:
        task_rows[-1]["task_status"] = "Overdue"
        task_rows[-1]["completed_date"] = ""
        task_rows[-1]["due_date"] = (
            AS_OF - timedelta(days=7)
        ).isoformat()

        ground_truth.append({
            "anomaly_id": "ANOM-006",
            "issue_type": "overdue_tasks",
            "entity_id": task_rows[-1]["task_id"],
            "expected_detection": "Open task is past its due date"
        })

    # ANOM-007: Mid-process department transfer.
    if len(employees) > 4:
        old = employees[4]["department_id"]
        eligible_departments = list(dict.fromkeys(
            role["department_id"] for role in roles
        ))
        transfer_options = [
            department_id for department_id in eligible_departments
            if department_id != old
        ]
        new = transfer_options[0] if transfer_options else old

        if new != old:
            dept_history.append({
                "history_id": "DEPT-HIST-ANOM-001",
                "employee_id": employees[4]["employee_id"],
                "old_department_id": old,
                "new_department_id": new,
                "effective_date": AS_OF.isoformat()
            })

            employees[4]["department_id"] = new
            employees[4]["role_id"] = next(
                role["role_id"] for role in roles
                if role["department_id"] == new
            )

            ground_truth.append({
                "anomaly_id": "ANOM-007",
                "issue_type": "mid_process_department_change",
                "entity_id": employees[4]["employee_id"],
                "expected_detection": (
                    "Department changed during active onboarding"
                )
            })

    offboarding_tasks = []
    for case in offboarding:
        employee_id = case["employee_id"]
        active_access = [
            request for request in access
            if request["employee_id"] == employee_id
            and request["request_status"] == "Approved"
        ]
        employee_assignments = [
            assignment for assignment in assignments
            if assignment["employee_id"] == employee_id
        ]
        assets_recovered = all(
            assignment["returned_date"] for assignment in employee_assignments
        )
        for task_no, (task_name, complete) in enumerate([
            ("Revoke system access", not active_access),
            ("Recover assigned assets", assets_recovered)
        ], start=1):
            offboarding_tasks.append({
                "offboarding_task_id": (
                    f"TASK-OFF-{case['offboarding_id']}-{task_no:03d}"
                ),
                "offboarding_id": case["offboarding_id"],
                "employee_id": employee_id,
                "task_name": task_name,
                "task_status": "Completed" if complete else "Pending",
                "due_date": AS_OF.isoformat(),
                "completed_date": AS_OF.isoformat() if complete else ""
            })

    audit_sequence = len(audit)
    for request in access:
        if request["provisioned_date"]:
            audit_sequence += 1
            audit.append({
                "audit_id": f"AUD-{AS_OF.strftime('%Y%m%d')}-{audit_sequence:06d}",
                "entity_type": "AccessRequest",
                "entity_id": request["request_id"],
                "event_type": "AccessProvisioned",
                "event_timestamp": request["provisioned_date"] + "T09:00:00",
                "actor_id": "SYSTEM",
                "details": "Access provisioned after approval"
            })
    for revocation in access_revocations:
        audit_sequence += 1
        audit.append({
            "audit_id": f"AUD-{AS_OF.strftime('%Y%m%d')}-{audit_sequence:06d}",
            "entity_type": "AccessRequest",
            "entity_id": revocation["request_id"],
            "event_type": "AccessRevoked",
            "event_timestamp": revocation["revoked_date"] + "T09:00:00",
            "actor_id": "SYSTEM",
            "details": revocation["reason"]
        })
    for case in offboarding:
        audit_sequence += 1
        audit.append({
            "audit_id": f"AUD-{AS_OF.strftime('%Y%m%d')}-{audit_sequence:06d}",
            "entity_type": "OffboardingCase",
            "entity_id": case["offboarding_id"],
            "event_type": "OffboardingStarted",
            "event_timestamp": case["exit_date"] + "T09:00:00",
            "actor_id": "SYSTEM",
            "details": f"Offboarding started for {case['employee_id']}"
        })
    for history in dept_history:
        audit_sequence += 1
        audit.append({
            "audit_id": f"AUD-{AS_OF.strftime('%Y%m%d')}-{audit_sequence:06d}",
            "entity_type": "Employee",
            "entity_id": history["employee_id"],
            "event_type": "DepartmentChanged",
            "event_timestamp": history["effective_date"] + "T09:00:00",
            "actor_id": "SYSTEM",
            "details": (
                f"Department changed from {history['old_department_id']} "
                f"to {history['new_department_id']}"
            )
        })

    # --------------------------------------------------
    # 15. Normalize the one intentional dependency violation.
    # --------------------------------------------------

    intentional_violation = None
    for record in ground_truth:
        if record["issue_type"] == "task_before_prerequisite":
            intentional_violation = record["entity_id"]
            break

    if intentional_violation:
        task_by_id = {task["task_id"]: task for task in task_rows}
        prerequisite_by_task = {
            dep["task_id"]: dep["prerequisite_task_id"]
            for dep in dependencies
        }

        for task in task_rows:
            prereq_id = prerequisite_by_task.get(task["task_id"])
            if (
                prereq_id
                and task["task_id"] != intentional_violation
                and task["task_status"] == "Completed"
            ):
                prereq = task_by_id.get(prereq_id)
                if prereq and prereq["task_status"] != "Completed":
                    task["task_status"] = (
                        "Overdue" if task["due_date"] < AS_OF.isoformat() else "Pending"
                    )
                    task["completed_date"] = ""

        target = task_by_id.get(intentional_violation)
        if target:
            prereq_id = prerequisite_by_task.get(target["task_id"])
            prereq = task_by_id.get(prereq_id)
            if prereq:
                prereq["task_status"] = "Pending"
                prereq["completed_date"] = ""

            target["task_status"] = "Completed"
            target["completed_date"] = (
                min(
                    AS_OF,
                    date.fromisoformat(target["due_date"]) - timedelta(days=3)
                )
            ).isoformat()

    tasks_by_case = {}
    for task in task_rows:
        tasks_by_case.setdefault(task["case_id"], []).append(task)
    for case in cases:
        case_tasks = tasks_by_case.get(case["case_id"], [])
        if case_tasks and all(t["task_status"] == "Completed" for t in case_tasks):
            case["case_status"] = "Completed"
        elif any(t["task_status"] in ("In Progress", "Completed", "Overdue") for t in case_tasks):
            case["case_status"] = "In Progress"
        else:
            case["case_status"] = "Not Started"

    # --------------------------------------------------
    # 16. Assemble tables
    # --------------------------------------------------

    tables = {
        "departments": departments,
        "roles": roles,
        "managers": managers,
        "employees": employees,
        "onboarding_cases": cases,
        "task_templates": templates,
        "task_instances": task_rows,
        "task_dependencies": dependencies,
        "assets": assets,
        "asset_assignments": assignments,
        "access_requests": access,
        "approvals": approvals,
        "offboarding_cases": offboarding,
        "offboarding_tasks": offboarding_tasks,
        "access_revocations": access_revocations,
        "employee_department_history": dept_history,
        "audit_events": audit
    }

    # --------------------------------------------------
    # 16. CSV and JSON exports
    # --------------------------------------------------

    for name, rows in tables.items():
        write_csv(data_dir / f"{name}.csv", rows)

        (data_dir / f"{name}.json").write_text(
            json.dumps(rows, indent=2),
            encoding="utf-8"
        )

    write_csv(gt_dir / "ground_truth.csv", ground_truth)

    (gt_dir / "ground_truth.json").write_text(
        json.dumps(ground_truth, indent=2),
        encoding="utf-8"
    )

    # --------------------------------------------------
    # 17. Source manifest
    # --------------------------------------------------

    manifest = {
        "generator": "src/generator.py",
        "seed": SEED,
        "as_of_date": AS_OF.isoformat(),
        "data_kind": "synthetic",
        "external_sources": [],
        "note": "All people and records are fictional synthetic data."
    }

    (data_dir / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    # --------------------------------------------------
    # 18. Database loading
    # --------------------------------------------------

    load_database(tables)

    return tables, ground_truth


def load_database(tables):
    db = ROOT / "database" / "yottaflex.db"

    db.parent.mkdir(parents=True, exist_ok=True)

    if db.exists():
        db.unlink()

    conn = sqlite3.connect(db)

    try:
        conn.execute("PRAGMA foreign_keys=ON")

        conn.executescript(
            (ROOT / "database" / "schema.sql").read_text(
                encoding="utf-8"
            )
        )

        order = [
            "departments",
            "roles",
            "managers",
            "employees",
            "onboarding_cases",
            "task_templates",
            "task_instances",
            "task_dependencies",
            "assets",
            "asset_assignments",
            "access_requests",
            "approvals",
            "offboarding_cases",
            "access_revocations",
            "offboarding_tasks",
            "employee_department_history",
            "audit_events"
        ]

        for table in order:
            rows = tables[table]

            if not rows:
                continue

            columns = list(rows[0].keys())

            sql = (
                f"INSERT INTO {table} "
                f"({','.join(columns)}) "
                f"VALUES ({','.join(['?'] * len(columns))})"
            )

            values = [
                [
                    None if row.get(column, "") == ""
                    else row.get(column)
                    for column in columns
                ]
                for row in rows
            ]

            conn.executemany(sql, values)

        conn.commit()

        violations = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(
                f"SQLite foreign-key violations: {violations}"
            )

        seed_sql = (
            "PRAGMA foreign_keys = OFF;\n"
            + "\n".join(conn.iterdump())
            + "\nPRAGMA foreign_keys = ON;\n"
        )
        (ROOT / "database" / "seed_data.sql").write_text(
            seed_sql,
            encoding="utf-8"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def checksums():
    result = {}

    output_files = [
        path
        for directory in (ROOT / "data", ROOT / "ground_truth")
        for path in directory.glob("*")
        if path.is_file()
    ]
    for path in sorted(output_files):
        result[str(path.relative_to(ROOT))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

    return result


if __name__ == "__main__":
    tables, ground_truth = generate()

    total_rows = sum(len(rows) for rows in tables.values())

    print(
        f"Generated {total_rows} rows across "
        f"{len(tables)} tables."
    )

    print(
        f"Generated {len(ground_truth)} labelled anomalies."
    )
