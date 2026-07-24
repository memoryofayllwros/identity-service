from __future__ import annotations

from dataclasses import dataclass

from src.application.dto import UserDTO, user_to_dto
from src.application.ports.password_hasher import PasswordHasher
from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.user import User
from src.domain.enums import UserRole
from src.domain.exceptions import DuplicateEmail, DuplicateUsername, InvalidRoleCode
from src.domain.id_generator import IDGenerator
from src.domain.repositories import RoleRepository, UserRepository
from src.domain.unit_of_work import UnitOfWork
from src.domain.value_objects.email import Email
from src.domain.value_objects.phone import Phone


@dataclass(frozen=True)
class CreateUserCommand:
    username: str
    email: str
    full_name: str
    password: str
    role_code: str
    position: str = ""
    is_outsourced: bool = False
    phone: Phone | None = None
    created_by_user_id: str | None = None


@dataclass
class CreateUserHandler:
    user_repo: UserRepository
    role_repo: RoleRepository
    authz: AuthorizationService
    password_hasher: PasswordHasher
    uow: UnitOfWork
    id_gen: IDGenerator

    async def execute(self, command: CreateUserCommand) -> UserDTO:
        if await self.user_repo.find_by_username(command.username):
            raise DuplicateUsername()
        if await self.user_repo.find_by_email(command.email):
            raise DuplicateEmail()

        role = await self.role_repo.find_by_code(command.role_code)
        if role is None:
            raise InvalidRoleCode(f"Unknown role_code: {command.role_code}")

        user = User.register(
            user_id=self.id_gen(),
            username=command.username,
            email=Email(command.email),
            full_name=command.full_name,
            password_hash=self.password_hasher.hash(command.password),
            permissions=list(role.permissions),
            phone=command.phone,
            position=command.position,
            is_outsourced=command.is_outsourced,
            must_change_password=True,
        )

        async with self.uow:
            self.uow.register(user)
            await self.uow.commit()

        role_enum = (
            UserRole.ADMIN
            if command.role_code == self.authz.shared_kernel.role_code_admin
            else UserRole.OPERATIONS
        )
        return user_to_dto(user, role=role_enum, permissions=list(role.permissions))
