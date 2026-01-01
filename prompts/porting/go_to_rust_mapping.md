version=1
## Go to Rust Type and Pattern Mappings

Based on the Go source analysis, generate comprehensive mappings for porting to idiomatic Rust.

{previous_context}

---

### SECTION 1: Primitive Type Mappings

| Go Type | Rust Type | Notes |
|---------|-----------|-------|
| `bool` | `bool` | Direct |
| `string` | `String` / `&str` | Owned vs borrowed |
| `int` | `i32` / `isize` | Check platform requirements |
| `int8` | `i8` | Direct |
| `int16` | `i16` | Direct |
| `int32` | `i32` | Direct |
| `int64` | `i64` | Direct |
| `uint` | `u32` / `usize` | Check platform requirements |
| `uint8` / `byte` | `u8` | Direct |
| `uint16` | `u16` | Direct |
| `uint32` | `u32` | Direct |
| `uint64` | `u64` | Direct |
| `float32` | `f32` | Direct |
| `float64` | `f64` | Direct |
| `complex64` | `num::Complex<f32>` | num crate |
| `complex128` | `num::Complex<f64>` | num crate |
| `rune` | `char` | Direct |
| `[]byte` | `Vec<u8>` / `&[u8]` / `Bytes` | Context dependent |

---

### SECTION 2: Composite Type Mappings

**2.1 Slices and Arrays**

| Go | Rust | Notes |
|----|------|-------|
| `[N]T` | `[T; N]` | Fixed array |
| `[]T` | `Vec<T>` | Dynamic slice |
| `[]T` (read-only) | `&[T]` | Slice reference |
| `[]T` (mutable) | `&mut [T]` | Mutable slice |

**2.2 Maps**

| Go | Rust | Notes |
|----|------|-------|
| `map[K]V` | `HashMap<K, V>` | std::collections |
| `map[K]V` (ordered) | `BTreeMap<K, V>` | Ordered iteration |
| `map[K]struct{}` | `HashSet<K>` | Set pattern |

**2.3 Structs**

```go
// Go
type User struct {
    ID        string
    Name      string
    Email     string
    CreatedAt time.Time
}
```

```rust
// Rust
#[derive(Debug, Clone, PartialEq, Eq)]
#[derive(Serialize, Deserialize)]
pub struct User {
    pub id: String,
    pub name: String,
    pub email: String,
    pub created_at: DateTime<Utc>,
}
```

**2.4 Embedded Structs**

```go
// Go
type Admin struct {
    User        // embedded
    Permissions []string
}
```

```rust
// Rust - composition
pub struct Admin {
    pub user: User,
    pub permissions: Vec<String>,
}

// Or with Deref for convenience
impl std::ops::Deref for Admin {
    type Target = User;
    fn deref(&self) -> &Self::Target {
        &self.user
    }
}
```

---

### SECTION 3: Interface to Trait Mappings

For each Go interface in the codebase:

**Pattern:**
```go
// Go interface
type Storage interface {
    Get(ctx context.Context, key string) ([]byte, error)
    Set(ctx context.Context, key string, value []byte) error
    Delete(ctx context.Context, key string) error
}
```

```rust
// Rust trait
use async_trait::async_trait;

#[async_trait]
pub trait Storage: Send + Sync {
    async fn get(&self, key: &str) -> Result<Vec<u8>, Error>;
    async fn set(&self, key: &str, value: &[u8]) -> Result<(), Error>;
    async fn delete(&self, key: &str) -> Result<(), Error>;
}
```

**Map all interfaces from the Go source analysis:**

| Go Interface | Rust Trait | Async | Notes |
|--------------|------------|-------|-------|
| `io.Reader` | `std::io::Read` / `tokio::io::AsyncRead` | Optional | |
| `io.Writer` | `std::io::Write` / `tokio::io::AsyncWrite` | Optional | |
| `fmt.Stringer` | `std::fmt::Display` | No | |
| `error` | `std::error::Error` | No | |
| [Custom interfaces from analysis] | | | |

---

### SECTION 4: Error Handling Mappings

**4.1 Error Types**

```go
// Go
var ErrNotFound = errors.New("not found")

type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed for %s: %s", e.Field, e.Message)
}
```

```rust
// Rust with thiserror
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("not found")]
    NotFound,
    
    #[error("validation failed for {field}: {message}")]
    Validation {
        field: String,
        message: String,
    },
    
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
}
```

**4.2 Error Wrapping**

