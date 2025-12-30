# Mouchak Mail Agent Communication

> Mouchak Mail (`am`) is a drop-in replacement for MCP Agent Mail, providing multi-agent coordination via messaging, file reservations, and thread-based workflows. Agents communicate through the MCP server at `http://127.0.0.1:8765/mcp/` using JSON-RPC calls for inbox/outbox, file locks, and cross-agent handoffs.

Key concepts:

- **Projects**: Workspaces identified by slug (e.g., `repo-swarm`) containing agents, messages, file reservations
- **Agents**: AI identities registered per project with program/model metadata (e.g., `claude-code/opus-4`)
- **Threads**: Conversation chains identified by thread_id (e.g., `PORT-user-service`, `FEAT-123`)
- **File Reservations**: Exclusive/shared locks on file patterns with TTL expiry
- **MCP Endpoint**: `http://127.0.0.1:8765/mcp/` for all tool calls via JSON-RPC

## Multi-Agent Setup (Without NTM)

Multiple AI agents can coordinate using Mouchak Mail directly:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TERMINAL 1                                        │
│  $ cd /project && claude                                                    │
│  Agent: PortingAgent (claude-code/opus-4)                                   │
│  Task: Port TypeScript services to Rust                                     │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │  register_agent() → file_reservation_paths() → work → send_message()
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MOUCHAK MAIL SERVER                                 │
│                      http://127.0.0.1:8765/mcp                              │
│  ┌────────────────┬────────────────┬────────────────┐                      │
│  │    Messages    │  Reservations  │    Threads     │                      │
│  │  (inbox/outbox)│  (file locks)  │ (conversations)│                      │
│  └────────────────┴────────────────┴────────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
        ▲
        │  register_agent() → list_inbox() → work → reply_message()
        │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TERMINAL 2                                        │
│  $ cd /project && claude                                                    │
│  Agent: ReviewAgent (claude-code/sonnet-4)                                  │
│  Task: Review ported code, suggest improvements                             │
└─────────────────────────────────────────────────────────────────────────────┘
        ▲
        │  register_agent() → list_inbox() → work → send_message()
        │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TERMINAL 3                                        │
│  $ cd /project && codex                                                     │
│  Agent: TestAgent (codex/gpt-4)                                             │
│  Task: Write tests for ported code                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Agent Startup Sequence

Each agent (in separate terminal/process) executes on startup:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. ENSURE PROJECT                                                          │
│     ensure_project(human_key="my-project", slug="my-project")               │
│     → Creates project if not exists, returns project_id                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  2. REGISTER SELF                                                           │
│     register_agent(project_slug, name="MyAgent", program="claude-code",     │
│                    model="opus-4", task_description="...")                  │
│     → Creates agent identity, returns agent_id                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  3. CHECK INBOX                                                             │
│     list_inbox(project_slug, agent_name="MyAgent", limit=10)                │
│     → Fetches pending messages from other agents                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  4. RESERVE FILES (before editing)                                          │
│     file_reservation_paths(project_slug, agent_name, paths=["src/**"],      │
│                            exclusive=true, ttl_seconds=3600)                │
│     → Locks files, prevents conflicts with other agents                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

Or use macro for steps 1-4 in single call:

```json
{
  "name": "macro_start_session",
  "arguments": {
    "human_key": "my-project",
    "program": "claude-code",
    "model": "opus-4",
    "agent_name": "PortingAgent",
    "file_reservation_paths": ["src/services/**", "crates/**"],
    "file_reservation_ttl_seconds": 3600,
    "inbox_limit": 10
  }
}
```

