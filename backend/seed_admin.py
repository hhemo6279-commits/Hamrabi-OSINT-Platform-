"""Create or promote an admin account.

Usage:
    backend\.venv\Scripts\python backend\seed_admin.py
    set HAMRABI_ADMIN_USERNAME=admin   (default "admin")
    set HAMRABI_ADMIN_PASSWORD=...     (default "admin123456")
"""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.security import hash_password
from app.models.entities import User
from app.services.store import Store

USERNAME = os.getenv("HAMRABI_ADMIN_USERNAME", "admin")
PASSWORD = os.getenv("HAMRABI_ADMIN_PASSWORD", "admin123456")

existing = Store.get_user_by_username(USERNAME)
if existing:
    existing.role = "admin"
    Store.create_user(existing)
    print(f"[ok] '{USERNAME}' promoted to admin (password unchanged)")
else:
    Store.create_user(User(id=uuid.uuid4().hex, username=USERNAME,
                           password_hash=hash_password(PASSWORD), role="admin"))
    print(f"[ok] admin account created")
print("username:", USERNAME)
print("password:", PASSWORD)
