# Twilio Conversation Relay Voice Agent

A service for Twilio Conversation Relay - built with FastAPI and designed for AWS deployment. Supports webhooks, WebSocket streaming, and modular AI agent components and more to come ...

## Features

- FastAPI for HTTP and WebSocket endpoints
- `/call/twiml` and `/call/action` webhook routes
- Modular structure for config, utils, services, AI, persistence, and monitoring - WIP
- Pydantic models for type safety
- Ready for AWS integration (DynamoDB, Lambda, etc.) - WIP

## Project Structure

```
src/
  config/         # Environment configuration
  types/          # Pydantic models
  utils/          # Utility functions
  routes/         # FastAPI API routes (call/twiml, call/action)
  websocket/      # WebSocket server and handlers
  services/       # Service container and dependency injection
  stream/         # Token streaming and processing
  ai/
    agent/        # Core agent logic
    prompts/      # Prompt management
    guardrails/   # Input/output validation
    tools/        # Function calling and tool registry
    retrieval/    # Knowledge base integration
  persistence/    # DynamoDB session and conversation store
  monitoring/     # Metrics and observability
```

## Quick Start

1. Create and activate a virtual environment:

   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

3. Run the server (default port 8000):

   ```sh
   uvicorn src.main:app --reload --port 8000
   ```

4. Expose localhost with ngrok for Twilio webhooks:

   ```sh
   ngrok http 8000
   ```

   Use the generated ngrok URL in your Twilio configuration.

5. Available endpoints:
   - Webhook: `POST /call/twiml` and `POST /call/action`
   - WebSocket: `ws://localhost:8000/ws/`

## License

MIT
