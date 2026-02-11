# APIM Products Component

A GitLab CI/CD Catalog component for managing Products, Groups, and Subscriptions in Azure API Management.

## Quick Start

Add the component to your `.gitlab-ci.yml`:

```yaml
include:
  - component: $CI_SERVER_FQDN/devops/components/api-management/apim-products@1.0.0
```

Then run the pipeline from the GitLab UI and select your operation.

## Features

- Create, update, and delete products
- Associate/disassociate APIs with products
- Manage product-level policies
- Control product visibility with groups
- Create and manage subscriptions
- Automatic vendor product detection and prefixing
- Multi-environment deployments (dev, tst, stg, prd)
- Email notifications to approvers
- Audit logging

## Operations Quick Reference

| Operation | Description | Required Variables |
|-----------|-------------|-------------------|
| `list_products` | List all products | - |
| `get_product` | Get product details | `PRODUCT_NAME` |
| `create_product` | Create new product | `PRODUCT_DISPLAY_NAME` |
| `update_product` | Update product | `PRODUCT_NAME` |
| `delete_product` | Delete product | `PRODUCT_NAME` |
| `list_product_apis` | List APIs in product | `PRODUCT_NAME` |
| `add_api_to_product` | Add API to product | `PRODUCT_NAME`, `API_NAME` |
| `remove_api_from_product` | Remove API from product | `PRODUCT_NAME`, `API_NAME` |
| `get_product_policy` | Get product policy | `PRODUCT_NAME` |
| `set_product_policy` | Set product policy | `PRODUCT_NAME`, `POLICY_FILE_PATH` |
| `clear_product_policy` | Remove product policy | `PRODUCT_NAME` |
| `list_product_groups` | List visibility groups | `PRODUCT_NAME` |
| `add_group_to_product` | Add visibility group | `PRODUCT_NAME` |
| `remove_group_from_product` | Remove visibility group | `PRODUCT_NAME`, `GROUP_NAME` |
| `list_product_subscriptions` | List subscriptions | `PRODUCT_NAME` |
| `create_product_subscription` | Create subscription | `PRODUCT_NAME`, `SUBSCRIPTION_NAME` |
| `delete_product_subscription` | Delete subscription | `SUBSCRIPTION_ID` |

## Default Values

The following variables have default values and don't need to be provided unless you want to override them:

| Variable | Default | Description |
|----------|---------|-------------|
| `PRODUCT_TYPE` | `internal` | Product type (`internal` or `vendor`) |
| `PRODUCT_STATE` | `published` | Product state (`published` or `notPublished`) |
| `SUBSCRIPTION_REQUIRED` | `true` | Whether subscription is required to access APIs |
| `APPROVAL_REQUIRED` | `false` | Whether subscription approval is required |
| `SUBSCRIPTIONS_LIMIT` | _(unlimited)_ | Maximum subscriptions allowed |
| `TERMS_OF_USE` | _(empty)_ | Legal terms for the product |
| `GROUP_NAME` | `developers` | Default group for visibility operations |
| `SUBSCRIPTION_STATE` | `active` | Subscription state (`active`, `suspended`, `cancelled`) |
| `DEBUG_MODE` | `false` | Enable verbose logging |

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

Repeat for `TST_`, `STG_`, and `PRD_` prefixes.

### Policy Repository (for product policies)

| Variable | Description |
|----------|-------------|
| `POLICY_REPO_URL` | GitLab repo URL containing policy XML files |
| `POLICY_REPO_USERNAME` | Username for cloning (usually `gitlab-ci-token`) |
| `POLICY_REPO_TOKEN` | Deploy token or CI job token |

### Email Notifications (optional)

