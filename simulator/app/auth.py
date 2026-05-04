from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

@dataclass(frozen=True)
class User:
    username: str
    role: str   # "trainee" | "trainer"

TEACHER_REGISTRATION_SECRET = "teachconfirm123"
_ACCOUNTS_PATH = Path(__file__).resolve().parents[1] / "user_accounts.json"

def _make_accounts() -> Dict[str, Tuple[str, str]]:
    """
    returns: username -> (password, role)
    v1: 内置账号，不用服务器
    """
    accounts: Dict[str, Tuple[str, str]] = {}

    # 20 trainees
    for i in range(1, 21):
        u = f"training{i:02d}"
        p = "train123"
        accounts[u] = (p, "trainee")

    # 10 trainers
    for i in range(1, 11):
        u = f"trainer{i:02d}"
        p = "teach123"
        accounts[u] = (p, "trainer")

    return accounts

def _load_registered_accounts() -> Dict[str, Tuple[str, str]]:
    if not _ACCOUNTS_PATH.exists():
        return {}

    try:
        data = json.loads(_ACCOUNTS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[Auth] Failed to load registered accounts: {exc}")
        return {}

    raw_accounts = data.get("accounts", {}) if isinstance(data, dict) else {}
    if not isinstance(raw_accounts, dict):
        return {}

    accounts: Dict[str, Tuple[str, str]] = {}
    for username, record in raw_accounts.items():
        if not isinstance(record, dict):
            continue
        password = record.get("password", "")
        role = record.get("role", "")
        if username and password and role in ("trainee", "trainer"):
            accounts[str(username)] = (str(password), role)
    return accounts

def _save_registered_accounts(accounts: Dict[str, Tuple[str, str]]):
    data = {
        "accounts": {
            username: {"password": password, "role": role}
            for username, (password, role) in sorted(accounts.items())
        }
    }
    _ACCOUNTS_PATH.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")

def _combined_accounts() -> Dict[str, Tuple[str, str]]:
    accounts = _make_accounts()
    accounts.update(_load_registered_accounts())
    return accounts

ACCOUNTS = _combined_accounts()

def register_user(username: str, password: str, role: str, secret_key: str = "") -> Tuple[bool, str]:
    """Register a local student or teacher account."""
    username = (username or "").strip()
    password = password or ""
    role = (role or "").strip()
    secret_key = secret_key or ""

    if not username:
        return False, "Username is required."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if any(ch.isspace() for ch in username):
        return False, "Username cannot contain spaces."
    if not password:
        return False, "Password is required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if role not in ("trainee", "trainer"):
        return False, "Invalid account role."
    if role == "trainer" and secret_key != TEACHER_REGISTRATION_SECRET:
        return False, "Invalid teacher secret key."

    built_in_accounts = _make_accounts()
    registered_accounts = _load_registered_accounts()
    if username in built_in_accounts or username in registered_accounts:
        return False, "Username already exists."

    registered_accounts[username] = (password, role)
    try:
        _save_registered_accounts(registered_accounts)
    except Exception as exc:
        print(f"[Auth] Failed to save registered account: {exc}")
        return False, "Failed to save account. Please try again."

    ACCOUNTS[username] = (password, role)
    return True, "Registration successful. Please log in."

def authenticate(username: str, password: str) -> Optional[User]:
    username = (username or "").strip()
    password = password or ""
    global ACCOUNTS
    ACCOUNTS = _combined_accounts()
    rec = ACCOUNTS.get(username)
    if not rec:
        return None
    pw, role = rec
    if password != pw:
        return None
    return User(username=username, role=role)
