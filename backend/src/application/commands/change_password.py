from __future__ import annotations

from dataclasses import dataclass

from src.application.ports.password_hasher import PasswordHasher
from src.domain.entities.auth_event import AuthEvent
from src.domain.exceptions import InvalidCredentials
from src.domain.id_generator import IDGenerator
from src.domain.repositories import AuthEventRepository, UserRepository
from src.domain.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class ChangePasswordCommand:
    user_id: str
    current_password: str
    new_password: str


@dataclass
class ChangePasswordHandler:
    user_repo: UserRepository
    auth_events: AuthEventRepository
    password_hasher: PasswordHasher
    uow: UnitOfWork
    id_gen: IDGenerator

    async def execute(self, command: ChangePasswordCommand) -> None:
        user = await self.user_repo.find_by_id(command.user_id)
        if user is None:
            raise InvalidCredentials("User not found.")
        if not self.password_hasher.verify(command.current_password, user.password_hash):
            raise InvalidCredentials("Current password is incorrect.")

        user.change_password(self.password_hasher.hash(command.new_password))

        async with self.uow:
            self.uow.register(user)
            await self.uow.commit()

        await self.auth_events.save(
            AuthEvent.record(
                event_id=self.id_gen(),
                event_type="auth.password_changed",
                user_id=user.id,
            )
        )
