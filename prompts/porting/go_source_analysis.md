version=1
## Repository Structure and Files

{repo_structure}
---

## Go Source Codebase - Comprehensive Analysis for Rust Porting

You are a senior software architect analyzing a Go codebase that will be ported to Rust. Your analysis must be thorough enough to serve as the complete blueprint for the Rust implementation.

---

### SECTION 1: Project Overview

**1.1 Project Identity**
- Repository name: [[name]]
- Primary purpose/domain
- Target users/consumers
- CLI tool / Library / Service / Hybrid
- Business context

**1.2 Technology Stack**
- Go version (from go.mod)
- Build system (go build, make, goreleaser, etc.)
- CLI framework (cobra, urfave/cli, kong, etc.)
- TUI framework (bubbletea, tview, termui, etc.)
- Web framework (gin, echo, chi, fiber, etc.)
- Database drivers (pgx, go-sqlite3, mongo-driver, etc.)
- Configuration (viper, envconfig, koanf, etc.)

**1.3 Dependency Analysis**
Analyze go.mod thoroughly:

| Package | Version | Purpose | Rust Equivalent |
|---------|---------|---------|-----------------|
| github.com/spf13/cobra | vX.X.X | CLI framework | clap |
| github.com/charmbracelet/bubbletea | vX.X.X | TUI framework | ratatui |
| github.com/spf13/viper | vX.X.X | Configuration | config-rs |
| ... | ... | ... | ... |

---

### SECTION 2: Architecture Deep Dive

**2.1 Architectural Pattern**
- Pattern used (Clean Architecture, Hexagonal, Simple Package Structure, etc.)
- Evidence for pattern choice
- Deviation from standard Go project layout

**2.2 Directory Structure**
```
.
├── cmd/           # Entry points
│   └── app/       # Main binary
├── internal/      # Private packages
│   ├── pkg1/      # Purpose: ...
│   └── pkg2/      # Purpose: ...
├── pkg/           # Public packages
└── ...
```

For each top-level directory, explain:
- What code lives here
- How it relates to other directories
- Key files and their roles

**2.3 Package Boundaries**
- How are packages separated?
- Internal vs exported packages
- Circular dependency handling
- Inter-package communication patterns

---

### SECTION 3: Type System Analysis

**3.1 Core Domain Types**
List and explain all major structs/types:

```go
// File: internal/models/user.go
type User struct {
    ID        string    `json:"id"`        // Format: UUID v4
    Email     string    `json:"email"`     // Validated email
    CreatedAt time.Time `json:"created_at"`
    // ... document each field
}
```

**Rust mapping:**
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: Uuid,
    pub email: String,
    pub created_at: DateTime<Utc>,
}
```

**3.2 Interface Patterns**
Document all interfaces and their implementations:

```go
type Repository interface {
    Get(ctx context.Context, id string) (*Entity, error)
    Save(ctx context.Context, entity *Entity) error
}
```

**Rust trait mapping:**
```rust
#[async_trait]
pub trait Repository: Send + Sync {
    async fn get(&self, id: &str) -> Result<Entity, Error>;
    async fn save(&self, entity: &Entity) -> Result<(), Error>;
}
```

**3.3 Type Aliases and Custom Types**
- Type aliases (`type UserID string`)
- Embedded structs
- Generic types (Go 1.18+)

---

### SECTION 4: Concurrency Patterns

**4.1 Goroutine Usage**
For each goroutine pattern:
- Purpose
- Spawning pattern
- Cancellation mechanism
- Error propagation

| Pattern | Location | Purpose | Rust Equivalent |
|---------|----------|---------|-----------------|
| Worker pool | pkg/worker | Parallel processing | tokio::spawn + JoinSet |
| Background task | internal/bg | Periodic cleanup | tokio::spawn + interval |
| Fan-out/fan-in | internal/proc | Parallel API calls | futures::join_all |

**4.2 Channel Patterns**
```go
// Document channel types and usage
resultCh := make(chan Result, 100)
errCh := make(chan error, 1)
```

**Rust mapping:**
```rust
let (tx, rx) = tokio::sync::mpsc::channel::<Result>(100);
```

**4.3 Synchronization Primitives**
- sync.Mutex usage
- sync.RWMutex usage
- sync.WaitGroup patterns
- sync.Once patterns
- Context cancellation

---

### SECTION 5: Error Handling

**5.1 Error Types**
Document custom error types:

```go
type NotFoundError struct {
    Resource string
    ID       string
}

