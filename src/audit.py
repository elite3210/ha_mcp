import json
from datetime import datetime, timezone
from src.config import settings


def log_action(user: str, tool: str, params: dict, result: str) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": user,
        "tool": tool,
        "params": params,
        "result": result,
    }
    try:
        with open(settings.audit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass
