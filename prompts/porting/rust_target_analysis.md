version=1
## Repository Structure and Files

{repo_structure}
---

## Rust Target Codebase - Comprehensive Analysis

You are a senior Rust engineer analyzing a Rust codebase that is a partial port from TypeScript. Your analysis must document exactly what has been ported, what patterns are established, and how to continue the port.

---

### SECTION 1: Project Overview

**1.1 Project Identity**
- Crate/workspace name
- Binary or library crate
- Rust edition (2018, 2021, 2024)
- MSRV (Minimum Supported Rust Version)

**1.2 Workspace Structure**
If workspace:
```
Cargo.toml (workspace)
├── crates/
│   ├── core/        # Shared types and traits
│   ├── api/         # HTTP server
│   ├── db/          # Database layer
│   └── ...
```

**1.3 Dependency Analysis**
From Cargo.toml(s):

| Crate | Version | Purpose | Features Used |
|-------|---------|---------|---------------|
| axum | 0.7 | Web framework | macros, ws |
| sqlx | 0.8 | Database | postgres, runtime-tokio |
| serde | 1.0 | Serialization | derive |
| tokio | 1.0 | Async runtime | full |
| ... | ... | ... | ... |

---

### SECTION 2: Architecture Analysis

**2.1 Architectural Pattern**
- Pattern implemented (Layered, Hexagonal, Clean Architecture)
- How Rust idioms adapt the pattern
- Trait-based abstractions

**2.2 Module Structure**
```
src/
├── lib.rs           # Public API surface
├── main.rs          # Binary entry point
├── [module]/
│   ├── mod.rs       # Module root
│   ├── types.rs     # Types for this module
│   ├── handlers.rs  # HTTP handlers
│   └── service.rs   # Business logic
```

**2.3 Visibility and Encapsulation**
- What's `pub`?
- What's `pub(crate)`?
- Private implementation details

---

### SECTION 3: Type System

**3.1 Core Domain Types**
Document all major structs/enums:

```rust
// src/models/user.rs

/// User entity representing an authenticated user
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    /// Unique identifier (UUID v4)
    pub id: Uuid,
    /// User's email address
    pub email: String,
    /// Timestamp of account creation
    pub created_at: DateTime<Utc>,
}
```

**3.2 Error Types**
How errors are modeled:

```rust
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("User not found: {0}")]
    UserNotFound(Uuid),
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    // ...
}
```

**3.3 Trait Definitions**
Custom traits defined:

```rust
#[async_trait]
pub trait UserRepository {
    async fn find_by_id(&self, id: Uuid) -> Result<Option<User>>;
    async fn create(&self, user: CreateUser) -> Result<User>;
}
```

**3.4 Type Patterns**
- NewType patterns
- Builder patterns
- Phantom types
- Type state patterns

---

### SECTION 4: Data Layer

**4.1 Database Setup**
- SQLx or Diesel
- Connection pool configuration
- Migration setup

**4.2 Models vs Entities**
- Database models (row representation)
- Domain entities (business objects)
- Mapping between them

**4.3 Query Patterns**
```rust
// Example query pattern used
sqlx::query_as!(
    User,
    r#"SELECT id, email, created_at FROM users WHERE id = $1"#,
    id
)
.fetch_optional(&pool)
.await
```

**4.4 Transactions**
How transactions are handled:
- Manual transaction management
- Transaction scope patterns

---

### SECTION 5: API Layer

**5.1 Router Structure**
```rust
// How routes are organized
pub fn routes() -> Router {
    Router::new()
        .route("/users", post(create_user).get(list_users))
        .route("/users/:id", get(get_user).delete(delete_user))
        .layer(...)
}
```

**5.2 Handler Patterns**
Standard handler signature:
```rust
async fn handler(
    State(state): State<AppState>,
    Extension(user): Extension<AuthUser>,
    Json(body): Json<CreateRequest>,
) -> Result<Json<Response>, AppError> {
    // ...
}
```

**5.3 Request/Response Types**
Document DTOs:

```rust
#[derive(Debug, Deserialize, Validate)]
pub struct CreateUserRequest {
    #[validate(email)]
    pub email: String,
    #[validate(length(min = 8))]
    pub password: String,
}
```

