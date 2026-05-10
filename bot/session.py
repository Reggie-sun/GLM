import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from playwright.async_api import BrowserContext


class Session:
    def __init__(
        self,
        session_id: str,
        cookies: Optional[List[Dict[str, Any]]] = None,
        local_storage: Optional[Dict[str, str]] = None,
        created_at: Optional[datetime] = None,
        last_used_at: Optional[datetime] = None,
    ):
        self.session_id = session_id
        self.cookies = cookies or []
        self.local_storage = local_storage or {}
        self.created_at = created_at or datetime.now()
        self.last_used_at = last_used_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "cookies": self.cookies,
            "local_storage": self.local_storage,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        return cls(
            session_id=data.get("session_id", ""),
            cookies=data.get("cookies", []),
            local_storage=data.get("local_storage", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            last_used_at=datetime.fromisoformat(data["last_used_at"]) if data.get("last_used_at") else None,
        )

    async def apply_to_context(self, context: BrowserContext):
        """Apply this session to a browser context"""
        if self.cookies:
            await context.add_cookies(self.cookies)
        # Note: LocalStorage can't be directly set, needs to be set via page

    async def save_from_context(self, context: BrowserContext):
        """Save session from a browser context"""
        self.cookies = await context.cookies()
        self.last_used_at = datetime.now()
        # LocalStorage would need to be collected from pages


class SessionManager:
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else Path("data/sessions")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, Session] = {}
        self._load_all()

    def _load_all(self):
        """Load all saved sessions"""
        for session_file in self.storage_dir.glob("*.json"):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    session = Session.from_dict(data)
                    self._sessions[session.session_id] = session
            except Exception:
                pass

    def save(self, session: Session):
        """Save a session to file"""
        self._sessions[session.session_id] = session
        session_file = self.storage_dir / f"{session.session_id}.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

    def get(self, session_id: str) -> Optional[Session]:
        """Get a saved session"""
        session = self._sessions.get(session_id)
        if session:
            session.last_used_at = datetime.now()
            self.save(session)
        return session

    def create(self, session_id: Optional[str] = None) -> Session:
        """Create a new session"""
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session = Session(session_id=session_id)
        self.save(session)
        return session

    def delete(self, session_id: str):
        """Delete a saved session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            session_file = self.storage_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()

    def list_all(self) -> List[str]:
        """List all saved session IDs"""
        return list(self._sessions.keys())

    def get_recent(self, limit: int = 10) -> List[Session]:
        """Get recently used sessions"""
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.last_used_at,
            reverse=True
        )
        return sessions[:limit]


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance"""
    global _session_manager
    if not _session_manager:
        _session_manager = SessionManager()
    return _session_manager
