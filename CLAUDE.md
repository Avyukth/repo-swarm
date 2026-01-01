# Python Extreme TDD Agent Instructions (OAuth & Security Edition)

> Optimized prompt for spawning background agents with strict TDD enforcement for secure Python applications

---

## Overview

This document serves as the authority for Worker and Reviewer agents implementing Python code using Extreme TDD (Red-Yellow-Green) methodology, with emphasis on OAuth implementations and security best practices.

---

## Common Python Security Mistakes (AVOID THESE)

| Anti-Pattern | What Agents Do | Why It's Bad |
|--------------|----------------|--------------|
| `pass` / `...` in functions | Stub functions to run | Silent no-ops in production |
| Bare `except:` | Catch everything | Hides security errors |
| `eval()` / `exec()` | Dynamic code execution | Code injection vulnerability |
| Hardcoded secrets | `SECRET_KEY = "abc123"` | Credential exposure |
| `verify=False` in requests | Skip SSL verification | MITM vulnerability |
| `pickle.loads(user_input)` | Deserialize untrusted data | Remote code execution |
| `==` for secrets | String comparison | Timing attack vulnerability |
| `random` for tokens | Predictable RNG | Token prediction attacks |
| `.format()` with SQL | String interpolation | SQL injection |
| Storing plaintext passwords | No hashing | Credential theft |

---

## Master Prompt

```
Continue next task. Act sequentially: Worker → Reviewer.
```

---

## WORKER PHASE

**Source of truth:** `agents.md`

### Initial Steps

1. Pick next priority task from board
2. Review existing code for context
3. Ensure correct component/module usage per `agents.md`

---

### Extreme TDD Cycle (MANDATORY FOR EACH FUNCTION)

#### 🔴 RED (Test First)

```bash
pytest tests/test_<module>.py::<test_name> -v  # MUST FAIL
```

- Write test before implementation
- Use `pytest.raises()` for exception tests
- **Commit:** `test(red): [behavior under test]`

#### 🟡 YELLOW (Minimal Pass)

- Write MINIMAL code to pass—hardcoded values OK
- Example:
  ```python
  # RED: test expects validate_token("valid_jwt") -> {"user_id": 123}
  # YELLOW (acceptable):
  def validate_token(token: str) -> dict:
      return {"user_id": 123}  # Hardcoded! Will refactor in GREEN
  ```
- Run: `pytest` → MUST PASS
- **Commit:** `feat(yellow): [minimal impl]`

#### 🟢 GREEN (Refactor)

- Proper implementation, type hints, error handling
- Run: `pytest` → STILL PASSES
- Run: `ruff check .` → NO WARNINGS
- Run: `mypy .` → NO TYPE ERRORS
- Run: `bandit -r src/` → NO SECURITY ISSUES
- **Commit:** `refactor(green): [improvements]`

---

### Negative Test Requirements (Per Function)

```python
import pytest
from unittest.mock import patch
from myapp.auth import validate_token, TokenError

class TestValidateTokenNegative:
    def test_empty_token_raises_error(self):
        with pytest.raises(TokenError, match="Token cannot be empty"):
            validate_token("")

    def test_malformed_token_raises_error(self):
        with pytest.raises(TokenError, match="Invalid token format"):
            validate_token("not.a.valid.jwt.token")

    def test_expired_token_raises_error(self):
        expired = create_expired_token()
        with pytest.raises(TokenError, match="Token has expired"):
            validate_token(expired)

    def test_invalid_signature_raises_error(self):
        tampered = create_tampered_token()
        with pytest.raises(TokenError, match="Invalid signature"):
            validate_token(tampered)

    def test_missing_required_claims_raises_error(self):
        token = create_token_without_sub_claim()
        with pytest.raises(TokenError, match="Missing required claim"):
            validate_token(token)
```

#### Required Coverage Per Function

- [ ] Exception path tested with SPECIFIC exception type and message
- [ ] `None` input path tested
- [ ] Boundary: empty string, zero, MAX_INT, negative values
- [ ] Invalid state/input
- [ ] Security edge cases (malicious input, injection attempts)

---

### BANNED PATTERNS IN FINAL CODE