func (e *NotFoundError) Error() string {
    return fmt.Sprintf("%s with id %s not found", e.Resource, e.ID)
}
```

**Rust mapping:**
```rust
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("{resource} with id {id} not found")]
    NotFound { resource: String, id: String },
}
```

**5.2 Error Wrapping**
- How errors are wrapped (fmt.Errorf with %w)
- Error chain inspection
- Sentinel errors

**5.3 Error Handling Patterns**
- Early return pattern
- Error accumulation
- Deferred cleanup with errors

---

### SECTION 6: CLI/TUI Analysis (if applicable)

**6.1 Command Structure**
```
app
├── command1
│   ├── subcommand1
│   └── subcommand2
└── command2
```

For each command:
- Name and aliases
- Flags (persistent/local)
- Arguments
- Implementation file

**6.2 TUI Components (if using bubbletea, etc.)**
- Model structure
- Update loop patterns
- View rendering
- Component composition

**6.3 User Interaction Patterns**
- Input validation
- Interactive prompts
- Progress indicators
- Output formatting

---

### SECTION 7: Data Layer

**7.1 Database/Storage**
- Database type (PostgreSQL, SQLite, embedded, etc.)
- Connection management
- Query patterns (raw SQL, query builder, ORM)

**7.2 Data Access Patterns**
- Repository pattern usage
- Transaction handling
- Connection pooling

**7.3 File System Operations**
- Configuration file handling
- State persistence
- Temporary files

---

### SECTION 8: External Integrations

**8.1 HTTP Client Usage**
For each external API:
- Service name
- Endpoints called
- Authentication
- Error handling
- Retry logic

**8.2 Process/System Interaction**
- exec.Command usage
- Signal handling
- Environment variables
- IPC mechanisms

**8.3 External Tools**
- Tool dependencies (tmux, git, etc.)
- Integration patterns
- Version requirements

---

### SECTION 9: Testing Strategy (Comprehensive)

**9.1 Test Organization**
Document the complete test structure:

```
tests/
├── unit/              # Unit tests (if separate)
├── integration/       # Integration tests
├── e2e/               # End-to-end tests
└── testdata/          # Test fixtures
```

Or inline test organization:
```
internal/
├── pkg/
│   ├── pkg.go
│   └── pkg_test.go    # Unit tests
├── integration_test.go # Integration tests (build tag)
```

**9.2 Unit Tests**
For each package, document:

| Package | Test File | Test Count | Coverage | Key Test Patterns |
|---------|-----------|------------|----------|-------------------|
| internal/cli | cli_test.go | 25 | 85% | Table-driven, mocks |
| internal/config | config_test.go | 15 | 90% | Fixtures, temp files |

**Unit Test Patterns Used:**
```go
// Table-driven tests
func TestParse(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    Result
        wantErr bool
    }{
        {"valid input", "abc", Result{...}, false},
        {"empty input", "", Result{}, true},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := Parse(tt.input)
            // assertions
        })
    }
}
```

**Rust equivalent:**
```rust
#[cfg(test)]
mod tests {
    use super::*;
    use rstest::rstest;
    
    #[rstest]
    #[case("abc", Ok(Result{...}))]
    #[case("", Err(Error::Empty))]
    fn test_parse(#[case] input: &str, #[case] expected: Result<Result, Error>) {
        assert_eq!(parse(input), expected);
    }
}
```

**9.3 Integration Tests**
Document integration test setup:

| Test Suite | Purpose | External Deps | Setup Required |
|------------|---------|---------------|----------------|
| db_integration_test.go | Database operations | PostgreSQL | Docker/testcontainers |
| api_integration_test.go | API endpoints | HTTP server | Start server |
| tmux_integration_test.go | Tmux operations | tmux binary | tmux installed |

**Build Tags:**
```go
//go:build integration
// +build integration

package integration
```

**Test Setup/Teardown:**
```go
func TestMain(m *testing.M) {
    // Setup
    db := setupTestDB()
    defer db.Close()
    
    // Run tests
    code := m.Run()
    
    // Teardown
    cleanupTestDB(db)
    os.Exit(code)
}
```

**Rust equivalent:**
```rust
// tests/integration/mod.rs
use once_cell::sync::Lazy;

