# Porting Prompts: TypeScript → Rust Migration

Specialized prompts for incremental feature porting from TypeScript to Rust.

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INCREMENTAL PORTING WORKFLOW                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SESSION 1: Analyze TypeScript Source                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  typescript_source_analysis.md                                   │   │
│  │  → Comprehensive TS codebase documentation                       │   │
│  │  → Output: ts_source.arch.md                                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  rust_mapping.md                                                 │   │
│  │  → Type/pattern translations                                     │   │
│  │  → Uses context from typescript_source_analysis                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SESSION 2: Analyze Rust Target                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  rust_target_analysis.md                                         │   │
│  │  → Comprehensive Rust codebase documentation                     │   │
│  │  → What's already ported, patterns established                   │   │
│  │  → Output: rust_target.arch.md                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SESSION 3: Gap Analysis (Optional - use Claude Code directly)         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  delta_analysis.md                                               │   │
│  │  → Analyze git diff from PORTED_COMMIT to HEAD                   │   │
│  │  → Identify new features to port                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  parity_check.md                                                 │   │
│  │  → Compare ts_source.arch.md with rust_target.arch.md            │   │
│  │  → Generate porting backlog                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Usage

### Step 1: Analyze TypeScript Source

```bash
# Add TS repo to repos.json
# prompts/repos.json
{
  "repositories": {
    "my-ts-project": {
      "url": "https://github.com/org/ts-project",
      "type": "porting",
      "description": "TypeScript source for porting"
    }
  }
}

# Run analysis
mise investigate-one https://github.com/org/ts-project porting
```

Output: `ts_source.arch.md` with:
- Complete architecture blueprint
- Type mappings to Rust
- Dependency equivalents
- Porting task list

### Step 2: Analyze Rust Target

```bash
# Add Rust repo to repos.json
{
  "repositories": {
    "my-rust-port": {
      "url": "https://github.com/org/rust-port",
      "type": "porting",
      "description": "Rust target (partial port)"
    }
  }
}

# Run analysis (use rust_target_analysis prompt specifically)
mise investigate-one https://github.com/org/rust-port porting
```

Output: `rust_target.arch.md` with:
- Current porting status
- Established patterns
- Technical debt
- Ready-to-port features

### Step 3: Delta Analysis (for incremental ports)

Before running delta analysis, extract git changes:

```bash
cd /path/to/ts-repo

# Create context file for delta_analysis
cat > delta_context.md << 'EOF'
## Changes Since Last Port

### Changed Files
$(git diff --name-only PORTED_COMMIT..HEAD)

### Commit History
$(git log --oneline PORTED_COMMIT..HEAD)

### Statistics
$(git diff --stat PORTED_COMMIT..HEAD)
EOF
```

Then run delta_analysis with this context.

### Step 4: Feature Parity Check

Compare both `.arch.md` files to identify gaps:

```bash
# Manual comparison or use Claude Code:
# "Compare ts_source.arch.md with rust_target.arch.md and identify missing features"
```

## Prompts Reference

| Prompt | Purpose | Run On |
|--------|---------|--------|
| `typescript_source_analysis.md` | Full TS codebase analysis | TypeScript repo |
| `rust_mapping.md` | TS→Rust translations | TypeScript repo (uses TS analysis context) |
| `rust_target_analysis.md` | Full Rust codebase analysis | Rust repo |
| `delta_analysis.md` | Changes since baseline | TypeScript repo (with git diff) |
| `parity_check.md` | Gap identification | Both repos (comparison) |

## Outputs

### ts_source.arch.md
- Project overview & stack
- Architecture patterns
- Type definitions (with Rust mappings)
- API surface
- Business logic
- Auth/authz
- Porting complexity assessment

### rust_target.arch.md
- Current port status
- Established patterns (must follow)
- Module structure
- Error handling patterns
- Test coverage
- Technical debt
- Next porting tasks

## Porting Priority Matrix

When analyzing, outputs include:

| Priority | Criteria |
|----------|----------|
| P0 | Core types, shared utilities - blocks everything |
| P1 | Database layer, auth - blocks features |
| P2 | Business logic services - main features |
| P3 | API handlers - consumes services |
| P4 | Tests, docs - validates port |

## Complexity Assessment

| Level | Description | Example |
|-------|-------------|---------|
| Low | Direct 1:1 translation | Simple types, pure functions |
| Medium | Rust idiom adaptation | Error handling, Option usage |
| High | Significant redesign | Decorators, reflection, complex generics |

## Common TS → Rust Mappings

```
TypeScript              Rust
──────────────────────────────────────
string                  String / &str
number                  i32/i64/f64
boolean                 bool
null/undefined          Option<T>
any                     (needs redesign)
Promise<T>              impl Future<Output=T>
Array<T>                Vec<T>
Record<K,V>             HashMap<K,V>
interface               struct + traits
class                   struct + impl
throw                   Result<T,E>
try/catch               ? operator
?.                      .ok() / Option methods
??                      .unwrap_or()
```

## Tips

1. **Start with types** - Port domain types first, they're dependencies for everything
2. **Follow established patterns** - rust_target_analysis shows what patterns exist
3. **Don't port tests first** - Port implementation, then write Rust-idiomatic tests
4. **Watch for `any`** - TypeScript `any` usage indicates redesign needed
5. **Check async boundaries** - TS async might map differently in Rust
