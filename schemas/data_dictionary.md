# Data Dictionary

All records are synthetic. Dates use ISO-8601 `YYYY-MM-DD`; event timestamps use
`YYYY-MM-DDTHH:MM:SS`. In CSV/JSON, an optional value is an empty string. In
SQLite, empty optional values are stored as `NULL`.

## Entities and cardinality

- Department `1:N` Role, Manager, Employee.
- Role `1:N` Employee; Manager `1:N` Employee and TaskInstance owner.
- Employee `1:1` OnboardingCase in the generated baseline; Employee `1:N`
  AccessRequest, AssetAssignment, OffboardingCase and AuditEvent.
- OnboardingCase `1:N` TaskInstance. TaskInstance has a many-to-many
  prerequisite relationship through TaskDependency.
- Asset `1:N` AssetAssignment over time. AccessRequest `1:N` Approval and
  `0:N` AccessRevocation history. OffboardingCase `1:N` OffboardingTask.
- EmployeeDepartmentHistory and AuditEvent preserve lifecycle/state changes.

## Field-level definitions

`PK` means primary key; `FK` means foreign key. “Required” means non-null in
SQLite; all listed enum values are case-sensitive.

### Department (`departments`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| department_id | string | Required, PK | Stable `DEPT-001` style identifier |
| department_name | string | Required, unique | Non-empty department name |

### Role (`roles`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| role_id | string | Required, PK | Stable `ROLE-001` style identifier |
| role_name | string | Required, unique | Non-empty role name |
| department_id | string | Required, FK -> departments | Must identify the role's department |

### Manager (`managers`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| manager_id | string | Required, PK | Stable `MGR-0001` style identifier |
| manager_name | string | Required | Synthetic name |
| department_id | string | Required, FK -> departments | Existing department |
| email | string | Required, unique | Synthetic `.test` email |

### Employee (`employees`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| employee_id | string | Required, PK | `EMP-000001` format |
| employee_name | string | Required | Synthetic name |
| email | string | Required, unique | Synthetic `.test` email |
| department_id | string | Required, FK -> departments | Current department |
| role_id | string | Required, FK -> roles | Role must belong to current department |
| manager_id | string | Optional, FK -> managers | Missing only for the labelled anomaly |
| employment_type | string | Required | `Permanent` or `Contractor` |
| work_location | string | Required | `Remote` or `On-site` |
| start_date | date | Required | ISO date; may be in the future for urgent starts |
| employment_status | string | Required | `Preboarding`, `Active`, `On Leave`, `Terminated` |

### OnboardingCase (`onboarding_cases`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| case_id | string | Required, PK | `ONB-2026-000001` format |
| employee_id | string | Required, unique FK -> employees | One generated onboarding case per employee |
| created_date | date | Required | ISO date, no later than employee start date |
| case_status | string | Required | `Not Started`, `In Progress`, `Completed`, `Blocked`; derived from task states |

### TaskTemplate (`task_templates`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| template_id | string | Required, PK | `TPL-001` style identifier |
| task_name | string | Required | Descriptive workflow task |
| department_owner | string | Required | Owning department/team label |
| required_role | string | Optional, FK -> roles | If set, task applies to this role |
| required_location | string | Optional | If set, `Remote` or `On-site` |
| sequence_number | integer | Required | Positive order within the workflow |

### TaskInstance (`task_instances`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| task_id | string | Required, PK | `TASK-ONB-<case-id>-001` format |
| case_id | string | Required, FK -> onboarding_cases | Existing parent case |
| template_id | string | Required, FK -> task_templates | Existing template; role/location variants must match employee |
| owner_manager_id | string | Required in generated data, FK -> managers | Existing task owner; fallback owner is used for missing employee manager |
| task_status | string | Required | `Pending`, `In Progress`, `Completed`, `Blocked`, `Overdue` |
| due_date | date | Required | ISO date; overdue open tasks have due date before as-of date |
| completed_date | date | Optional | Present only for completed tasks; may exceed due date for a labelled late completion |

### TaskDependency (`task_dependencies`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| task_id | string | Required, composite PK, FK -> task_instances | Dependent task |
| prerequisite_task_id | string | Required, composite PK, FK -> task_instances | Existing, different task in the same case |