**5.4 Error Responses**
How errors map to HTTP:
```rust
impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        // error -> status code + JSON body
    }
}
```

---

### SECTION 6: Service Layer

**6.1 Service Structs**
```rust
pub struct UserService {
    repo: Arc<dyn UserRepository>,
    hasher: Arc<dyn PasswordHasher>,
}

impl UserService {
    pub async fn create_user(&self, req: CreateUser) -> Result<User> {
        // business logic
    }
}
```

**6.2 Dependency Injection**
How dependencies are wired:
- Constructor injection
- State sharing
- Arc usage patterns

**6.3 Business Logic Patterns**
- Validation approach
- Error handling strategy
- Logging patterns

---

### SECTION 7: Authentication & Authorization

**7.1 Auth Middleware**
```rust
// How auth is implemented
pub async fn auth_middleware(
    State(state): State<AppState>,
    request: Request,
    next: Next,
) -> Result<Response, AuthError> {
    // extract token, validate, inject user
}
```

**7.2 JWT/Token Handling**
- Token generation
- Token validation
- Claims structure

**7.3 Permission Checks**
How authorization is enforced in handlers.

---

### SECTION 8: Async Patterns

**8.1 Runtime Configuration**
```rust
#[tokio::main]
async fn main() {
    // runtime setup
}
```

**8.2 Concurrency Patterns**
- `tokio::spawn` usage
- `join!` / `select!` patterns
- Stream processing
- Semaphore/rate limiting

**8.3 Error Propagation**
- `?` operator usage
- `anyhow` vs `thiserror`
- Error context addition

---

### SECTION 9: Testing

**9.1 Test Organization**
```
tests/
├── common/mod.rs     # Shared test utilities
├── integration/
│   ├── api_tests.rs  # HTTP tests
│   └── db_tests.rs   # Database tests
```

**9.2 Test Patterns**
- Unit tests (inline `#[cfg(test)]`)
- Integration tests
- Test database setup
- Mocking strategy

**9.3 Test Coverage**
What's tested vs what's not:
- [ ] User CRUD - ✅ covered
- [ ] Auth flows - ⚠️ partial
- [ ] Payment processing - ❌ missing

---

### SECTION 10: Configuration

**10.1 Config Loading**
```rust
#[derive(Debug, Deserialize)]
pub struct Config {
    pub database_url: String,
    pub jwt_secret: String,
    #[serde(default = "default_port")]
    pub port: u16,
}
```

**10.2 Environment Variables**
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DATABASE_URL | yes | - | PostgreSQL URL |
| JWT_SECRET | yes | - | Token secret |
| PORT | no | 3000 | Server port |

---

### SECTION 11: Code Quality

**11.1 Clippy Lints**
Configured lints in `Cargo.toml` or `clippy.toml`

**11.2 Formatting**
`rustfmt.toml` configuration

**11.3 Documentation**
- Doc comments coverage
- Examples in docs
- README completeness

---

### SECTION 12: Ported Status

**12.1 What's Ported**
| TS Module | Rust Module | Status | Notes |
|-----------|-------------|--------|-------|
| src/users | crates/users | ✅ Complete | - |
| src/auth | crates/auth | ⚠️ Partial | Missing refresh |
| src/orders | - | ❌ Not started | - |

**12.2 Established Patterns**
Patterns that MUST be followed for consistency:
1. Error handling: Use `thiserror` for domain errors
2. Validation: Use `validator` crate
3. Logging: Use `tracing` with structured fields
4. Testing: Use `sqlx::test` for DB tests

**12.3 Technical Debt**
Known issues to address:
- `todo!()` or `unimplemented!()` markers
- `unwrap()` usage that should be handled
- Missing error variants

---

### SECTION 13: Next Steps

**13.1 Ready to Port**
Features that can be ported now (dependencies satisfied):

| Feature | Complexity | Estimated LOC | Dependencies Met |
|---------|------------|---------------|------------------|
| ... | ... | ... | ... |

**13.2 Blocked Features**
Features waiting on dependencies:

| Feature | Blocked By | Notes |
|---------|------------|-------|
| ... | ... | ... |

**13.3 Recommended Porting Order**
1. [ ] First port this...
2. [ ] Then this...
3. [ ] Finally...

{previous_context}
