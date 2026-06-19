import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.platform.infrastructure.db.session import SessionLocal
from app.modules.auth.services import AuthService
from app.modules.auth.security import verify_password, get_password_hash

db = SessionLocal()
auth_service = AuthService(db)

user = auth_service.get_user_by_email("testagent@example.com")
print(f"User: {user}")
print(f"Hashed password in DB: {user.hashed_password}")
print(f"Checkpw result: {verify_password('Password123!', user.hashed_password)}")

new_hash = get_password_hash('Password123!')
print(f"New hash: {new_hash}")
print(f"Checkpw with new hash: {verify_password('Password123!', new_hash)}")