| Variable | Description |
|----------|-------------|
| `GITLAB_TOKEN` | GitLab API token with `read_api` scope (requires Maintainer access to project) |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_FROM` | Sender email address |
| `SMTP_PORT` | SMTP port (default: 25) |
| `SMTP_EXCLUDE_EMAILS` | Additional emails to exclude (service accounts starting with `group_` are excluded by default) |
| `EMAIL_DOMAIN` | Domain for constructing emails from usernames (default: `lazard.com`) |
| `APPROVER_EMAILS` | Fallback comma-separated list of approver emails |

**Note:** Either `GITLAB_TOKEN` or `APPROVER_EMAILS` must be provided.

**EMAIL_DOMAIN:** When using role-based approvers (e.g., Maintainers group), GitLab's API often cannot retrieve user emails directly. The default domain is `lazard.com`, so emails are automatically constructed as `{gitlab_username}@lazard.com`.

## Operations

### Product Operations

#### `list_products`

List all products in the APIM instance (read-only, no approval required).

#### `get_product`

Get details of a specific product (read-only).

**Required inputs:**
- `PRODUCT_NAME` - ID of the product

#### `create_product`

Create a new product.

**Required inputs:**
- `PRODUCT_DISPLAY_NAME` - Display name shown in developer portal (e.g., `Premium Tier`, `Starter Plan`)

**Optional inputs:**
- `PRODUCT_DESCRIPTION` - Description of the product (defaults to `[Automated Product]` if not provided)
- `PRODUCT_NAME` - Override the auto-generated ID (by default, derived from display name)

All other settings use the default values shown in the [Default Values](#default-values) section.

> **Note:** If `PRODUCT_DESCRIPTION` is not provided, a warning will be displayed in the validation stage and the default value `[Automated Product]` will be used.

**Auto-generated Product ID:**

The Product ID is automatically derived from the display name by converting to lowercase and replacing spaces/special characters with hyphens:

| Display Name | Type | Generated Product ID | Final Display Name |
|--------------|------|---------------------|-------------------|
| `Premium Tier` | internal | `premium-tier` | `Premium Tier` |
| `Starter Plan` | internal | `starter-plan` | `Starter Plan` |
| `Partner API Access` | vendor | `vendor-partner-api-access` | `Vendor: Partner API Access` |

#### `update_product`

Update an existing product.

**Required inputs:**
- `PRODUCT_NAME` - ID of the product to update

**Optional inputs:**
- `PRODUCT_DISPLAY_NAME` - New display name for the product
- `PRODUCT_DESCRIPTION` - New description for the product

All other settings can be overridden from the [Default Values](#default-values) section.

> **Note:** Only provided values will be updated. If a field is not provided, the current value is preserved.

#### `delete_product`

Delete a product (creates backup first).

**Required inputs:**
- `PRODUCT_NAME` - ID of the product to delete

### API Association Operations

#### `list_product_apis`

List all APIs associated with a product (read-only).

**Required inputs:**
- `PRODUCT_NAME` - ID of the product

#### `add_api_to_product`

Associate an API with a product.

**Required inputs:**
- `PRODUCT_NAME` - ID of the product
- `API_NAME` - ID of the API to add

#### `remove_api_from_product`

Remove an API from a product.

**Required inputs:**
- `PRODUCT_NAME` - ID of the product
- `API_NAME` - ID of the API to remove

### Policy Operations

#### `get_product_policy`

Retrieve the current policy for a product (read-only).

**Required inputs:**
- `PRODUCT_NAME` - ID of the product

#### `set_product_policy`

Apply a policy XML file to a product.

**Required inputs:**
- `PRODUCT_NAME` - ID of the product
- `POLICY_FILE_PATH` - Path to policy XML in the policy repo

#### `clear_product_policy`

Remove the policy from a product.

**Required inputs:**
- `PRODUCT_NAME` - ID of the product

### Group Operations (Visibility)

Groups control who can see and subscribe to a product in the developer portal.

#### `list_product_groups`

List all groups associated with a product (read-only).

**Required inputs:**
- `PRODUCT_NAME` - ID of the product

#### `add_group_to_product`

Add a visibility group to a product.

**Required inputs:**
- `PRODUCT_NAME` - ID of the product

**Optional inputs:**
- `GROUP_NAME` - Name of the group (default: `developers`). Options: `developers`, `guests`, `administrators`

#### `remove_group_from_product`

Remove a visibility group from a product.

**Required inputs:**
- `PRODUCT_NAME` - ID of the product
- `GROUP_NAME` - Name of the group to remove

### Subscription Operations

#### `list_product_subscriptions`

List all subscriptions for a product (read-only).

**Required inputs:**
- `PRODUCT_NAME` - ID of the product

#### `create_product_subscription`

Create a new subscription for a product.

**Required inputs:**
- `PRODUCT_NAME` - ID of the product
- `SUBSCRIPTION_NAME` - Display name for the subscription

Subscription state defaults to `active`. See [Default Values](#default-values) to override.

#### `delete_product_subscription`

Delete a subscription.

**Required inputs:**
- `SUBSCRIPTION_ID` - ID of the subscription to delete

## Built-in Groups

APIM comes with three built-in groups:

| Group | Description |
|-------|-------------|
| `administrators` | Azure subscription administrators |
| `developers` | Authenticated developer portal users |
| `guests` | Unauthenticated developer portal visitors |

## Vendor Products

Set `PRODUCT_TYPE: vendor` to automatically:
- Prefix the Product ID with `vendor-`
- Prefix the display name with `Vendor: `

This helps distinguish third-party/vendor products from internal products in the APIM portal.

## Environment Mapping

The component automatically selects the environment based on the branch:

| Branch | Environment |
|--------|-------------|
| `dev`, `develop` | dev |
| `tst`, `test` | tst |
| `stg`, `staging` | stg |
| `prd`, `main` | prd |

## Pipeline Flow

1. **Validate** - Validates inputs and policy files (if applicable)
2. **Backup** - Creates backup of existing resources (for updates/deletes)
3. **Plan** - Shows what will be changed
4. **Notify** - Sends email to approvers (if configured)
5. **Deploy** - Manual approval required, then executes the operation

## Audit Logging

All operations are logged to `audit-{pipeline_id}.json` and saved as a pipeline artifact for 30 days.

## Examples

### Create a New Product

1. Go to your project's CI/CD > Pipelines > Run pipeline
2. Select branch: `dev`
3. Set variables:
   - `OPERATION`: `create_product`
   - `PRODUCT_DISPLAY_NAME`: `Premium Tier`
   - `PRODUCT_DESCRIPTION`: `Premium access with higher rate limits`
   - `SUBSCRIPTION_REQUIRED`: `true`
   - `APPROVAL_REQUIRED`: `true`
4. Click "Run pipeline"
5. Review the plan stage output (Product ID will be `premium-tier`)
6. Approve the deploy job

### Add APIs to a Product

1. Run pipeline on the appropriate branch
2. Set variables:
   - `OPERATION`: `add_api_to_product`
   - `PRODUCT_NAME`: `premium-tier`
   - `API_NAME`: `orders-api`
3. Review and approve

### Set Product Policy

1. Run pipeline on the appropriate branch
2. Set variables:
   - `OPERATION`: `set_product_policy`
   - `PRODUCT_NAME`: `premium-tier`
   - `POLICY_FILE_PATH`: `products/premium-tier/policy.xml`
3. Review and approve

### Make Product Visible to Developers

1. Run pipeline on the appropriate branch
2. Set variables:
   - `OPERATION`: `add_group_to_product`
   - `PRODUCT_NAME`: `premium-tier`
   - `GROUP_NAME`: `developers`
3. Review and approve

### Create a Subscription

1. Run pipeline on the appropriate branch
2. Set variables:
   - `OPERATION`: `create_product_subscription`
   - `PRODUCT_NAME`: `premium-tier`
   - `SUBSCRIPTION_NAME`: `Partner ABC Production`
3. Review and approve
4. Retrieve subscription keys from Azure Portal

## Product Policy Example

```xml
<policies>
    <inbound>
        <base />
        <!-- Rate limiting for this product -->
        <rate-limit calls="1000" renewal-period="60" />
        <!-- Quota for this product -->
        <quota calls="10000" renewal-period="86400" />
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

## Troubleshooting

### "Product not found"

Ensure `PRODUCT_NAME` matches exactly - it's case-sensitive.

### "Missing Azure credentials"

Verify that all required `{ENV}_*` variables are set for the branch you're running on.

### "API not found" when adding to product

Ensure the API exists in APIM before associating it with a product. Use the `apim-api` component to import APIs first.

### Subscription keys not visible

Subscription keys are managed through the Azure Portal or Azure CLI for security. The pipeline creates the subscription but doesn't expose the keys.

### Group not found

Use one of the built-in groups (`administrators`, `developers`, `guests`) or create custom groups through the Azure Portal first.
