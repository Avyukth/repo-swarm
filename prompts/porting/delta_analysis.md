version=1
## Repository Structure and Files

{repo_structure}
---

## Git Diff Context (Changes Since Last Port)

{git_diff_context}
---

## Delta Feature Analysis for Incremental Porting

Analyze the NEW code changes introduced since the last porting baseline.

### Focus Areas

**1. New Files Added**
For each new file:
- File path
- Purpose
- Key exports (functions, types, classes)
- Dependencies on existing code

**2. Modified Files**
For each modified file:
- What functionality was added/changed?
- Does this affect already-ported Rust code?
- Breaking changes to existing interfaces?

**3. New Dependencies**
| Package | Version | Purpose | Rust Equivalent |
|---------|---------|---------|-----------------|
| ... | ... | ... | ... |

**4. New Types/Interfaces**
Document new TypeScript types that need Rust structs.

**5. New API Endpoints**
| Method | Path | Handler | TS Location |
|--------|------|---------|-------------|
| ... | ... | ... | ... |

**6. New Business Logic**
- New services or service methods
- New validation rules
- New workflows

**7. Database Changes**
- New migrations
- Schema changes
- New queries

---

### Porting Impact Assessment

**High Impact (Requires new Rust modules)**
- [ ] ...

**Medium Impact (Extends existing Rust code)**
- [ ] ...

**Low Impact (Minor additions)**
- [ ] ...

---

### Recommended Porting Tasks

Generate actionable tasks in dependency order:

1. **Task**: [description]
   - TS source: `src/...`
   - Rust target: `crates/...`
   - Complexity: Low/Medium/High
   - Depends on: [other tasks]

{previous_context}
