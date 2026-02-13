# APIM Global Policy Component

A GitLab CI/CD Catalog component for managing the global (service-level) policy in Azure API Management.

## Quick Start

1. Add the component to your `.gitlab-ci.yml`:

```yaml
include:
  - component: $CI_SERVER_FQDN/devops/components/api-management/apim-global-policy@1.0.0
```

2. Store your global policy XML file in the same project (e.g., `policies/global-policy.xml`)

3. Run the pipeline from the GitLab UI and select your operation.

## Features

- View current global policy (gracefully handles when no policy exists)
- Apply new global policy from XML file
- Clear/reset global policy
- Multi-environment deployments (dev, tst, stg, prd)
- Automatic backup before changes (skips gracefully if no policy exists)
- Email notifications to approvers (supports users, groups, and roles)
- Audit logging in JSON format

## What is the Global Policy?

The global policy in Azure API Management applies to **all APIs** in the service. It's the outermost policy layer and executes before any product-level or API-level policies.

Common use cases:
- CORS configuration
- Authentication/authorization
- Global rate limiting
- Request/response logging
- IP filtering
- Common headers

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

## Operations Quick Reference

| Operation | Required Fields | Description |
|-----------|----------------|-------------|
| `get_global_policy` | - | View current global policy |
| `set_global_policy` | `POLICY_FILE_PATH` | Apply a new global policy |
| `clear_global_policy` | - | Remove the global policy |

## Operations

### `get_global_policy`

Retrieve and display the current global policy (read-only operation, approval required).

```
Required: (none)
```

If no policy is configured, the job will display a friendly message instead of failing.

### `set_global_policy`

Apply a new global policy from an XML file stored in your project.

```
Required: POLICY_FILE_PATH
```

| Field | Description |
|-------|-------------|
| `POLICY_FILE_PATH` | Path to policy XML file in this project (e.g., `policies/global-policy.xml`) |

The policy file is read from the same branch that triggers the pipeline.

### `clear_global_policy`

Remove the global policy, resetting to default behavior.

```
Required: (none)
```

**Warning:** This is a destructive operation that affects all APIs.

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

1. **Validate** - Validates inputs and policy XML syntax
2. **Backup** - Creates backup of current global policy (skips if none exists)
3. **Plan** - Shows current policy and planned changes
4. **Notify** - Sends email to approvers
5. **Deploy** - Manual approval required, then applies the policy

## Approval & Notification Rules

| Operation | All Branches |
|-----------|--------------|
| `get_global_policy` | Approval Required |
| `set_global_policy` | Approval Required |
| `clear_global_policy` | Approval Required |

**Notifications:** Email notifications are sent to approvers for all operations on all branches.

## Automatic Backups

Before any change, the component attempts to backup the current global policy:

| Scenario | Behavior |
|----------|----------|
| Policy exists | Backed up to `backup-{pipeline_id}/global-policy.xml` |
| No policy configured | Skipped gracefully with info message |
| Error retrieving | Continues with warning |

Backup metadata is saved to `backup-{pipeline_id}/metadata.json`:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "pipeline_id": "123456",
  "user": "developer@company.com",
  "operation": "set_global_policy",
  "environment": "dev",
  "policy_existed": true
}
```

Backups are retained as pipeline artifacts for 7 days.

## Audit Logging

All operations are logged to `audit-{pipeline_id}.json` and saved as a pipeline artifact for 30 days.

Example audit entry:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "pipeline_id": "123456",
  "job_id": "789012",
  "job_name": "set_global_policy_dev",
  "triggered_by": "developer",
  "action": "set_global_policy",
  "resource": "global",
  "environment": "dev",
  "apim_service": "apim-mycompany-dev",
  "details": "policy_file=policies/global-policy.xml"
}
```

## Global Policy Example

