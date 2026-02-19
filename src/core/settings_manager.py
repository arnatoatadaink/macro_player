"""Settings manager — reads/writes settings.ini via configparser."""
from configparser import ConfigParser
from pathlib import Path

from src.core.prefix import COMMENT_PREFIX


class SettingsManager:
    def __init__(self, ini_path: Path) -> None:
        self.ini_path = ini_path
        self.config = ConfigParser(comment_prefixes=(COMMENT_PREFIX, ";"), inline_comment_prefixes=(COMMENT_PREFIX,))
        if ini_path.exists():
            self.config.read(ini_path, encoding="utf-8")

    # ------------------------------------------------------------------
    # Generic getters
    # ------------------------------------------------------------------
    def get(self, section: str, key: str, fallback: str = "") -> str:
        return self.config.get(section, key, fallback=fallback)

    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        return self.config.getint(section, key, fallback=fallback)

    def getfloat(self, section: str, key: str, fallback: float = 0.0) -> float:
        return self.config.getfloat(section, key, fallback=fallback)

    def getbool(self, section: str, key: str, fallback: bool = False) -> bool:
        return self.config.getboolean(section, key, fallback=fallback)

    def set(self, section: str, key: str, value: str) -> None:
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, value)
        self.save()

    def save(self) -> None:
        with open(self.ini_path, "w", encoding="utf-8") as f:
            self.config.write(f)

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------
    @property
    def macros_dir(self) -> Path:
        return Path(self.get("GENERAL", "macros_dir", "macros"))

    @property
    def templates_dir(self) -> Path:
        return Path(self.get("GENERAL", "templates_dir", "templates"))

    @property
    def mousewait(self) -> int:
        return self.getint("INPUT", "mousewait", 50)

    @property
    def keywait(self) -> int:
        return self.getint("INPUT", "keywait", 30)

    @property
    def playback_speed(self) -> float:
        return self.getfloat("INPUT", "playback_speed", 1.0)

    @property
    def syntax_sugar(self) -> dict[str, str]:
        """Return alias→canonical mapping from [COMMANDS] section."""
        if not self.config.has_section("COMMANDS"):
            return {}
        return {k.upper(): v.upper() for k, v in self.config.items("COMMANDS")}
