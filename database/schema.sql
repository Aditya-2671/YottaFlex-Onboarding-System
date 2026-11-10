PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departments (
    department_id TEXT PRIMARY KEY,
    department_name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS roles (
    role_id TEXT PRIMARY KEY,
    role_name TEXT NOT NULL UNIQUE,
    department_id TEXT NOT NULL REFERENCES departments(department_id)
);
CREATE TABLE IF NOT EXISTS managers (
    manager_id TEXT PRIMARY KEY,
    manager_name TEXT NOT NULL,
    department_id TEXT NOT NULL REFERENCES departments(department_id),
    email TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    employee_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    department_id TEXT NOT NULL REFERENCES departments(department_id),
    role_id TEXT NOT NULL REFERENCES roles(role_id),
    manager_id TEXT REFERENCES managers(manager_id),
    employment_type TEXT NOT NULL CHECK(employment_type IN ('Permanent','Contractor')),
    work_location TEXT NOT NULL CHECK(work_location IN ('Remote','On-site')),
    start_date TEXT NOT NULL,
    employment_status TEXT NOT NULL CHECK(employment_status IN ('Preboarding','Active','On Leave','Terminated'))
);
CREATE TABLE IF NOT EXISTS onboarding_cases (
    case_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL UNIQUE REFERENCES employees(employee_id),
    created_date TEXT NOT NULL,
    case_status TEXT NOT NULL CHECK(case_status IN ('Not Started','In Progress','Completed','Blocked'))
);
CREATE TABLE IF NOT EXISTS task_templates (
    template_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    department_owner TEXT NOT NULL,
    required_role TEXT REFERENCES roles(role_id),
    required_location TEXT CHECK(required_location IN ('Remote','On-site')),
    sequence_number INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS task_instances (
    task_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES onboarding_cases(case_id),
    template_id TEXT NOT NULL REFERENCES task_templates(template_id),
    owner_manager_id TEXT REFERENCES managers(manager_id),
    task_status TEXT NOT NULL CHECK(task_status IN ('Pending','In Progress','Completed','Blocked','Overdue')),
    due_date TEXT NOT NULL,
    completed_date TEXT
);
CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id TEXT NOT NULL REFERENCES task_instances(task_id),
    prerequisite_task_id TEXT NOT NULL REFERENCES task_instances(task_id),
    PRIMARY KEY(task_id, prerequisite_task_id),
    CHECK(task_id <> prerequisite_task_id)
);
CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    asset_type TEXT NOT NULL,
    serial_number TEXT NOT NULL UNIQUE,
    asset_status TEXT NOT NULL CHECK(asset_status IN ('Available','Assigned','Maintenance','Retired'))
);
CREATE TABLE IF NOT EXISTS asset_assignments (
    assignment_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    assigned_date TEXT NOT NULL,
    returned_date TEXT,
    CHECK(returned_date IS NULL OR returned_date >= assigned_date)
);
CREATE TABLE IF NOT EXISTS access_requests (
    request_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    system_name TEXT NOT NULL,
    request_status TEXT NOT NULL CHECK(request_status IN ('Pending','Approved','Rejected','Revoked')),
    request_date TEXT NOT NULL,
    provisioned_date TEXT,
    CHECK(provisioned_date IS NULL OR request_status IN ('Approved','Revoked'))
);
CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    request_id TEXT REFERENCES access_requests(request_id),
    task_id TEXT REFERENCES task_instances(task_id),
    approver_id TEXT NOT NULL REFERENCES managers(manager_id),
    decision TEXT NOT NULL CHECK(decision IN ('Pending','Approved','Rejected')),
    decision_date TEXT,
    CHECK(request_id IS NOT NULL OR task_id IS NOT NULL),
    CHECK(decision_date IS NULL OR decision IN ('Approved','Rejected'))
);
CREATE TABLE IF NOT EXISTS offboarding_cases (
    offboarding_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL UNIQUE REFERENCES employees(employee_id),
    exit_date TEXT NOT NULL,
    case_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS access_revocations (
    revocation_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES access_requests(request_id),
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    revoked_date TEXT NOT NULL,
    reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS offboarding_tasks (
    offboarding_task_id TEXT PRIMARY KEY,
    offboarding_id TEXT NOT NULL REFERENCES offboarding_cases(offboarding_id),
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    task_name TEXT NOT NULL CHECK(task_name IN ('Revoke system access','Recover assigned assets')),
    task_status TEXT NOT NULL CHECK(task_status IN ('Pending','Completed')),
    due_date TEXT NOT NULL,
    completed_date TEXT,
    UNIQUE(offboarding_id, task_name),
    CHECK(
        (task_status = 'Completed' AND completed_date IS NOT NULL)
        OR (task_status = 'Pending' AND completed_date IS NULL)
    )
);
CREATE TABLE IF NOT EXISTS employee_department_history (
    history_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    old_department_id TEXT REFERENCES departments(department_id),
    new_department_id TEXT NOT NULL REFERENCES departments(department_id),
    effective_date TEXT NOT NULL,
    CHECK(old_department_id IS NULL OR old_department_id <> new_department_id)
);
CREATE TABLE IF NOT EXISTS audit_events (
    audit_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    actor_id TEXT,
    details TEXT
);
CREATE INDEX IF NOT EXISTS idx_employee_department ON employees(department_id);
CREATE INDEX IF NOT EXISTS idx_tasks_case ON task_instances(case_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON task_instances(task_status);
CREATE INDEX IF NOT EXISTS idx_access_employee ON access_requests(employee_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_type, entity_id);