```go
// Go
if err != nil {
    return fmt.Errorf("failed to process: %w", err)
}
```

```rust
// Rust with anyhow
use anyhow::{Context, Result};

fn process() -> Result<()> {
    do_something().context("failed to process")?;
    Ok(())
}
```

**4.3 Multiple Return Values**

```go
// Go
func divide(a, b int) (int, error) {
    if b == 0 {
        return 0, errors.New("division by zero")
    }
    return a / b, nil
}
```

```rust
// Rust
fn divide(a: i32, b: i32) -> Result<i32, Error> {
    if b == 0 {
        return Err(Error::DivisionByZero);
    }
    Ok(a / b)
}
```

---

### SECTION 5: Concurrency Mappings

**5.1 Goroutines**

```go
// Go
go func() {
    result := doWork()
    ch <- result
}()
```

```rust
// Rust with tokio
tokio::spawn(async move {
    let result = do_work().await;
    tx.send(result).await.ok();
});
```

**5.2 Channels**

| Go Channel | Rust Equivalent | Crate |
|------------|-----------------|-------|
| `make(chan T)` | `tokio::sync::mpsc::channel` | tokio |
| `make(chan T, n)` | `tokio::sync::mpsc::channel(n)` | tokio |
| `chan<- T` (send only) | `Sender<T>` | tokio |
| `<-chan T` (recv only) | `Receiver<T>` | tokio |
| `close(ch)` | `drop(tx)` | - |
| `select` | `tokio::select!` | tokio |

**5.3 Sync Primitives**

| Go | Rust | Notes |
|----|------|-------|
| `sync.Mutex` | `std::sync::Mutex` / `tokio::sync::Mutex` | Async vs sync |
| `sync.RWMutex` | `std::sync::RwLock` / `tokio::sync::RwLock` | |
| `sync.WaitGroup` | `tokio::task::JoinSet` | Different API |
| `sync.Once` | `std::sync::Once` / `once_cell::sync::Lazy` | |
| `sync.Map` | `dashmap::DashMap` | |
| `sync.Pool` | Object pool crate or custom | |

**5.4 Context**

```go
// Go
ctx, cancel := context.WithTimeout(parentCtx, 5*time.Second)
defer cancel()
```

```rust
// Rust
use tokio::time::{timeout, Duration};
use tokio_util::sync::CancellationToken;

let token = CancellationToken::new();
let result = timeout(Duration::from_secs(5), async {
    do_work().await
}).await;
```

---

### SECTION 6: Common Patterns

**6.1 Defer → Drop/Scopeguard**

```go
// Go
func process() error {
    f, err := os.Open("file.txt")
    if err != nil {
        return err
    }
    defer f.Close()
    // ... use f
}
```

```rust
// Rust - automatic with Drop
fn process() -> Result<()> {
    let f = File::open("file.txt")?;
    // f automatically closed when dropped
    Ok(())
}

// Or explicit with scopeguard
use scopeguard::defer;
fn process() -> Result<()> {
    let f = File::open("file.txt")?;
    defer! { cleanup(); }
    // ... use f
    Ok(())
}
```

**6.2 Init Functions → Lazy Static**

```go
// Go
var config *Config

func init() {
    config = loadConfig()
}
```

```rust
// Rust with once_cell
use once_cell::sync::Lazy;

static CONFIG: Lazy<Config> = Lazy::new(|| {
    load_config()
});
```

**6.3 Type Assertions**

```go
// Go
if v, ok := val.(string); ok {
    // use v
}
```

```rust
// Rust - use enums instead of interface{}
match val {
    Value::String(s) => { /* use s */ }
    _ => {}
}

// Or with Any (rarely needed)
if let Some(s) = val.downcast_ref::<String>() {
    // use s
}
```

**6.4 Method Receivers**

```go
// Go - value receiver
func (u User) FullName() string {
    return u.FirstName + " " + u.LastName
}

// Go - pointer receiver
func (u *User) SetEmail(email string) {
    u.Email = email
}
```

```rust
// Rust
impl User {
    pub fn full_name(&self) -> String {
        format!("{} {}", self.first_name, self.last_name)
    }
    
    pub fn set_email(&mut self, email: String) {
        self.email = email;
    }
}
```

---

### SECTION 7: CLI/TUI Mappings

**7.1 Cobra → Clap**

