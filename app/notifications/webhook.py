import logging
import json
from typing import Dict, Any, Optional

import httpx

from app.notifications.base import (
    Notification,
    NotificationChannel,
    NotificationChannelError,
)

logger = logging.getLogger(__name__)


class WebhookNotificationChannel(NotificationChannel):
    """Webhook notification channel - sends to an HTTP endpoint"""

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = 10.0

    def name(self) -> str:
        return "webhook"

    def is_available(self) -> bool:
        return bool(self.webhook_url)

    async def send(self, notification: Notification) -> bool:
        if not self.webhook_url:
            logger.warning("Webhook URL not configured, skipping notification")
            return False

        try:
            payload = self._build_payload(notification)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()

            logger.info(f"Webhook notification sent to {self.webhook_url}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Webhook returned status error: {e.response.status_code}")
            raise NotificationChannelError(f"Webhook error: {e}")

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            raise NotificationChannelError(f"Error: {e}")

    def _build_payload(self, notification: Notification) -> Dict[str, Any]:
        """Build the webhook payload"""
        return {
            "title": notification.title,
            "message": notification.message,
            "level": notification.level.value,
            "data": notification.data or {},
            "timestamp": notification.created_at.isoformat(),
        }
