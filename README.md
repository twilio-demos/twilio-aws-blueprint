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

- Python 3.13+
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

3. **AWS Setup**:

   Configure AWS SSO for accessing AWS services (required for AI agents and DynamoDB):

   ```bash
   # Configure AWS SSO (one-time setup)
   aws configure sso

   # Login to AWS SSO (run this whenever your session expires)
   source ./aws-sso-login.sh
   ```

   Note: The `aws-sso-login.sh` script helps maintain your AWS session for local development. You'll need to run this periodically when your AWS credentials expire.

4. **Run locally**:

   ```bash
   # Direct FastAPI
   source venv/bin/activate
   python -m uvicorn src.main:app --reload --port 8000

   # Or with Docker
   docker-compose up --build
   ```

5. **Test endpoints**:
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
| `ENVIRONMENT`        | Environment name   | `prod`            |

### Optional Configuration

| Variable                | Description                                                        | Default                                  |
|-------------------------|--------------------------------------------------------------------|------------------------------------------|
| `LOG_LEVEL`             | Logging level                                                      | `INFO`                                   |
| `WELCOME_GREETING`      | Greeting message when the assistant starts                         | `Hello! I'm your AI assistant. How can I help you today?` |
| `DTMF_MAX_DIGITS`       | Maximum number of digits accepted in DTMF input                    | `10`                                     |
| `DTMF_TIMEOUT`          | Timeout (in seconds) for DTMF input                                | `3`                                      |
| `IDLE_REMINDER`         | Reminder message when idle                                         | `I'm still here, let me know when you are ready to continue.` |
| `IDLE_MAX_ATTEMPTS`     | Maximum number of idle attempts before action                      | `3`                                      |
| `IDLE_TIMEOUT`          | Idle timeout duration in seconds                                   | `20`                                     |
| `ERROR_MAX_ATTEMPTS`    | Maximum number of error retries                                    | `5`                                      |

### Optional Language Configuration

For each of the below options, you may include multiple values separated by `|` (pipe) in order to specify configuration for multiple languages. If you do so, each option must include the same number of values.

For valid parameters for text-to-speech and speech-to-text configuration, please consult the [ConversationRelay documentation](https://www.twilio.com/docs/voice/conversationrelay/conversationrelay-noun).

| Variable                | Description                                                        | Default                                  |
|-------------------------|--------------------------------------------------------------------|------------------------------------------|
| `LANGUAGE`              | Language code(s) for recognition and responses.                    | `en-US`                                  |
| `TTS_PROVIDER`          | Text-to-Speech service provider.                                   | `ElevenLabs`                             |
| `TTS_VOICE`             | Voice identifier(s) for the TTS provider.                          | `lxYfHSkYm1EzQzGhdbfc`                   |
| `TRANSCRIPTION_PROVIDER`| Speech-to-Text service provider.                                   | `Deepgram`                               |
| `SPEECH_MODEL`          | Model(s) used for speech transcription.                            | `nova-3-general`                         |
| `INITIAL_HINTS`         | Initial hints for speech recognition. Each hint is separated by `,` (comma). | (empty)                                |


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