```xml
<policies>
    <inbound>
        <!-- CORS for developer portal and testing -->
        <cors allow-credentials="true">
            <allowed-origins>
                <origin>https://developer.mycompany.com</origin>
                <origin>https://localhost:3000</origin>
            </allowed-origins>
            <allowed-methods preflight-result-max-age="300">
                <method>GET</method>
                <method>POST</method>
                <method>PUT</method>
                <method>DELETE</method>
                <method>PATCH</method>
                <method>OPTIONS</method>
            </allowed-methods>
            <allowed-headers>
                <header>*</header>
            </allowed-headers>
        </cors>

        <!-- Global rate limiting -->
        <rate-limit-by-key calls="100" renewal-period="60"
                          counter-key="@(context.Request.IpAddress)" />

        <!-- Add correlation ID to all requests -->
        <set-header name="X-Correlation-ID" exists-action="skip">
            <value>@(Guid.NewGuid().ToString())</value>
        </set-header>
    </inbound>

    <backend>
        <base />
    </backend>

    <outbound>
        <!-- Remove internal headers -->
        <set-header name="X-Powered-By" exists-action="delete" />
        <set-header name="X-AspNet-Version" exists-action="delete" />

        <!-- Add security headers -->
        <set-header name="X-Content-Type-Options" exists-action="override">
            <value>nosniff</value>
        </set-header>
        <set-header name="X-Frame-Options" exists-action="override">
            <value>DENY</value>
        </set-header>
    </outbound>

    <on-error>
        <base />
        <!-- Log errors to Application Insights -->
        <trace source="Global Policy" severity="error">
            <message>@(context.LastError.Message)</message>
        </trace>
    </on-error>
</policies>
```

## Policy Inheritance

When you use `<base />` in API or product policies, the global policy is inherited at that point:

```
Request Flow:
  Global Policy (inbound)
    -> Product Policy (inbound)
      -> API Policy (inbound)
        -> Operation Policy (inbound)
          -> Backend
        -> Operation Policy (outbound)
      -> API Policy (outbound)
    -> Product Policy (outbound)
  -> Global Policy (outbound)
```

## Examples

### View Current Global Policy

1. Go to your project's CI/CD > Pipelines > Run pipeline
2. Select branch: `dev`
3. Set variables:
   - `OPERATION`: `get_global_policy`
4. Click "Run pipeline"
5. View the output in the job logs

If no policy is configured, you'll see:
```
[INFO] No global policy is currently configured for this APIM instance

==========================================
Status: No policy configured
==========================================

To set a global policy, run this pipeline with:
  OPERATION: set_global_policy
  POLICY_FILE_PATH: path/to/your/policy.xml
```

### Apply Global Policy

1. Create your policy file in your project:
   ```
   policies/global-policy.xml
   ```

2. Commit and push your changes to your branch
3. Run pipeline on that branch
4. Set variables:
   - `OPERATION`: `set_global_policy`
   - `POLICY_FILE_PATH`: `policies/global-policy.xml`
5. Review the plan showing current vs new policy
6. Approve the deploy job

### Clear Global Policy

1. Run pipeline on the appropriate branch
2. Set variables:
   - `OPERATION`: `clear_global_policy`
3. Review the backup in artifacts
4. Approve the deploy job (be careful - this affects all APIs!)

## Best Practices

### 1. Always Use `<base />`

Include `<base />` in your global policy sections to allow inheritance:

```xml
<inbound>
    <!-- Your global rules -->
    <base />  <!-- Allows product/API policies to add more rules -->
</inbound>
```

### 2. Test in Lower Environments First

Always apply changes to `dev` first, then promote through `tst` -> `stg` -> `prd`.

### 3. Keep Global Policy Minimal

Only include truly global concerns:
- CORS
- Security headers
- Global rate limiting
- Logging/tracing

API-specific logic should go in API or product policies.

### 4. Version Your Policies

Store policy files in Git with meaningful commit messages. The pipeline tracks which commit introduced each change.

### 5. Review Backups

Before approving changes in production, download and review the backup artifact to understand what's being replaced.

## Troubleshooting

### "Policy file not found"

Ensure `POLICY_FILE_PATH` is relative to the root of your project and the file exists in the branch you're running the pipeline from.

### "Invalid XML syntax"

The pipeline validates XML before applying. Check the validate_policy job output for syntax errors.

### "Missing `<policies>` element"

Global policy must have `<policies>` as the root element with `<inbound>`, `<backend>`, `<outbound>`, and `<on-error>` sections.

### "No global policy configured"

This is not an error. It means no global policy has been set yet. Use `set_global_policy` to apply one.

### Changes not taking effect

Global policy changes are immediate but may take a few seconds to propagate. If issues persist, check that `<base />` is properly placed in downstream policies.

### "Missing Azure credentials"

Verify that all required `{ENV}_*` variables are set for the branch you're running on.
