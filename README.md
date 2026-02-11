# APIM Components

GitLab CI/CD Catalog components for managing Azure API Management resources.

## Available Components

| Component | Description |
|-----------|-------------|
| `apim-api` | Manage APIs, operations, and their policies |
| `apim-products` | Manage products, API associations, and product policies |
| `apim-global-policy` | Manage the global (service-level) policy |
| `apim-subscriptions` | Manage subscriptions and subscription keys |

## Overview

These components provide reusable pipelines for:
- Importing APIs from OpenAPI/Swagger specs (spec-driven, no manual overrides)
- Managing API-level and operation-level policies
- Managing the global service-level policy
- Creating and configuring APIM products
- Managing product-to-API associations
- Managing product-level policies
- Managing subscriptions with flexible scope (product, API, or all APIs)
- Subscription key management (view and regenerate keys)
- Multi-environment deployments (dev, tst, stg, prd)
- Automatic vendor API detection and prefixing

## Quick Start

### 1. Include a Component

Add components to your `.gitlab-ci.yml` as needed:

```yaml
# For API management
include:
  - component: $CI_SERVER_FQDN/devops/components/api-management/apim-api@1.0.0

# For Product management
include:
  - component: $CI_SERVER_FQDN/devops/components/api-management/apim-products@1.0.0

# For Global Policy management
include:
  - component: $CI_SERVER_FQDN/devops/components/api-management/apim-global-policy@1.0.0

# For Subscription management
include:
  - component: $CI_SERVER_FQDN/devops/components/api-management/apim-subscriptions@1.0.0
```

That's it! When you run the pipeline, you'll see variable prompts in the GitLab UI.

### 2. Configure CI/CD Variables

Set these variables in your project (Settings > CI/CD > Variables):

**Spec Repository:**
```
SPEC_REPO_URL        = https://gitlab.com/your-group/api-specs.git
SPEC_REPO_USERNAME   = deploy-token-user
SPEC_REPO_TOKEN      = <deploy-token>  (masked)
```

**Policy Repository (for policy operations):**
```
POLICY_REPO_URL      = https://gitlab.com/your-group/apim-policies.git
POLICY_REPO_USERNAME = deploy-token-user
POLICY_REPO_TOKEN    = <deploy-token>  (masked)
```

**Azure Credentials:**
```
AZ_TENANT_ID              = <tenant-id>

DEV_AZ_SPN_CLIENT_ID      = <client-id>
DEV_AZ_SPN_CLIENT_SECRET  = <client-secret>  (masked)
DEV_AZ_SUBSCRIPTION_ID    = <subscription-id>
DEV_RESOURCE_GROUP        = rg-apim-dev
DEV_APIM_SERVICE          = apim-dev
DEV_BACKEND_URL           = https://api-dev.example.com

# Repeat for TST, STG, PRD environments
```

**Container Images (Optional):**

The components use self-hosted images from your GitLab registry by default. To override the default images, set these variables:

```
IMAGE_AZURE_CLI  = ${CI_REGISTRY}/devops/images/azure-cli:latest
IMAGE_PYTHON     = ${CI_REGISTRY}/devops/images/python:3.11-slim
IMAGE_ALPINE     = ${CI_REGISTRY}/devops/images/alpine:latest
```

To use public images instead (e.g., for testing), override with:
```
IMAGE_AZURE_CLI  = mcr.microsoft.com/azure-cli:latest
IMAGE_PYTHON     = python:3.11-slim
IMAGE_ALPINE     = alpine:latest
```

### 3. Run the Pipeline

1. Go to **CI/CD > Pipelines > Run pipeline**
2. Select the branch matching your target environment
3. Fill in the variables shown in the UI:
   - **OPERATION** - Select from dropdown (e.g., `import_api`)
   - **SPEC_FILE_PATH** - Path to your API spec (for import)
   - **API_NAME** - API identifier (for delete/policy operations)
4. Click **Run pipeline**
5. Approve the deploy job when prompted

---

## apim-api Component

### Spec File Requirements

The `import_api` operation is **100% spec-driven**. Your OpenAPI/Swagger spec must include:

| Field | Required | Description |
|-------|----------|-------------|
| `info.title` | Yes | Display name (used to generate API ID if `x-lzd-api-id` not set) |
| `x-lzd-api-path` | Yes | URL path in APIM (must be lowercase) |
| `x-lzd-api-id` | No | API identifier (auto-generated from title if not set) |
| `x-lzd-api-tags` | No | Tags for categorization (string or array) |
| `x-lzd-api-subscription-required` | No | Whether subscription key is required (default: `true`) |
| `x-lzd-api-subscription-key-header-name` | No | Custom header name (default: `x-lzd-{namespace}-api-key`) |
| `x-lzd-api-subscription-key-query-param-name` | No | Custom query param (default: `x-lzd-{namespace}-api-key`) |

**Example internal API spec:**

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

**Result:** API ID = `orders-api` (auto-generated from title)

### Vendor APIs

Vendor APIs are **automatically detected** when `x-lzd-api-path` starts with `vendors/`.

**Requirements:**
- `x-lzd-api-path` must start with `vendors/` (lowercase, with 's')
- `info.title` must start with `Vendor: ` (capital V, colon, space)

**Example vendor API spec:**

```json
{
  "openapi": "3.0.0",
  "x-lzd-api-path": "vendors/acme/orders",
  "info": {
    "title": "Vendor: Acme Orders API",
    "version": "1.0.0"
  }
}
```

**Result:** API ID = `vendor-acme-orders-api` (auto-generated with `vendor-` prefix)

### Validation Rules

| Scenario | `x-lzd-api-path` | `info.title` | Result | Correction |
|----------|------------------|--------------|--------|------------|
| Internal API | `orders` | `Orders API` | **Pass** | API ID → `orders-api` |
| Internal (uppercase path) | `Orders` | `Orders API` | **Pass** | Path → `orders` |
| Vendor API | `vendors/acme/orders` | `Vendor: Acme API` | **Pass** | API ID → `vendor-acme-api` |
| Vendor (wrong case title) | `vendors/acme/orders` | `vendor: Acme API` | **Pass** | Title → `Vendor: Acme API` |
| Vendor (uppercase path) | `Vendors/Acme/Orders` | `Vendor: Acme API` | **Pass** | Path lowercased |
| Missing colon | `vendors/acme/orders` | `Vendor Acme API` | **Fail** | - |
| Missing `Vendor:` | `vendors/acme/orders` | `Acme API` | **Fail** | - |
| Wrong prefix | `vendor/acme/orders` | `Vendor: Acme API` | **Fail** | - |
| Vendor title, wrong path | `acme/orders` | `Vendor: Acme API` | **Fail** | - |
| Path already in use | `orders` *(exists)* | `Orders API` | **Fail** | - |

**Auto-corrections:**
| Field | Issue | Correction |
|-------|-------|------------|
| `x-lzd-api-path` | Uppercase | Lowercased |
| `info.title` | Wrong case `vendor:` | Fixed to `Vendor:` |
| `x-lzd-api-id` | Not provided | Generated from title |
| `x-lzd-api-subscription-required` | Invalid value | Defaults to `true` |

**Fail conditions:**
| Condition | Error |
|-----------|-------|
| Path starts with `vendor/` (no 's') | Must use `vendors/` |
| Vendor path without `Vendor:` title | Title must start with `Vendor: ` |
| Vendor path with `Vendor` but no colon | Missing colon after `Vendor` |
| `Vendor:` title without `vendors/` path | Path must start with `vendors/` |

### Pipeline Variables (UI Prompts)

| Variable | Description | Used By |
|----------|-------------|---------|
| `OPERATION` | Operation to perform (dropdown) | All |
| `SPEC_FILE_PATH` | Path to spec file in spec repo | `import_api` |
| `API_NAME` | API identifier | `delete_api`, `list_operations`, policy operations |
| `OPERATION_ID` | Operation ID for operation-level policies | `*_operation_policy` |
| `POLICY_FILE_PATH` | Path to policy XML in policy repo | `set_*_policy` |

### Available Operations

#### API Operations

| Operation | Description | Required Variables |
|-----------|-------------|-------------------|
| `import_api` | Import new API from spec | `SPEC_FILE_PATH` |
| `delete_api` | Delete an API | `API_NAME` |
| `list_apis` | List all APIs | None |
| `list_operations` | List operations for an API | `API_NAME` |

#### Policy Operations

