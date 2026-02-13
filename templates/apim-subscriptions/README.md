# APIM Subscriptions Component

A GitLab CI/CD Catalog component for managing Subscriptions and subscription keys in Azure API Management.

## Quick Start

Add the component to your `.gitlab-ci.yml`:

```yaml
include:
  - component: $CI_SERVER_FQDN/devops/components/api-management/apim-subscriptions@1.0.0
```

Then run the pipeline from the GitLab UI and select your operation.

## Features

- List and view subscriptions across the APIM instance
- Create product-scoped subscriptions
- Retrieve subscription keys (with approval required)
- Regenerate primary, secondary, or both keys
- Delete subscriptions
- Multi-environment deployments (dev, tst, stg, prd)
- Email notifications to approvers with product details
- Audit logging

## Operations Quick Reference

| Operation | Description | Required Variables | Approval |
|-----------|-------------|-------------------|----------|
| `list_subscriptions` | List all subscriptions | - | No |
| `get_subscription` | Get subscription details | `SUBSCRIPTION_ID` | No |
| `create_product_subscription` | Create new subscription | `SUBSCRIPTION_NAME`, `PRODUCT_ID` | Yes |
| `delete_product_subscription` | Delete subscription | `SUBSCRIPTION_ID` | Yes |
| `get_subscription_keys` | Show primary & secondary keys | `SUBSCRIPTION_ID` | **Yes** |
| `regenerate_primary_key` | Regenerate primary key | `SUBSCRIPTION_ID` | Yes |
| `regenerate_secondary_key` | Regenerate secondary key | `SUBSCRIPTION_ID` | Yes |
| `regenerate_both_keys` | Regenerate both keys at once | `SUBSCRIPTION_ID` | Yes |

## Default Values

| Variable | Default | Description |
|----------|---------|-------------|
| `PRODUCT_ID` | _(empty)_ | Product ID for the subscription |
| `SUBSCRIPTION_STATE` | `active` | Initial state (`active`, `suspended`, `cancelled`) |
| `ALLOW_TRACING` | `false` | Enable request tracing |
| `SEND_KEYS_VIA_EMAIL` | `true` | Send retrieved keys via email instead of displaying in logs |
| `AUTO_SEND_KEYS` | `true` | Automatically send keys after create/regenerate operations |
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

### Read Operations (No Approval Required)

#### `list_subscriptions`

List all subscriptions in the APIM instance.

#### `get_subscription`

Get details of a specific subscription (metadata only, not keys).

**Required inputs:**
- `SUBSCRIPTION_ID` - ID of the subscription

### Write Operations (Approval Required)

#### `create_product_subscription`

Create a new subscription for a product.

**Required inputs:**
- `SUBSCRIPTION_NAME` - Display name for the subscription
- `PRODUCT_ID` - ID of the product

**Optional inputs:**
- `SUBSCRIPTION_STATE` - Initial state (default: `active`)
- `ALLOW_TRACING` - Enable request tracing (default: `false`)

#### `delete_product_subscription`

Delete a subscription permanently.

**Required inputs:**
- `SUBSCRIPTION_ID` - ID of the subscription to delete

### Sensitive Operations (Approval Required)

#### `get_subscription_keys`

Retrieve the primary and secondary keys for a subscription.

**Required inputs:**
- `SUBSCRIPTION_ID` - ID of the subscription

**Security Notes:**
- This operation exposes sensitive API keys
- Keys are displayed in the job output
- Ensure you're in a secure environment before running
- Keys should never be shared or stored in insecure locations

### Key Management Operations (Approval Required)

#### `regenerate_primary_key`

Regenerate the primary key for a subscription.

**Required inputs:**
- `SUBSCRIPTION_ID` - ID of the subscription

**Warning:** This immediately invalidates the current primary key. Applications using this key will lose access.

#### `regenerate_secondary_key`

Regenerate the secondary key for a subscription.

**Required inputs:**
- `SUBSCRIPTION_ID` - ID of the subscription

**Warning:** This immediately invalidates the current secondary key. Applications using this key will lose access.

#### `regenerate_both_keys`

Regenerate both primary and secondary keys for a subscription in a single operation.

**Required inputs:**
- `SUBSCRIPTION_ID` - ID of the subscription

**Warning:** This immediately invalidates BOTH keys. ALL applications using this subscription will lose access. Use this only when you need to completely rotate all keys at once. For zero-downtime rotation, use individual key regeneration instead.

## Key Rotation Best Practices

For zero-downtime key rotation:

1. **Check current usage** - Identify which key (primary/secondary) your applications use
2. **Regenerate unused key** - Regenerate the key that's NOT currently in use
3. **Update applications** - Update your applications to use the newly regenerated key
4. **Verify connectivity** - Confirm applications work with the new key
5. **Regenerate old key** - Now regenerate the original key for security

