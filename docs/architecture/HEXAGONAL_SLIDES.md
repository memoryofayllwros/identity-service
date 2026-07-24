# Identity Platform — Hexagonal Architecture Presentation

Bilingual PPT outline (10 slides) and speaker script for explaining hexagonal purity in `pacific-identity-platform`.

**Estimated duration:** 8–10 minutes  
**Related docs:** [ADR-003](adr/003-hexagonal-architecture.md) · [README](../../README.md) · [EVENT_CONTRACT.md](EVENT_CONTRACT.md)

---

## PPT Outline (10 Slides)

### Slide 1 — Title

**Title:** Identity Platform — Hexagonal Architecture & Purity  
**Subtitle:** 业务在内，技术在外 / Business at the core, technology at the edges

**Visual:** Hexagon diagram + repo name

**Bullets:**
- IAM microservice: authentication, authorization, tenants, users
- Hexagonal Architecture + DDD bounded context
- Stack: FastAPI · MongoDB · Redis Streams · RS256 JWT

---

### Slide 2 — The One-Liner

**中文：**
> 业务规则在中间；HTTP、MongoDB、JWT、Redis 在边缘当可替换插件；**依赖永远从外向内**。

**English:**
> Business rules live in the center; HTTP, MongoDB, JWT, and Redis are replaceable adapters at the edge; **dependencies always point inward**.

**Visual:** Core (Domain + Application) surrounded by four adapters

---

### Slide 3 — What Hexagonal Purity Means

**Core idea:** Not folder names — **dependency direction**

| Inner | Defines ports (what I need) |
|-------|-----------------------------|
| Outer | Implements adapters (how it's done) |

**Rule:** Outer → Inner ✅ · Inner → Outer ❌

**Visual:** Dependency diagram

```mermaid
flowchart TB
  subgraph outer ["Adapters - replaceable technology"]
    API["FastAPI / api/"]
    Mongo["MongoDB / Beanie"]
    JWT["JWT / security"]
    Redis["Redis Streams / outbox"]
  end

  subgraph core ["Core - business"]
    App["Application - use cases"]
    Dom["Domain - business rules"]
  end

  API --> App
  App --> Dom
  Mongo --> Dom
  JWT --> App
  Redis --> Dom

  Dom -. never .-> API
  Dom -. never .-> Mongo
  App -. never .-> Mongo
  App -. never .-> JWT
```

**Purity =** the core does not know HTTP status codes, Mongo document shapes, or JWT library details.

---

### Slide 4 — Four Layers

| Layer | Directory | Does | Does NOT |
|-------|-----------|------|----------|
| **Domain** | `domain/` | Entities, rules, events, repository interfaces | Import FastAPI / Beanie / Mongo |
| **Application** | `application/` | Command/Query handlers, orchestration | Touch DB or JWT implementations |
| **Infrastructure** | `infrastructure/` | Mongo repos, JWT, outbox, Redis | Business rules |
| **API** | `api/` + `main.py` | HTTP parsing, exception → status mapping | `User.deactivate()` logic |

**Visual:** Layer pyramid + directory tree snapshot

README phrase **"Dependencies always point inward"** refers to this model.

---

### Slide 5 — Five Verifiable Proofs (1/2)

**① Domain is framework-free** — `User.deactivate()` only mutates state and `_record(event)`

**② Ports inside, adapters outside** — `UserRepository`, `TokenService`, `EventPublisher`

**③ Application does not import infrastructure** — enforced by `test_phase1_boundaries.py`

**Visual:** Code snippets — `User.deactivate`, repository port, boundary test

---

### Slide 6 — Five Verifiable Proofs (2/2)

**④ API is a thin adapter** — `DomainError` → HTTP status only in `main.py`

**⑤ Persistence separation** — `Tenant` entity ↔ `TenantDocument` ↔ mappers

**Recent polish (landed):**
- `SharedKernelPort` — application no longer imports `src.shared.*` directly
- `ensure_default_tenant` — aligned with UoW + outbox path
- `UserDTO` — transport-neutral names in application; HTTP aliases in `schemas/`

**Visual:** Exception handler + entity vs document comparison

---

### Slide 7 — End-to-End Example: User Updates Own Profile

**Scenario:** A logged-in user changes their name, email, or phone — one request, one application service, one aggregate.

**Flow:**
```
PATCH /auth/me
  → api/auth.py (thin adapter — auth + load user)
  → AuthApplicationService.update_profile()
  → duplicate-email check (application rule)
  → User.update_profile()  (domain)
  → UserRepository.save()  (port)
  → UserDTO → UserResponse
```

**Visual:** Sequence diagram

```mermaid
sequenceDiagram
  participant User
  participant API as auth.py
  participant Svc as AuthApplicationService
  participant Domain as User entity
  participant Repo as UserRepository

  User->>API: PATCH /auth/me
  API->>Repo: find_by_id(user_id)
  Repo-->>API: User
  API->>Svc: update_profile(user, payload)
  Svc->>Domain: update_profile(email, full_name, phone)
  Svc->>Repo: save(user)
  Svc-->>API: UserDTO
  API-->>User: UserResponse
```

**Talking point:** Business says "let the user edit their profile"; HTTP and Mongo stay outside — the application service orchestrates through repository ports, and the domain holds the update rules.

---

### Slide 8 — Events: Outbox Inside, Redis Outside

**Internal:** Command Handler + Outbox binds DB writes and event emission

**External:** `EVENT_TRANSPORT=redis_streams` → `XADD` to `identity:events`

**Subscribe:** Identity publishes only; Tracking consumes via `XREADGROUP` (not in this repo)

**Visual:**
```
OutboxRelayWorker
      │
      ▼
EventPublisher.publish()
      ├── InProcessEventPublisher  →  handler(event)     [same process]
      └── RedisStreamsPublisher    →  XADD identity:events
                                              │
                                              ▼
                                    Tracking XREADGROUP  [external]
```

See [EVENT_CONTRACT.md](EVENT_CONTRACT.md) for full catalog.

---

### Slide 9 — vs Traditional Three-Tier & Value

| Traditional three-tier | Hexagonal (this repo) |
|------------------------|------------------------|
| Service imports `UserDoc` | Handler knows `User` entity only |
| `HTTPException(409)` in business | `DuplicateEmail()` domain exception |
| JWT scattered in services | `TokenService` port + infra adapter |
| Swap DB → touch many services | Swap DB → mainly `infrastructure/persistence/` |

**Value:** testable core · swappable technology · clear boundaries

---

### Slide 10 — Evidence & Close

**Evidence:**
1. [ADR-003](adr/003-hexagonal-architecture.md)
2. Boundary tests — `backend/tests/test_phase1_boundaries.py` (53 pytest tests pass)
3. Directory layout — `domain/` → `application/` → `infrastructure/` + `api/`

**30-second close (bilingual below)**

**Q&A backup:** Application uses Pydantic DTOs — does not break dependency direction; framework choice, not an architecture leak.

---

## Appendix — Code References for Slides

### Domain purity — `User.deactivate()`

```74:77:backend/src/domain/entities/user.py
    def deactivate(self) -> None:
        self.status = UserStatus.DEACTIVATED
        self.updated_at = now_hk()
        self._record(UserDeactivated(user_id=self.id))
```

### Boundary translation — `main.py`

```110:116:backend/src/main.py
@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    status_code = _DOMAIN_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc) or type(exc).__name__},
    )
```

### UoW + outbox — `create_user.py`

```63:65:backend/src/application/commands/create_user.py
        async with self.uow:
            self.uow.register(user)
            await self.uow.commit()
```