```go
// Go with Cobra
var rootCmd = &cobra.Command{
    Use:   "app",
    Short: "App description",
    Run: func(cmd *cobra.Command, args []string) {
        // ...
    },
}

func init() {
    rootCmd.PersistentFlags().StringVarP(&cfgFile, "config", "c", "", "config file")
    rootCmd.AddCommand(subCmd)
}
```

```rust
// Rust with Clap (derive)
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "app")]
#[command(about = "App description")]
struct Cli {
    #[arg(short, long, global = true)]
    config: Option<PathBuf>,
    
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Sub { /* args */ },
}
```

**7.2 Bubbletea → Ratatui**

```go
// Go bubbletea model
type model struct {
    choices  []string
    cursor   int
    selected map[int]struct{}
}

func (m model) Init() tea.Cmd { return nil }
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) { ... }
func (m model) View() string { ... }
```

```rust
// Rust ratatui - different paradigm
struct App {
    choices: Vec<String>,
    cursor: usize,
    selected: HashSet<usize>,
}

impl App {
    fn handle_key(&mut self, key: KeyCode) { ... }
    fn render(&self, frame: &mut Frame, area: Rect) { ... }
}

// Main loop
loop {
    terminal.draw(|f| app.render(f, f.size()))?;
    if let Event::Key(key) = event::read()? {
        app.handle_key(key.code);
    }
}
```

---

### SECTION 8: Dependency Mapping Summary

Based on go.mod analysis, complete crate mapping:

| Go Dependency | Rust Crate | Notes |
|---------------|------------|-------|
| Standard library | std | |
| golang.org/x/term | crossterm | Terminal handling |
| github.com/spf13/cobra | clap | CLI framework |
| github.com/spf13/viper | config, figment | Configuration |
| github.com/charmbracelet/bubbletea | ratatui + crossterm | TUI (different paradigm) |
| github.com/charmbracelet/lipgloss | ratatui styles | Built into ratatui |
| github.com/fatih/color | colored, owo-colors | Terminal colors |
| github.com/sirupsen/logrus | tracing, log | Logging |
| github.com/pelletier/go-toml | toml | TOML parsing |
| github.com/stretchr/testify | built-in + rstest | Testing |

---

### SECTION 9: Test Porting Mappings

**9.1 Test Framework Mapping**

| Go Testing | Rust Equivalent | Crate |
|------------|-----------------|-------|
| `testing.T` | Built-in `#[test]` | std |
| `testing.B` (benchmarks) | Criterion | criterion |
| `testing.F` (fuzz) | cargo-fuzz | libfuzzer |
| `testify/assert` | Built-in `assert!` macros | std |
| `testify/require` | `assert!` (panics) | std |
| `testify/suite` | rstest fixtures | rstest |
| `testify/mock` | mockall | mockall |
| `gomock/mockgen` | mockall | mockall |
| `httptest` | wiremock | wiremock |
| `go-cmp` | pretty_assertions | pretty_assertions |

**9.2 Table-Driven Tests**

```go
// Go table-driven
func TestAdd(t *testing.T) {
    tests := []struct {
        name string
        a, b int
        want int
    }{
        {"positive", 1, 2, 3},
        {"negative", -1, -2, -3},
        {"zero", 0, 0, 0},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            if got := Add(tt.a, tt.b); got != tt.want {
                t.Errorf("Add() = %v, want %v", got, tt.want)
            }
        })
    }
}
```

```rust
// Rust with rstest
use rstest::rstest;

#[rstest]
#[case::positive(1, 2, 3)]
#[case::negative(-1, -2, -3)]
#[case::zero(0, 0, 0)]
fn test_add(#[case] a: i32, #[case] b: i32, #[case] expected: i32) {
    assert_eq!(add(a, b), expected);
}

// Or with test_case
use test_case::test_case;

#[test_case(1, 2 => 3 ; "positive")]
#[test_case(-1, -2 => -3 ; "negative")]
#[test_case(0, 0 => 0 ; "zero")]
fn test_add(a: i32, b: i32) -> i32 {
    add(a, b)
}
```

**9.3 Test Setup/Teardown**

```go
// Go TestMain
func TestMain(m *testing.M) {
    setup()
    code := m.Run()
    teardown()
    os.Exit(code)
}

// Go t.Cleanup
func TestSomething(t *testing.T) {
    resource := createResource()
    t.Cleanup(func() {
        resource.Close()
    })
}
```