static TEST_DB: Lazy<TestDb> = Lazy::new(|| {
    TestDb::setup()
});

#[tokio::test]
async fn test_database_operations() {
    let db = &*TEST_DB;
    // test code
}
```

**9.4 End-to-End Tests**
Document E2E test coverage:

| E2E Test | Scenario | Commands Tested | Expected Outcome |
|----------|----------|-----------------|------------------|
| test_spawn_session | Create new session | spawn, status | Session created with agents |
| test_send_message | Send to agents | spawn, send, copy | Message delivered |
| test_full_workflow | Complete workflow | spawn, send, save, kill | Full cycle success |

**E2E Test Patterns:**
```go
func TestE2E_FullWorkflow(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping e2e test in short mode")
    }
    
    // Setup: create temp directory, mock external services
    tmpDir := t.TempDir()
    
    // Execute: run commands
    cmd := exec.Command("ntm", "spawn", "test-session", "--cc=1")
    output, err := cmd.CombinedOutput()
    require.NoError(t, err)
    
    // Verify: check outcomes
    assert.Contains(t, string(output), "Session created")
    
    // Cleanup: handled by t.Cleanup or defer
    t.Cleanup(func() {
        exec.Command("ntm", "kill", "-f", "test-session").Run()
    })
}
```

**Rust equivalent:**
```rust
// tests/e2e/workflow_test.rs
use assert_cmd::Command;
use predicates::prelude::*;

#[test]
#[ignore] // Run with: cargo test -- --ignored
fn test_full_workflow() {
    let temp = tempfile::tempdir().unwrap();
    
    // Spawn session
    Command::cargo_bin("ntm")
        .unwrap()
        .args(["spawn", "test-session", "--cc=1"])
        .assert()
        .success()
        .stdout(predicate::str::contains("Session created"));
    
    // Cleanup
    Command::cargo_bin("ntm")
        .unwrap()
        .args(["kill", "-f", "test-session"])
        .assert()
        .success();
}
```

**9.5 Mocking Strategy**

| Mock Type | Go Tool | Usage | Rust Equivalent |
|-----------|---------|-------|-----------------|
| Interface mocks | mockgen | Service layer | mockall |
| HTTP mocks | httptest | API calls | wiremock |
| File system | afero | File operations | tempfile + traits |
| Time | clock interface | Time-based logic | mock_instant |
| External commands | exec mock | CLI calls | assert_cmd |

**Go mock example:**
```go
//go:generate mockgen -source=repository.go -destination=mock_repository.go

type MockRepository struct {
    // generated
}
```

**Rust mock example:**
```rust
use mockall::automock;

#[automock]
pub trait Repository {
    async fn get(&self, id: &str) -> Result<Entity, Error>;
}

#[tokio::test]
async fn test_service() {
    let mut mock = MockRepository::new();
    mock.expect_get()
        .with(eq("123"))
        .returning(|_| Ok(Entity::default()));
    
    let service = Service::new(Box::new(mock));
    // test service
}
```

**9.6 Test Fixtures and Factories**

Document test data patterns:
```go
// testdata/fixtures.go
func NewTestUser() *User {
    return &User{
        ID:    "test-id",
        Email: "test@example.com",
        Name:  "Test User",
    }
}

// Golden files
// testdata/golden/expected_output.txt
```

**Rust equivalent:**
```rust
// tests/fixtures/mod.rs
pub fn test_user() -> User {
    User {
        id: "test-id".into(),
        email: "test@example.com".into(),
        name: "Test User".into(),
    }
}

// Or with fake crate
use fake::{Fake, Faker};
let user: User = Faker.fake();
```

**9.7 Test Commands and CI**

```bash
# Go test commands
go test ./...                          # All tests
go test -short ./...                   # Skip long tests
go test -race ./...                    # With race detector
go test -cover ./...                   # With coverage
go test -tags=integration ./...        # Integration tests
go test -v -run TestE2E ./tests/e2e/  # E2E tests only
```

**Rust equivalent:**
```bash
# Rust test commands
cargo test                             # All tests
cargo test --lib                       # Unit tests only
cargo test --test '*'                  # Integration tests
cargo test -- --ignored                # E2E tests (marked #[ignore])
cargo test -- --test-threads=1        # Sequential (for stateful tests)
cargo tarpaulin                        # Coverage (with tarpaulin)
```

**9.8 Test Porting Checklist**

| Test Category | Go Location | Rust Location | Porting Notes |
|---------------|-------------|---------------|---------------|
| Unit tests | `*_test.go` in pkg | `#[cfg(test)] mod tests` | Inline in source |
| Integration | `integration/` or build tag | `tests/` directory | Separate crate |
| E2E | `e2e/` or `tests/` | `tests/e2e/` | assert_cmd |
| Benchmarks | `*_test.go` with Benchmark | `benches/` with criterion | Different location |
| Examples | `example_*_test.go` | `examples/` directory | Different pattern |
| Fuzz tests | Go 1.18+ fuzz | cargo-fuzz | Similar concept |