```python
# ❌ NEVER IN PRODUCTION CODE:

# Stubs
pass  # in non-abstract methods
...   # ellipsis as implementation
NotImplementedError  # unless abstract method
TODO  # in any form in code

# Dangerous error handling
except:  # bare except
except Exception:  # overly broad (use specific exceptions)
except Exception as e: pass  # swallowing errors

# Security vulnerabilities
eval(user_input)
exec(user_input)
pickle.loads(untrusted_data)
yaml.load(data)  # use yaml.safe_load()
subprocess.shell=True  # with user input
os.system(user_input)
SECRET_KEY = "hardcoded"
verify=False  # in requests/httpx
password == user_input  # use secrets.compare_digest()
random.random()  # for security tokens (use secrets module)
hashlib.md5(password)  # use bcrypt/argon2
f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection

# OAuth-specific banned patterns
token = request.args.get("token")  # tokens in URL (use headers)
storing_access_tokens_in_logs
redirect_uri_without_validation
state_parameter_missing  # CSRF in OAuth
```

---

### BANNED TEST PATTERNS

```python
# ❌ WEAK ASSERTIONS - REJECT:
assert result is not None           # What IS the value?
assert result                       # Truthy isn't specific
assert isinstance(result, dict)    # What's in the dict?
assert "error" not in result       # Implicit success check
assert response.status_code < 400  # Which exact code?

# ✅ STRONG ASSERTIONS - REQUIRED:
assert result == {"user_id": 123, "scope": "read"}
assert result.access_token == expected_token
assert response.status_code == 200
assert response.json() == {"status": "authenticated"}

# For exceptions:
with pytest.raises(SpecificError, match="exact message"):
    function_under_test()

# For complex objects:
assert result.model_dump() == expected_dict  # Pydantic
assert result.__dict__ == expected_dict
```

---

### Worker Handoff

**Output ONLY:**
```
TASK_ID: xxx | COMMIT: yyy
```

**Do NOT send completion mail.**

---

## REVIEWER PHASE (FRESH CONTEXT)

**Source of truth:** `agents.md` + git history ONLY

**Input:** Task ID + Commit ID from Worker (nothing else)

---

### 1. Verify TDD Commit Pattern

```bash
git log --oneline | head -30
# Expected pattern per feature:
# abc123 refactor(green): ...
# def456 feat(yellow): ...
# ghi789 test(red): ...
```

**Reject if:** commits don't follow red → yellow → green sequence

---

### 2. Scan for Banned Patterns

```bash
# Stubs and incomplete code
grep -rn "pass$\|^\s*\.\.\.\s*$\|NotImplementedError\|TODO\|FIXME" src/

# Dangerous error handling
grep -rn "except:\|except Exception:" src/

# Security vulnerabilities
grep -rn "eval(\|exec(\|pickle\.loads\|yaml\.load(" src/
grep -rn "shell=True\|os\.system(" src/
grep -rn "verify=False\|verify\s*=\s*False" src/
grep -rn "SECRET.*=.*['\"]" src/  # hardcoded secrets
grep -rn "random\.random\|random\.randint" src/ | grep -i "token\|secret\|key"
grep -rn "md5\|sha1" src/ | grep -i "password"

# SQL injection patterns
grep -rn "f\".*SELECT\|f\".*INSERT\|f\".*UPDATE\|f\".*DELETE" src/
grep -rn "\.format.*SELECT\|\.format.*INSERT" src/

# OAuth vulnerabilities
grep -rn "request\.args\.get.*token\|request\.query.*token" src/
grep -rn "redirect_uri" src/ | grep -v "validate\|whitelist\|allowed"
```

**Action:** Any match = immediate fix required

---

### 3. Scan for Weak Tests

```bash
grep -rn "is not None\|assert result$\|assert response$" tests/
grep -rn "isinstance.*assert\|< 400\|< 500" tests/
# Each hit must be accompanied by specific value assertion
```

**Action:** Replace weak assertions with strong ones

---

### 4. Verify Negative Coverage

```bash
pytest --collect-only 2>&1 | grep -E "test_.*invalid|test_.*error|test_.*empty|test_.*expired|test_.*unauthorized|test_.*forbidden"
# Must exist for each new public function
```

**Action:** Add missing negative tests

---

### 5. Security-Specific Scans