### Asset (`assets`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| asset_id | string | Required, PK | `AST-LAP-000001` style; type code follows asset type |
| asset_type | string | Required | `Laptop`, `Monitor`, `Phone`, `Access Card` |
| serial_number | string | Required, unique | Synthetic serial identifier |
| asset_status | string | Required | `Available`, `Assigned`, `Maintenance`, `Retired` |

### AssetAssignment (`asset_assignments`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| assignment_id | string | Required, PK | `ASSIGN-000001` style identifier |
| asset_id | string | Required, FK -> assets | Existing inventory item |
| employee_id | string | Required, FK -> employees | Existing employee |
| assigned_date | date | Required | ISO date |
| returned_date | date | Optional | ISO date on/after assignment date; blank while assigned |

### AccessRequest (`access_requests`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| request_id | string | Required, PK | `ACCREQ-2026-000001` format |
| employee_id | string | Required, FK -> employees | Existing employee |
| system_name | string | Required | Named system from the generator's catalog |
| request_status | string | Required | `Pending`, `Approved`, `Rejected`, `Revoked` |
| request_date | date | Required | ISO date |
| provisioned_date | date | Optional | Must not precede the approved decision |

### Approval (`approvals`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| approval_id | string | Required, PK | `APR-000001` style identifier |
| request_id | string | Optional, FK -> access_requests | Access request being decided |
| task_id | string | Optional, FK -> task_instances | Alternative task being decided |
| approver_id | string | Required, FK -> managers | Existing approver |
| decision | string | Required | `Pending`, `Approved`, `Rejected` |
| decision_date | date | Optional | Required for a recorded decision; no earlier than request date |

At least one of `request_id` or `task_id` must be populated.

### OffboardingCase (`offboarding_cases`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| offboarding_id | string | Required, PK | `OFF-000001` style identifier |
| employee_id | string | Required, FK -> employees | Terminated employee |
| exit_date | date | Required | ISO date, on/after employee start date |
| case_status | string | Required | Workflow state; generated as `In Progress` |

### OffboardingTask (`offboarding_tasks`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| offboarding_task_id | string | Required, PK | `TASK-OFF-<offboarding-id>-001` format |
| offboarding_id | string | Required, FK -> offboarding_cases | Existing exit case |
| employee_id | string | Required, FK -> employees | Must match its offboarding case |
| task_name | string | Required | `Revoke system access` or `Recover assigned assets` |
| task_status | string | Required | `Pending` or `Completed`; derived from access/asset records |
| due_date | date | Required | ISO date |
| completed_date | date | Optional | Required when completed |

### AccessRevocation (`access_revocations`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| revocation_id | string | Required, PK | `REVOKE-000001` style identifier |
| request_id | string | Required, FK -> access_requests | Existing request whose access was revoked |
| employee_id | string | Required, FK -> employees | Must match request employee |
| revoked_date | date | Required | ISO date, on/after provisioning |
| reason | string | Required | Revocation reason, e.g. employee offboarding |

### EmployeeDepartmentHistory (`employee_department_history`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| history_id | string | Required, PK | Stable history identifier |
| employee_id | string | Required, FK -> employees | Existing employee |
| old_department_id | string | Optional, FK -> departments | Previous department |
| new_department_id | string | Required, FK -> departments | New department |
| effective_date | date | Required | ISO date; preserves transfer history |

### AuditEvent (`audit_events`)

| Field | Type | Requirement | Allowed values / validation |
|---|---|---|---|
| audit_id | string | Required, PK | `AUD-YYYYMMDD-000001` format |
| entity_type | string | Required | Entity affected by the event |
| entity_id | string | Required | ID of the affected entity |
| event_type | string | Required | Event name such as `EmployeeCreated`, `AccessRevoked` |
| event_timestamp | timestamp | Required | ISO timestamp |
| actor_id | string | Optional | Actor or `SYSTEM` |
| details | string | Optional | Human-readable event context |

## Lifecycle and reproducibility notes

- The single missing manager, duplicate active asset, pre-background-check
  start, active access after exit, overdue tasks, dependency-order violation
  and department transfer are deliberate labelled exceptions.
- The generated offboarding flow includes access revocation and asset recovery
  tasks for every terminated employee. The labelled active-access case keeps
  its access-revocation task open.
- SLA breaches are derived as open tasks past due plus completed tasks finished
  after due date; the validation report exposes the counts and task completion
  rate.
- IDs are deterministic and generated data plus `ground_truth` checksums are
  compared by the reproducibility test. SQLite file bytes are not used as the
  cross-platform checksum target.
