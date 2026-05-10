from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class NotificationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class Notification:
    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    data: Optional[Dict[str, Any]] = None
    created_at: datetime = datetime.now()


class NotificationChannel(ABC):
    """Abstract base class for notification channels"""

    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Send a notification"""
        pass

    @abstractmethod
    def name(self) -> str:
        """Get the name of this channel"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this channel is available"""
        pass


class NotificationChannelError(Exception):
    """Error occurred while sending notification"""
    pass
