import logging
from typing import Dict, Any

from app.notifications.base import (
    Notification,
    NotificationChannel,
    NotificationLevel,
)

logger = logging.getLogger(__name__)


class ConsoleNotificationChannel(NotificationChannel):
    """Console notification channel - prints to console/logs"""

    def name(self) -> str:
        return "console"

    def is_available(self) -> bool:
        return True

    async def send(self, notification: Notification) -> bool:
        try:
            log_method = self._get_log_method(notification.level)
            log_method(
                f"[{notification.title}] {notification.message}",
                extra={"data": notification.data},
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send console notification: {e}")
            return False

    def _get_log_method(self, level: NotificationLevel):
        """Get the appropriate logging method for notification level"""
        level_map = {
            NotificationLevel.INFO: logger.info,
            NotificationLevel.WARNING: logger.warning,
            NotificationLevel.ERROR: logger.error,
            NotificationLevel.SUCCESS: logger.info,
        }
        return level_map.get(level, logger.info)
