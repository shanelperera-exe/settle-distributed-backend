docker compose exec -T node-1 python3 -c '
from app.platform.infrastructure.db.session import SessionLocal
from app.modules.auth.services import AuthService
from app.modules.auth.security import verify_password
db = SessionLocal()
auth_service = AuthService(db)
user = auth_service.get_user_by_email("testagent@example.com")
print(f"User: {user}")
print(f"Hash in DB: {user.hashed_password}")
print(f"Checkpw: {verify_password("Password123!", user.hashed_password)}")
'