## Complete Workflow (Start to Finish)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PROJECT WORKSPACE                              │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐             │
│  │ PortingAgent │ ReviewAgent  │ TestAgent    │ DocsAgent    │             │
│  │ (Terminal 1) │ (Terminal 2) │ (Terminal 3) │ (Terminal 4) │             │
│  │ claude/opus  │ claude/sonnet│ codex/gpt-4  │ gemini/pro   │             │
│  └──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘             │
│         │              │              │              │                      │
│         │      All communicate via Mouchak Mail      │                      │
│         └──────────────┼──────────────┼──────────────┘                      │
│                        ▼              ▼                                     │
│                ┌──────────────────────────────┐                             │
│                │       MOUCHAK MAIL MCP       │                             │
│                │   http://127.0.0.1:8765/mcp  │                             │
│                │  ┌────────┬────────┬──────┐  │                             │
│                │  │ Inbox  │ Files  │Thread│  │                             │
│                │  │Messages│ Locks  │ IDs  │  │                             │
│                │  └────────┴────────┴──────┘  │                             │
│                └──────────────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────────┘

PHASE 1: Setup (each agent)
─────────────────────────────
  ensure_project() → register_agent() → list_inbox()

PHASE 2: Work (parallel)
─────────────────────────────
  PortingAgent: file_reservation_paths(["src/services/**"]) → port code
  ReviewAgent:  list_inbox() → wait for work
  TestAgent:    list_inbox() → wait for work
  DocsAgent:    list_inbox() → wait for work

PHASE 3: Handoff
─────────────────────────────
  PortingAgent: send_message(to="ReviewAgent", thread="PORT-user-svc")
                release_reservation()
  ReviewAgent:  list_inbox() → review → send_message(to="TestAgent")
  TestAgent:    list_inbox() → write tests → send_message(to="DocsAgent")
  DocsAgent:    list_inbox() → update docs → send_message(to="PortingAgent")

PHASE 4: Complete
─────────────────────────────
  All agents: acknowledge_message() → release_reservation()
```

## Message Flow Between Agents

```
PortingAgent                Mouchak Mail                ReviewAgent
   │                            │                            │
   │──send_message(to=Review)──▶│                            │
   │   thread="PORT-user-svc"   │                            │
   │   "[COMPLETION] Ported"    │                            │
   │                            │──────────────────────────▶ │
   │                            │        list_inbox()        │
   │                            │                            │
   │                            │◀─────reply_message()───────│
   │                            │   "[APPROVED] LGTM"        │
   │◀───────list_inbox()────────│                            │
   │                            │                            │
   │──acknowledge_message()────▶│                            │
```

## File Reservation (Conflict Prevention)

```
PortingAgent                Mouchak Mail                TestAgent
   │                            │                            │
   │──file_reservation_paths()─▶│                            │
   │   paths=["src/user/**"]    │                            │
   │   exclusive=true           │                            │
   │◀────── granted (id:123) ───│                            │
   │                            │                            │
   │  (editing files...)        │◀──file_reservation_paths()─│
   │                            │   paths=["src/user/**"]    │
   │                            │────CONFLICT: held by       │
   │                            │    PortingAgent ──────────▶│
   │                            │                            │
   │──release_reservation(123)─▶│                            │
   │◀────── released ───────────│                            │
   │                            │──────── granted ──────────▶│
```

## Example: 3-Agent Porting Pipeline

**Terminal 1 - PortingAgent:**
```bash
cd /project && claude
# Agent registers, reserves src/services/**, ports code
# Sends: "[COMPLETION] Ported user service" to ReviewAgent
```

**Terminal 2 - ReviewAgent:**
```bash
cd /project && claude
# Agent registers, checks inbox, sees message from PortingAgent
# Reviews code, sends: "[APPROVED] LGTM, minor suggestions" to TestAgent
```

**Terminal 3 - TestAgent:**
```bash
cd /project && codex
# Agent registers, checks inbox, sees approval
# Reserves tests/**, writes tests
# Sends: "[COMPLETION] Tests passing" to PortingAgent
```

## MCP API Format

All tools called via JSON-RPC at `http://127.0.0.1:8765/mcp`:

```bash
curl -X POST http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"<tool>","arguments":{...}},"id":1}'
```

## Core Tools

| Tool | Purpose | Key Arguments |
|------|---------|---------------|
| `ensure_project` | Create/get project | `human_key`, `slug` |
| `register_agent` | Register agent identity | `project_slug`, `name`, `program`, `model` |
| `list_inbox` | Check messages | `project_slug`, `agent_name`, `limit` |
| `send_message` | Send to agent(s) | `project_slug`, `sender_name`, `to`, `subject`, `body_md`, `thread_id` |
| `reply_message` | Reply to message | `project_slug`, `sender_name`, `message_id`, `body_md` |
| `acknowledge_message` | Mark handled | `project_slug`, `agent_name`, `message_id` |
| `file_reservation_paths` | Reserve files | `project_slug`, `agent_name`, `paths[]`, `exclusive`, `ttl_seconds` |
| `list_reservations` | View locks | `project_slug`, `all_agents` |
| `release_reservation` | Release by ID | `reservation_id` |
| `list_threads` | List conversations | `project_slug`, `limit` |
| `get_thread` | Get thread messages | `project_slug`, `thread_id` |
| `summarize_thread` | AI summary | `project_slug`, `thread_id` |

## Macros (Multi-Step)

| Macro | Purpose | Key Arguments |
|-------|---------|---------------|
| `macro_start_session` | Setup + reserve + inbox | `human_key`, `program`, `model`, `file_reservation_paths[]` |
| `macro_prepare_thread` | Align with thread | `project_key`, `thread_id`, `program`, `model` |
| `macro_file_reservation_cycle` | Reserve with auto-release | `project_key`, `agent_name`, `paths[]`, `auto_release` |
| `macro_contact_handshake` | Agent-to-agent contact | `project_key`, `requester`, `target`, `auto_accept` |

## CLI Commands

```bash
am health                          # Server health check
am serve                           # Start server (port 8765)
am mail status                     # Project/agent status
am guard status                    # Pre-commit guard status
am products ensure <uid> --name    # Create product (multi-repo)
am products link <uid> .           # Link repo to product
am products status <uid>           # Product status
am products inbox <uid> <agent>    # Product-wide inbox
am tools                           # List all 74 tools
am schema                          # Export JSON schemas
```

## Environment Variables

```bash
AGENT_NAME=MyAgent                    # Default agent name
MOUCHAK_MAIL_GUARD_MODE=enforce       # Guard mode: enforce|warn|disabled
WORKTREES_ENABLED=1                   # Enable worktree support
PROJECT_IDENTITY_MODE=false           # Project-based identity
```

## Error Codes

| Code | Meaning | Resolution |
|------|---------|------------|
| `AGENT_NOT_FOUND` | Agent not registered | Call `register_agent` first |
| `FILE_RESERVATION_CONFLICT` | Files already locked | Wait for expiry or use non-exclusive |
| `PROJECT_NOT_FOUND` | Project doesn't exist | Call `ensure_project` first |
| `MESSAGE_NOT_FOUND` | Invalid message_id | Check with `list_inbox` |

## Thread ID Conventions

| Pattern | Usage |
|---------|-------|
| `PORT-{feature}` | Porting tasks |
| `FEAT-{id}` | Feature development |
| `BUG-{id}` | Bug fixes |
| `REVIEW-{id}` | Code reviews |
| `TASK-{hash}` | Generic tasks |

## Message Prefixes

| Prefix | Meaning |
|--------|---------|
| `[COMPLETION]` | Task finished, ready for review |
| `[REVIEWING]` | Review in progress |
| `[APPROVED]` | Review passed |
| `[CHANGES_REQUESTED]` | Needs revision |
| `[BLOCKED]` | Waiting on dependency |

## Products (Multi-Repo)

