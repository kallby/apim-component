# APIM API Component

A GitLab CI/CD Catalog component for managing APIs and policies in Azure API Management.

## Quick Start

Add the component to your `.gitlab-ci.yml`:

```yaml
include:
  - component: $CI_SERVER_FQDN/devops/components/api-management/apim-api@1.0.0
```

Then run the pipeline from the GitLab UI and select your operation.

## Features

- Import APIs from OpenAPI/Swagger specifications (100% spec-driven)
- Delete APIs with automatic backup
- Manage API-level and operation-level policies
- Automatic vendor API detection and prefixing
- Multi-environment deployments (dev, tst, stg, prd)
- Automatic tagging from spec files (`x-lzd-api-tags`)
- Configurable subscription requirement (`x-lzd-api-subscription-required`)
- Email notifications to approvers
- Audit logging

## Required CI/CD Variables

Configure these variables in your GitLab project settings (Settings > CI/CD > Variables):

### Azure Credentials (per environment)

| Variable | Description | Example |
|----------|-------------|---------|
| `AZ_TENANT_ID` | Azure AD tenant ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `DEV_AZ_SPN_CLIENT_ID` | Service principal client ID for dev | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `DEV_AZ_SPN_CLIENT_SECRET` | Service principal secret for dev (masked) | `***` |
| `DEV_AZ_SUBSCRIPTION_ID` | Azure subscription ID for dev | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `DEV_RESOURCE_GROUP` | Resource group containing APIM for dev | `rg-apim-dev` |
| `DEV_APIM_SERVICE` | APIM service name for dev | `apim-mycompany-dev` |
| `DEV_BACKEND_URL` | Backend service URL for dev | `https://api-dev.mycompany.com` |

Repeat for `TST_`, `STG_`, and `PRD_` prefixes.

### Repository Credentials

| Variable | Description |
|----------|-------------|
| `SPEC_REPO_URL` | GitLab repo URL containing API specs |
| `SPEC_REPO_USERNAME` | Username for cloning (usually `gitlab-ci-token`) |
| `SPEC_REPO_TOKEN` | Deploy token or CI job token |
| `POLICY_REPO_URL` | GitLab repo URL containing policy XML files |
| `POLICY_REPO_USERNAME` | Username for cloning |
| `POLICY_REPO_TOKEN` | Deploy token for policy repo |

### Email Notifications (optional)

| Variable | Description |
|----------|-------------|
| `GITLAB_TOKEN` | GitLab API token with `read_api` scope (requires Maintainer access to project) |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_FROM` | Sender email address |
| `SMTP_PORT` | SMTP port (default: 25) |
| `SMTP_EXCLUDE_EMAILS` | Additional emails to exclude from notifications (service accounts starting with `group_` are excluded by default) |
| `EMAIL_DOMAIN` | Domain for constructing emails from usernames (default: `lazard.com`) |
| `APPROVER_EMAILS` | Fallback comma-separated list of approver emails |

**Note:** Either `GITLAB_TOKEN` or `APPROVER_EMAILS` must be provided.

**EMAIL_DOMAIN:** When using role-based approvers (e.g., Maintainers group), GitLab's API often cannot retrieve user emails directly. The default domain is `lazard.com`, so emails are automatically constructed as `{gitlab_username}@lazard.com`.

## Spec File Requirements

The `import_api` operation is **100% spec-driven**. Your spec must include these fields:

| Field | Required | Description |
|-------|----------|-------------|
| `info.title` | Yes | Display name (used to generate API ID if `x-lzd-api-id` not set) |
| `x-lzd-api-path` | Yes | URL path in APIM (must be lowercase) |
| `x-lzd-api-id` | No | API identifier (auto-generated from title if not set) |
| `x-lzd-api-tags` | No | Tags for categorization (string or array) |
| `x-lzd-api-subscription-required` | No | Whether subscription key is required (default: `true`) |
| `x-lzd-api-subscription-key-header-name` | No | Custom header name for subscription key (default: `x-lzd-{namespace}-api-key`) |
| `x-lzd-api-subscription-key-query-param-name` | No | Custom query param name for subscription key (default: `subscription-key`) |

### Example Internal API Spec

```yaml
openapi: 3.0.0
info:
  title: Orders API
  version: 1.0.0

x-lzd-api-path: orders
x-lzd-api-tags:
  - Orders
  - Internal

paths:
  /orders:
    get:
      operationId: get-orders
      summary: List all orders
