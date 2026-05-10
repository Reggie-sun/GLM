from app.notifications.base import (
    Notification,
    NotificationLevel,
    NotificationChannel,
    NotificationChannelError,
)
from app.notifications.console import ConsoleNotificationChannel
from app.notifications.webhook import WebhookNotificationChannel


class NotificationService:
    """Service to manage multiple notification channels"""

    def __init__(self):
        self._channels: Dict[str, NotificationChannel] = {}
        self._default_channels: list[str] = []

    def register_channel(self, channel: NotificationChannel, set_default: bool = False):
        """Register a notification channel"""
        self._channels[channel.name()] = channel
        if set_default:
            if channel.name() not in self._default_channels:
                self._default_channels.append(channel.name())

    def get_channel(self, name: str) -> NotificationChannel:
        """Get a channel by name"""
        if name not in self._channels:
            raise ValueError(f"Channel not found: {name}")
        return self._channels[name]

    def list_channels(self) -> list[str]:
        """List all registered channels"""
        return list(self._channels.keys())

    async def send(self, notification: Notification, channels: Optional[list[str]] = None):
        """Send notification to specified channels (or defaults if None)"""
        target_channels = channels or self._default_channels

        results = {}
        for channel_name in target_channels:
            if channel_name in self._channels:
                channel = self._channels[channel_name]
                if channel.is_available():
                    try:
                        results[channel_name] = await channel.send(notification)
                    except Exception as e:
                        logger.error(f"Error sending to channel {channel_name}: {e}")
                        results[channel_name] = False

        return results


import logging
logger = logging.getLogger(__name__)

# Global notification service
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get the global notification service instance"""
    global _notification_service
    if not _notification_service:
        _notification_service = NotificationService()
        # Register default console channel
        console_channel = ConsoleNotificationChannel()
        _notification_service.register_channel(console_channel, set_default=True)
    return _notification_service


__all__ = [
    "Notification",
    "NotificationLevel",
    "NotificationChannel",
    "NotificationChannelError",
    "ConsoleNotificationChannel",
    "WebhookNotificationChannel",
    "NotificationService",
    "get_notification_service",
]
