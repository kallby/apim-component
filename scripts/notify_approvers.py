#!/usr/bin/env python3
"""
APIM Pipeline Approval Notification Script

Sends email notifications to protected environment approvers when a pipeline
job is waiting for approval. Designed for GitLab Dedicated instances.

Uses GitLab API to fetch approver details and SMTP (port 25) to send emails.

Usage:
    python notify_approvers.py

Required Environment Variables:
    GITLAB_URL          - GitLab instance URL (e.g., https://gitlab.yourcompany.com)
    GITLAB_TOKEN        - GitLab API token with read_api scope
    SMTP_HOST           - SMTP server hostname
    SMTP_FROM           - From email address

    # GitLab CI/CD Variables (auto-populated in pipeline)
    CI_PROJECT_ID       - Project ID
    CI_PIPELINE_ID      - Pipeline ID
    CI_PIPELINE_URL     - Pipeline URL
    CI_COMMIT_BRANCH    - Branch name
    CI_PROJECT_URL      - Project URL
    GITLAB_USER_NAME    - User who triggered the pipeline
    GITLAB_USER_EMAIL   - Email of user who triggered the pipeline

    # Pipeline-specific variables
    OPERATION           - Operation being performed
    POLICY_FILE_PATH    - Path to policy file (if applicable)
    SPEC_FILE_PATH      - Path to spec file (if applicable)
    API_ID              - API ID (if applicable)
    PRODUCT_ID          - Product ID (if applicable)

Optional Environment Variables:
    SMTP_PORT           - SMTP port (default: 25)
    SMTP_USE_TLS        - Use STARTTLS (default: false)
    SMTP_USERNAME       - SMTP authentication username
    SMTP_PASSWORD       - SMTP authentication password
    SMTP_FROM_NAME      - Display name for the sender (e.g., "APIM Pipeline")
    POLICY_REPO_URL     - Policy repository URL for direct links
    SPEC_REPO_URL       - Spec repository URL for direct links
    POLICY_REPO_BRANCH  - Policy repo branch (default: main)
    SPEC_REPO_BRANCH    - Spec repo branch (default: main)
    APPROVER_EMAILS     - Comma-separated list of approver emails (fallback if API fails)
    NOTIFICATION_CC     - Comma-separated list of CC recipients

GitLab Dedicated Notes:
    - Protected environments API is fully supported
    - User email visibility depends on admin settings
    - For user emails, the token owner needs admin access OR users must have public_email set
    - If API cannot retrieve emails, use APPROVER_EMAILS as fallback
    - Service accounts can be used with appropriate scopes
"""

import os
import sys
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, Dict, List, Set
from datetime import datetime, timezone, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    logger.error("requests library not installed. Run: pip install requests")
    sys.exit(1)


class GitLabClient:
    """Client for GitLab API interactions (GitLab Dedicated compatible)."""

    def __init__(self, gitlab_url: str, token: str):
        self.gitlab_url = gitlab_url.rstrip('/')
        self.token = token
        self.headers = {'PRIVATE-TOKEN': token}
        self.api_url = f"{self.gitlab_url}/api/v4"
        self._is_admin = None

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make GET request to GitLab API."""
        url = f"{self.api_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning(f"Access denied for endpoint: {endpoint}")
            elif e.response.status_code == 404:
                logger.warning(f"Resource not found: {endpoint}")
            raise

    def check_admin_access(self) -> bool:
        """Check if the token has admin access."""
        if self._is_admin is not None:
            return self._is_admin
        try:
            # Try to access admin-only endpoint
            self._get("application/settings")
            self._is_admin = True
            logger.info("Token has admin access - can retrieve user emails")
        except:
            self._is_admin = False
            logger.info("Token does not have admin access - will use public_email only")
        return self._is_admin

    def get_current_user(self) -> dict:
        """Get current authenticated user."""
        return self._get("user")

    def get_protected_environment(self, project_id: str, environment_name: str) -> dict:
        """Get protected environment details including approvers."""
        endpoint = f"projects/{project_id}/protected_environments/{environment_name}"
        return self._get(endpoint)

    def get_user(self, user_id: int) -> dict:
        """Get user details by ID."""
        endpoint = f"users/{user_id}"
        return self._get(endpoint)

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Get user details by username."""
        try:
            users = self._get("users", params={'username': username})
            return users[0] if users else None
        except:
            return None

    def get_group_members(self, group_id: int) -> list:
        """Get all members of a group."""
        endpoint = f"groups/{group_id}/members/all"
        members = []
        page = 1
        while True:
            try:
                result = self._get(endpoint, params={'page': page, 'per_page': 100})
                if not result:
                    break
                members.extend(result)
                page += 1
                if len(result) < 100:
                    break
            except:
                break
        return members

    def get_group(self, group_id: int) -> dict:
        """Get group details by ID."""
        endpoint = f"groups/{group_id}"
        return self._get(endpoint)

    def get_project(self, project_id: str) -> dict:
        """Get project details."""
        endpoint = f"projects/{project_id}"
        return self._get(endpoint)

    def get_project_members(self, project_id: str) -> list:
        """Get all members of a project (alternative for getting approvers)."""
        endpoint = f"projects/{project_id}/members/all"
        members = []
        page = 1
        while True:
            try:
                result = self._get(endpoint, params={'page': page, 'per_page': 100})
                if not result:
                    break
                members.extend(result)
                page += 1
                if len(result) < 100:
                    break
            except:
                break
        return members