```rust
// Rust with rstest fixtures
use rstest::fixture;

#[fixture]
fn test_db() -> TestDb {
    let db = TestDb::new();
    // Setup happens here
    db
}

#[rstest]
fn test_something(test_db: TestDb) {
    // test_db is automatically created and dropped
}

// Or with ctor for module-level setup
use ctor::{ctor, dtor};

#[ctor]
fn setup() {
    // Runs before tests
}

#[dtor]
fn teardown() {
    // Runs after tests
}
```

**9.4 Mocking Interfaces**

```go
// Go with mockgen
//go:generate mockgen -destination=mocks/mock_store.go -package=mocks . Store

type Store interface {
    Get(ctx context.Context, id string) (*Item, error)
    Save(ctx context.Context, item *Item) error
}

func TestService(t *testing.T) {
    ctrl := gomock.NewController(t)
    defer ctrl.Finish()
    
    mockStore := mocks.NewMockStore(ctrl)
    mockStore.EXPECT().
        Get(gomock.Any(), "123").
        Return(&Item{ID: "123"}, nil)
    
    svc := NewService(mockStore)
    result, err := svc.GetItem(context.Background(), "123")
    require.NoError(t, err)
    assert.Equal(t, "123", result.ID)
}
```

```rust
// Rust with mockall
use mockall::{automock, predicate::*};

#[automock]
#[async_trait]
pub trait Store: Send + Sync {
    async fn get(&self, id: &str) -> Result<Item, Error>;
    async fn save(&self, item: &Item) -> Result<(), Error>;
}

#[tokio::test]
async fn test_service() {
    let mut mock_store = MockStore::new();
    mock_store
        .expect_get()
        .with(eq("123"))
        .times(1)
        .returning(|_| Ok(Item { id: "123".into() }));
    
    let svc = Service::new(Arc::new(mock_store));
    let result = svc.get_item("123").await.unwrap();
    assert_eq!(result.id, "123");
}
```

**9.5 HTTP Testing**

```go
// Go httptest
func TestHandler(t *testing.T) {
    req := httptest.NewRequest("GET", "/users/123", nil)
    w := httptest.NewRecorder()
    
    handler.ServeHTTP(w, req)
    
    assert.Equal(t, http.StatusOK, w.Code)
    
    var user User
    json.Unmarshal(w.Body.Bytes(), &user)
    assert.Equal(t, "123", user.ID)
}

// Mock external HTTP
server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"status": "ok"}`))
}))
defer server.Close()
```

```rust
// Rust with axum test utilities
use axum::body::Body;
use axum::http::{Request, StatusCode};
use tower::ServiceExt;