```bash
# Run bandit security linter
bandit -r src/ -f json -o bandit_report.json
cat bandit_report.json | python -c "import json,sys; r=json.load(sys.stdin); exit(1 if r['results'] else 0)"

# Run safety for dependency vulnerabilities
safety check --json

# Check for secrets in code
detect-secrets scan src/
```

**Action:** All security scans must pass clean

---

### 6. Verify Component/Module Compliance

Cross-reference implementation against `agents.md`:
- [ ] Correct modules used
- [ ] API interfaces match spec
- [ ] No unauthorized dependencies
- [ ] Security middleware properly applied

---

### 7. Full Validation Suite

```bash
pytest --cov=src --cov-fail-under=80
ruff check .
mypy .
bandit -r src/
```

**All must pass with zero warnings.**

---

### On ANY Gap Found

1. **Fix immediately** (do not defer to Worker)
2. **Commit:** `fix(review): [description]`
3. **Re-run all checks** from step 1

---

### Completion Mail (MANDATORY)

Send ONLY after ALL checks pass.

**Required contents:**
- Task ID
- Full commit chain (red → yellow → green → any fixes)
- Gaps found & fixed (list each)
- `pytest` summary output
- `bandit` clean confirmation
- Coverage percentage

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ PYTHON SECURE TDD CHEAT SHEET                           │
├─────────────────────────────────────────────────────────┤
│ 🔴 RED:    pytest → FAIL                                │
│ 🟡 YELLOW: hardcode OK, pytest → PASS                   │
│ 🟢 GREEN:  refactor, bandit clean, pytest → STILL PASS  │
├─────────────────────────────────────────────────────────┤
│ EVERY fn needs:                                         │
│   • Happy path test (assert x == expected)              │
│   • Exception test (pytest.raises(Specific, match=...)) │
│   • None/empty test                                     │
│   • Security edge case test                             │
├─────────────────────────────────────────────────────────┤
│ BANNED: pass  eval()  except:  verify=False  random()   │
│ USE:    secrets.token_urlsafe()  bcrypt  parameterized  │
└─────────────────────────────────────────────────────────┘
```

---

## Commit Message Format

```
# TDD Cycle Commits
test(red): add failing test for OAuth token validation
feat(yellow): minimal impl for token validation (hardcoded)
refactor(green): proper JWT validation with signature verification

# Review Fix Commits  
fix(review): replace bare except with specific TokenExpiredError
fix(review): add missing test for expired token handling
fix(review): use secrets.compare_digest for token comparison
```

---

## Example: Complete TDD Cycle

### Feature: `validate_oauth_token(token: str) -> TokenPayload`

#### 🔴 RED Commit

```python
# tests/test_oauth.py
import pytest
from datetime import datetime, timedelta, UTC
from myapp.oauth import validate_oauth_token, TokenPayload, TokenError
from myapp.testing import create_test_token

class TestValidateOAuthToken:
    """Tests for OAuth token validation."""

    def test_valid_token_returns_payload(self):
        token = create_test_token(
            sub="user_123",
            scope="read write",
            exp=datetime.now(UTC) + timedelta(hours=1)
        )
        result = validate_oauth_token(token)
        assert result == TokenPayload(
            sub="user_123",
            scope=["read", "write"],
            exp=pytest.approx(datetime.now(UTC) + timedelta(hours=1), abs=5)
        )

    def test_empty_token_raises_token_error(self):
        with pytest.raises(TokenError, match="Token cannot be empty"):
            validate_oauth_token("")

    def test_none_token_raises_token_error(self):
        with pytest.raises(TokenError, match="Token cannot be empty"):
            validate_oauth_token(None)

    def test_malformed_token_raises_token_error(self):
        with pytest.raises(TokenError, match="Invalid token format"):
            validate_oauth_token("not-a-valid-jwt")

    def test_expired_token_raises_token_error(self):
        token = create_test_token(
            sub="user_123",
            exp=datetime.now(UTC) - timedelta(hours=1)
        )
        with pytest.raises(TokenError, match="Token has expired"):
            validate_oauth_token(token)

    def test_invalid_signature_raises_token_error(self):
        token = create_test_token(sub="user_123")
        tampered = token[:-5] + "XXXXX"  # Corrupt signature
        with pytest.raises(TokenError, match="Invalid token signature"):
            validate_oauth_token(tampered)

    def test_missing_sub_claim_raises_token_error(self):
        token = create_test_token(sub=None)  # Missing subject
        with pytest.raises(TokenError, match="Missing required claim: sub"):
            validate_oauth_token(token)

    def test_invalid_issuer_raises_token_error(self):
        token = create_test_token(sub="user_123", iss="https://evil.com")
        with pytest.raises(TokenError, match="Invalid token issuer"):
            validate_oauth_token(token)