Example rotation flow:
```
1. Apps using primary key
2. Regenerate secondary key
3. Update apps to use secondary key
4. Verify apps work
5. Regenerate primary key (now unused)
6. Keep secondary as active, primary as backup
```

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
┌─────────────────┐
│ list operations │ ← No approval needed
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌─────────┐
│validate│ │  plan   │
└────┬───┘ └────┬────┘
     │          │
     └────┬─────┘
          ▼
    ┌──────────┐
    │  notify  │
    └────┬─────┘
         ▼
   ┌──────────────┐
   │ deploy_<env> │  ← Manual approval required
   └──────────────┘
```

## Approval Email Notifications

When an operation requires approval, email notifications are sent to configured approvers. The email includes:

- **Operation details** - What action is being requested
- **Subscription information** - Display name and ID
- **Product information** - Which product the subscription is associated with
- **Environment** - Target environment (dev, tst, stg, prd)
- **Risk indicators** - Warnings for destructive or sensitive operations
- **Direct link** - Link to the pipeline for review and approval

Example email content for a delete operation:
```
Requested Action: Delete Subscription

Delete subscription: Partner ABC Production
Subscription ID: sub-partner-abc-1234567890
Scope: Product: premium-tier

What will happen:
- All API keys for this subscription will be invalidated
- Applications using this subscription will lose access immediately
- This action cannot be undone
```

## Audit Logging

All operations are logged to `audit-{pipeline_id}.json` and saved as a pipeline artifact for 30 days. The audit log includes:

- Timestamp
- Operation performed
- Target resource (subscription ID)
- User who triggered the pipeline
- Environment and APIM service
- Additional details

## Examples

### Create a Subscription

1. Go to CI/CD > Pipelines > Run pipeline
2. Select branch: `dev`
3. Set variables:
   - `OPERATION`: `create_product_subscription`
   - `SUBSCRIPTION_NAME`: `Partner ABC Production`
   - `PRODUCT_ID`: `premium-tier`
4. Click "Run pipeline"
5. Review the plan
6. Approve the deploy job
7. Retrieve subscription keys using `get_subscription_keys` or Azure Portal

### Retrieve Subscription Keys

1. Run pipeline on the appropriate branch
2. Set variables:
   - `OPERATION`: `get_subscription_keys`
   - `SUBSCRIPTION_ID`: `sub-partner-abc-production-1234567890`
   - `SEND_KEYS_VIA_EMAIL`: `true` (default) or `false` to display in logs
3. Review the security warnings in the plan
4. Approve the deploy job
5. Keys are sent to your email (or displayed in job output if `SEND_KEYS_VIA_EMAIL=false`)

### Rotate Keys (Zero Downtime)

1. First, regenerate the secondary key:
   - `OPERATION`: `regenerate_secondary_key`
   - `SUBSCRIPTION_ID`: `sub-partner-abc-production-1234567890`
2. Update your applications to use the new secondary key
3. Then regenerate the primary key:
   - `OPERATION`: `regenerate_primary_key`
   - `SUBSCRIPTION_ID`: `sub-partner-abc-production-1234567890`

### Rotate Both Keys (With Downtime)

Use this when you need to invalidate all existing keys immediately (e.g., after a security incident):

1. Run pipeline on the appropriate branch
2. Set variables:
   - `OPERATION`: `regenerate_both_keys`
   - `SUBSCRIPTION_ID`: `sub-partner-abc-production-1234567890`
3. Review the warnings - all applications will lose access
4. Approve the deploy job
5. Use `get_subscription_keys` to retrieve the new keys
6. Update all applications with new keys

## Troubleshooting

### "Subscription not found"

If you see `SUBSCRIPTION NOT FOUND`, the subscription ID doesn't exist in the target APIM service:

```
The subscription ID 'my-sub-123' does not exist in apim-dev.

To find valid subscription IDs:
  Run the pipeline with OPERATION=list_subscriptions
```

**Common causes:**
- Typo in the subscription ID (IDs are case-sensitive)
- Subscription was deleted
- Wrong environment (running on wrong branch)

**Resolution:**
1. Run the pipeline with `OPERATION=list_subscriptions` to see all valid IDs
2. Copy the exact subscription ID from the list
3. Re-run your operation with the correct ID

### "Missing Azure credentials"

Verify that all required `{ENV}_*` variables are set for the branch you're running on.

### "PRODUCT_ID is required"

When creating a subscription, you must provide the `PRODUCT_ID` for the product the subscription will be scoped to.

### "Product not found" when creating subscription

Ensure the product exists in APIM before creating a subscription for it. Use the `apim-products` component to create products first.

### Keys not displaying

The `get_subscription_keys` operation requires manual approval due to the sensitive nature of the data. Make sure you approve the deploy job after reviewing the plan.

## Differences from apim-products

This component (`apim-subscriptions`) is the central component for all subscription management in APIM. It includes:

- **Create/delete subscriptions**: Product-scoped subscriptions
- **Key management**: View, regenerate primary, secondary, or both keys
- **Centralized management**: All subscription operations in one place

The `apim-products` component provides:
- `list_product_subscriptions` to view subscriptions for a product
- All other product management operations (create/update/delete products, policies, groups, API associations)

> **Migration Note:** The `create_product_subscription` and `delete_product_subscription` operations have been moved from `apim-products` to this component for centralized subscription management.
