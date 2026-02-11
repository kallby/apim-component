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
- Create subscriptions with flexible scope (product, API, or all APIs)
- Retrieve subscription keys (with approval required)
- Regenerate primary, secondary, or both keys
- Delete subscriptions
- Multi-environment deployments (dev, tst, stg, prd)
- Email notifications to approvers with product/scope details
- Audit logging

## Operations Quick Reference

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

## Subscription Scopes

Subscriptions can be scoped to different levels:

| Scope Type | Description | SCOPE_ID Required |
|------------|-------------|-------------------|
| `product` | Access to all APIs in a specific product | Yes (Product ID) |
| `api` | Access to a specific API only | Yes (API ID) |
| `all_apis` | Service-level access to all APIs | No |

## Default Values

| Variable | Default | Description |
|----------|---------|-------------|
| `SCOPE_TYPE` | `product` | Subscription scope type |
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

#### `create_subscription`

Create a new subscription with flexible scope.

**Required inputs:**
- `SUBSCRIPTION_NAME` - Display name for the subscription
- `SCOPE_TYPE` - Type of scope (`product`, `api`, or `all_apis`)
- `SCOPE_ID` - Product ID or API ID (required for `product` and `api` scopes)

**Optional inputs:**
- `SUBSCRIPTION_STATE` - Initial state (default: `active`)
- `ALLOW_TRACING` - Enable request tracing (default: `false`)

#### `delete_subscription`

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
- **Product/Scope information** - Which product or API the subscription is associated with
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

### Create a Product-Scoped Subscription

1. Go to CI/CD > Pipelines > Run pipeline
2. Select branch: `dev`
3. Set variables:
   - `OPERATION`: `create_subscription`
   - `SUBSCRIPTION_NAME`: `Partner ABC Production`
   - `SCOPE_TYPE`: `product`
   - `SCOPE_ID`: `premium-tier`
4. Click "Run pipeline"
5. Review the plan
6. Approve the deploy job

### Create an API-Scoped Subscription

1. Run pipeline on the appropriate branch
2. Set variables:
   - `OPERATION`: `create_subscription`
   - `SUBSCRIPTION_NAME`: `Mobile App - Orders API`
   - `SCOPE_TYPE`: `api`
   - `SCOPE_ID`: `orders-api`
3. Review and approve

### Create a Service-Level Subscription (All APIs)

1. Run pipeline on the appropriate branch
2. Set variables:
   - `OPERATION`: `create_subscription`
   - `SUBSCRIPTION_NAME`: `Internal Service Account`
   - `SCOPE_TYPE`: `all_apis`
   - `SCOPE_ID`: _(leave empty)_
3. Review and approve

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

### "SCOPE_ID is required"

When `SCOPE_TYPE` is `product` or `api`, you must provide the corresponding `SCOPE_ID`. Only `all_apis` scope type doesn't require a `SCOPE_ID`.

### "Product/API not found" when creating subscription

Ensure the product or API exists in APIM before creating a subscription scoped to it. Use the `apim-products` or `apim-api` components to create them first.

### Keys not displaying

The `get_subscription_keys` operation requires manual approval due to the sensitive nature of the data. Make sure you approve the deploy job after reviewing the plan.

## Differences from apim-products Subscriptions

This component (`apim-subscriptions`) manages subscriptions at the APIM service level with flexible scope options. The `apim-products` component also has subscription operations, but they are specifically for product-scoped subscriptions.

Use this component when you need:
- Service-level subscriptions (access to all APIs)
- API-specific subscriptions
- Full key management (viewing and regenerating keys)
- Centralized subscription management across products

Use `apim-products` subscriptions when you need:
- Simple product-scoped subscriptions
- Subscription management as part of product lifecycle