| Operation | Description | Required Variables |
|-----------|-------------|-------------------|
| `get_api_policy` | Get API-level policy | `API_NAME` |
| `set_api_policy` | Set API-level policy | `API_NAME`, `POLICY_FILE_PATH` |
| `clear_api_policy` | Remove API-level policy | `API_NAME` |
| `get_operation_policy` | Get operation-level policy | `API_NAME`, `OPERATION_ID` |
| `set_operation_policy` | Set operation-level policy | `API_NAME`, `OPERATION_ID`, `POLICY_FILE_PATH` |
| `clear_operation_policy` | Remove operation-level policy | `API_NAME`, `OPERATION_ID` |

---

## apim-products Component

### Pipeline Variables (UI Prompts)

| Variable | Description |
|----------|-------------|
| `OPERATION` | Operation to perform (dropdown) |
| `PRODUCT_ID` | Product identifier (e.g., basic-tier) |
| `PRODUCT_DISPLAY_NAME` | Display name for the product |
| `PRODUCT_DESCRIPTION` | Product description |
| `PRODUCT_STATE` | published or notPublished |
| `SUBSCRIPTION_REQUIRED` | Whether subscription is required (true/false) |
| `APPROVAL_REQUIRED` | Whether subscription approval is required (true/false) |
| `SUBSCRIPTIONS_LIMIT` | Max subscriptions per user |
| `TERMS_OF_USE` | Legal terms for the product |
| `API_ID` | API ID for add/remove operations |
| `POLICY_FILE_PATH` | Path to policy XML in policy repo |
| `GROUP_NAME` | Group name for visibility operations |
| `SUBSCRIPTION_NAME` | Display name for new subscription |
| `SUBSCRIPTION_ID` | Subscription ID for delete operation |
| `SUBSCRIPTION_STATE` | active, suspended, or cancelled |

### Available Operations

#### Product Operations

| Operation | Description | Required Variables |
|-----------|-------------|-------------------|
| `list_products` | List all products | None |
| `get_product` | Get product details | `PRODUCT_ID` |
| `create_product` | Create new product | `PRODUCT_ID`, `PRODUCT_DISPLAY_NAME` |
| `update_product` | Update existing product | `PRODUCT_ID` |
| `delete_product` | Delete a product | `PRODUCT_ID` |

#### API Association Operations

| Operation | Description | Required Variables |
|-----------|-------------|-------------------|
| `list_product_apis` | List APIs in a product | `PRODUCT_ID` |
| `add_api_to_product` | Add API to product | `PRODUCT_ID`, `API_ID` |
| `remove_api_from_product` | Remove API from product | `PRODUCT_ID`, `API_ID` |

#### Product Policy Operations

| Operation | Description | Required Variables |
|-----------|-------------|-------------------|
| `get_product_policy` | Get product policy | `PRODUCT_ID` |
| `set_product_policy` | Set product policy | `PRODUCT_ID`, `POLICY_FILE_PATH` |
| `clear_product_policy` | Remove product policy | `PRODUCT_ID` |

#### Group (Visibility) Operations

| Operation | Description | Required Variables |
|-----------|-------------|-------------------|
| `list_product_groups` | List groups with access to product | `PRODUCT_ID` |
| `add_group_to_product` | Add visibility group to product | `PRODUCT_ID`, `GROUP_NAME` |
| `remove_group_from_product` | Remove visibility group from product | `PRODUCT_ID`, `GROUP_NAME` |

#### Subscription Operations

| Operation | Description | Required Variables |
|-----------|-------------|-------------------|
| `list_product_subscriptions` | List subscriptions for a product | `PRODUCT_ID` |
| `create_product_subscription` | Create subscription for product | `PRODUCT_ID`, `SUBSCRIPTION_NAME` |
| `delete_product_subscription` | Delete a subscription | `SUBSCRIPTION_ID` |

---

## apim-global-policy Component

### Pipeline Variables (UI Prompts)

| Variable | Description |
|----------|-------------|
| `OPERATION` | Operation to perform (dropdown) |
| `POLICY_FILE_PATH` | Path to policy XML in policy repo |

### Available Operations

| Operation | Description | Required Variables |
|-----------|-------------|-------------------|
| `get_global_policy` | Get current global policy | None |
| `set_global_policy` | Set global policy | `POLICY_FILE_PATH` |
| `clear_global_policy` | Remove global policy | None |

### Notes

The global policy applies to all APIs in the APIM service. It's the top-level policy in the hierarchy:

```
Global Policy (service-level)
  └── Product Policy
       └── API Policy
            └── Operation Policy
```

Each level inherits from its parent via the `<base />` element.

---

## apim-subscriptions Component

### Pipeline Variables (UI Prompts)

| Variable | Description |
|----------|-------------|
| `OPERATION` | Operation to perform (dropdown) |
| `SUBSCRIPTION_ID` | Subscription ID (for get/delete/keys/regenerate operations) |
| `SUBSCRIPTION_NAME` | Display name for new subscription |
| `SCOPE_TYPE` | Scope type: `product`, `api`, or `all_apis` |
| `SCOPE_ID` | Product ID or API ID (required for product/api scopes) |
| `SUBSCRIPTION_STATE` | Subscription state: `active`, `suspended`, `cancelled` |
| `ALLOW_TRACING` | Enable tracing for the subscription |

### Available Operations

| Operation | Description | Required Variables | Approval |
|-----------|-------------|-------------------|----------|
| `list_subscriptions` | List all subscriptions | - | No |
| `get_subscription` | Get subscription details | `SUBSCRIPTION_ID` | No |
| `create_subscription` | Create new subscription | `SUBSCRIPTION_NAME`, `SCOPE_TYPE`, `SCOPE_ID`* | Yes |
| `delete_subscription` | Delete subscription | `SUBSCRIPTION_ID` | Yes |
| `get_subscription_keys` | Show primary & secondary keys | `SUBSCRIPTION_ID` | **Yes** |
| `regenerate_primary_key` | Regenerate primary key | `SUBSCRIPTION_ID` | Yes |
| `regenerate_secondary_key` | Regenerate secondary key | `SUBSCRIPTION_ID` | Yes |
| `regenerate_both_keys` | Regenerate both keys at once | `SUBSCRIPTION_ID` | Yes |

*`SCOPE_ID` not required when `SCOPE_TYPE` is `all_apis`

### Subscription Scopes

| Scope Type | Description |
|------------|-------------|
| `product` | Access to all APIs in a specific product |
| `api` | Access to a specific API only |
| `all_apis` | Service-level access to all APIs |

### Notes

- The `get_subscription_keys` operation requires manual approval due to the sensitive nature of API keys
- Key regeneration is irreversible - the old key is immediately invalidated
- For zero-downtime key rotation, update applications to use the secondary key before regenerating the primary key
- Use `regenerate_both_keys` only when you need to invalidate all keys immediately (e.g., after a security incident)

---

## Environment Mapping

The component determines the target environment based on branch:

| Branch | Environment |
|--------|-------------|
| `dev`, `develop` | dev |
| `tst`, `test` | tst |
| `stg`, `staging` | stg |
| `prd`, `main` | prd |

## Pipeline Flow

```
┌─────────────────┐
│ validate_inputs │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────────┐
│validate│ │validate    │
│_spec   │ │_policy     │
└────┬───┘ └─────┬──────┘
     │           │
┌────┴───────────┴────┐
│     backup_*        │
└──────────┬──────────┘
           ▼
      ┌────────┐
      │  plan  │
      └────┬───┘
           │
           ▼
    ┌──────────────┐
    │ deploy_<env> │  ← Manual approval required
    └──────────────┘
```

## Approval Configuration

Deploy jobs require approval via GitLab protected environments:

1. Go to **Settings > CI/CD > Protected Environments**
2. Add environments: `dev`, `tst`, `stg`, `prd`
3. Configure **Allowed to Deploy** for each environment

## Email Notifications

The components can send email notifications to approvers when a pipeline is waiting for approval. Designed for GitLab Dedicated instances.

### Configuration

Add these CI/CD variables to enable email notifications:

| Variable | Description | Required |
|----------|-------------|----------|
| `GITLAB_TOKEN` | GitLab API token with `read_api` scope (requires Maintainer access to project) | Yes* |
| `SMTP_HOST` | SMTP server hostname | Yes |
| `SMTP_FROM` | From email address | Yes |
| `SMTP_PORT` | SMTP port (default: 25) | No |
| `SMTP_USE_TLS` | Enable STARTTLS (default: false) | No |
| `SMTP_USERNAME` | SMTP authentication username | No |
| `SMTP_PASSWORD` | SMTP authentication password | No |
| `EMAIL_DOMAIN` | Domain for constructing emails from usernames (default: `lazard.com`) | No |
| `SMTP_EXCLUDE_EMAILS` | Additional emails to exclude (service accounts starting with `group_` are excluded by default) | No |
| `APPROVER_EMAILS` | Comma-separated fallback emails | No* |
| `NOTIFICATION_CC` | Comma-separated CC recipients | No |