class ApproverCollector:
    """Collects approver emails from protected environment configuration."""

    def __init__(self, gitlab_client: GitLabClient):
        self.gitlab = gitlab_client
        self.approvers: Dict[str, dict] = {}  # email -> {name, username, source}

    def collect_from_environment(self, project_id: str, environment_name: str) -> Dict[str, dict]:
        """
        Collect all approvers for a protected environment.

        Returns dict of {email: {name, username, source}}
        """
        try:
            env_config = self.gitlab.get_protected_environment(project_id, environment_name)
            logger.info(f"Found protected environment configuration for '{environment_name}'")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Protected environment '{environment_name}' not found")
                logger.info("This may indicate the environment is not configured as protected")
            elif e.response.status_code == 403:
                logger.warning(f"Access denied to protected environment '{environment_name}'")
                logger.info("Token may need maintainer+ access to the project")
            return {}
        except Exception as e:
            logger.warning(f"Error fetching protected environment: {e}")
            return {}

        # Process approval_rules (who can approve)
        approval_rules = env_config.get('approval_rules', [])
        logger.info(f"Found {len(approval_rules)} approval rules")
        for rule in approval_rules:
            self._process_access_level(rule, f"approval rule for {environment_name}")

        return self.approvers

    def _process_access_level(self, access: dict, source: str):
        """Process a single access level entry (user or group)."""
        user_id = access.get('user_id')
        group_id = access.get('group_id')
        access_level = access.get('access_level')
        access_level_desc = access.get('access_level_description', '')

        if user_id:
            self._add_user(user_id, source)
        elif group_id:
            self._add_group_members(group_id, source)
        elif access_level:
            # Access level based (e.g., "Maintainers", "Developers")
            logger.info(f"Access level based rule: {access_level_desc} (level {access_level})")
            # Cannot resolve individual emails for access level rules

    def _add_user(self, user_id: int, source: str):
        """Add a single user to approvers."""
        try:
            user = self.gitlab.get_user(user_id)
            # Try multiple email fields
            email = (
                user.get('email') or
                user.get('public_email') or
                user.get('commit_email')
            )

            if email and email != 'private':
                name = user.get('name', user.get('username', 'Unknown'))
                username = user.get('username', '')
                self.approvers[email] = {
                    'name': name,
                    'username': username,
                    'source': source,
                    'user_id': user_id
                }
                logger.info(f"Added approver: {name} <{email}> (from {source})")
            else:
                username = user.get('username', f'user_{user_id}')
                logger.warning(f"No accessible email for user '{username}' (id: {user_id})")
                logger.info("User may need to set a public email, or token needs admin access")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"Failed to fetch user {user_id}: {e}")
        except Exception as e:
            logger.warning(f"Error processing user {user_id}: {e}")

    def _add_group_members(self, group_id: int, source: str):
        """Add all members of a group to approvers."""
        try:
            group = self.gitlab.get_group(group_id)
            group_name = group.get('name', f'Group {group_id}')
            logger.info(f"Processing group: {group_name} (id: {group_id})")

            members = self.gitlab.get_group_members(group_id)
            added_count = 0

            for member in members:
                # Only include users with at least Maintainer access (40+)
                access_level = member.get('access_level', 0)
                if access_level >= 40:  # Maintainer or higher
                    email = (
                        member.get('email') or
                        member.get('public_email') or
                        member.get('commit_email')
                    )
                    if email and email != 'private':
                        name = member.get('name', member.get('username', 'Unknown'))
                        username = member.get('username', '')
                        self.approvers[email] = {
                            'name': name,
                            'username': username,
                            'source': f"{source} (group: {group_name})",
                            'user_id': member.get('id')
                        }
                        added_count += 1

            logger.info(f"Added {added_count} approvers from group '{group_name}'")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"Failed to fetch group {group_id} members: {e}")
        except Exception as e:
            logger.warning(f"Error processing group {group_id}: {e}")


