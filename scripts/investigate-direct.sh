#!/bin/bash
set -e

REPO_URL="${1:-https://github.com/sindresorhus/is}"

if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    export ANTHROPIC_BASE_URL="http://localhost:8080"
    export ANTHROPIC_API_KEY="test"
    echo "🔗 Using antigravity proxy"
else
    echo "📡 Using direct Anthropic API"
fi

echo "🔍 Investigating: $REPO_URL"

cd /Users/amrit/Documents/Projects/Rust/mouchak/repo-swarm
export INVESTIGATE_REPO_URL="$REPO_URL"
uv run python3 -c "
import sys, asyncio, os
sys.path.insert(0, 'src')
from investigator.investigator import ClaudeInvestigator
async def run():
    repo = os.environ['INVESTIGATE_REPO_URL']
    print(f'Repository: {repo}')
    inv = ClaudeInvestigator(log_level='INFO')
    result = await inv.investigate_repository(repo)
    print(f'Done: {result}')
asyncio.run(run())
"
