#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment
source venv/bin/activate

# Install watchdog if not present (for auto-restart)
if ! python -c "import watchdog" 2>/dev/null; then
    echo "📦 Installing watchdog for auto-restart..."
    pip install watchdog[watchmedo] -q
fi

# Check if using TAC mode (TWILIO_CONVERSATION_CONFIGURATION_ID is set)
if [ -n "$TWILIO_CONVERSATION_CONFIGURATION_ID" ]; then
    echo "🚀 Starting TAC application (Conversation Orchestrator mode)"
    echo "   Agent: ${AGENT_RUNNER_TYPE:-langgraph}"
    echo "   Port: 8000"
    echo "   Auto-restart: enabled (watching src/)"
    echo ""

    watchmedo auto-restart \
        --directory=./src \
        --pattern="*.py" \
        --recursive \
        -- python -m src.main_tac
else
    echo "🚀 Starting original FastAPI application (Relay-only mode)"
    echo "   Agent: ${AGENT_RUNNER_TYPE:-langgraph}"
    echo "   Port: 8000"
    echo "   Auto-restart: enabled (uvicorn --reload)"
    echo ""

    uvicorn src.main:app --reload --port 8000
fi