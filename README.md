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
- AWS CLI configured with appropriate permissions
- Twilio account
- For local development: ngrok or similar tool to expose your local app endpoints
- For Windows users: Bash shell

### Local Development

1. **Clone and setup**:

   ```bash
   git clone https://github.com/twilio-professional-services/twilio-conversation-relay-aws.git
   cd twilio-conversation-relay-aws
   ./setup.sh
   ```

2. **Environment configuration**:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your Twilio and AWS credentials:

   | Variable             | Description        | Example           |
   | -------------------- | ------------------ | ----------------- |
   | `TWILIO_ACCOUNT_SID` | Twilio Account SID | `ACxxxxxxxxx`     |
   | `TWILIO_AUTH_TOKEN`  | Twilio Auth Token  | `your-auth-token` |
   | `AWS_PROFILE`        | AWS CLI Profile    | `profile-name`    |
   | `AWS_REGION`         | AWS Region         | `us-east-1`       |

3. **Run locally**:

   ```bash
   # Run directly
   ./dev.sh

   # Or with Docker
   docker-compose up --build
   ```

4. **Test endpoints**:
   ```bash
   curl http://localhost:8000/
   ```

### Local Testing with Twilio

1. Expose the app endpoints with **ngrok**:

   ```bash
   ngrok http 8000
   ```

2. Update **.env** with the **ngrok Forwarding URL** emitted by the previous step:

   ```
   EXTERNAL_URL=https://abc123.ngrok.app
   ```

3. Run the app:

   ```bash
   ./dev.sh
   ```

   (Note: If you already had the app running, you'll need to restart it to pick up the updated values from **.env**!)

4. [Create a new TwiML app](https://console.twilio.com/us1/develop/voice/manage/twiml-apps?frameUrl=%2Fconsole%2Fvoice%2Ftwiml%2Fapps%3Fx-target-region%3Dus1) in the Twilio Console with the following settings:

   - **Friendly Name**: Enter a name of your choosing.
   - **Voice Configuration Request URL**: `https://your-ngrok-url-here.ngrok.app/call/twiml`

5. [Configure a phone number](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming) to point to the TwiML app you just created.

6. Dial the configured phone number and chat away.

## Production Deployment on AWS

## Environment Variables

### Required for Production

| Variable             | Description        | Example           |
| -------------------- | ------------------ | ----------------- |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | `ACxxxxxxxxx`     |
| `TWILIO_AUTH_TOKEN`  | Twilio Auth Token  | `your-auth-token` |
| `ENVIRONMENT`        | Environment name   | `prod`            |

### Optional Configuration

| Variable             | Description                                                                  | Default |
| -------------------- | ---------------------------------------------------------------------------- | ------- |
| `LANGUAGE`           | Default language for recognition and responses.                              | `en-US` |
| `LOG_LEVEL`          | Logging level                                                                | `INFO`  |
| `DTMF_MAX_DIGITS`    | Maximum number of digits accepted in DTMF input                              | `10`    |
| `DTMF_TIMEOUT`       | Timeout (in seconds) for DTMF input                                          | `3`     |
| `IDLE_MAX_ATTEMPTS`  | Maximum number of idle attempts before action                                | `3`     |
| `IDLE_TIMEOUT`       | Idle timeout duration in seconds                                             | `20`    |
| `ERROR_MAX_ATTEMPTS` | Maximum number of error retries                                              | `5`     |
| `INITIAL_HINTS`      | Initial hints for speech recognition. Each hint is separated by `,` (comma). | (empty) |

### Language Configuration

You may define language configurations using the following YAML format by placing files in the `src/languages` directory. Each language file should be named using a valid ConversationRelay language code (i.e. `en-US`, `pt-BR`, `multi`, etc).

When no `language` parameter is specified in the URL, the file corresponding to the `LANGUAGE` environment variable is used. Languages can also be switched at runtime.

An example language file for `en-US` is included by default and can be used as a template. For valid parameters for text-to-speech and speech-to-text configuration, please consult the [ConversationRelay documentation](https://www.twilio.com/docs/voice/conversationrelay/conversationrelay-noun).

```yaml
prompts:
  welcome_greeting: The initial prompt that plays when starting a new session without specifying a welcome_greeting parameter in the URL
  welcome_error: The message when failing to generate the initial <ConversationRelay> TwiML
  error: The message when an error occurs during the conversation
  idle: The message when no input is detected from the user after IDLE_TIMEOUT seconds
  idle_timeout: The message when the session is ended due to no input being detected from the user IDLE_MAX_ATTEMPTS times

settings:
  transcription_provider: Speech-to-text service provider
  speech_model: Model used for speech transcription
  tts_provider: Text-to-speech service provider
  tts_voice: Voice identifier(s) for the TTS provider
  fallback_tts: Voice identifier(s) for non-ConverationRelay TTS messages
```

### Optional AWS Bedrock Configuration

| Variable                       | Description                                                                                    | Default                                       |
| ------------------------------ | ---------------------------------------------------------------------------------------------- | --------------------------------------------- |
| `BEDROCK_MODEL`                | Amazon Bedrock model identifier                                                                | `us.anthropic.claude-3-5-haiku-20241022-v1:0` |
| `BEDROCK_REGION`               | AWS region for Bedrock service                                                                 | `us-east-2`                                   |
| `BEDROCK_TEMPERATURE`          | Model temperature (0.0-1.0, controls randomness)                                               | `0`                                           |
| `BEDROCK_MAX_TOKENS`           | Maximum tokens the model can generate                                                          | `4000`                                        |
| `BEDROCK_GUARDRAIL_ID`         | Bedrock guardrail identifier for content filtering (if not set, no guardrails will be applied) | None (optional)                               |
| `BEDROCK_GUARDRAIL_VERSION`    | Version of the guardrail to use                                                                | `DRAFT`                                       |
| `BEDROCK_GUARD_LAST_TURN_ONLY` | Apply guardrails only to the last conversation turn                                            | `true`                                        |
| `BEDROCK_GUARDRAIL_TRACE`      | Enable tracing for guardrail evaluation debugging                                              | `enabled`                                     |
| `BEDROCK_KB_ID`                | Knowledge base identifier for retrieval (if not set, knowledge base search is skipped)         | None (optional)                               |
| `BEDROCK_RETRIEVAL_RESULTS`    | Number of results to retrieve from knowledge base                                              | `5`                                           |
| `BEDROCK_MIN_SCORE_CONFIDENCE` | Minimum confidence score for retrieval results                                                 | `0.0`                                         |

## API Endpoints

### Health Check

- **GET** `/` - Health status

### Twilio Webhooks

- **POST** `/call/twiml` - `<Connect><ConversationRelay>` TwiML generation for incoming calls
  - Optional query parameters:
    - `language` - The language to use by default (overrides the `LANGUAGE` environment variable)
    - `welcome_greeting` - The welcome greeting to use (overrides the `welcome_greeting` from the language file)
    - `initial_hints` - The initial speech recognition hints to use by default (overrides the `INITIAL_HINTS` environment variable)
    - `action_url` - Overrides the `<Connect>` action handler URL (`/call/action` by default)
- **POST** `/call/action` - `<Connect>` action handler

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