```

```bash
pytest tests/test_oauth.py -v  # FAILS - validate_oauth_token doesn't exist
git commit -m "test(red): add validation tests for OAuth token"
```

#### 🟡 YELLOW Commit

```python
# src/myapp/oauth.py
from dataclasses import dataclass

class TokenError(Exception):
    """Raised when token validation fails."""
    pass

@dataclass
class TokenPayload:
    sub: str
    scope: list[str]
    exp: datetime

def validate_oauth_token(token: str | None) -> TokenPayload:
    """Validate OAuth token and return payload."""
    if not token:
        raise TokenError("Token cannot be empty")
    
    if token == "not-a-valid-jwt":
        raise TokenError("Invalid token format")
    
    # Hardcoded for yellow phase
    return TokenPayload(
        sub="user_123",
        scope=["read", "write"],
        exp=datetime.now(UTC) + timedelta(hours=1)
    )
```

```bash
pytest tests/test_oauth.py -v  # PASSES (most tests)
git commit -m "feat(yellow): minimal OAuth token validation (hardcoded)"
```

#### 🟢 GREEN Commit

```python
# src/myapp/oauth.py
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any

import jwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidSignatureError,
    InvalidTokenError,
)

from myapp.config import settings


class TokenError(Exception):
    """Raised when token validation fails."""
    pass


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """Validated OAuth token payload."""
    sub: str
    scope: list[str]
    exp: datetime
    iss: str | None = None
    aud: str | None = None


def validate_oauth_token(token: str | None) -> TokenPayload:
    """
    Validate an OAuth JWT token and return its payload.

    Args:
        token: The JWT token string to validate.

    Returns:
        TokenPayload with validated claims.

    Raises:
        TokenError: If token is invalid, expired, or malformed.
    """
    if not token or not token.strip():
        raise TokenError("Token cannot be empty")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_public_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={
                "require": ["sub", "exp", "iat"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            }
        )
    except ExpiredSignatureError as e:
        raise TokenError("Token has expired") from e
    except InvalidSignatureError as e:
        raise TokenError("Invalid token signature") from e
    except DecodeError as e:
        raise TokenError("Invalid token format") from e
    except InvalidTokenError as e:
        # Check for specific missing claims
        if "sub" not in str(e).lower() and hasattr(e, "args"):
            raise TokenError(f"Missing required claim: sub") from e
        raise TokenError(f"Invalid token: {e}") from e

    # Validate issuer explicitly for security
    if payload.get("iss") != settings.jwt_issuer:
        raise TokenError("Invalid token issuer")

    # Parse scope (space-separated string to list)
    scope_str = payload.get("scope", "")
    scope_list = scope_str.split() if scope_str else []

    return TokenPayload(
        sub=payload["sub"],
        scope=scope_list,
        exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
        iss=payload.get("iss"),
        aud=payload.get("aud"),
    )


def generate_secure_state() -> str:
    """Generate cryptographically secure state parameter for OAuth."""
    return secrets.token_urlsafe(32)


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return secrets.compare_digest(a.encode(), b.encode())
```

```bash
pytest tests/test_oauth.py -v  # STILL PASSES
ruff check src/myapp/oauth.py  # CLEAN
mypy src/myapp/oauth.py        # CLEAN
bandit src/myapp/oauth.py      # CLEAN
git commit -m "refactor(green): proper JWT validation with full security checks"
```

---

## OAuth Security Best Practices

### Required Security Headers

```python
# src/myapp/middleware/security.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Cache-Control"] = "no-store"  # For auth responses
        response.headers["Pragma"] = "no-cache"
        
        return response
```

### Secure Token Storage

```python
# ❌ NEVER:
response.set_cookie("access_token", token)  # Accessible to JS

