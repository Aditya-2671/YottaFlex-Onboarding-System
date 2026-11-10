import csv, json, sqlite3
from pathlib import Path
from datetime import date
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
AS_OF = date.fromisoformat(CONFIG["as_of_date"])

def read_rows(name):
    with (ROOT/"data"/f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def validate():
    results = []
    def add(name, passed, detail):
        results.append({"check":name,"status":"PASS" if passed else "FAIL","detail":detail})

    employees = read_rows("employees")
    departments = read_rows("departments")
    roles = read_rows("roles")
    managers = read_rows("managers")
    cases = read_rows("onboarding_cases")
    tasks = read_rows("task_instances")
    templates = read_rows("task_templates")
    deps = read_rows("task_dependencies")
    assets = read_rows("assets")
    assignments = read_rows("asset_assignments")
    access = read_rows("access_requests")
    approvals = read_rows("approvals")
    offboarding = read_rows("offboarding_cases")
    offboarding_tasks = read_rows("offboarding_tasks")
    revocations = read_rows("access_revocations")
    history = read_rows("employee_department_history")
    audit = read_rows("audit_events")
    gt = json.loads((ROOT/"ground_truth"/"ground_truth.json").read_text())
    access_by_id = {request["request_id"]: request for request in access}

    primary_keys = [
        ("departments", departments, "department_id"),
        ("roles", roles, "role_id"),
        ("managers", managers, "manager_id"),
        ("employees", employees, "employee_id"),
        ("onboarding_cases", cases, "case_id"),
        ("task_templates", templates, "template_id"),
        ("task_instances", tasks, "task_id"),
        ("assets", assets, "asset_id"),
        ("asset_assignments", assignments, "assignment_id"),
        ("access_requests", access, "request_id"),
        ("approvals", approvals, "approval_id"),
        ("offboarding_cases", offboarding, "offboarding_id"),
        ("offboarding_tasks", offboarding_tasks, "offboarding_task_id"),
        ("access_revocations", revocations, "revocation_id"),
        ("employee_department_history", history, "history_id"),
        ("audit_events", audit, "audit_id")
    ]
    for table, rows, key in primary_keys:
        vals = [r[key] for r in rows]
        add(f"{table} primary-key uniqueness", all(vals) and len(vals)==len(set(vals)),
            f"{len(vals)} rows; {len(set(vals))} unique IDs")

    scale = CONFIG["scale"]
    expected_counts = {
        "employees": scale["employees"],
        "departments": scale["departments"],
        "roles": scale["roles"],
        "managers": scale["managers"],
        "onboarding_cases": scale["onboarding_cases"],
        "task_instances": scale["tasks"],
        "assets": scale["assets"],
        "access_requests": scale["access_requests"]
    }
    actual_counts = {
        "employees": len(employees),
        "departments": len(departments),
        "roles": len(roles),
        "managers": len(managers),
        "onboarding_cases": len(cases),
        "task_instances": len(tasks),
        "assets": len(assets),
        "access_requests": len(access)
    }
    add("Configured baseline volumes", actual_counts == expected_counts,
        f"Expected {expected_counts}; generated {actual_counts}")

    emp_ids = {e["employee_id"] for e in employees}
    dept_ids = {d["department_id"] for d in departments}
    role_ids = {r["role_id"] for r in roles}
    manager_ids = {m["manager_id"] for m in managers}
    case_ids = {c["case_id"] for c in cases}
    task_ids = {t["task_id"] for t in tasks}
    add("Employee-to-case coverage", all(c["employee_id"] in emp_ids for c in cases), "Every case references an employee")
    add("Task-to-case integrity", all(t["case_id"] in case_ids for t in tasks), "Every task references a case")
    add("Dependency references", all(d["task_id"] in task_ids and d["prerequisite_task_id"] in task_ids for d in deps), "Dependency endpoints exist")
    employee_fk_valid = all(
        e["department_id"] in dept_ids
        and e["role_id"] in role_ids
        and (not e["manager_id"] or e["manager_id"] in manager_ids)
        for e in employees
    )
    add("Employee reference integrity", employee_fk_valid,
        "Employee department, role and optional manager references resolve")
    owner_ids = {t["owner_manager_id"] for t in tasks}
    add("Task owner validity", bool(owner_ids) and owner_ids.issubset(manager_ids),
        "Every task has a valid manager owner")
    add("Role-department alignment",
        all(
            next(r for r in roles if r["role_id"] == e["role_id"])["department_id"]
            == e["department_id"]
            for e in employees
        ),
        "Each employee's role belongs to the employee's current department")
    template_by_id = {t["template_id"]: t for t in templates}
    case_by_id = {c["case_id"]: c for c in cases}
    employee_by_id = {e["employee_id"]: e for e in employees}
    role_location_pairs = {
        (t["required_role"], t["required_location"])
        for t in templates if t["required_role"]
    }
    expected_role_location_pairs = {
        (role["role_id"], location)
        for role in roles for location in ("Remote", "On-site")
    }
    tailored_tasks_match = all(
        template_by_id[t["template_id"]]["required_role"]
        == employee_by_id[case_by_id[t["case_id"]]["employee_id"]]["role_id"]
        and template_by_id[t["template_id"]]["required_location"]
        == employee_by_id[case_by_id[t["case_id"]]["employee_id"]]["work_location"]
        for t in tasks
        if template_by_id[t["template_id"]]["sequence_number"] == 6
    )
    add("Role/location task template coverage",
        role_location_pairs == expected_role_location_pairs and tailored_tasks_match,
        f"{len(role_location_pairs)} role/location templates; generated tasks match employee attributes")

    graph = nx.DiGraph()
    graph.add_nodes_from(task_ids)
    graph.add_edges_from((d["prerequisite_task_id"], d["task_id"]) for d in deps)
    add("Dependency graph acyclic", nx.is_directed_acyclic_graph(graph), "Task prerequisites form a directed acyclic graph")

    task_by_id = {t["task_id"]:t for t in tasks}
    completed_before_prereq = []
    for dep in deps:
        task = task_by_id[dep["task_id"]]
        prereq = task_by_id[dep["prerequisite_task_id"]]
        if task["task_status"] == "Completed" and prereq["task_status"] != "Completed":
            completed_before_prereq.append(task["task_id"])
    add("Task prerequisite completion rule", len(completed_before_prereq)==1,
        f"Detected {len(completed_before_prereq)} completed task(s) with incomplete prerequisite(s); one is intentionally injected")
    intentional_task_ids = {
        row["entity_id"] for row in gt
        if row["issue_type"] == "task_before_prerequisite"
    }
    add("Task anomaly label alignment",
        set(completed_before_prereq) == intentional_task_ids,
        "The dependency exception exactly matches its ground-truth label")

    expected = {"task_before_prerequisite","missing_manager","duplicate_asset_assignment",
                "start_before_background_check","offboarding_active_access","overdue_tasks",
                "mid_process_department_change"}
    found = {x["issue_type"] for x in gt}
    add("Seven anomaly labels", expected == found, f"Found {len(found)} expected anomaly labels")

    missing_manager = [e for e in employees if not e["manager_id"]]
    add("Missing-manager anomaly detection", len(missing_manager)==1, f"Detected {len(missing_manager)} employee(s) with no manager")
    add("Required workforce variation",
        {e["employment_type"] for e in employees} == {"Permanent", "Contractor"}
        and {e["work_location"] for e in employees} == {"Remote", "On-site"}
        and any(0 < (date.fromisoformat(e["start_date"]) - AS_OF).days <= 7 for e in employees),
        "Permanent/contractor, remote/on-site and an urgent future start are represented")

    active_assignments = {}
    for a in assignments:
        if not a["returned_date"]:
            active_assignments.setdefault(a["asset_id"], []).append(a)
    duplicate_assets = [k for k,v in active_assignments.items() if len(v)>1]
    add("Duplicate active asset assignment detection", len(duplicate_assets)==1, f"Detected {len(duplicate_assets)} duplicated asset(s)")

    emp_by_id = {e["employee_id"]:e for e in employees}
    terminated_ids = {o["employee_id"] for o in offboarding}
    approved_access = [a for a in access if a["request_status"]=="Approved"]
    anomaly_exit_ids = {
        row["entity_id"] for row in gt
        if row["issue_type"] == "offboarding_active_access"
    }
    active_access_after_exit = [
        a for a in approved_access
        if a["employee_id"] in terminated_ids
        and not (
            a["employee_id"] in anomaly_exit_ids
            and a["request_status"] == "Approved"
            and a["request_id"] in {
                r["request_id"] for r in revocations
            }
        )
    ]
    add("Offboarding active access detection", len(active_access_after_exit)>=1, f"Detected {len(active_access_after_exit)} active access request(s) for exiting employees")
    terminated_ids = {e["employee_id"] for e in employees if e["employment_status"] == "Terminated"}
    offboarding_by_employee = {o["employee_id"]: o for o in offboarding}
    add("Terminated employee offboarding coverage",
        terminated_ids == set(offboarding_by_employee),
        f"{len(terminated_ids)} terminated employees; {len(offboarding_by_employee)} offboarding cases")

    revocation_by_request = {r["request_id"]: r for r in revocations}
    revoked_request_ids = {r["request_id"] for r in access if r["request_status"] == "Revoked"}
    add("Access revocation history",
        revoked_request_ids == set(revocation_by_request)
        and all(r["employee_id"] in terminated_ids for r in revocations),
        f"{len(revocations)} revoked requests have corresponding offboarding history")
    offboarding_task_map = {
        (task["offboarding_id"], task["task_name"]): task
        for task in offboarding_tasks
    }
    required_exit_tasks = {
        (case["offboarding_id"], name)
        for case in offboarding
        for name in ("Revoke system access", "Recover assigned assets")
    }
    add("Offboarding revocation and asset tasks",
        set(offboarding_task_map) == required_exit_tasks
        and all(task["employee_id"] == offboarding[
            next(i for i, case in enumerate(offboarding)
                 if case["offboarding_id"] == task["offboarding_id"])
        ]["employee_id"] for task in offboarding_tasks),
        f"{len(offboarding_tasks)} explicit offboarding tasks cover {len(offboarding)} exits")
    pending_revocations = [
        task for task in offboarding_tasks
        if task["task_name"] == "Revoke system access"
        and task["task_status"] != "Completed"
    ]
    add("Offboarding access-removal outcomes",
        len(pending_revocations) == 1
        and pending_revocations[0]["employee_id"] in {
            row["entity_id"] for row in gt
            if row["issue_type"] == "offboarding_active_access"
        },
        f"{len(pending_revocations)} open revocation task(s), matching the intentional exception")

    overdue = [t for t in tasks if t["task_status"] in ("Pending","In Progress","Overdue") and t["due_date"] < AS_OF.isoformat()]
    add("Overdue task detection", len(overdue)>=1, f"Detected {len(overdue)} open overdue task(s)")
    task_date_consistency = all(
        (t["task_status"] == "Completed") == bool(t["completed_date"])
        and (not t["completed_date"] or t["completed_date"] <= AS_OF.isoformat())
        and (t["task_status"] != "Overdue" or t["due_date"] < AS_OF.isoformat())
        for t in tasks
    )
    add("Task lifecycle and date consistency", task_date_consistency,
        "Completion dates and overdue statuses agree with task state and as-of date")

    case_by_emp = {c["employee_id"]:c for c in cases}
    task_by_case_template = {}
    for t in tasks:
        task_by_case_template[(t["case_id"], template_by_id[t["template_id"]]["task_name"])] = t
    start_before_bg = []
    for e in employees:
        c = case_by_emp.get(e["employee_id"])
        if not c: continue
        bg = task_by_case_template.get((c["case_id"], "Complete background verification"))
        if bg and bg["completed_date"] and e["start_date"] < bg["completed_date"]:
            start_before_bg.append(e["employee_id"])
    add("Start-before-background-check detection", len(start_before_bg)==1, f"Detected {len(start_before_bg)} employee(s)")

    changed_during_onboarding = []
    for h in history:
        if h["employee_id"] in case_by_emp and h["old_department_id"] != h["new_department_id"]:
            changed_during_onboarding.append(h["employee_id"])
    add("Mid-process department-change history", len(changed_during_onboarding)==1, f"Detected {len(changed_during_onboarding)} department change(s)")

    # Every approved request must have an approved approval record.
    approved_ids = {a["request_id"] for a in approvals if a["request_id"] and a["decision"]=="Approved"}
    approved_req_ids = {a["request_id"] for a in access if a["request_status"]=="Approved"}
    add("Approval-before-access consistency", approved_req_ids.issubset(approved_ids),
        f"{len(approved_req_ids)} approved access request(s); all have approved decisions")
    approval_by_request = {
        a["request_id"]: a for a in approvals if a["request_id"]
    }
    access_timing_valid = all(
        request["request_id"] in approval_by_request
        and approval_by_request[request["request_id"]]["decision"] == "Approved"
        and approval_by_request[request["request_id"]]["decision_date"]
        and approval_by_request[request["request_id"]]["decision_date"] >= request["request_date"]
        and request["provisioned_date"]
        and request["provisioned_date"] >= approval_by_request[request["request_id"]]["decision_date"]
        for request in access if request["request_status"] in ("Approved", "Revoked")
    ) and all(
        not request["provisioned_date"]
        for request in access if request["request_status"] in ("Pending", "Rejected")
    )
    add("Provisioning after approval",
        access_timing_valid,
        "Approved access is provisioned only after a dated approval")
    add("Request approval decision consistency",
        all(
            approval_by_request[request["request_id"]]["decision"] == request["request_status"]
            or (
                request["request_status"] == "Revoked"
                and approval_by_request[request["request_id"]]["decision"] == "Approved"
            )
            for request in access
            if request["request_id"] in approval_by_request
        )
        and set(approval_by_request) == {request["request_id"] for request in access},
        "Every access request has one corresponding approval with a consistent decision")
    add("Late approvals represented",
        any(
            a["decision_date"] > next(
                request["request_date"] for request in access
                if request["request_id"] == a["request_id"]
            )
            for a in approvals if a["decision_date"] and a["request_id"]
        ),
        "At least one approval occurs after its request date")

    date_order_valid = (
        all(c["created_date"] <= next(e for e in employees if e["employee_id"] == c["employee_id"])["start_date"]
            for c in cases)
        and all(a["assigned_date"] <= a["returned_date"] for a in assignments if a["returned_date"])
        and all(r["revoked_date"] >= access_by_id[r["request_id"]]["provisioned_date"]
                for r in revocations
                if r["request_id"] in access_by_id
                and access_by_id[r["request_id"]]["provisioned_date"])
        and all(o["exit_date"] >= next(e for e in employees if e["employee_id"] == o["employee_id"])["start_date"]
                for o in offboarding)
    )
    add("Lifecycle date ordering", date_order_valid,
        "Case, assignment, access-revocation and offboarding dates are ordered")

    sla_breaches = [
        t for t in tasks
        if (
            (t["task_status"] != "Completed" and t["due_date"] < AS_OF.isoformat())
            or (t["completed_date"] and t["completed_date"] > t["due_date"])
        )
    ]
    late_completions = [
        t for t in tasks if t["completed_date"] and t["completed_date"] > t["due_date"]
    ]
    add("SLA breach reconciliation",
        len(sla_breaches) == len(overdue) + len(late_completions),
        f"{len(sla_breaches)} SLA breaches = {len(overdue)} open overdue + {len(late_completions)} late completions")

    audit_ids = {event["audit_id"] for event in audit}
    audit_events_present = (
        len(audit_ids) == len(audit)
        and any(event["event_type"] == "DepartmentChanged" for event in audit)
        and any(event["event_type"] == "AccessRevoked" for event in audit)
        and all(any(event["event_type"] == "OffboardingStarted"
                    and event["entity_id"] == case["offboarding_id"] for event in audit)
                for case in offboarding)
    )
    add("State-change audit history", audit_events_present,
        f"{len(audit)} uniquely identified audit events; key workflow changes retained")

    conn = sqlite3.connect(ROOT/"database"/"yottaflex.db")
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    conn.close()
    add("SQLite foreign-key integrity", len(fk)==0, f"{len(fk)} foreign-key violation(s)")

    total_tasks = len(tasks)
    completed_tasks = sum(t["task_status"] == "Completed" for t in tasks)
    report = {"summary":{"total_checks":len(results),"passed":sum(x["status"]=="PASS" for x in results),
                         "failed":sum(x["status"]=="FAIL" for x in results)},
              "metrics": {
                  "employee_count": len(employees),
                  "onboarding_case_count": len(cases),
                  "task_count": total_tasks,
                  "task_completion_rate": round(completed_tasks / total_tasks, 4) if total_tasks else 0,
                  "open_overdue_task_count": len(overdue),
                  "late_completion_count": len(late_completions),
                  "sla_breach_count": len(sla_breaches),
                  "access_revocation_count": len(revocations),
                  "offboarding_task_count": len(offboarding_tasks)
              },
              "checks":results,
              "known_limitations":[
                  "Synthetic scenario labels are intentionally injected for testing, not real employee events.",
                  "The generator models workflow records and rules; it does not integrate with real HR, identity, email, or asset-management systems.",
                  "This validator tests the explicitly implemented challenge rules; it is not a production policy engine."
              ]}
    (ROOT/"reports").mkdir(exist_ok=True)
    (ROOT/"reports"/"validation_summary.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    with (ROOT/"reports"/"validation_summary.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["check","status","detail"]); w.writeheader(); w.writerows(results)
    return report

if __name__ == "__main__":
    report=validate()
    print(f"Validation: {report['summary']['passed']}/{report['summary']['total_checks']} passed")
    for item in report["checks"]:
        print(f"[{item['status']}] {item['check']}: {item['detail']}")
