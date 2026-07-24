from __future__ import annotations

from dataclasses import dataclass

from src.application.commands.ensure_default_tenant import EnsureDefaultTenantHandler
from src.application.dto import (
    ChangePasswordDTO,
    ForgotPasswordDTO,
    ForgotPasswordResultDTO,
    LoginDTO,
    LoginResult,
    ProfileUpdateDTO,
    RegisterDTO,
    UserDTO,
    normalize_mobile_identifier,
    user_to_dto,
)
from src.application.ports.password_hasher import PasswordHasher
from src.application.ports.token_service import TokenService
from src.application.queries.user_queries import GetUserHandler, GetUserQuery
from src.application.services.authorization_service import AuthorizationService
from src.application.services.token_issuance_service import TokenIssuanceService
from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.user import User
from src.domain.enums import UserRole, UserStatus
from src.domain.exceptions import (
    DuplicateEmail,
    DuplicateUsername,
    InvalidCredentials,
    InvalidToken,
    RegistrationClosed,
    TenantSuspended,
    UserInactive,
)
from src.domain.id_generator import IDGenerator
from src.domain.repositories import AuthEventRepository, TenantRepository, UserRepository
from src.domain.utils import now_hk
from src.domain.value_objects.email import Email
from src.domain.value_objects.phone import Phone
from src.shared.permissions import ADMIN_PERMISSIONS


@dataclass
class AuthApplicationService:
    user_repo: UserRepository
    tenant_repo: TenantRepository
    authz: AuthorizationService
    auth_events: AuthEventRepository
    jwt_expire_minutes: int
    id_gen: IDGenerator
    password_hasher: PasswordHasher
    token_service: TokenService
    token_issuance: TokenIssuanceService
    get_user_handler: GetUserHandler
    ensure_default_tenant_handler: EnsureDefaultTenantHandler

    async def _ensure_active_company(self) -> None:
        tenant = await self.ensure_default_tenant_handler.execute()
        if tenant.is_suspended:
            raise TenantSuspended()

    async def _find_by_login(self, identifier: str) -> User | None:
        user = await self.user_repo.find_by_username(identifier)
        if user:
            return user
        user = await self.user_repo.find_by_email(identifier)
        if user:
            return user
        for candidate in await self.user_repo.find_all():
            if candidate.phone and candidate.phone.mobile() == normalize_mobile_identifier(
                identifier
            ):
                return candidate
        return None

    async def issue_login(self, user: User) -> LoginResult:
        return await self.token_issuance.issue_login(user)

    async def register(self, payload: RegisterDTO) -> UserDTO:
        await self._ensure_active_company()
        if await self.user_repo.count() > 0:
            raise RegistrationClosed()
        if await self.user_repo.find_by_username(payload.username):
            raise DuplicateUsername()
        if await self.user_repo.find_by_email(str(payload.email)):
            raise DuplicateEmail()

        phone = None
        if payload.phone:
            phone = Phone(
                country_code=payload.phone.country_code,
                phone_number=payload.phone.phone_number,
            )
        user = User.register(
            user_id=self.id_gen(),
            username=payload.username,
            email=Email(str(payload.email)),
            full_name=payload.full_name,
            password_hash=self.password_hasher.hash(payload.password),
            permissions=list(ADMIN_PERMISSIONS),
            phone=phone,
            position=payload.position,
            is_outsourced=payload.is_outsourced,
            must_change_password=False,
        )
        await self.user_repo.save(user)
        await self._record_event("user.registered", user_id=user.id)
        return user_to_dto(user, role=UserRole.ADMIN, permissions=list(ADMIN_PERMISSIONS))

    async def login(self, payload: LoginDTO) -> LoginResult:
        await self._ensure_active_company()
        user = await self._find_by_login(payload.mobile)
        if user is None or not self.password_hasher.verify(payload.password, user.password_hash):
            await self._record_event("auth.login_failed", detail={"identifier": payload.mobile})
            raise InvalidCredentials()
        if user.status != UserStatus.ACTIVE:
            raise UserInactive()
        if user.lockout_until and user.lockout_until > now_hk():
            raise InvalidCredentials("Account is temporarily locked.")
        user.record_login()
        await self.user_repo.save(user)
        result = await self.issue_login(user)
        await self._record_event("auth.login", user_id=user.id)
        return result

    async def refresh(self, refresh_token: str) -> LoginResult:
        await self._ensure_active_company()
        token_payload = self.token_service.decode_refresh_token(refresh_token)
        user_id = token_payload.get("sub")
        if not user_id:
            raise InvalidToken("Invalid refresh token payload.")
        user = await self.user_repo.find_by_id(user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise UserInactive("User is inactive or missing.")
        return await self.issue_login(user)

    async def change_password(self, user: User, payload: ChangePasswordDTO) -> None:
        if not self.password_hasher.verify(payload.current_password, user.password_hash):
            raise InvalidCredentials("Current password is incorrect.")
        user.change_password(self.password_hasher.hash(payload.new_password))
        await self.user_repo.save(user)
        await self._record_event("auth.password_changed", user_id=user.id)

    async def update_profile(self, user: User, payload: ProfileUpdateDTO) -> UserDTO:
        updates = payload.model_dump(exclude_unset=True)
        email = updates.get("email")
        if email is not None:
            existing = await self.user_repo.find_by_email(str(email))
            if existing and existing.id != user.id:
                raise DuplicateEmail()
        phone = None
        if "phone" in updates and updates["phone"] is not None:
            phone = Phone(
                country_code=updates["phone"].country_code,
                phone_number=updates["phone"].phone_number,
            )
        user.update_profile(
            email=Email(str(email)) if email else None,
            full_name=updates.get("full_name"),
            phone=phone if "phone" in updates else None,
            position=updates.get("position"),
        )
        await self.user_repo.save(user)
        refreshed = await self.user_repo.find_by_id(user.id)
        return await self.get_user_handler.execute(
            GetUserQuery(user_id=user.id, user=refreshed or user)
        )

    async def request_password_reset(
        self, payload: ForgotPasswordDTO
    ) -> ForgotPasswordResultDTO:
        return ForgotPasswordResultDTO(
            message=(
                "If an account exists for that identifier, your administrator can reset "
                "your password. Please contact your system administrator."
            ),
        )

    async def _record_event(self, event_type: str, **kwargs) -> None:
        await self.auth_events.save(
            AuthEvent.record(event_id=self.id_gen(), event_type=event_type, **kwargs)
        )