# ✅ ALWAYS:
response.set_cookie(
    "access_token",
    token,
    httponly=True,      # Not accessible to JavaScript
    secure=True,        # HTTPS only
    samesite="strict",  # CSRF protection
    max_age=3600,       # Explicit expiry
    path="/api",        # Limit scope
)
```

### OAuth State Parameter (CSRF Protection)

```python
# tests/test_oauth_flow.py
class TestOAuthFlow:
    def test_oauth_callback_requires_state(self, client):
        """OAuth callback must validate state parameter."""
        response = client.get("/oauth/callback?code=abc123")
        assert response.status_code == 400
        assert response.json()["error"] == "missing_state"

    def test_oauth_callback_rejects_invalid_state(self, client, session):
        """OAuth callback must reject mismatched state."""
        session["oauth_state"] = "correct_state"
        response = client.get("/oauth/callback?code=abc123&state=wrong_state")
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_state"

    def test_oauth_callback_validates_state(self, client, session):
        """OAuth callback accepts matching state."""
        state = generate_secure_state()
        session["oauth_state"] = state
        response = client.get(f"/oauth/callback?code=abc123&state={state}")
        assert response.status_code == 200
```

### Redirect URI Validation

```python
# src/myapp/oauth/validation.py
from urllib.parse import urlparse

ALLOWED_REDIRECT_DOMAINS = frozenset({
    "myapp.com",
    "www.myapp.com",
    "localhost",  # Only in development
})

def validate_redirect_uri(uri: str) -> bool:
    """
    Validate redirect URI against whitelist.
    
    Prevents open redirect vulnerabilities in OAuth flow.
    """
    if not uri:
        return False
    
    try:
        parsed = urlparse(uri)
    except ValueError:
        return False
    
    # Must be HTTPS in production (allow HTTP for localhost)
    if parsed.hostname != "localhost" and parsed.scheme != "https":
        return False
    
    # Domain must be in whitelist
    if parsed.hostname not in ALLOWED_REDIRECT_DOMAINS:
        return False
    
    # No fragments allowed (prevents token leakage)
    if parsed.fragment:
        return False
    
    return True
```

---

## Async Function Testing

```python
import pytest
from httpx import AsyncClient
from myapp.oauth import refresh_token_async, TokenError

class TestAsyncOAuth:
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, mock_oauth_server):
        result = await refresh_token_async("valid_refresh_token")
        assert result.access_token is not None
        assert result.expires_in == 3600

    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, mock_oauth_server):
        with pytest.raises(TokenError, match="Refresh token expired"):
            await refresh_token_async("expired_refresh_token")

    @pytest.mark.asyncio
    async def test_refresh_token_revoked(self, mock_oauth_server):
        with pytest.raises(TokenError, match="Refresh token revoked"):
            await refresh_token_async("revoked_refresh_token")

    @pytest.mark.asyncio
    async def test_refresh_token_network_error(self, mock_oauth_server_unavailable):
        with pytest.raises(TokenError, match="OAuth server unavailable"):
            await refresh_token_async("valid_refresh_token")
```

---

## Password & Secret Handling

```python
# src/myapp/auth/password.py
import bcrypt
import secrets

def hash_password(password: str) -> str:
    """Hash password using bcrypt with secure work factor."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash in constant time."""
    return bcrypt.checkpw(password.encode(), hashed.encode())

def generate_api_key() -> str:
    """Generate cryptographically secure API key."""
    return secrets.token_urlsafe(32)


