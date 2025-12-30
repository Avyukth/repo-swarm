#!/usr/bin/env bash
# Mouchak Mail (am) Workflow Demo
# Demonstrates the complete multi-agent coordination flow
#
# Usage: ./scripts/am-workflow-demo.sh [project_slug] [agent_name] [work_duration]
#
# Prerequisites:
#   - am server running (am serve or am service start)
#   - curl and jq installed

set -euo pipefail

# Configuration
PROJECT_SLUG="${1:-repo-swarm}"
AGENT_NAME="${2:-DemoAgent}"
REVIEWER_NAME="${AGENT_NAME}-Reviewer"
WORK_DURATION="${3:-30}"
MCP_URL="http://localhost:8765/mcp"
HEADERS=(-H "Content-Type: application/json" -H "Accept: application/json, text/event-stream")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_step() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# MCP tool call helper
mcp_call() {
    local tool_name="$1"
    local arguments="$2"
    local id="${3:-1}"

    curl -s -X POST "$MCP_URL" "${HEADERS[@]}" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"$tool_name\",\"arguments\":$arguments},\"id\":$id}"
}

# Check server health
check_health() {
    log_step "Checking Server Health"
    local health
    health=$(curl -s "$MCP_URL/health" 2>/dev/null || echo '{"status":"error"}')

    if echo "$health" | grep -q '"healthy"'; then
        log_success "Server is healthy"
        return 0
    else
        log_error "Server not responding. Start with: am serve"
        exit 1
    fi
}

# Step 1: Ensure Project
ensure_project() {
    log_step "Step 1: Ensure Project"
    local result
    result=$(mcp_call "ensure_project" "{\"human_key\":\"$PROJECT_SLUG\",\"slug\":\"$PROJECT_SLUG\"}" 1)

    if echo "$result" | jq -e '.result.content[0].text' > /dev/null 2>&1; then
        local msg
        msg=$(echo "$result" | jq -r '.result.content[0].text')
        log_success "$msg"
    else
        log_error "Failed to ensure project"
        echo "$result" | jq .
        exit 1
    fi
}

# Step 2: Register Agent
register_agent() {
    local name="$1"
    local task="$2"
    log_step "Step 2: Register Agent '$name'"

    local result
    result=$(mcp_call "register_agent" "{\"project_slug\":\"$PROJECT_SLUG\",\"name\":\"$name\",\"program\":\"claude-code\",\"model\":\"opus-4\",\"task_description\":\"$task\"}" 2)

    if echo "$result" | jq -e '.result.content[0].text' > /dev/null 2>&1; then
        local msg
        msg=$(echo "$result" | jq -r '.result.content[0].text')
        log_success "$msg"
    else
        local err
        err=$(echo "$result" | jq -r '.error.message // "Unknown error"')
        if [[ "$err" == *"already exists"* ]]; then
            log_info "Agent '$name' already registered"
        else
            log_error "Failed: $err"
        fi
    fi
}

# Step 3: Check Inbox
check_inbox() {
    local agent="$1"
    log_step "Step 3: Check Inbox for '$agent'"

    local result
    result=$(mcp_call "list_inbox" "{\"project_slug\":\"$PROJECT_SLUG\",\"agent_name\":\"$agent\",\"limit\":10}" 3)

    local msg
    msg=$(echo "$result" | jq -r '.result.content[0].text // "Error"')
    echo "$msg"
}

# Step 4: Reserve Files
reserve_files() {
    local agent="$1"
    shift
    local paths="$*"
    log_step "Step 4: Reserve Files"

    # Convert paths to JSON array
    local paths_json
    paths_json=$(printf '%s\n' "$@" | jq -R . | jq -s .)

    local result
    result=$(mcp_call "file_reservation_paths" "{\"project_slug\":\"$PROJECT_SLUG\",\"agent_name\":\"$agent\",\"paths\":$paths_json,\"exclusive\":true,\"ttl_seconds\":120,\"reason\":\"Workflow demo\"}" 4)

    if echo "$result" | jq -e '.result.content[0].text' > /dev/null 2>&1; then
        local msg
        msg=$(echo "$result" | jq -r '.result.content[0].text')
        log_success "Reserved files:"
        echo "$msg"

        # Extract reservation IDs for later release
        RESERVATION_IDS=$(echo "$msg" | grep -oE 'id: [0-9]+' | grep -oE '[0-9]+' || true)
    else
        local err
        err=$(echo "$result" | jq -r '.error.message // "Unknown error"')
        log_error "Failed: $err"
    fi
}