Products link multiple projects for unified messaging across repos:

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRODUCT: MyApp                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  frontend   │  │  backend    │  │  shared     │             │
│  │  (project)  │  │  (project)  │  │  (project)  │             │
│  │  Agent: UI  │  │  Agent: API │  │  Agent: Lib │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                         │                                       │
│              product_inbox() → aggregated messages              │
│              search_messages_product() → cross-repo search      │
└─────────────────────────────────────────────────────────────────┘
```

## Supported Agent Types

| Program | Model Examples | Use Case |
|---------|----------------|----------|
| `claude-code` | `opus-4`, `sonnet-4` | General coding, porting |
| `codex` | `gpt-4`, `gpt-4-turbo` | Code generation, tests |
| `gemini` | `pro`, `ultra` | Analysis, documentation |
| `cursor` | `claude`, `gpt-4` | IDE-integrated agents |
| `aider` | `claude`, `gpt-4` | Git-aware coding |
| `continue` | various | VS Code agents |

## Quick Start (Single Agent)

```bash
# 1. Start server (once)
am serve &

# 2. In your Claude Code session:
# - ensure_project(human_key="my-project")
# - register_agent(project_slug="my-project", name="MyAgent", program="claude-code", model="opus-4")
# - file_reservation_paths(project_slug="my-project", agent_name="MyAgent", paths=["src/**"], exclusive=true)
# - ... do work ...
# - release_reservation(reservation_id=123)
```

## Quick Start (Multi-Agent)

```bash
# Terminal 0: Start server
am serve

# Terminal 1: Agent A
cd /project && claude
# "Register as PortingAgent, reserve src/services/**, port the user service"

# Terminal 2: Agent B
cd /project && claude
# "Register as ReviewAgent, check inbox, review code from PortingAgent"

# Terminal 3: Agent C
cd /project && codex
# "Register as TestAgent, check inbox, write tests when ReviewAgent approves"
```

## Manual Multi-Window Agent Setup

Step-by-step guide for creating multiple agent sessions manually:

### Step 0: Start Mouchak Mail Server

```bash
# Terminal 0 (Server)
am serve
# Server running at http://127.0.0.1:8765
# Keep this terminal open
```

### Step 1: Create Project (once)

```bash
# Any terminal - create shared project
curl -X POST http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "ensure_project",
      "arguments": {"human_key": "my-project", "slug": "my-project"}
    },
    "id": 1
  }'
```

### Step 2: Open Agent Windows

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WINDOW LAYOUT (tmux, iTerm2, or multiple terminals)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                  │
│  │  Terminal 1             │  │  Terminal 2             │                  │
│  │  $ cd /project          │  │  $ cd /project          │                  │
│  │  $ claude               │  │  $ claude               │                  │
│  │                         │  │                         │                  │
│  │  Agent: PortingAgent    │  │  Agent: ReviewAgent     │                  │
│  │  Role: Port TS to Rust  │  │  Role: Review code      │                  │
│  └─────────────────────────┘  └─────────────────────────┘                  │
│                                                                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                  │
│  │  Terminal 3             │  │  Terminal 4             │                  │
│  │  $ cd /project          │  │  $ cd /project          │                  │
│  │  $ codex                │  │  $ claude               │                  │
│  │                         │  │                         │                  │
│  │  Agent: TestAgent       │  │  Agent: DocsAgent       │                  │
│  │  Role: Write tests      │  │  Role: Update docs      │                  │
│  └─────────────────────────┘  └─────────────────────────┘                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 3: Agent Registration (each terminal)

**Terminal 1 - PortingAgent:**
```bash
cd /project && claude
```
Then tell Claude:
```
Register with Mouchak Mail as PortingAgent:
- ensure_project(human_key="my-project")
- register_agent(project_slug="my-project", name="PortingAgent",
                 program="claude-code", model="opus-4",
                 task_description="Port TypeScript services to Rust")
- file_reservation_paths(project_slug="my-project", agent_name="PortingAgent",
                         paths=["src/services/**"], exclusive=true, ttl_seconds=3600)
