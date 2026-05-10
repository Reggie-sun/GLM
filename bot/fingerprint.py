import json
import random
from pathlib import Path
from typing import Dict, Any, Optional, List

# Common User-Agent templates
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) Gecko/20100101 Firefox/{version}.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

CHROME_VERSIONS = ["120", "121", "122", "123", "124"]
FIREFOX_VERSIONS = ["120", "121", "122"]


class Fingerprint:
    def __init__(
        self,
        user_agent: str,
        language: str = "zh-CN,zh;q=0.9",
        platform: str = "Win32",
        vendor: str = "Google Inc.",
        webgl_vendor: str = "Intel Inc.",
        webgl_renderer: str = "Intel Iris OpenGL Engine",
    ):
        self.user_agent = user_agent
        self.language = language
        self.platform = platform
        self.vendor = vendor
        self.webgl_vendor = webgl_vendor
        self.webgl_renderer = webgl_renderer

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_agent": self.user_agent,
            "language": self.language,
            "platform": self.platform,
            "vendor": self.vendor,
            "webgl_vendor": self.webgl_vendor,
            "webgl_renderer": self.webgl_renderer,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Fingerprint":
        return cls(
            user_agent=data.get("user_agent", ""),
            language=data.get("language", "zh-CN,zh;q=0.9"),
            platform=data.get("platform", "Win32"),
            vendor=data.get("vendor", "Google Inc."),
            webgl_vendor=data.get("webgl_vendor", "Intel Inc."),
            webgl_renderer=data.get("webgl_renderer", "Intel Iris OpenGL Engine"),
        )


class FingerprintManager:
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else Path("data/fingerprints")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._fingerprints: Dict[str, Fingerprint] = {}
        self._load_all()

    def _load_all(self):
        """Load all saved fingerprints"""
        for fp_file in self.storage_dir.glob("*.json"):
            try:
                with open(fp_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    fp = Fingerprint.from_dict(data)
                    self._fingerprints[fp_file.stem] = fp
            except Exception:
                pass

    def generate(self, name: Optional[str] = None) -> Fingerprint:
        """Generate a new random fingerprint"""
        # Randomly select User-Agent
        ua_template = random.choice(USER_AGENTS)
        if "Chrome" in ua_template:
            version = random.choice(CHROME_VERSIONS)
        elif "Firefox" in ua_template:
            version = random.choice(FIREFOX_VERSIONS)
        else:
            version = ""
        user_agent = ua_template.format(version=version)

        # Random platform
        platforms = ["Win32", "MacIntel", "Linux x86_64"]
        platform = random.choice(platforms)

        # Random vendors
        vendors = ["Google Inc.", "Mozilla Foundation", "Apple Inc."]
        vendor = random.choice(vendors)

        webgl_vendors = ["Intel Inc.", "NVIDIA Corporation", "AMD Inc.", "Apple Inc."]
        webgl_vendor = random.choice(webgl_vendors)

        webgl_renderers = [
            "Intel Iris OpenGL Engine",
            "NVIDIA GeForce GTX 1650",
            "AMD Radeon RX 580",
            "Apple M1 Pro",
        ]
        webgl_renderer = random.choice(webgl_renderers)

        fp = Fingerprint(
            user_agent=user_agent,
            platform=platform,
            vendor=vendor,
            webgl_vendor=webgl_vendor,
            webgl_renderer=webgl_renderer,
        )

        if name:
            self.save(name, fp)

        return fp

    def save(self, name: str, fingerprint: Fingerprint):
        """Save a fingerprint to file"""
        self._fingerprints[name] = fingerprint
        fp_file = self.storage_dir / f"{name}.json"
        with open(fp_file, "w", encoding="utf-8") as f:
            json.dump(fingerprint.to_dict(), f, ensure_ascii=False, indent=2)

    def get(self, name: str) -> Optional[Fingerprint]:
        """Get a saved fingerprint"""
        return self._fingerprints.get(name)

    def get_or_generate(self, name: str) -> Fingerprint:
        """Get a fingerprint or generate if not exists"""
        fp = self.get(name)
        if not fp:
            fp = self.generate(name)
        return fp

    def list_all(self) -> List[str]:
        """List all saved fingerprint names"""
        return list(self._fingerprints.keys())

    def delete(self, name: str):
        """Delete a saved fingerprint"""
        if name in self._fingerprints:
            del self._fingerprints[name]
            fp_file = self.storage_dir / f"{name}.json"
            if fp_file.exists():
                fp_file.unlink()


# Global fingerprint manager instance
_fp_manager: Optional[FingerprintManager] = None


def get_fingerprint_manager() -> FingerprintManager:
    """Get the global fingerprint manager instance"""
    global _fp_manager
    if not _fp_manager:
        _fp_manager = FingerprintManager()
    return _fp_manager
