# APIM API Component - Developer Guide

A quick reference for importing APIs and managing policies in Azure API Management.

## Branch Strategy

The target environment is determined by which branch you run the pipeline on:

| Branch | Environment | APIM Instance |
|--------|-------------|---------------|
| `dev` or `develop` | Development | `apim-dev` |
| `tst` or `test` | Test | `apim-tst` |
| `stg` or `staging` | Staging | `apim-stg` |
| `prd` or `main` | Production | `apim-prd` |

**To deploy to a specific environment**, run the pipeline from the corresponding branch.

---

## Preparing Your API Spec

Your OpenAPI/Swagger spec **must** include these fields:

```json
{
  "openapi": "3.0.0",
  "x-lzd-api-path": "orders",
  "info": {
    "title": "Orders API",
    "version": "1.0.0"
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `info.title` | Yes | Display name (used to generate API ID) |
| `x-lzd-api-path` | Yes | URL path in APIM (must be lowercase) |
| `x-lzd-api-id` | No | API ID (auto-generated from title if not set) |
| `x-lzd-api-tags` | No | Tags for categorization |
| `x-lzd-api-subscription-required` | No | Whether subscription key is required (default: `true`) |
| `x-lzd-api-subscription-key-header-name` | No | Custom header name (default: `x-lzd-{namespace}-api-key`) |
| `x-lzd-api-subscription-key-query-param-name` | No | Custom query param name (default: `x-lzd-{namespace}-api-key`) |

**Result:** API ID = `orders-api` (auto-generated from title)

### Vendor APIs

For vendor/third-party APIs:
- `x-lzd-api-path` must start with `vendors/` (with an 's')
- `info.title` must start with `Vendor: ` (capital V, colon, space)

```json
{
  "x-lzd-api-path": "vendors/acme/orders",
  "info": {
    "title": "Vendor: Acme Orders API"
  }
}
```

**Result:** API ID = `vendor-acme-orders-api` (auto-generated with `vendor-` prefix)

---

## Running the Pipeline

### Import a New API

1. **Push your spec** to the spec repository
2. Go to **CI/CD > Pipelines > Run pipeline**
3. Select the branch for your target environment
4. Set variables:
   - `OPERATION` = `import_api`
   - `SPEC_FILE_PATH` = path to your spec (e.g., `orders-api.json`)
5. Click **Run pipeline**
6. **Approve** the deploy job when prompted

### Delete an API

1. Go to **CI/CD > Pipelines > Run pipeline**
2. Select the branch for your target environment
3. Set variables:
   - `OPERATION` = `delete_api`
   - `API_NAME` = the API ID (e.g., `orders-api`)
4. Click **Run pipeline**
5. **Approve** the deploy job (backup is created automatically)

### List APIs

1. Go to **CI/CD > Pipelines > Run pipeline**
2. Select the branch for your target environment
3. Set variables:
   - `OPERATION` = `list_apis`
4. Click **Run pipeline** (no approval needed)

---

## Policy Operations

### Set API-Level Policy

1. **Push your policy XML** to the policy repository
2. Go to **CI/CD > Pipelines > Run pipeline**
3. Set variables:
   - `OPERATION` = `set_api_policy`
   - `API_NAME` = the API ID
   - `POLICY_FILE_PATH` = path to policy XML (e.g., `apis/orders-api/policy.xml`)
4. Click **Run pipeline** and approve

### Set Operation-Level Policy

1. First, find the operation ID:
   - Run pipeline with `OPERATION` = `list_operations` and `API_NAME` = your API
2. Then set the policy:
   - `OPERATION` = `set_operation_policy`
   - `API_NAME` = the API ID
   - `OPERATION_ID` = the operation ID (e.g., `get-orders`)
   - `POLICY_FILE_PATH` = path to policy XML

### Get/Clear Policies

| Operation | Variables |
|-----------|-----------|
| `get_api_policy` | `API_NAME` |
| `clear_api_policy` | `API_NAME` |
| `get_operation_policy` | `API_NAME`, `OPERATION_ID` |
| `clear_operation_policy` | `API_NAME`, `OPERATION_ID` |

---

## Quick Reference

### Operations Summary

| Operation | What it does | Required Variables |
|-----------|--------------|-------------------|
| `import_api` | Import API from spec | `SPEC_FILE_PATH` |
| `delete_api` | Delete an API | `API_NAME` |
| `list_apis` | List all APIs | - |
| `list_operations` | List API operations | `API_NAME` |
| `get_api_policy` | View API policy | `API_NAME` |
| `set_api_policy` | Apply API policy | `API_NAME`, `POLICY_FILE_PATH` |
| `clear_api_policy` | Remove API policy | `API_NAME` |
| `get_operation_policy` | View operation policy | `API_NAME`, `OPERATION_ID` |
| `set_operation_policy` | Apply operation policy | `API_NAME`, `OPERATION_ID`, `POLICY_FILE_PATH` |
| `clear_operation_policy` | Remove operation policy | `API_NAME`, `OPERATION_ID` |

### Pipeline Stages

```
validate_inputs → validate_spec → backup → plan → notify → deploy
                                    ↓
                              (approval required)
```

- **Read-only operations** (`list_*`, `get_*`) run immediately
- **Write operations** require manual approval
- **Destructive operations** (`delete_*`, `clear_*`) create backups first

---

## Examples

### Example: Deploy API to Dev, then promote to Test

```bash
# 1. Deploy to dev (run pipeline on dev branch)
Branch: dev
OPERATION: import_api
SPEC_FILE_PATH: orders-api.json