```

**Terminal 2 - ReviewAgent:**
```bash
cd /project && claude
```
Then tell Claude:
```
Register with Mouchak Mail as ReviewAgent:
- ensure_project(human_key="my-project")
- register_agent(project_slug="my-project", name="ReviewAgent",
                 program="claude-code", model="sonnet-4",
                 task_description="Review ported code for quality and correctness")
- list_inbox(project_slug="my-project", agent_name="ReviewAgent", limit=10)
```

**Terminal 3 - TestAgent:**
```bash
cd /project && codex
```
Then tell Codex:
```
Register with Mouchak Mail as TestAgent:
- ensure_project(human_key="my-project")
- register_agent(project_slug="my-project", name="TestAgent",
                 program="codex", model="gpt-4",
                 task_description="Write comprehensive tests for ported code")
- list_inbox(project_slug="my-project", agent_name="TestAgent", limit=10)
```

**Terminal 4 - DocsAgent:**
```bash
cd /project && claude
```
Then tell Claude:
```
Register with Mouchak Mail as DocsAgent:
- ensure_project(human_key="my-project")
- register_agent(project_slug="my-project", name="DocsAgent",
                 program="claude-code", model="haiku-3",
                 task_description="Update documentation for ported code")
- list_inbox(project_slug="my-project", agent_name="DocsAgent", limit=10)
```

### Step 4: Work & Handoff Flow

```
TIME    TERMINAL 1           TERMINAL 2           TERMINAL 3           TERMINAL 4
─────   ──────────────────   ──────────────────   ──────────────────   ──────────────────
t0      [reserves files]     [waiting inbox]      [waiting inbox]      [waiting inbox]
        [porting code...]

t1      [send_message
         to=ReviewAgent
         "Ported user svc"]  [list_inbox]
        [release_reservation] [sees message]
                             [reviewing...]

t2                           [send_message
                              to=TestAgent
                              "APPROVED"]         [list_inbox]
                                                  [sees approval]
                                                  [reserves tests/**]
                                                  [writing tests...]

t3                                                [send_message
                                                   to=DocsAgent
                                                   "Tests done"]       [list_inbox]
                                                  [release_reservation] [sees message]
                                                                       [updating docs...]

t4                                                                     [send_message
                                                                        to=PortingAgent
                                                                        "Docs updated"]
        [list_inbox]
        [sees completion]
        [acknowledge all]
```

### Step 5: Monitor Status

From any terminal, check agent mail status:

```bash
# Check all agents in project
am mail status

# Check specific project reservations
curl -X POST http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "list_reservations",
      "arguments": {"project_slug": "my-project", "all_agents": true}
    },
    "id": 1
  }'

# Check threads
curl -X POST http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "list_threads",
      "arguments": {"project_slug": "my-project", "limit": 10}
    },
    "id": 1
  }'
```

## Using tmux for Multi-Agent Sessions

```bash
# Create new tmux session with 4 panes
tmux new-session -s agents -n work

# Split into 4 panes (2x2 grid)
tmux split-window -h
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v

# Name panes (optional, for reference)
# Pane 0: PortingAgent
# Pane 1: ReviewAgent
# Pane 2: TestAgent
# Pane 3: DocsAgent

# Send commands to each pane
tmux send-keys -t agents:0.0 'cd /project && claude' C-m
tmux send-keys -t agents:0.1 'cd /project && claude' C-m
tmux send-keys -t agents:0.2 'cd /project && codex' C-m
tmux send-keys -t agents:0.3 'cd /project && claude' C-m
```

## Using iTerm2 for Multi-Agent Sessions

```
Cmd+D        → Split vertically
Cmd+Shift+D  → Split horizontally
Cmd+[/]      → Navigate between panes
```

Create 4 panes, then in each:
```bash
cd /project && claude  # or codex, aider, etc.
```