---

### SECTION 10: Configuration & Environment

**10.1 Configuration Schema**
All configuration sources:

| Source | Variable/Key | Type | Required | Default | Description |
|--------|--------------|------|----------|---------|-------------|
| Env | DATABASE_URL | string | yes | - | Database connection |
| File | config.toml | - | no | - | User config |
| Flag | --verbose | bool | no | false | Verbose output |

**10.2 Configuration Loading Order**
1. Defaults
2. Config file
3. Environment variables
4. Command-line flags

---

### SECTION 11: Go → Rust Porting Considerations

**11.1 Go-Specific Patterns**
Patterns requiring special attention:

| Go Pattern | Complexity | Rust Approach |
|------------|------------|---------------|
| defer | Low | Drop trait, scopeguard |
| goroutines | Medium | tokio::spawn, async/await |
| channels | Medium | tokio::sync channels |
| interfaces | Low | Traits |
| error interface | Low | thiserror, anyhow |
| context.Context | Medium | CancellationToken, timeout |
| struct embedding | Low | Composition or Deref |
| init() functions | Low | lazy_static, once_cell |
| panic/recover | Medium | panic! (rarely), Result |
| reflect | High | Avoid or redesign |

**11.2 Concurrency Translation**

```go
// Go: goroutine with channel
go func() {
    result := doWork()
    ch <- result
}()
```

```rust
// Rust: tokio spawn with channel
tokio::spawn(async move {
    let result = do_work().await;
    tx.send(result).await.ok();
});
```

**11.3 Complexity Hotspots**
Areas challenging to port:
- Heavy reflection usage
- Dynamic interface assertions
- CGO dependencies
- Complex generics with constraints
- Build-time code generation

---

### SECTION 12: Build & Deployment

**12.1 Build Configuration**
- Build tags/constraints
- CGO requirements
- Cross-compilation setup
- ldflags usage

**12.2 Release Process**
- goreleaser configuration
- Multi-platform builds
- Asset generation

---

### SECTION 13: Porting Task List

Generate a prioritized list of porting tasks:

| Priority | Module/Feature | Complexity | Dependencies | Rust Crates | Notes |
|----------|----------------|------------|--------------|-------------|-------|
| P0 | Core types | Low | None | serde | Start here |
| P0 | Error types | Low | Core types | thiserror | Foundation |
| P0 | Config loading | Low | Error types | config, clap | Early need |
| P1 | CLI structure | Medium | Config | clap | Main interface |
| P1 | TUI components | High | CLI | ratatui | Complex state |
| P2 | External tool integration | Medium | Core | std::process | tmux, git |
| P3 | Tests | Medium | All | - | After impl |

**Recommended Porting Order:**
1. Core types and errors
2. Configuration system
3. CLI skeleton
4. Core business logic
5. External integrations
6. TUI (if applicable)
7. Tests

---

### SECTION 14: Rust Crate Recommendations

Based on Go dependencies, recommend Rust crates:

| Go Package | Purpose | Rust Crate | Notes |
|------------|---------|------------|-------|
| spf13/cobra | CLI | clap | Derive or builder API |
| spf13/viper | Config | config, figment | |
| charmbracelet/bubbletea | TUI | ratatui | Different paradigm |
| charmbracelet/lipgloss | Styling | ratatui styles | Built-in |
| fatih/color | Terminal color | colored, owo-colors | |
| sirupsen/logrus | Logging | tracing | Structured logging |
| go-git/go-git | Git operations | git2 | libgit2 bindings |
| pelletier/go-toml | TOML parsing | toml | serde integration |
| BurntSushi/toml | TOML parsing | toml | serde integration |
| stretchr/testify | Testing | Built-in + rstest | |
| golang.org/x/term | Terminal | crossterm | |

{previous_context}