```

**Result:** API ID = `orders-api` (auto-generated from title)

## Vendor APIs

Vendor APIs are **automatically detected** when `x-lzd-api-path` starts with `vendors/`.

**Requirements for vendor APIs:**
- `x-lzd-api-path` must start with `vendors/` (lowercase, with 's')
- `info.title` must start with `Vendor: ` (capital V, colon, space)

### Example Vendor API Spec

```yaml
openapi: 3.0.0
info:
  title: "Vendor: Acme Orders API"
  version: 1.0.0

x-lzd-api-path: vendors/acme/orders
```

**Result:**
- API ID: `vendor-acme-orders-api` (auto-generated with `vendor-` prefix)
- Display Name: `Vendor: Acme Orders API`
- Path: `/vendors/acme/orders`

## Validation Rules

The pipeline validates your spec file and auto-corrects minor issues.

### Pass/Fail Table

| Scenario | `x-lzd-api-path` | `info.title` | Result | Correction Applied |
|----------|------------------|--------------|--------|-------------------|
| Internal API | `orders` | `Orders API` | **Pass** | API ID → `orders-api` |
| Internal API (uppercase path) | `Orders` | `Orders API` | **Pass** | Path → `orders` |
| Vendor API | `vendors/acme/orders` | `Vendor: Acme API` | **Pass** | API ID → `vendor-acme-api` |
| Vendor API (wrong case title) | `vendors/acme/orders` | `vendor: Acme API` | **Pass** | Title → `Vendor: Acme API` |
| Vendor API (mixed case title) | `vendors/acme/orders` | `VeNDor: Acme API` | **Pass** | Title → `Vendor: Acme API` |
| Vendor API (uppercase path) | `Vendors/Acme/Orders` | `Vendor: Acme API` | **Pass** | Path → `vendors/acme/orders` |
| Missing colon in title | `vendors/acme/orders` | `Vendor Acme API` | **Fail** | - |
| Missing `Vendor:` prefix | `vendors/acme/orders` | `Acme API` | **Fail** | - |
| Wrong path prefix | `vendor/acme/orders` | `Vendor: Acme API` | **Fail** | - |
| Vendor title, non-vendor path | `acme/orders` | `Vendor: Acme API` | **Fail** | - |
| Missing path | *(empty)* | `Orders API` | **Fail** | - |
| Missing title | `orders` | *(empty)* | **Fail** | - |

### Auto-Corrections

| Field | Issue | Auto-Correction |
|-------|-------|-----------------|
| `x-lzd-api-path` | Uppercase characters | Lowercased (e.g., `Orders` → `orders`) |
| `info.title` | Wrong case on `Vendor:` | Fixed to `Vendor:` (e.g., `vendor:` → `Vendor:`) |
| `x-lzd-api-id` | Not provided | Generated from title |
| `x-lzd-api-subscription-required` | Invalid value | Defaults to `true` |

### Fail Conditions

| Condition | Error Message |
|-----------|---------------|
| `x-lzd-api-path` missing | `x-lzd-api-path: MISSING` |
| `info.title` missing | `info.title: MISSING` |
| Path starts with `vendor/` (no 's') | `x-lzd-api-path: invalid prefix 'vendor/' (must be 'vendors/' with an 's')` |
| Vendor path without `Vendor:` title | `Title format: INVALID (must start with 'Vendor: ')` |
| Vendor path with `Vendor` but no colon | `Title format: INVALID (missing colon after 'Vendor')` |
| `Vendor:` title without `vendors/` path | `Title starts with 'Vendor:' but path doesn't start with 'vendors/'` |

### Validation Output Examples

**Internal API (valid):**
```
[OK]    info.title: Orders API
[OK]    x-lzd-api-path: orders
[OK]    x-lzd-api-subscription-required: true

[INFO]  Internal API detected
[WARN]  x-lzd-api-id: not set (will be generated: orders-api)
[OK]    Spec validation passed
```

**Vendor API (valid with auto-corrections):**
```
[OK]    info.title: vendor: Acme Orders API
[WARN]  x-lzd-api-path: Vendors/Acme/Orders -> vendors/acme/orders (will be lowercased)
[OK]    x-lzd-api-subscription-required: true

[INFO]  Vendor API detected (path starts with 'vendors/')
[WARN]  Title case fixed: vendor:  -> Vendor:
[OK]    Title format: valid (starts with 'Vendor: ')
[WARN]  x-lzd-api-id: not set (will be generated: vendor-acme-orders-api)
[OK]    Spec validation passed
```

**Vendor API (invalid - missing colon):**
```
[OK]    info.title: Vendor Acme Orders API
[OK]    x-lzd-api-path: vendors/acme/orders

[INFO]  Vendor API detected (path starts with 'vendors/')
[ERROR] Title format: INVALID (missing colon after 'Vendor')
[ERROR] Current: Vendor Acme Orders API
[ERROR] Expected: Vendor: <API Name>

==========================================
  SPEC VALIDATION FAILED
==========================================
```