*Either `GITLAB_TOKEN` or `APPROVER_EMAILS` must be provided.

**EMAIL_DOMAIN Note:** When using role-based approvers (e.g., Maintainers), GitLab's API often cannot retrieve user emails. The default domain is `lazard.com`, so emails are automatically constructed as `{gitlab_username}@lazard.com`.

### How It Works

1. When a pipeline reaches the approval stage, the `notify_approvers` job runs
2. It queries the GitLab API for protected environment approvers (users and groups)
3. Sends an HTML email with:
   - Operation details (import_api, set_policy, etc.)
   - Target environment (dev/tst/stg/prd)
   - Direct links to spec files or policy files
   - Link to the pipeline for approval
4. The notification job uses `allow_failure: true` so it won't block the pipeline

### Email Content

The email includes:
- Project name and operation type
- Environment with color-coded badge (red for prd, orange for stg, etc.)
- Who triggered the pipeline
- Direct links to spec/policy files in GitLab
- "Review Pipeline" button linking to the approval page

### GitLab Dedicated Considerations

**User Email Visibility:**
- The [Users API](https://docs.gitlab.com/api/users/) requires admin access to see the `email` field
- Non-admin tokens can only see `public_email` if the user has set one
- Users should set a public email in their GitLab profile (Settings > Profile > Public email)

**Fallback Option:**
If the API cannot retrieve emails (due to permissions or missing public emails), use the `APPROVER_EMAILS` variable:
```
APPROVER_EMAILS = "approver1@company.com,approver2@company.com,team-leads@company.com"
```

**Service Accounts:**
On GitLab Dedicated, you can use [service accounts](https://docs.gitlab.com/api/service_accounts/) with appropriate scopes for the `GITLAB_TOKEN`.

**Protected Environments API:**
The [Protected Environments API](https://docs.gitlab.com/api/protected_environments/) is fully supported on GitLab Dedicated. The token needs at least Maintainer access to the project.

### Notes

- Requires GitLab Premium/Ultimate for protected environment approvers feature
- Falls back to `APPROVER_EMAILS` if API cannot retrieve user emails
- Falls back gracefully if notification fails (pipeline continues)
- SMTP port 25 is used by default (no authentication required on internal mail servers)

## Versioning

These components follow semantic versioning:

```yaml
# Recommended - pin to specific version
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-api@1.0.0
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-products@1.0.0
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-global-policy@1.0.0
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-subscriptions@1.0.0

# Latest minor version in 1.x
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-api@~1
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-products@~1
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-global-policy@~1
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-subscriptions@~1

# Latest version (not recommended for production)
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-api@~latest
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-products@~latest
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-global-policy@~latest
- component: $CI_SERVER_FQDN/devops/components/api-management/apim-subscriptions@~latest
```

## Troubleshooting

### Spec validation fails
- Ensure the spec file path is relative to the spec repo root
- Check JSON/YAML syntax locally with `jq . spec.json` or `yq . spec.yaml`
- Verify required fields are present:
  - `info.title` - display name (API ID auto-generated from this)
  - `x-lzd-api-path` - URL path in APIM
- For vendor APIs, ensure `x-lzd-api-path` starts with `vendors/`

### Azure authentication fails
- Verify all `{ENV}_AZ_*` variables are set correctly
- Ensure the service principal has Contributor role on APIM

### Policy import fails
- Validate XML syntax with `xmllint --noout policy.xml`
- Ensure `<policies>` root element exists
- Check for valid APIM policy expressions

### Vendor API not detected
- Ensure `x-lzd-api-path` starts with `vendors/` (e.g., `vendors/acme/orders`)
- The pipeline auto-generates API ID with `vendor-` prefix from title

### Path conflict detected

If you see the error `PATH CONFLICT DETECTED`, it means the path in your spec is already used by a different API:

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

## Publishing to Catalog

To publish this component to the GitLab CI/CD Catalog:

1. Push the repository to GitLab
2. Tag with semantic version: `git tag v1.0.0 && git push --tags`
3. The release pipeline creates a catalog entry

## License

MIT License