# 2. After testing, deploy to test (run pipeline on tst branch)
Branch: tst
OPERATION: import_api
SPEC_FILE_PATH: orders-api.json
```

### Example: Internal vs Vendor API Specs

**Internal API:**
```json
{
  "openapi": "3.0.0",
  "x-lzd-api-path": "orders",
  "info": { "title": "Orders API", "version": "1.0.0" }
}
```
Result: API ID = `orders-api` (auto-generated), Path = `/orders`

**Vendor API:**
```json
{
  "openapi": "3.0.0",
  "x-lzd-api-path": "vendors/acme/orders",
  "info": { "title": "Vendor: Acme Orders API", "version": "1.0.0" }
}
```
Result: API ID = `vendor-acme-orders-api` (auto-generated), Path = `/vendors/acme/orders`

### Example: Policy File Structure

```
apim-policies/
├── apis/
│   ├── orders-api/
│   │   ├── policy.xml              # API-level policy
│   │   └── operations/
│   │       ├── get-orders.xml      # Operation-level policy
│   │       └── create-order.xml
│   └── payments-api/
│       └── policy.xml
└── products/
    └── premium/
        └── policy.xml
```

### Example: Basic Policy XML

```xml
<policies>
  <inbound>
    <base />
    <rate-limit calls="100" renewal-period="60" />
  </inbound>
  <backend>
    <base />
  </backend>
  <outbound>
    <base />
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>
```

---

## Validation Rules

The pipeline validates your spec and auto-corrects minor issues.

### Pass/Fail Table

| Scenario | `x-lzd-api-path` | `info.title` | Result | Correction |
|----------|------------------|--------------|--------|------------|
| Internal API | `orders` | `Orders API` | **Pass** | API ID → `orders-api` |
| Internal (uppercase path) | `Orders` | `Orders API` | **Pass** | Path → `orders` |
| Vendor API | `vendors/acme/orders` | `Vendor: Acme API` | **Pass** | API ID → `vendor-acme-api` |
| Vendor (wrong case title) | `vendors/acme/orders` | `vendor: Acme API` | **Pass** | Title → `Vendor: Acme API` |
| Vendor (mixed case) | `vendors/acme/orders` | `VeNDor: Acme API` | **Pass** | Title → `Vendor: Acme API` |
| Vendor (uppercase path) | `Vendors/Acme/Orders` | `Vendor: Acme API` | **Pass** | Path lowercased |
| Missing colon | `vendors/acme/orders` | `Vendor Acme API` | **Fail** | - |
| Missing `Vendor:` | `vendors/acme/orders` | `Acme API` | **Fail** | - |
| Wrong prefix (`vendor/`) | `vendor/acme/orders` | `Vendor: Acme API` | **Fail** | - |
| Vendor title, wrong path | `acme/orders` | `Vendor: Acme API` | **Fail** | - |
| Missing path | *(empty)* | `Orders API` | **Fail** | - |
| Missing title | `orders` | *(empty)* | **Fail** | - |
| Path already in use | `orders` *(exists)* | `Orders API` | **Fail** | - |

### Auto-Corrections

| Field | Issue | Correction |
|-------|-------|------------|
| `x-lzd-api-path` | Uppercase characters | Lowercased |
| `info.title` | Wrong case on `Vendor:` | Fixed to `Vendor:` |
| `x-lzd-api-id` | Not provided | Generated from title |
| `x-lzd-api-subscription-required` | Invalid value | Defaults to `true` |

### Common Errors

**Missing title or path:**
```
[ERROR] info.title: MISSING
[ERROR] x-lzd-api-path: MISSING
```
**Fix:** Add required fields to your spec.

**Wrong vendor path prefix:**
```
[ERROR] x-lzd-api-path: invalid prefix 'vendor/' (must be 'vendors/' with an 's')
```
**Fix:** Use `vendors/` not `vendor/`.

**Missing colon in vendor title:**
```
[ERROR] Title format: INVALID (missing colon after 'Vendor')
[ERROR] Current: Vendor Acme API
[ERROR] Expected: Vendor: <API Name>
```
**Fix:** Add colon after "Vendor" → `Vendor: Acme API`

**Missing Vendor prefix:**
```
[ERROR] Title format: INVALID (must start with 'Vendor: ')
[ERROR] Current: Acme API
[ERROR] Expected: Vendor: <API Name>
```
**Fix:** Add `Vendor: ` prefix to title.

**Vendor title without vendors/ path:**
```
[INFO]  Internal API detected
[ERROR] Title starts with 'Vendor:' but path doesn't start with 'vendors/'
[ERROR] Current path: acme/orders
[ERROR] Expected path: vendors/<vendor-name>/...
```
**Fix:** Change path to start with `vendors/` (e.g., `vendors/acme/orders`).

**Path already in use:**
```
==========================================
  PATH CONFLICT DETECTED
==========================================

  The path '/orders' is already in use by another API.

  Conflicting API:
    - API ID:       existing-orders-api
    - Display Name: Existing Orders API
    - Path:         /orders

  Your spec:
    - API ID:       new-orders-api
    - Display Name: New Orders API
    - Path:         /orders
==========================================
```
**Fix:** Use a different `x-lzd-api-path` or delete the existing API first.

---

## Tips

1. **Use `list_operations`** to find operation IDs before setting operation policies
2. **Backups are automatic** for delete operations
3. **Approval emails** are sent to environment approvers
4. **Vendor APIs** require `vendors/` in path AND `Vendor: ` in title
5. **API ID is auto-generated** from title - no need to set `x-lzd-api-id`
6. **Subscription keys** are required by default - set `x-lzd-api-subscription-required: false` to disable
7. **Custom subscription key names** - override defaults with `x-lzd-api-subscription-key-header-name` and `x-lzd-api-subscription-key-query-param-name`
