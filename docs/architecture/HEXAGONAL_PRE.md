## Bilingual Speaker Script (by slide)

### Slide 1 — Opening

**中文（~30s）：**  
大家好。今天介绍 Pacific Identity Platform 的架构设计。这是一个 IAM 微服务，负责用户、租户、权限和认证。内部采用 Hexagonal Architecture 和 DDD，对外通过 HTTP 和 JWT 供 Tracking 等服务使用。接下来我会说明：什么叫 hexagonal purity、我们怎么实现、以及怎么验证。

**English (~30s):**  
Hello everyone. Today I'll walk through the architecture of Pacific Identity Platform—an IAM microservice for users, tenants, permissions, and authentication. Internally we use Hexagonal Architecture and DDD; externally other services consume us via HTTP and JWT. I'll cover what hexagonal purity means, how we implement it, and how we verify it.

---

### Slide 2 — One-Liner

**中文（~20s）：**  
如果用一句话概括：**业务规则放在中间，HTTP、MongoDB、JWT、Redis 都推到边缘，当可替换的插件。** 最关键的规则是：**依赖永远从外向内。** 这就是 hexagonal purity 的核心。

**English (~20s):**  
In one sentence: business rules sit at the center; HTTP, MongoDB, JWT, and Redis are pushed to the edge as replaceable plugins. The key rule is: dependencies always point inward. That is the essence of hexagonal purity.

---

### Slide 3 — Definition

**中文（~45s）：**  
Hexagonal Architecture 也叫 Ports and Adapters。重点不是目录叫什么，而是 **谁依赖谁**。Domain 和 Application 定义 Port——「我需要保存用户、我需要发 token」；Infrastructure 和 API 提供 Adapter——「我用 Mongo 存、我用 RS256 签 JWT」。外层可以依赖内层，内层绝不能依赖外层。满足 purity，意思是：**核心层不知道 HTTP 状态码、Mongo 文档结构、JWT 库怎么用。**

**English (~45s):**  
Hexagonal Architecture is also called Ports and Adapters. What matters is not folder names but dependency direction. Domain and Application define ports—"I need to persist users," "I need to issue tokens." Infrastructure and API provide adapters—"I use Mongo," "I sign JWT with RS256." Outer layers may depend on inner layers; inner layers must never depend on outer ones. Purity means the core doesn't know HTTP status codes, Mongo document shapes, or how the JWT library works.

---

### Slide 4 — Four Layers

**中文（~50s）：**  
我们分四层。**Domain** 放实体、值对象、业务规则和 Repository 接口，零框架。**Application** 放 Command Handler 和 Query Handler，编排用例，不直接碰数据库。**Infrastructure** 实现 Mongo、JWT、Outbox、Redis。**API** 只做 HTTP 解析和响应，业务逻辑不进 router。README 里写的 "Dependencies always point inward" 就是这个意思。

**English (~50s):**  
We have four layers. Domain holds entities, value objects, business rules, and repository interfaces—with zero framework imports. Application holds command and query handlers that orchestrate use cases without touching the database directly. Infrastructure implements Mongo, JWT, outbox, and Redis. API only parses HTTP and returns responses—no business logic in routers. "Dependencies always point inward" in our README means exactly this.

---

### Slide 5 — Proofs 1–3

**中文（~60s）：**  
为什么说我们 **满足** purity？有三点可以直接验证。  
第一，Domain 是纯业务——比如 `Tenant.suspend()` 只改状态、抛 domain exception、用 `_record()` 记事件，没有 FastAPI、没有 Beanie。  
第二，Port 在内、Adapter 在外——`UserRepository` 在 domain，`MongoUserRepository` 在 infrastructure；`TokenService` port 在 application，JWT 实现在 infrastructure。  
第三，Application 不 import infrastructure——`test_phase1_boundaries.py` 自动化检查，application 里不能出现 fastapi、beanie、infrastructure、src.shared。

**English (~60s):**  
Why do we say we meet purity? Three verifiable points. First, Domain is pure business—e.g. `Tenant.suspend()` only changes state, raises domain exceptions, and records events via `_record()`—no FastAPI, no Beanie. Second, ports inside, adapters outside—`UserRepository` in domain, `MongoUserRepository` in infrastructure; `TokenService` port in application, JWT impl in infrastructure. Third, Application never imports infrastructure—`test_phase1_boundaries.py` enforces no fastapi, beanie, infrastructure, or src.shared in the application layer.

---

### Slide 6 — Proofs 4–5 & Recent Fixes

**中文（~60s）：**  
第四，API 是薄 Adapter——Application 抛 `DuplicateEmail()`，HTTP 409 只在 `main.py` 的 exception handler 里翻译，这叫 boundary translation。  
第五，持久化分离——Domain 里是 `Tenant` entity，Infrastructure 里是 `TenantDocument`，中间用 Mapper 转换。  
`SharedKernelPort` 让 application 不再直接引用 shared permissions；`ensure_default_tenant` 也走 UoW + outbox；DTO 改成 `UserDTO` 等中性命名，HTTP alias 留在 schemas。

**English (~60s):**  
Fourth, API is a thin adapter—Application raises `DuplicateEmail()`; HTTP 409 is mapped only in `main.py`'s exception handler—that's boundary translation. Fifth, persistence separation—`Tenant` entity in domain, `TenantDocument` in infrastructure, mappers in between. 
`SharedKernelPort` so application no longer imports shared permissions directly; `ensure_default_tenant` now uses UoW + outbox; DTOs renamed to neutral names like `UserDTO`, with HTTP aliases kept in schemas.

---

### Slide 7 — Add User to Existing Tenant

**中文（~60s）：**  
用一个完整例子：**在已有 tenant 下添加新 user**。分两步：管理员 `POST /tenants/me/invites`，`InviteUserHandler` 调 `Invite.create()`，UoW 写入 invite 和 `InviteCreated` 事件。被邀请人 `POST /tenants/invites/accept`，`AcceptInviteHandler` 调 `User.register()` 和 `invite.accept()`，再在同一 UoW 里注册 user、invite、membership 并 `commit()`——`UserRegistered`、`InviteAccepted`、`UserAddedToTenant` 一并进 outbox，Relay 再发到 Redis。重点是：**业务说「把这个人加进我的 tenant，并原子落库+产事件」；Mongo 用 UoW + outbox 实现——通过 `UnitOfWork` port 连接，互不渗透。**

**English (~60s):**  
A full example: **adding a new user to an existing tenant**. Two steps: an admin `POST`s `/tenants/me/invites`; `InviteUserHandler` calls `Invite.create()` and UoW persists the invite plus `InviteCreated`. The invitee `POST`s `/tenants/invites/accept`; `AcceptInviteHandler` calls `User.register()` and `invite.accept()`, then registers user, invite, and membership in one UoW `commit()`—`UserRegistered`, `InviteAccepted`, and `UserAddedToTenant` land in the outbox; the relay forwards to Redis. The point: business says "add this person to my tenant atomically with events"; Mongo implements that via UoW + outbox—connected through the `UnitOfWork` port without leaking either way.

---

### Slide 8 — Event Architecture

**中文（~50s）：**  
事件方面：**内部**用 Command Handler + Outbox 保证可靠产出事件——commit 成功就不会 silently 丢事件。**外部**生产环境配 `EVENT_TRANSPORT=redis_streams`，Relay 用 `XADD` 写到 `identity:events`，Tracking 等服务用 `XREADGROUP` 消费。Identity **只 publish，不 subscribe Redis**——跨服务消费在下游实现。开发默认 `in_process`，不需要 Redis。

**English (~50s):**  
For events: internally we use Command Handler + Outbox so events are produced reliably—a successful commit won't silently drop events. Externally, with `EVENT_TRANSPORT=redis_streams`, the relay `XADD`s to `identity:events`; Tracking and others consume via `XREADGROUP`. Identity only publishes—it does not subscribe to Redis; cross-service consumption lives in downstream services. Local dev defaults to `in_process` without Redis.

---

### Slide 9 — Comparison & Value

**中文（~40s）：**  
和传统三层比：以前 Service 直接 import `UserDoc`、在业务里抛 `HTTPException`；现在是 Handler 只认识 entity、抛 domain exception、JWT 走 port。换 Mongo 主要改 infrastructure，不动 domain。Purity 的价值不是文件多，而是 **核心可单测、技术可替换、边界清晰**。

**English (~40s):**  
Compared to classic three-tier: services used to import `UserDoc` and raise `HTTPException` in business code; now handlers know entities, raise domain exceptions, and JWT goes through ports. Swapping Mongo mostly touches infrastructure, not domain. Purity's value isn't more files—it's testable core, swappable tech, and clear boundaries.

---

### Slide 10 — Evidence & Close

**中文（~40s）：**  
证据三条：ADR-003 文档、`test_phase1_boundaries.py` 边界测试、以及 `domain → application → infrastructure + api` 的目录结构。总结：**业务核心与技术细节解耦，依赖单向向内——这就是 hexagonal purity。** Q&A 时若问「100% 纯吗」：Application 仍用 Pydantic DTO，但不破坏依赖方向，属于框架选择，不是架构泄漏。谢谢。

**English (~40s):**  
Three pieces of evidence: ADR-003, boundary tests in `test_phase1_boundaries.py`, and the directory layout domain → application → infrastructure + api. In summary: business core decoupled from technical details, dependencies point inward—that is hexagonal purity. If asked "100% pure?": Application still uses Pydantic DTOs, but that doesn't break dependency direction—it's a framework choice, not an architecture leak. Thank you.

---

## Appendix — 30-Second Elevator Pitch

**中文：**  
Identity Platform 采用 Hexagonal Architecture。中间是 Domain 和 Application，负责用户、租户、权限等业务规则；外面是 API、MongoDB、JWT、Redis 等 Adapter。Domain 定义 Repository、EventPublisher、UnitOfWork 这些 Port，Infrastructure 去实现。Application 层没有 infrastructure import，HTTP 异常只在 API 边界翻译。**业务核心与技术细节解耦，依赖单向向内——这就是 hexagonal purity。**

**English:**  
Identity Platform uses Hexagonal Architecture. Domain and Application at the center own users, tenants, and permissions; API, MongoDB, JWT, and Redis are adapters at the edge. Domain defines ports like Repository, EventPublisher, and UnitOfWork; Infrastructure implements them. Application has no infrastructure imports; HTTP errors are translated only at the API boundary. **Business core decoupled from technology, dependencies point inward—that is hexagonal purity.**