# Step 5: Simulate Work
simulate_work() {
    local duration="$1"
    log_step "Step 5: Simulating Work ($duration seconds)"
    log_info "Started at: $(date)"

    # Progress bar
    for ((i=1; i<=duration; i++)); do
        local pct=$((i * 100 / duration))
        local filled=$((pct / 5))
        local empty=$((20 - filled))
        printf "\r  [%s%s] %d%%" "$(printf '#%.0s' $(seq 1 $filled 2>/dev/null) || true)" "$(printf '.%.0s' $(seq 1 $empty 2>/dev/null) || true)" "$pct"
        sleep 1
    done
    echo ""

    log_info "Finished at: $(date)"
    log_success "Work completed"
}

# Step 6: Send Message
send_message() {
    local from="$1"
    local to="$2"
    local subject="$3"
    local body="$4"
    local thread="${5:-DEMO-workflow}"

    log_step "Step 6: Send Message"

    local result
    result=$(mcp_call "send_message" "{\"project_slug\":\"$PROJECT_SLUG\",\"sender_name\":\"$from\",\"to\":\"$to\",\"subject\":\"$subject\",\"body_md\":\"$body\",\"thread_id\":\"$thread\",\"importance\":\"normal\"}" 5)

    if echo "$result" | jq -e '.result.content[0].text' > /dev/null 2>&1; then
        local msg
        msg=$(echo "$result" | jq -r '.result.content[0].text')
        log_success "$msg"
    else
        local err
        err=$(echo "$result" | jq -r '.error.message // "Unknown error"')
        log_error "Failed: $err"
    fi
}

# Step 7: Release Reservations
release_reservations() {
    log_step "Step 7: Release Reservations"

    if [[ -z "${RESERVATION_IDS:-}" ]]; then
        log_info "No reservations to release"
        return
    fi

    for id in $RESERVATION_IDS; do
        local result
        result=$(mcp_call "release_reservation" "{\"reservation_id\":$id}" 6)

        if echo "$result" | jq -e '.result.content[0].text' > /dev/null 2>&1; then
            log_success "Released reservation $id"
        else
            log_error "Failed to release reservation $id"
        fi
    done
}

# Step 8: Verify State
verify_state() {
    log_step "Step 8: Verify Clean State"

    # Check reservations
    local res_result
    res_result=$(mcp_call "list_reservations" "{\"project_slug\":\"$PROJECT_SLUG\",\"all_agents\":true}" 7)
    local res_msg
    res_msg=$(echo "$res_result" | jq -r '.result.content[0].text // "Error"')
    echo "Reservations: $res_msg"

    # Check inbox
    local inbox_result
    inbox_result=$(mcp_call "list_inbox" "{\"project_slug\":\"$PROJECT_SLUG\",\"agent_name\":\"$REVIEWER_NAME\",\"limit\":5}" 8)
    local inbox_msg
    inbox_msg=$(echo "$inbox_result" | jq -r '.result.content[0].text // "Error"')
    echo "Reviewer inbox: $inbox_msg"
}

# Main workflow
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║           MOUCHAK MAIL WORKFLOW DEMO                           ║"
    echo "╠════════════════════════════════════════════════════════════════╣"
    echo "║  Project: $PROJECT_SLUG"
    echo "║  Agent: $AGENT_NAME"
    echo "║  Reviewer: $REVIEWER_NAME"
    echo "║  Work Duration: ${WORK_DURATION}s"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""

    check_health
    echo ""

    ensure_project
    echo ""

    register_agent "$AGENT_NAME" "Demo workflow agent"
    register_agent "$REVIEWER_NAME" "Reviews demo work"
    echo ""

    check_inbox "$AGENT_NAME"
    echo ""

    reserve_files "$AGENT_NAME" "src/**/*.rs" "prompts/**/*.md"
    echo ""

    simulate_work "$WORK_DURATION"
    echo ""

    send_message "$AGENT_NAME" "$REVIEWER_NAME" \
        "Workflow demo complete" \
        "Completed demo workflow: reserved files, simulated work, releasing reservations." \
        "DEMO-workflow-$(date +%s)"
    echo ""

    release_reservations
    echo ""

    verify_state
    echo ""

    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                    WORKFLOW COMPLETE ✅                        ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
}

# Run
main "$@"
