version=1
## TypeScript Repository Structure

{repo_structure}
---

## Rust Repository Structure

{rust_repo_structure}
---

## Feature Parity Check

Compare the TypeScript source with the Rust port to identify gaps.

### Analysis

1. **Module Parity**
   | TS Module | Rust Equivalent | Status |
   |-----------|-----------------|--------|
   | src/users | crates/users | ✅ Complete |
   | src/auth | crates/auth | ⚠️ Partial |
   | src/payments | - | ❌ Missing |

2. **API Endpoint Parity**
   | TS Endpoint | Rust Endpoint | Status |
   |-------------|---------------|--------|
   | POST /users | POST /users | ✅ |
   | GET /users/:id | GET /users/:id | ✅ |
   | DELETE /users/:id | - | ❌ Missing |

3. **Feature Gaps**
   List features present in TypeScript but missing in Rust:
   - [ ] Feature A - complexity: Medium
   - [ ] Feature B - complexity: High
   - [ ] Feature C - complexity: Low

4. **Test Coverage Comparison**
   - TS test count: X
   - Rust test count: Y
   - Missing test scenarios: [list]

5. **Porting Backlog (Priority Order)**

   | Priority | Feature | TS Location | Estimated Effort |
   |----------|---------|-------------|------------------|
   | P0 | Critical feature | src/... | ... |
   | P1 | Important feature | src/... | ... |
   | P2 | Nice to have | src/... | ... |

{previous_context}
