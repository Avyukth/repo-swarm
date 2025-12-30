version=1
## Repository Structure and Files

{repo_structure}
---

## TypeScript Source Codebase - Comprehensive Analysis

You are a senior software architect analyzing a TypeScript codebase that will be ported to Rust. Your analysis must be thorough enough to serve as the complete blueprint for the Rust implementation.

---

### SECTION 1: Project Overview

**1.1 Project Identity**
- Repository name: [[name]]
- Primary purpose/domain
- Target users/consumers
- Business context

**1.2 Technology Stack**
- Node.js version
- TypeScript version
- Runtime (Node, Deno, Bun)
- Framework (Express, Fastify, NestJS, Hono, etc.)
- Database (PostgreSQL, MongoDB, Redis, etc.)
- ORM/Query builder (Prisma, TypeORM, Drizzle, Knex)
- Message queues (Redis, RabbitMQ, Kafka, SQS)
- Caching layer

**1.3 Package Analysis**
Analyze package.json thoroughly:

| Package | Version | Purpose | Rust Equivalent |
|---------|---------|---------|-----------------|
| express | x.x.x | Web server | axum |
| prisma | x.x.x | ORM | sqlx/diesel |
| zod | x.x.x | Validation | serde + validator |
| ... | ... | ... | ... |

---

### SECTION 2: Architecture Deep Dive

**2.1 Architectural Pattern**
- Pattern used (Layered, Hexagonal, Clean, DDD, etc.)
- Evidence for pattern choice
- Deviation from standard pattern

**2.2 Directory Structure**
```
src/
├── [directory]    # Purpose: ...
│   ├── [subdir]   # Purpose: ...
│   └── ...
```

For each top-level directory, explain:
- What code lives here
- How it relates to other directories
- Key files and their roles

**2.3 Module Boundaries**
- How are modules separated?
- What defines a module boundary?
- Inter-module communication patterns

---

### SECTION 3: Type System Analysis

**3.1 Core Domain Types**
List and explain all major types/interfaces:

```typescript
// File: src/types/user.ts
interface User {
  id: string;        // Format: UUID v4
  email: string;     // Validated email
  // ... document each field
}
```

**3.2 Type Patterns Used**
- Discriminated unions
- Generics patterns
- Utility types (Partial, Pick, Omit)
- Type guards
- Branded types

**3.3 Type Dependencies**
Which types depend on which? Create a dependency graph.

---

### SECTION 4: Data Layer

**4.1 Database Schema**
For each table/collection:
- Name
- Fields with types
- Relationships (1:1, 1:N, N:M)
- Indexes
- Constraints

**4.2 Data Access Patterns**
- Repository pattern?
- Active Record?
- Query builder usage
- Raw SQL queries
- Transactions handling

**4.3 Migrations**
- Migration system used
- Migration history
- Schema versioning

---

### SECTION 5: API Surface

**5.1 REST Endpoints**
For each endpoint:

| Method | Path | Request Body | Response | Auth | Description |
|--------|------|--------------|----------|------|-------------|
| POST | /users | CreateUserDto | User | JWT | Create user |
| GET | /users/:id | - | User | JWT | Get user |

**5.2 Request/Response DTOs**
Document all DTOs with validation rules:

```typescript
// CreateUserDto
{
  email: string;    // required, email format
  password: string; // required, min 8 chars
  name?: string;    // optional
}
```

**5.3 Error Responses**
- Error format standard
- Error codes used
- HTTP status code mapping

---

### SECTION 6: Business Logic

**6.1 Service Layer**
For each service:
- Name and responsibility
- Methods with signatures
- Dependencies injected
- Side effects (DB, external APIs, events)

**6.2 Business Rules**
- Validation rules beyond type checks
- Business invariants
- State machine transitions
- Permission checks

**6.3 Workflows**
Document complex multi-step operations:
1. Step 1: ...
2. Step 2: ...
3. Compensation/rollback logic

---

### SECTION 7: Authentication & Authorization

**7.1 Authentication**
- Auth mechanism (JWT, Session, OAuth, API Key)
- Token structure and claims
- Token refresh flow
- Password hashing (bcrypt, argon2, etc.)

**7.2 Authorization**
- RBAC/ABAC/ACL
- Role definitions
- Permission model
- Resource ownership checks

**7.3 Security Middleware**
- Rate limiting
- CORS configuration
- Input sanitization
- CSRF protection

---

### SECTION 8: External Integrations

**8.1 Third-Party APIs**
For each integration:
- Service name
- SDK/client used
- Endpoints called
- Error handling
- Retry logic

**8.2 Event System**
- Event bus (internal/external)
- Event types and payloads
- Publishers and subscribers
- Event ordering guarantees

---

### SECTION 9: Testing Strategy

**9.1 Test Structure**
- Test framework (Jest, Vitest, Mocha)
- Test organization
- Fixtures and factories

**9.2 Test Coverage**
- Unit test patterns
- Integration test patterns
- E2E test patterns
- Mocked vs real dependencies

---

### SECTION 10: Configuration & Environment

**10.1 Configuration Schema**
All environment variables and config:

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| DATABASE_URL | string | yes | - | PostgreSQL connection |
| JWT_SECRET | string | yes | - | Token signing key |

**10.2 Feature Flags**
- Feature flag system
- Current flags and their purpose

---

### SECTION 11: Porting Considerations

**11.1 TypeScript-Specific Patterns**
Patterns that need special attention in Rust:
- Optional chaining (`?.`)
- Nullish coalescing (`??`)
- Type assertions
- `any` usage (technical debt)

**11.2 Async Patterns**
- Promise patterns used
- Concurrent operations
- Stream processing

**11.3 Complexity Hotspots**
Areas that will be challenging to port:
- Complex generics
- Decorators (if NestJS)
- Reflection/metadata
- Dynamic type construction

---

### SECTION 12: Porting Task List

Generate a prioritized list of porting tasks:

| Priority | Module/Feature | Complexity | Dependencies | Notes |
|----------|----------------|------------|--------------|-------|
| P0 | Core types | Low | None | Start here |
| P0 | Database models | Medium | Core types | ... |
| P1 | Auth service | Medium | DB models | ... |

{previous_context}
