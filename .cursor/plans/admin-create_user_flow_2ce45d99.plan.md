---
name: Admin-Create User Flow
overview: "Replace the invite-based onboarding with an admin-create-account flow: admin creates user with a temporary password inside the proper hexagonal command layer, then the user changes their own password after first login."
todos:
  - id: user-entity
    content: Add must_change_password field to User entity and User.register() factory
    status: pending
  - id: create-user-cmd
    content: Create application/commands/create_user.py with CreateUserCommand + CreateUserHandler (extract from identity_routers.py)
    status: pending
  - id: change-pwd-cmd
    content: Create application/commands/change_password.py with ChangePasswordCommand + ChangePasswordHandler
    status: pending
  - id: lift-router
    content: Update api/identity_routers.py to call CreateUserHandler instead of inline logic
    status: pending
  - id: change-pwd-endpoint
    content: Add POST /auth/change-password endpoint in api/auth.py wired to ChangePasswordHandler
    status: pending
  - id: dto-schema
    content: Add must_change_password to UserDTO (application/dto.py) and UserResponse schemas (schemas/reference.py)
    status: pending
isProject: false
---

# Admin-Create User Flow (Hexagonal Lift)

## Goal
Admin creates a user account with a temporary password. User logs in and changes password. No email token/invite lifecycle needed.

## Current state to change

- `POST /api/users` in [`api/identity_routers.py`](backend/src/api/identity_routers.py) creates users directly with `User(...)`, bypassing the UoW and domain events
- No proper change-own-password endpoint exists (only `User.change_password()` on the entity)
- `Invite` entity and its commands can be **kept but deprioritised** (may still be useful for external invitations later)

## Proposed flow

```mermaid
sequenceDiagram
    participant Admin
    participant API
    participant CreateUserHandler
    participant User_Entity as User
    participant UoW
    participant NewUser as New User

    Admin->>API: POST /api/users {username, password, full_name, email, role}
    API->>CreateUserHandler: CreateUserCommand
    CreateUserHandler->>User_Entity: User.register(..., must_change_password=True)
    CreateUserHandler->>UoW: register(user) + register(membership)
    UoW->>UoW: commit + drain UserRegistered event
    API-->>Admin: UserDTO

    Admin-->>NewUser: communicates credentials out of band

    NewUser->>API: POST /api/auth/change-password {old_password, new_password}
    API->>ChangePasswordHandler: ChangePasswordCommand
    ChangePasswordHandler->>User_Entity: user.change_password(new_hash)
    ChangePasswordHandler->>UoW: commit
    API-->>NewUser: 200 OK
```

## Files to change

### 1. `domain/entities/user.py`
Add `must_change_password: bool = False` field. Update `User.register()` to accept and store it. No new events needed — `UserRegistered` is sufficient.

### 2. `application/commands/create_user.py` (new file)
Extract logic from `identity_routers.py::create_user` into a proper command handler:
- `CreateUserCommand(username, email, full_name, password, role_code, is_outsourced, tenant_id, created_by_user_id)`
- `CreateUserHandler.execute()`: check duplicates, `User.register(must_change_password=True)`, `MembershipService.ensure_membership`, UoW commit

### 3. `application/commands/change_password.py` (new file)
- `ChangePasswordCommand(user_id, old_password, new_password)`
- `ChangePasswordHandler.execute()`: verify old password, hash new password, `user.change_password(new_hash)`, clear `must_change_password`, UoW commit

### 4. `api/identity_routers.py`
Replace the inline `create_user` logic with a call to `CreateUserHandler`. Wire dependencies via FastAPI `Depends`.

### 5. `api/auth.py`
Add `POST /auth/change-password` endpoint wired to `ChangePasswordHandler`. Requires authenticated user (any role).

### 6. `schemas/reference.py`
Add `must_change_password: bool` to `UserResponse` / `UserListResponse` so the frontend can redirect to password-change screen.

### 7. `application/dto.py`
Add `must_change_password: bool` to `UserDTO` and `user_to_dto()`.

## What stays the same
- `Invite` entity, `InviteUserHandler`, `AcceptInviteHandler` — unchanged, kept for potential future external invite flows
- Bootstrap `POST /auth/register` (first admin only) — unchanged
- `RegisterTenantHandler` — unchanged