# tests/test_password.py
class TestPasswordSecurity:
    def test_hash_password_returns_bcrypt_hash(self):
        hashed = hash_password("secure_password_123")
        assert hashed.startswith("$2b$")  # bcrypt identifier
        assert len(hashed) == 60  # bcrypt hash length

    def test_verify_correct_password(self):
        hashed = hash_password("my_password")
        assert verify_password("my_password", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("my_password")
        assert verify_password("wrong_password", hashed) is False

    def test_same_password_different_hashes(self):
        """Each hash should be unique due to random salt."""
        hash1 = hash_password("same_password")
        hash2 = hash_password("same_password")
        assert hash1 != hash2

    def test_api_key_is_url_safe(self):
        key = generate_api_key()
        assert all(c.isalnum() or c in "-_" for c in key)

    def test_api_key_has_sufficient_entropy(self):
        key = generate_api_key()
        assert len(key) >= 32  # At least 256 bits of entropy
```

---

## Configuration & Secrets Management

```python
# src/myapp/config.py
from pydantic_settings import BaseSettings
from pydantic import SecretStr, field_validator

class Settings(BaseSettings):
    """Application settings with secure secret handling."""
    
    # Secrets - never logged or exposed
    jwt_secret_key: SecretStr
    database_url: SecretStr
    oauth_client_secret: SecretStr
    
    # Public config
    jwt_algorithm: str = "RS256"
    jwt_issuer: str = "https://auth.myapp.com"
    jwt_audience: str = "myapp-api"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # Security settings
    allowed_hosts: list[str] = ["myapp.com"]
    cors_origins: list[str] = []
    
    @field_validator("jwt_algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Ensure only secure algorithms are used."""
        secure_algorithms = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}
        if v not in secure_algorithms:
            raise ValueError(f"Insecure algorithm: {v}. Use one of {secure_algorithms}")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Usage - secret value is protected
settings = Settings()
# print(settings.jwt_secret_key)  # Outputs: SecretStr('**********')
# settings.jwt_secret_key.get_secret_value()  # Only way to access actual value
```

---

## Rate Limiting Tests

```python
# tests/test_rate_limiting.py
import pytest
from freezegun import freeze_time

class TestOAuthRateLimiting:
    def test_login_rate_limit_blocks_after_threshold(self, client):
        """Prevent brute force attacks on login."""
        for _ in range(5):
            client.post("/auth/login", json={"email": "user@test.com", "password": "wrong"})
        
        response = client.post("/auth/login", json={"email": "user@test.com", "password": "wrong"})
        assert response.status_code == 429
        assert response.json()["error"] == "rate_limit_exceeded"

    def test_token_refresh_rate_limit(self, client, valid_refresh_token):
        """Prevent token refresh abuse."""
        for _ in range(10):
            client.post("/auth/refresh", json={"refresh_token": valid_refresh_token})
        
        response = client.post("/auth/refresh", json={"refresh_token": valid_refresh_token})
        assert response.status_code == 429

    @freeze_time("2024-01-01 12:00:00")
    def test_rate_limit_resets_after_window(self, client):
        """Rate limit should reset after time window."""
        # Exhaust rate limit
        for _ in range(5):
            client.post("/auth/login", json={"email": "user@test.com", "password": "wrong"})
        
        # Move time forward
        with freeze_time("2024-01-01 12:15:00"):
            response = client.post("/auth/login", json={"email": "user@test.com", "password": "wrong"})
            assert response.status_code != 429
```

---

## Final Checklist Before Handoff

### Worker Checklist
- [ ] All functions have RED → YELLOW → GREEN commits
- [ ] Each function has ≥1 negative test
- [ ] No banned patterns in code
- [ ] No weak assertions in tests
- [ ] `pytest` passes with ≥80% coverage
- [ ] `ruff check .` clean
- [ ] `mypy .` clean  
- [ ] `bandit -r src/` clean
- [ ] No hardcoded secrets (use `detect-secrets`)

### Reviewer Checklist
- [ ] Commit history shows proper TDD sequence
- [ ] `grep` scans return no banned patterns
- [ ] Negative test coverage verified
- [ ] Security scans pass (bandit, safety)
- [ ] OAuth flow includes state parameter
- [ ] Redirect URIs are validated
- [ ] Tokens use secure algorithms (RS256, ES256)
- [ ] Passwords use bcrypt/argon2
- [ ] Secrets use `SecretStr` or env vars
- [ ] All gaps fixed and committed
- [ ] Full validation suite passes
- [ ] Completion mail sent with all required info

---

## Security Testing Tools

```bash
# Install security tools
pip install bandit safety detect-secrets pytest-cov ruff mypy

# Run security audit
bandit -r src/ -ll -ii                    # Security linting
safety check                                # Dependency vulnerabilities
detect-secrets scan src/                   # Hardcoded secrets
pytest --cov=src --cov-fail-under=80      # Coverage

# Full security pipeline
bandit -r src/ && safety check && detect-secrets scan src/ && pytest
```
