version=1
## Repository Structure and Files

{repo_structure}
---

## TypeScript to Rust Mapping Guide

Analyze this TypeScript codebase and create detailed Rust implementation mappings.

### Type Mappings

For each TypeScript type/interface found, provide:

```
TypeScript                    →  Rust
─────────────────────────────────────────
interface User {              →  #[derive(Debug, Clone, Serialize, Deserialize)]
  id: string;                 →  pub struct User {
  name: string;               →      pub id: String,  // or Uuid
  age?: number;               →      pub name: String,
}                             →      pub age: Option<i32>,
                              →  }
```

### Async Pattern Mappings

| TypeScript Pattern | Rust Equivalent |
|-------------------|-----------------|
| `async/await` | `async fn` + tokio runtime |
| `Promise.all([])` | `tokio::join!()` or `futures::join_all()` |
| `Promise.race([])` | `tokio::select!()` |
| `setTimeout` | `tokio::time::sleep()` |
| `setInterval` | `tokio::time::interval()` |

### Error Handling Mappings

| TypeScript | Rust |
|------------|------|
| `try/catch` | `Result<T, E>` + `?` operator |
| `throw new Error()` | `return Err()` or `anyhow::bail!()` |
| `?.` optional chaining | `.ok()` or `Option` methods |
| `??` nullish coalescing | `.unwrap_or()` / `.unwrap_or_default()` |

### Framework Mappings

| TypeScript Framework | Rust Equivalent |
|---------------------|-----------------|
| Express/Fastify | Axum / Actix-web |
| Prisma/TypeORM | SQLx / Diesel / SeaORM |
| Zod | serde + validator crate |
| Jest/Vitest | cargo test + rstest |
| Winston/Pino | tracing + tracing-subscriber |

### Specific Code Translations Needed

For each significant function/class in this codebase:

1. **Original TypeScript**
   - File path
   - Function signature
   - Key logic

2. **Rust Translation**
   - Suggested module path
   - Rust function signature
   - Idiomatic Rust implementation notes

3. **Gotchas**
   - Ownership considerations
   - Lifetime annotations needed
   - Trait implementations required

{previous_context}
