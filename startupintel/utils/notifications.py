"""Notification system for email and Slack alerts."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

import httpx
from startupintel.config import get_settings


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Notification:
    """Notification data structure."""
    title: str
    message: str
    channel: NotificationChannel
    priority: NotificationPriority = NotificationPriority.NORMAL
    recipient: str | None = None  # Email or Slack channel
    metadata: dict | None = None
    action_url: str | None = None
    action_text: str | None = None


class EmailNotifier:
    """Email notification handler using SendGrid or AWS SES."""
    
    def __init__(self):
        self.settings = get_settings()
        self.provider = self._detect_provider()
    
    def _detect_provider(self) -> str:
        """Detect which email provider to use."""
        if self.settings.sendgrid_api_key:
            return "sendgrid"
        elif self.settings.aws_access_key_id:
            return "ses"
        return "console"  # Fallback to console for development
    
    async def send(self, notification: Notification) -> dict:
        """Send email notification."""
        if self.provider == "sendgrid":
            return await self._send_sendgrid(notification)
        elif self.provider == "ses":
            return await self._send_ses(notification)
        else:
            # Console output for development
            print(f"[EMAIL TO: {notification.recipient}]")
            print(f"Subject: {notification.title}")
            print(f"Body: {notification.message}")
            return {"success": True, "provider": "console"}
    
    async def _send_sendgrid(self, notification: Notification) -> dict:
        """Send via SendGrid API."""
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        sg = SendGridAPIClient(self.settings.sendgrid_api_key)
        
        # HTML formatting
        html_content = self._format_html(notification)
        
        message = Mail(
            from_email=self.settings.email_from_address,
            to_emails=notification.recipient,
            subject=notification.title,
            html_content=html_content,
        )
        
        try:
            response = sg.send(message)
            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "provider": "sendgrid",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "sendgrid"}
    
    async def _send_ses(self, notification: Notification) -> dict:
        """Send via AWS SES."""
        import boto3
        
        ses = boto3.client(
            "ses",
            region_name=self.settings.aws_region or "us-east-1",
        )
        
        try:
            response = ses.send_email(
                Source=self.settings.email_from_address,
                Destination={"ToAddresses": [notification.recipient]},
                Message={
                    "Subject": {"Data": notification.title},
                    "Body": {
                        "Html": {"Data": self._format_html(notification)},
                        "Text": {"Data": notification.message},
                    },
                },
            )
            return {
                "success": True,
                "message_id": response["MessageId"],
                "provider": "ses",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "ses"}
    
    def _format_html(self, notification: Notification) -> str:
        """Format notification as HTML email."""
        action_button = ""
        if notification.action_url:
            action_button = f'''
            <tr>
                <td style="padding: 20px 30px;">
                    <a href="{html.escape(notification.action_url)}" 
                       style="background: #4F46E5; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 6px; display: inline-block;">
                        {html.escape(notification.action_text or "View Details")}
                    </a>
                </td>
            </tr>
            '''
        
        priority_color = {
            NotificationPriority.LOW: "#6B7280",
            NotificationPriority.NORMAL: "#4F46E5",
            NotificationPriority.HIGH: "#F59E0B",
            NotificationPriority.CRITICAL: "#EF4444",
        }.get(notification.priority, "#4F46E5")
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                     background: #f3f4f6; margin: 0; padding: 20px;">
            <table style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; 
                        overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <tr>
                    <td style="background: {priority_color}; padding: 20px 30px;">
                        <h1 style="color: white; margin: 0; font-size: 20px;">
                            StartupIntel Notification
                        </h1>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 30px;">
                        <h2 style="color: #111827; margin-top: 0;">{html.escape(notification.title)}</h2>
                        <p style="color: #4B5563; line-height: 1.6;">
                            {html.escape(notification.message).replace(chr(10), '<br>')}
                        </p>
                        {action_button}
                    </td>
                </tr>
                <tr>
                    <td style="background: #f9fafb; padding: 20px 30px; font-size: 12px; color: #6B7280;">
                        Sent at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """


class SlackNotifier:
    """Slack notification handler."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bot_token = self.settings.slack_bot_token
    
    async def send(self, notification: Notification) -> dict:
        """Send Slack notification."""
        if not self.bot_token:
            # Console output for development
            print(f"[SLACK TO: {notification.recipient}]")
            print(f"Message: {notification.title} - {notification.message}")
            return {"success": True, "provider": "console"}
        
        channel = notification.recipient or self.settings.slack_digest_channel
        
        # Format message as Slack blocks
        blocks = self._format_blocks(notification)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {self.bot_token}"},
                json={
                    "channel": channel,
                    "blocks": blocks,
                    "text": f"{notification.title}: {notification.message}",  # Fallback text
                },
            )
            
            result = response.json()
            return {
                "success": result.get("ok", False),
                "message_ts": result.get("ts"),
                "error": result.get("error"),
                "provider": "slack",
            }
    
    def _format_blocks(self, notification: Notification) -> list[dict]:
        """Format notification as Slack blocks."""
        priority_emoji = {
            NotificationPriority.LOW: ":information_source:",
            NotificationPriority.NORMAL: ":bell:",
            NotificationPriority.HIGH: ":warning:",
            NotificationPriority.CRITICAL: ":rotating_light:",
        }.get(notification.priority, ":bell:")
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{priority_emoji} {notification.title}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": notification.message,
                },
            },
        ]
        
        # Add action button if URL provided
        if notification.action_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": notification.action_text or "View Details",
                            "emoji": True,
                        },
                        "url": notification.action_url,
                        "style": "primary" if notification.priority in (
                            NotificationPriority.HIGH,
                            NotificationPriority.CRITICAL,
                        ) else "default",
                    },
                ],
            })
        
        # Add metadata context if available
        if notification.metadata:
            fields = []
            for key, value in list(notification.metadata.items())[:10]:  # Max 10 fields
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}:*\n{value}",
                })
            
            if fields:
                blocks.append({
                    "type": "section",
                    "fields": fields,
                })
        
        # Add footer with timestamp
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Sent at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
                },
            ],
        })
        
        return blocks


class WebhookNotifier:
    """Generic webhook notifier."""
    
    async def send(self, notification: Notification, webhook_url: str) -> dict:
        """Send notification to custom webhook."""
        payload = {
            "title": notification.title,
            "message": notification.message,
            "priority": notification.priority.value,
            "channel": notification.channel.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": notification.metadata or {},
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0,
                )
                return {
                    "success": 200 <= response.status_code < 300,
                    "status_code": response.status_code,
                    "provider": "webhook",
                }
            except Exception as e:
                return {"success": False, "error": str(e), "provider": "webhook"}


class NotificationManager:
    """Central notification manager."""
    
    def __init__(self):
        self.email = EmailNotifier()
        self.slack = SlackNotifier()
        self.webhook = WebhookNotifier()
    
    async def send(self, notification: Notification, webhook_url: str | None = None) -> dict:
        """Send notification through appropriate channel."""
        if notification.channel == NotificationChannel.EMAIL:
            return await self.email.send(notification)
        elif notification.channel == NotificationChannel.SLACK:
            return await self.slack.send(notification)
        elif notification.channel == NotificationChannel.WEBHOOK and webhook_url:
            return await self.webhook.send(notification, webhook_url)
        else:
            raise ValueError(f"Unsupported notification channel: {notification.channel}")
    
    async def notify_startup_score_change(
        self,
        startup_id: UUID,
        startup_name: str,
        bot_name: str,
        old_score: float,
        new_score: float,
        threshold_crossed: str | None = None,
        recipients: list[str] | None = None,
    ) -> list[dict]:
        """Notify about significant startup score changes."""
        score_change = new_score - old_score
        change_direction = "increased" if score_change > 0 else "decreased"
        
        # Determine priority based on threshold
        priority = NotificationPriority.NORMAL
        if threshold_crossed:
            priority = NotificationPriority.HIGH if threshold_crossed in ("warning", "alert") else NotificationPriority.CRITICAL
        
        notification = Notification(
            title=f"🚀 {startup_name} Score {change_direction.title()}",
            message=f"The {bot_name} score for {startup_name} has {change_direction} from {old_score:.1f} to {new_score:.1f}.",
            channel=NotificationChannel.SLACK,
            priority=priority,
            recipient=self.slack.settings.slack_digest_channel,
            metadata={
                "Startup": startup_name,
                "Bot": bot_name,
                "Previous Score": f"{old_score:.1f}",
                "New Score": f"{new_score:.1f}",
                "Change": f"{score_change:+.1f}",
                "Threshold": threshold_crossed or "N/A",
            },
            action_url=f"https://app.startupintel.io/startups/{startup_id}",
            action_text="View Startup",
        )
        
        results = []
        
        # Send to Slack
        results.append(await self.slack.send(notification))
        
        # Send to email recipients
        if recipients:
            for email in recipients:
                email_notification = Notification(
                    title=notification.title,
                    message=notification.message,
                    channel=NotificationChannel.EMAIL,
                    priority=priority,
                    recipient=email,
                    metadata=notification.metadata,
                    action_url=notification.action_url,
                    action_text=notification.action_text,
                )
                results.append(await self.email.send(email_notification))
        
        return results


# Global notification manager instance
notification_manager = NotificationManager()