class EmailNotifier:
    """Sends email notifications via SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_address: str,
        from_name: str = None,
        use_tls: bool = False,
        username: str = None,
        password: str = None
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_address = from_address
        self.from_name = from_name
        self.use_tls = use_tls
        self.username = username
        self.password = password

    def send_approval_notification(
        self,
        to_emails: List[str],
        cc_emails: List[str] = None,
        subject: str = "",
        html_body: str = "",
        text_body: str = ""
    ) -> bool:
        """Send email notification to approvers."""
        if not to_emails:
            logger.warning("No recipients to send email to")
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr((self.from_name, self.from_address)) if self.from_name else self.from_address
        msg['To'] = ', '.join(to_emails)

        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)
            all_recipients = to_emails + cc_emails
        else:
            all_recipients = to_emails

        # Attach both plain text and HTML versions
        part1 = MIMEText(text_body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)

        try:
            logger.info(f"Connecting to SMTP server {self.smtp_host}:{self.smtp_port}")

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                # Enable TLS if configured
                if self.use_tls:
                    server.starttls()
                    logger.info("STARTTLS enabled")

                # Authenticate if credentials provided
                if self.username and self.password:
                    server.login(self.username, self.password)
                    logger.info("SMTP authentication successful")

                server.sendmail(self.from_address, all_recipients, msg.as_string())

            logger.info(f"Email sent successfully to {len(all_recipients)} recipients")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipients refused: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except ConnectionRefusedError:
            logger.error(f"Connection refused to {self.smtp_host}:{self.smtp_port}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False


def get_environment_from_branch(branch: str) -> str:
    """Determine environment name from branch."""
    branch_env_map = {
        'dev': 'dev',
        'develop': 'dev',
        'tst': 'tst',
        'test': 'tst',
        'stg': 'stg',
        'staging': 'stg',
        'prd': 'prd',
        'main': 'prd',
        'master': 'prd'
    }
    return branch_env_map.get(branch, 'dev')


def build_file_url(repo_url: str, branch: str, file_path: str) -> Optional[str]:
    """Build a direct URL to a file in a GitLab repository."""
    if not repo_url or not file_path:
        return None

    # Remove .git suffix and trailing slashes
    repo_url = repo_url.rstrip('/').rstrip('.git')

    # Build blob URL
    return f"{repo_url}/-/blob/{branch}/{file_path}"


def build_email_content(context: dict) -> tuple:
    """Build HTML and plain text email content."""

    operation = context.get('operation', 'Unknown')
    environment = context.get('environment', 'Unknown')
    pipeline_url = context.get('pipeline_url', '#')
    project_name = context.get('project_name', 'Unknown Project')
    triggered_by = context.get('triggered_by', 'Unknown')
    triggered_by_email = context.get('triggered_by_email', '')
    branch = context.get('branch', 'Unknown')
    timestamp = context.get('timestamp', datetime.utcnow().isoformat())
    lob = context.get('lob', 'Unknown')
    apim_instance = context.get('apim_instance', 'Unknown')

    # Risk indicator for destructive operations
    destructive_ops = [
        'delete_api', 'clear_api_policy', 'clear_operation_policy',
        'delete_product', 'clear_product_policy', 'remove_api_from_product',
        'remove_group_from_product', 'delete_product_subscription',
        'clear_global_policy'
    ]
    is_destructive = operation in destructive_ops

    # Build additional details section based on operation type
    additional_details_html = ""
    additional_details_text = ""

    if context.get('api_id'):
        additional_details_html += f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee; color: #666;'><strong>API ID:</strong></td><td style='padding: 8px; border-bottom: 1px solid #eee;'><code style='background: #e9ecef; padding: 2px 6px; border-radius: 3px;'>{context['api_id']}</code></td></tr>"
        additional_details_text += f"API ID: {context['api_id']}\n"

    if context.get('product_id'):
        additional_details_html += f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee; color: #666;'><strong>Product ID:</strong></td><td style='padding: 8px; border-bottom: 1px solid #eee;'><code style='background: #e9ecef; padding: 2px 6px; border-radius: 3px;'>{context['product_id']}</code></td></tr>"
        additional_details_text += f"Product ID: {context['product_id']}\n"

    if context.get('operation_id'):
        additional_details_html += f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee; color: #666;'><strong>Operation ID:</strong></td><td style='padding: 8px; border-bottom: 1px solid #eee;'><code style='background: #e9ecef; padding: 2px 6px; border-radius: 3px;'>{context['operation_id']}</code></td></tr>"
        additional_details_text += f"Operation ID: {context['operation_id']}\n"

    if context.get('policy_file_path'):
        policy_url = context.get('policy_file_url')
        if policy_url:
            additional_details_html += f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee; color: #666;'><strong>Policy File:</strong></td><td style='padding: 8px; border-bottom: 1px solid #eee;'><a href=\"{policy_url}\" style='color: #1f75cb;'>{context['policy_file_path']}</a></td></tr>"
            additional_details_text += f"Policy File: {context['policy_file_path']}\n  Link: {policy_url}\n"
        else:
            additional_details_html += f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee; color: #666;'><strong>Policy File:</strong></td><td style='padding: 8px; border-bottom: 1px solid #eee;'>{context['policy_file_path']}</td></tr>"
            additional_details_text += f"Policy File: {context['policy_file_path']}\n"

    if context.get('spec_file_path'):
        spec_url = context.get('spec_file_url')
        if spec_url:
            additional_details_html += f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee; color: #666;'><strong>Spec File:</strong></td><td style='padding: 8px; border-bottom: 1px solid #eee;'><a href=\"{spec_url}\" style='color: #1f75cb;'>{context['spec_file_path']}</a></td></tr>"
            additional_details_text += f"Spec File: {context['spec_file_path']}\n  Link: {spec_url}\n"
        else:
            additional_details_html += f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee; color: #666;'><strong>Spec File:</strong></td><td style='padding: 8px; border-bottom: 1px solid #eee;'>{context['spec_file_path']}</td></tr>"
            additional_details_text += f"Spec File: {context['spec_file_path']}\n"

    # Environment-specific colors
    env_colors = {
        'prd': '#dc3545',  # Red
        'stg': '#fd7e14',  # Orange
        'tst': '#17a2b8',  # Teal
        'dev': '#28a745',  # Green
    }
    env_color = env_colors.get(environment, '#6c757d')

    # Risk banner for destructive operations
    risk_banner = ""
    if is_destructive:
        risk_banner = """<div style="background: #dc3545; color: white; padding: 15px 20px; margin-bottom: 20px; border-radius: 6px;">
            <strong>⚠️ DESTRUCTIVE OPERATION</strong>
            <p style="margin: 8px 0 0 0; font-size: 14px;">This action will permanently delete or clear resources. Please review carefully before approving.</p>
        </div>"""

    # Operation style - red for destructive, green for normal
    op_style = "background: #dc3545; color: white;" if is_destructive else "background: #d4edda; color: #155724;"
    destructive_badge = ' <span style="background: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 600;">DESTRUCTIVE</span>' if is_destructive else ''

    # HTML Email
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
    <div style="max-width: 650px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #1f75cb 0%, #1a5fa8 100%); color: white; padding: 25px; border-radius: 8px 8px 0 0;">
            <h1 style="margin: 0; font-size: 24px; font-weight: 600;">Pipeline Approval Required</h1>
            <p style="margin: 8px 0 0 0; opacity: 0.9; font-size: 14px;">Azure API Management Deployment</p>
            <p style="margin: 8px 0 0 0; opacity: 0.8; font-size: 12px;">Requested: {timestamp}</p>
        </div>
        <div style="background: #f9f9f9; padding: 25px; border: 1px solid #e1e1e1; border-top: none;">
            {risk_banner}
            <p style="margin-top: 0; font-size: 16px;">A pipeline is waiting for your approval to deploy to <span style="display: inline-block; background: {env_color}; color: white; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; text-transform: uppercase;">{environment.upper()}</span></p>

            <!-- Main Details Card -->
            <div style="background: white; border-radius: 6px; padding: 0; margin: 20px 0; border: 1px solid #e1e1e1; overflow: hidden;">
                <div style="background: #f8f9fa; padding: 12px 15px; border-bottom: 1px solid #e1e1e1;">
                    <strong style="color: #495057; font-size: 14px;">Deployment Details</strong>
                </div>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background: #f0f7ff;">
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #495057; width: 140px;"><strong>LOB:</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee;"><span style="background: #6f42c1; color: white; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 600;">{lob.upper()}</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #666;"><strong>APIM Instance:</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee;"><code style="background: #e9ecef; padding: 3px 8px; border-radius: 4px; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 13px;">{apim_instance}</code></td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #666;"><strong>Project:</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee;">{project_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #666;"><strong>Operation:</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee;"><code style="{op_style} padding: 3px 8px; border-radius: 4px; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 13px;">{operation}</code>{destructive_badge}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #666;"><strong>Environment:</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee;"><span style="background: {env_color}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600;">{environment.upper()}</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #666;"><strong>Branch:</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee;"><code style="background: #e9ecef; padding: 2px 6px; border-radius: 3px;">{branch}</code></td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #666;"><strong>Triggered by:</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee;">{triggered_by}{f' <span style="color: #666;">({triggered_by_email})</span>' if triggered_by_email else ''}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #666;"><strong>Requested at:</strong></td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #666; font-size: 13px;">{timestamp}</td>
                    </tr>
                    {additional_details_html}
                </table>
            </div>

            {"<div style='background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 6px; margin: 20px 0;'><strong style=\"color: #856404;\">⚠️ Production Deployment</strong><p style=\"margin: 8px 0 0 0; color: #856404; font-size: 14px;\">This deployment targets the <strong>PRODUCTION</strong> environment. Please review all changes carefully before approving.</p></div>" if environment == 'prd' else ""}

            <div style="text-align: center; margin: 25px 0;">
                <a href="{pipeline_url}" style="display: inline-block; background: linear-gradient(135deg, #1f75cb 0%, #1a5fa8 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">Review & Approve Pipeline</a>
            </div>

            <p style="color: #666; font-size: 13px; margin-top: 20px; text-align: center;">
                Click the button above to review the pipeline details and approve or reject the deployment.
            </p>
        </div>
        <div style="text-align: center; padding: 20px; color: #888; font-size: 11px; background: #f8f9fa; border-radius: 0 0 8px 8px; border: 1px solid #e1e1e1; border-top: none;">
            <p style="margin: 5px 0;">This is an automated notification from the APIM CI/CD Pipeline.</p>
            <p style="margin: 5px 0;">Do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
"""

    # Destructive warning for plain text
    destructive_warning = ""
    if is_destructive:
        destructive_warning = f"""
{"!" * 60}
⚠️  DESTRUCTIVE OPERATION
This action will permanently delete or clear resources.
Please review carefully before approving.
{"!" * 60}
"""

    # Plain Text Email
    text_body = f"""
PIPELINE APPROVAL REQUIRED
{'=' * 60}
{destructive_warning}
A pipeline is waiting for your approval to deploy to {environment.upper()}.

DEPLOYMENT DETAILS
{'-' * 60}
LOB:           {lob.upper()}
APIM Instance: {apim_instance}
Project:       {project_name}
Operation:     {operation} {"[DESTRUCTIVE]" if is_destructive else ""}
Environment:   {environment.upper()}
Branch:        {branch}
Triggered by:  {triggered_by}{f' ({triggered_by_email})' if triggered_by_email else ''}
Requested at:  {timestamp}

{additional_details_text}
{"!" * 60}
WARNING: This is a PRODUCTION deployment.
Please review all changes carefully before approving.
{"!" * 60}
" if environment == 'prd' else ""}

Review Pipeline: {pipeline_url}

{'=' * 60}
This is an automated notification from the APIM CI/CD Pipeline.
Do not reply to this email.
"""

    return html_body, text_body


