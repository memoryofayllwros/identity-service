from src.application.ports.password_hasher import PasswordHasher
from src.infrastructure.security.security import hash_password, verify_password


class BcryptPasswordHasher:
    def hash(self, password: str) -> str:
        return hash_password(password)

    def verify(self, plain: str, hashed: str) -> bool:
        return verify_password(plain, hashed)