## Operations Quick Reference

| Operation | Required Variables | Description |
|-----------|-------------------|-------------|
| `import_api` | `SPEC_FILE_PATH` | Import new API from spec |
| `delete_api` | `API_NAME` | Delete an API (creates backup) |
| `list_apis` | - | List all APIs |
| `list_operations` | `API_NAME` | List operations for an API |
| `get_api_policy` | `API_NAME` | Get API policy |
| `set_api_policy` | `API_NAME`, `POLICY_FILE_PATH` | Set API policy |
| `clear_api_policy` | `API_NAME` | Remove API policy |
| `get_operation_policy` | `API_NAME`, `OPERATION_ID` | Get operation policy |
| `set_operation_policy` | `API_NAME`, `OPERATION_ID`, `POLICY_FILE_PATH` | Set operation policy |
| `clear_operation_policy` | `API_NAME`, `OPERATION_ID` | Remove operation policy |

## Operations

### API Operations

#### `import_api`

Import a new API from an OpenAPI/Swagger specification.

```
Required:  SPEC_FILE_PATH
```

The API ID, display name, and path are derived from the spec file:
- `x-lzd-api-id` → API ID (auto-generated from title if not set)
- `info.title` → Display Name
- `x-lzd-api-path` → URL Path
- `x-lzd-api-subscription-required` → Subscription Required (default: true)
- `x-lzd-api-subscription-key-header-name` → Custom header name (default: `x-lzd-{namespace}-api-key`)
- `x-lzd-api-subscription-key-query-param-name` → Custom query param name (default: `subscription-key`)

#### `delete_api`

Delete an API. **Creates a backup before deletion.**

```
Required:  API_NAME
```

#### `list_apis`

List all APIs in the APIM instance. Read-only operation, no approval required.

```
Required:  (none)
```

### Policy Operations

#### `get_api_policy`

Retrieve the current policy for an API. Read-only operation.

```
Required:  API_NAME
```

#### `set_api_policy`

Apply a policy XML file to an API. Creates a backup of the existing policy before applying.

```
Required:  API_NAME, POLICY_FILE_PATH
```

| Field | Description |
|-------|-------------|
| `API_NAME` | ID of the API |
| `POLICY_FILE_PATH` | Path to policy XML in the policy repo (e.g., `apis/orders-api/policy.xml`) |

#### `clear_api_policy`

Remove the policy from an API. Creates a backup before clearing.

```
Required:  API_NAME
```

### Operation-Level Policy Operations

#### `list_operations`

List all operations for an API. Use this to find operation IDs.

```
Required:  API_NAME
```

#### `get_operation_policy`

Retrieve the current policy for a specific operation. Read-only operation.

```
Required:  API_NAME, OPERATION_ID
```

#### `set_operation_policy`

Apply a policy XML file to a specific operation. Creates a backup before applying.

```
Required:  API_NAME, OPERATION_ID, POLICY_FILE_PATH
```

| Field | Description |
|-------|-------------|
| `API_NAME` | ID of the API |
| `OPERATION_ID` | ID of the operation (e.g., `get-orders`, `create-order`) |
| `POLICY_FILE_PATH` | Path to policy XML in the policy repo |

#### `clear_operation_policy`

Remove the policy from a specific operation. Creates a backup before clearing.

```
Required:  API_NAME, OPERATION_ID
```

## Automatic Backups

The component automatically creates backups before destructive operations:

| Operation | Backup Created | Backup Location |
|-----------|---------------|-----------------|
| `delete_api` | Full API export (OpenAPI JSON) | `backup-api-{api_id}-{env}-{pipeline_id}.json` |
| `set_api_policy` | Current policy XML | `backup-policy-{api_id}-{env}-{pipeline_id}.xml` |
| `clear_api_policy` | Current policy XML | `backup-policy-{api_id}-{env}-{pipeline_id}.xml` |
| `set_operation_policy` | Current policy XML | `backup-policy-{api_id}-{operation_id}-{env}-{pipeline_id}.xml` |
| `clear_operation_policy` | Current policy XML | `backup-policy-{api_id}-{operation_id}-{env}-{pipeline_id}.xml` |

### Backup Details

- **API Backups**: Exported in OpenAPI+JSON format using the Azure APIM export API
- **Policy Backups**: Raw XML of the current policy configuration
- **Retention**: Backups are stored as pipeline artifacts and retained for **90 days**
- **Recovery**: Download the artifact and use `import_api` (for APIs) or `set_*_policy` (for policies)

## Environment Mapping

The component automatically selects the environment based on the branch:

| Branch | Environment |
|--------|-------------|
| `dev`, `develop` | dev |
| `tst`, `test` | tst |
| `stg`, `staging` | stg |
| `prd`, `main` | prd |

## Pipeline Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Validate │───►│  Backup  │───►│   Plan   │───►│  Notify  │───►│  Deploy  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                                      │
                                                               (manual approval)
```

1. **Validate** - Validates inputs and spec/policy files
2. **Backup** - Creates backup of existing resources (for deletes/policy changes)
3. **Plan** - Shows what will be changed
4. **Notify** - Sends email to approvers (for operations requiring approval)
5. **Deploy** - Executes the operation (may require manual approval)

## Approval & Notification Rules

| Operation | dev/tst | stg/prd |
|-----------|---------|---------|
| `list_apis` | Auto | Auto |
| `list_operations` | Auto | Auto |
| `import_api` | Auto | Approval Required |
| `delete_api` | Auto | Approval Required |
| `get_api_policy` | Auto | Auto |
| `set_api_policy` | Auto | Approval Required |
| `clear_api_policy` | Auto | Approval Required |
| `get_operation_policy` | Auto | Auto |
| `set_operation_policy` | Auto | Approval Required |
| `clear_operation_policy` | Auto | Approval Required |

**Notifications:** Email notifications are sent to approvers only for operations requiring approval on stg/prd branches. No notifications are sent for dev/tst branches.

## Subscription Key Header

APIs are imported with a custom subscription key header based on your project namespace:

```
x-lzd-{namespace}-api-key
```

For example, if your project is in the `finance` namespace, the header will be `x-lzd-finance-api-key`.

## Audit Logging

All operations are logged to `audit-{pipeline_id}.json` and saved as a pipeline artifact for 30 days.

Example audit entry:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "pipeline_id": "123456",
  "job_name": "import_api_dev",
  "triggered_by": "john.doe",
  "action": "import_api",
  "resource": "orders-api",
  "environment": "dev",
  "apim_service": "apim-mycompany-dev"
}
```

## Examples

### Import a New API

1. Go to your project's CI/CD > Pipelines > Run pipeline
2. Select branch: `dev`
3. Set variables:
   - `OPERATION`: `import_api`
   - `SPEC_FILE_PATH`: `specs/orders-api.yaml`
4. Click "Run pipeline"
5. Review the plan stage output
6. Approve the deploy job

### Set an API Policy

1. Run pipeline on the appropriate branch
2. Set variables:
   - `OPERATION`: `set_api_policy`
   - `API_NAME`: `orders-api`
   - `POLICY_FILE_PATH`: `apis/orders-api/policy.xml`
3. Review and approve

### Delete an API

1. Run pipeline on the appropriate branch
2. Set variables:
   - `OPERATION`: `delete_api`
   - `API_NAME`: `old-deprecated-api`
3. Review the backup artifact
4. Approve the deploy job

## Troubleshooting

### "Spec file not found"

Ensure `SPEC_FILE_PATH` is relative to the root of your spec repository, not an absolute path.

### "x-lzd-api-path: MISSING"

Your spec file must include the required path field:
```yaml
x-lzd-api-path: your/api/path
```

Note: `x-lzd-api-id` is optional and will be auto-generated from `info.title` if not set.

### "Missing Azure credentials"

Verify that all required `{ENV}_*` variables are set for the branch you're running on.

### "Failed to import API"

Check that:
- The spec file is valid OpenAPI/Swagger
- The service principal has sufficient permissions

### "Path conflict detected"

If you see `PATH CONFLICT DETECTED`, the path in your spec is already used by a different API:

```
The path 'my-api' is already in use by a different API.

  Your spec API ID:    my-api
  Existing API ID:     my-api-v1
  Conflicting path:    my-api
```

**Resolution options:**

| Option | Action |
|--------|--------|
| Update existing API | Set `x-lzd-api-id` in your spec to match the existing API ID |
| Use different path | Change `x-lzd-api-path` to a unique path |
| Delete existing API | Run pipeline with `OPERATION=delete_api` and `API_NAME=<existing-api-id>` |

This safeguard prevents accidentally overwriting another team's API.

### Vendor API not detected

Ensure `x-lzd-api-path` starts with `vendors/` (e.g., `vendors/acme/orders`). The pipeline automatically detects vendor APIs from the path.

### Tags not applied

Tags are created automatically if they don't exist. Ensure the service principal has permission to create tags in APIM.

### Restoring from Backup

1. Download the backup artifact from the pipeline that created it
2. For API restoration: Use `import_api` with the backup JSON file
3. For policy restoration: Use `set_api_policy` or `set_operation_policy` with the backup XML
