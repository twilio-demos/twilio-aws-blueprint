# Twilio Conversation Relay Voice Agent

A service for Twilio Conversation Relay - built with FastAPI and designed for AWS deployment. Supports webhooks, WebSocket streaming, and modular AI agent components and more to come ...

## Features

- **FastAPI Framework**: High-performance async web framework
- **Twilio Integration**: Complete webhook and WebSocket support for ConversationRelay
- **Security**: Request signature validation for all Twilio endpoints
- **Containerized**: Docker-based deployment with health checks
- **AWS Fargate**: Serverless container platform with auto-scaling
- **SSL/TLS Support**: HTTPS endpoints for production Twilio webhooks
- **Structured Logging**: Comprehensive logging for debugging and monitoring

## Architecture

## Project Structure

```
src/
├── main.py                 # FastAPI application entry point
├── config/
│   └── __init__.py
├── routes/
│   ├── __init__.py
│   └── call.py            # Twilio webhook endpoints (/call/twiml, /call/action)
├── websocket/
│   ├── __init__.py
│   └── ws.py              # ConversationRelay WebSocket handler
├── types/
│   ├── __init__.py
│   └── websocket.py       # Pydantic models for ConversationRelay messages
├── utils/
│   ├── __init__.py
│   ├── env.py             # Environment variable management
│   └── logger.py          # Structured logging configuration
├── services/
│   └── __init__.py
├── stream/
│   └── __init__.py
├── ai/
│   └── __init__.py
├── persistence/
│   └── __init__.py
└── monitoring/
    └── __init__.py

deployment/
├── cloudformation-template.yaml  # AWS infrastructure as code
└── deploy.sh                    # Deployment script

Dockerfile                       # Container configuration
docker-compose.yml               # Local development setup
requirements.txt                 # Python dependencies
.dockerignore                   # Docker build context exclusions
.gitignore                      # Git exclusions
```

## Quick Start

### Prerequisites

- Python 3.10+
- Docker
- AWS CLI configured with appropriate permissions
- Twilio account

### Local Development

1. **Clone and setup**:

   ```bash
   git clone <your-repo>
   cd twilio-conversation-relay-aws
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment configuration**:

   ```bash
   cp .env.example .env
   # Edit .env with your Twilio credentials
   ```

3. **Run locally**:

   ```bash
   # Direct FastAPI
   python -m uvicorn src.main:app --reload --port 8000

   # Or with Docker
   docker-compose up --build
   ```

4. **Test endpoints**:
   ```bash
   curl http://localhost:8000/
   curl http://localhost:8000/call/twiml
   ```

## Production Deployment on AWS

## Environment Variables

### Required for Production

| Variable             | Description        | Example           |
| -------------------- | ------------------ | ----------------- |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | `ACxxxxxxxxx`     |
| `TWILIO_AUTH_TOKEN`  | Twilio Auth Token  | `your-auth-token` |

### Optional Configuration

| Variable       | Description          | Default                |
| -------------- | -------------------- | ---------------------- |
| `ENVIRONMENT`  | Environment name     | `prod`                 |
| `LOG_LEVEL`    | Logging level        | `INFO`                 |
| `TTS_VOICE`    | Default TTS voice    | `lxYfHSkYm1EzQzGhdbfc` |
| `TTS_LANGUAGE` | Default TTS language | `en-US`                |

## Twilio Configuration

### 1. Configure Webhook URLs

In your Twilio Console, set:

- **Webhook URL**: `https://api.yourdomain.com/call/twiml`
- **HTTP Method**: `POST`
- **Webhook URL (Status Events)**: `https://api.yourdomain.com/call/action`

## API Endpoints

### Health Check

- **GET** `/` - Health status

### Twilio Webhooks

- **POST** `/call/twiml` - TwiML generation for incoming calls
- **POST** `/call/action` - Call status events and actions

### WebSocket

- **WS** `/ws` - ConversationRelay WebSocket connection

## Monitoring and Debugging

## Security

### Webhook Validation

All Twilio webhooks are validated using request signatures:

- HTTP webhooks: Automatic validation in middleware
- WebSocket connections: Signature validation during handshake

## License

[Add your license information here]

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review CloudWatch logs
3. Open an issue in the repository