def parse_email_list(email_string: str) -> List[str]:
    """Parse comma-separated email list."""
    if not email_string:
        return []
    return [e.strip() for e in email_string.split(',') if e.strip() and '@' in e]


def main():
    """Main function to send approval notifications."""

    # Required environment variables
    gitlab_url = os.environ.get('GITLAB_URL') or os.environ.get('CI_SERVER_URL')
    gitlab_token = os.environ.get('GITLAB_TOKEN') or os.environ.get('GITLAB_API_TOKEN')
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_from = os.environ.get('SMTP_FROM')

    # Validate required variables
    missing = []
    if not gitlab_url:
        missing.append('GITLAB_URL or CI_SERVER_URL')
    if not smtp_host:
        missing.append('SMTP_HOST')
    if not smtp_from:
        missing.append('SMTP_FROM')

    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    # GitLab token is optional if APPROVER_EMAILS is provided
    fallback_emails = parse_email_list(os.environ.get('APPROVER_EMAILS', ''))

    if not gitlab_token and not fallback_emails:
        logger.error("Either GITLAB_TOKEN or APPROVER_EMAILS must be provided")
        sys.exit(1)

    # GitLab CI/CD variables
    project_id = os.environ.get('CI_PROJECT_ID')
    pipeline_id = os.environ.get('CI_PIPELINE_ID')
    pipeline_url = os.environ.get('CI_PIPELINE_URL')
    branch = os.environ.get('CI_COMMIT_BRANCH', 'main')
    project_url = os.environ.get('CI_PROJECT_URL', '')
    project_name = os.environ.get('CI_PROJECT_NAME', 'APIM Pipeline')
    triggered_by = os.environ.get('GITLAB_USER_NAME', 'Unknown')
    triggered_by_email = os.environ.get('GITLAB_USER_EMAIL', '')

    # Pipeline-specific variables
    operation = os.environ.get('OPERATION', 'Unknown')
    policy_file_path = os.environ.get('POLICY_FILE_PATH', '')
    spec_file_path = os.environ.get('SPEC_FILE_PATH', '')
    api_id = os.environ.get('API_ID', '')
    product_id = os.environ.get('PRODUCT_ID', '')
    operation_id = os.environ.get('OPERATION_ID', '')

    # LOB and APIM instance
    lob = os.environ.get('CI_PROJECT_ROOT_NAMESPACE', 'Unknown')
    apim_instance = os.environ.get('APIM_SERVICE', 'Unknown')

    # Repository URLs for direct links
    policy_repo_url = os.environ.get('POLICY_REPO_URL', '')
    spec_repo_url = os.environ.get('SPEC_REPO_URL', '')
    policy_repo_branch = os.environ.get('POLICY_REPO_BRANCH', 'main')
    spec_repo_branch = os.environ.get('SPEC_REPO_BRANCH', 'main')

    # SMTP configuration
    smtp_port = int(os.environ.get('SMTP_PORT', '25'))
    smtp_use_tls = os.environ.get('SMTP_USE_TLS', '').lower() in ('true', '1', 'yes')
    smtp_username = os.environ.get('SMTP_USERNAME', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')
    smtp_from_name = os.environ.get('SMTP_FROM_NAME', '')

    # CC recipients
    cc_emails = parse_email_list(os.environ.get('NOTIFICATION_CC', ''))

    # Determine environment from branch
    environment = get_environment_from_branch(branch)

    logger.info(f"Starting approval notification for pipeline {pipeline_id}")
    logger.info(f"LOB: {lob}, APIM Instance: {apim_instance}")
    logger.info(f"Operation: {operation}, Environment: {environment}")
    logger.info(f"GitLab URL: {gitlab_url}")

    # Collect approvers
    approvers = {}

    if gitlab_token:
        # Initialize GitLab client and collect approvers from API
        gitlab = GitLabClient(gitlab_url, gitlab_token)
        collector = ApproverCollector(gitlab)

        logger.info(f"Fetching approvers for environment: {environment}")

        try:
            approvers = collector.collect_from_environment(project_id, environment)
        except Exception as e:
            logger.warning(f"Failed to collect approvers from API: {e}")

    # Add fallback emails if no approvers found from API
    if not approvers and fallback_emails:
        logger.info(f"Using fallback APPROVER_EMAILS: {len(fallback_emails)} recipients")
        for email in fallback_emails:
            approvers[email] = {
                'name': email.split('@')[0],
                'username': '',
                'source': 'APPROVER_EMAILS environment variable'
            }
    elif fallback_emails:
        # Add fallback emails in addition to API results
        for email in fallback_emails:
            if email not in approvers:
                approvers[email] = {
                    'name': email.split('@')[0],
                    'username': '',
                    'source': 'APPROVER_EMAILS environment variable (additional)'
                }

    if not approvers:
        logger.warning("No approvers found - notification cannot be sent")
        logger.info("To resolve this, either:")
        logger.info("  1. Configure protected environment with specific users/groups")
        logger.info("  2. Set APPROVER_EMAILS environment variable with recipient emails")
        logger.info("  3. Ensure users have public_email set in their GitLab profile")
        return

    logger.info(f"Total approvers to notify: {len(approvers)}")

    # Initialize email notifier
    notifier = EmailNotifier(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        from_address=smtp_from,
        from_name=smtp_from_name if smtp_from_name else None,
        use_tls=smtp_use_tls,
        username=smtp_username if smtp_username else None,
        password=smtp_password if smtp_password else None
    )

    # Build file URLs
    policy_file_url = build_file_url(policy_repo_url, policy_repo_branch, policy_file_path)
    spec_file_url = build_file_url(spec_repo_url, spec_repo_branch, spec_file_path)

    # Build email content
    context = {
        'lob': lob,
        'apim_instance': apim_instance,
        'operation': operation,
        'environment': environment,
        'pipeline_url': pipeline_url or f"{project_url}/-/pipelines/{pipeline_id}",
        'project_name': project_name,
        'triggered_by': triggered_by,
        'triggered_by_email': triggered_by_email,
        'branch': branch,
        'timestamp': datetime.now(timezone(timedelta(hours=-5))).strftime('%Y-%m-%d %I:%M:%S %p ET'),
        'api_id': api_id,
        'product_id': product_id,
        'operation_id': operation_id,
        'policy_file_path': policy_file_path,
        'policy_file_url': policy_file_url,
        'spec_file_path': spec_file_path,
        'spec_file_url': spec_file_url,
    }

    html_body, text_body = build_email_content(context)

    # Build subject line
    lob_prefix = f"[{lob.upper()}]" if lob and lob != 'Unknown' else "[APIM]"
    subject = f"{lob_prefix} [{environment.upper()}] Approval Required: {operation}"
    if environment == 'prd':
        subject = f"{lob_prefix} [PRODUCTION] Approval Required: {operation}"

    # Send email
    to_emails = list(approvers.keys())
    success = notifier.send_approval_notification(
        to_emails=to_emails,
        cc_emails=cc_emails,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )

    if success:
        logger.info("Approval notification sent successfully")
        logger.info("Recipients:")
        for email, info in approvers.items():
            logger.info(f"  - {info['name']} <{email}> (via {info['source']})")
        if cc_emails:
            logger.info(f"CC: {', '.join(cc_emails)}")
    else:
        logger.error("Failed to send approval notification")
        sys.exit(1)


if __name__ == '__main__':
    main()