#[tokio::test]
async fn test_handler() {
    let app = create_app();
    
    let response = app
        .oneshot(
            Request::builder()
                .uri("/users/123")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    
    assert_eq!(response.status(), StatusCode::OK);
    
    let body = hyper::body::to_bytes(response.into_body()).await.unwrap();
    let user: User = serde_json::from_slice(&body).unwrap();
    assert_eq!(user.id, "123");
}

// Mock external HTTP with wiremock
use wiremock::{MockServer, Mock, ResponseTemplate};
use wiremock::matchers::{method, path};

#[tokio::test]
async fn test_external_api() {
    let mock_server = MockServer::start().await;
    
    Mock::given(method("GET"))
        .and(path("/api/status"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({"status": "ok"})))
        .mount(&mock_server)
        .await;
    
    let client = Client::new(&mock_server.uri());
    let result = client.get_status().await.unwrap();
    assert_eq!(result.status, "ok");
}
```

**9.6 Integration Test Patterns**

```go
// Go integration test with build tag
//go:build integration

package integration

func TestDatabaseIntegration(t *testing.T) {
    db := setupTestDB(t)
    defer db.Close()
    
    repo := NewRepository(db)
    
    // Test actual database operations
    err := repo.Save(context.Background(), &entity)
    require.NoError(t, err)
    
    retrieved, err := repo.Get(context.Background(), entity.ID)
    require.NoError(t, err)
    assert.Equal(t, entity, retrieved)
}
```

```rust
// Rust integration tests in tests/ directory
// tests/integration/database_test.rs

use sqlx::PgPool;
use testcontainers::{clients, images::postgres::Postgres};

#[tokio::test]
async fn test_database_integration() {
    let docker = clients::Cli::default();
    let postgres = docker.run(Postgres::default());
    
    let pool = PgPool::connect(&format!(
        "postgres://postgres:postgres@localhost:{}/postgres",
        postgres.get_host_port_ipv4(5432)
    ))
    .await
    .unwrap();
    
    let repo = Repository::new(pool);
    
    repo.save(&entity).await.unwrap();
    let retrieved = repo.get(&entity.id).await.unwrap();
    assert_eq!(entity, retrieved);
}
```

**9.7 E2E/CLI Testing**

```go
// Go CLI testing
func TestCLI_SpawnCommand(t *testing.T) {
    cmd := exec.Command("ntm", "spawn", "test-session", "--cc=1")
    output, err := cmd.CombinedOutput()
    require.NoError(t, err)
    assert.Contains(t, string(output), "Session created")
    
    // Cleanup
    exec.Command("ntm", "kill", "-f", "test-session").Run()
}
```

```rust
// Rust with assert_cmd
use assert_cmd::Command;
use predicates::prelude::*;

#[test]
fn test_cli_spawn_command() {
    let mut cmd = Command::cargo_bin("ntm").unwrap();
    
    cmd.args(["spawn", "test-session", "--cc=1"])
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

// With temp directory
use assert_fs::prelude::*;

#[test]
fn test_with_temp_dir() {
    let temp = assert_fs::TempDir::new().unwrap();
    let config_file = temp.child("config.toml");
    config_file.write_str("[settings]\nkey = \"value\"").unwrap();
    
    Command::cargo_bin("ntm")
        .unwrap()
        .args(["--config", config_file.path().to_str().unwrap()])
        .assert()
        .success();
}
```

**9.8 Benchmark Porting**

```go
// Go benchmark
func BenchmarkParse(b *testing.B) {
    input := "test input"
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        Parse(input)
    }
}

func BenchmarkParseParallel(b *testing.B) {
    input := "test input"
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            Parse(input)
        }
    })
}
```

```rust
// Rust with criterion (benches/parsing.rs)
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn bench_parse(c: &mut Criterion) {
    let input = "test input";
    
    c.bench_function("parse", |b| {
        b.iter(|| parse(black_box(input)))
    });
}

fn bench_parse_parallel(c: &mut Criterion) {
    use rayon::prelude::*;
    let input = "test input";
    
    c.bench_function("parse_parallel", |b| {
        b.iter(|| {
            (0..1000).into_par_iter().for_each(|_| {
                parse(black_box(input));
            });
        })
    });
}

criterion_group!(benches, bench_parse, bench_parse_parallel);
criterion_main!(benches);
```

**9.9 Test Crate Dependencies**

Add to Cargo.toml:
```toml
[dev-dependencies]
# Core testing
rstest = "0.18"
pretty_assertions = "1.4"

# Mocking
mockall = "0.12"
wiremock = "0.5"

# CLI testing
assert_cmd = "2.0"
assert_fs = "1.0"
predicates = "3.0"

# Async testing
tokio-test = "0.4"
test-case = "3.0"

# Containers for integration
testcontainers = "0.15"

# Benchmarking
criterion = { version = "0.5", features = ["html_reports"] }

# Fuzzing (optional)
arbitrary = { version = "1.0", features = ["derive"] }
```

---

### SECTION 10: Porting Risk Assessment

| Pattern/Feature | Risk Level | Mitigation |
|-----------------|------------|------------|
| Reflection usage | High | Redesign with enums/traits |
| CGO dependencies | High | Find pure Rust alternative or FFI |
| Dynamic dispatch | Medium | Use trait objects or enums |
| Panic/recover | Medium | Convert to Result<T, E> |
| Global state | Medium | Use dependency injection |
| Complex generics | Medium | May need type bounds adjustment |
| Build tags | Low | Cargo features |
| Struct tags | Low | Serde attributes |

---

### SECTION 10: Generated Rust Module Structure

Recommended Rust project structure based on Go analysis:

```
src/
├── main.rs           # Entry point
├── lib.rs            # Library root (if needed)
├── cli/
│   ├── mod.rs        # CLI module
│   ├── commands/     # Subcommands
│   └── args.rs       # Argument definitions
├── core/
│   ├── mod.rs        # Core business logic
│   ├── types.rs      # Domain types
│   └── error.rs      # Error types
├── tui/              # TUI components (if applicable)
│   ├── mod.rs
│   ├── app.rs        # Main app state
│   └── components/   # UI components
├── config/
│   ├── mod.rs
│   └── schema.rs     # Config schema
└── external/         # External integrations
    ├── mod.rs
    └── [service].rs
```

{previous_context}
