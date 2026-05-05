# Twilio Conversation Relay Voice Agent

A service for Twilio Conversation Relay - built with FastAPI and designed for AWS deployment. Supports webhooks, WebSocket streaming, and modular AI agent components with more to come...

> **🚀 Multi-Channel Support Available**: Looking for SMS, WhatsApp, chat, and other messaging channels? Check out the [`twilio-conversations`](https://github.com/twilio-demos/twilio-aws-blueprint/tree/twilio-conversations) branch, which uses the [Twilio Agent Connect (TAC) SDK](https://github.com/twilio/twilio-agent-connect-python) to support multi-channel conversations with Conversation Orchestrator and Memory Store integration.

## Features

- **FastAPI Framework**: High-performance async web framework
- **Twilio Integration**: Complete webhook and WebSocket support for ConversationRelay
- **Security**: Request signature validation for all Twilio endpoints
- **Containerized**: Docker-based deployment with health checks
- **AWS Fargate**: Serverless container platform with auto-scaling
- **SSL/TLS Support**: HTTPS endpoints for production Twilio webhooks
- **Structured Logging**: Comprehensive logging for debugging and monitoring

## Quick Start

### Prerequisites

- Python 3.13+
- AWS CLI configured with appropriate permissions
- Twilio account
- For local development: ngrok or similar tool to expose your local app endpoints
- For Windows users: Bash shell

### Local Development and Testing with Twilio and ngrok

1. **Clone and setup**:

   ```bash
   git clone https://github.com/twilio-demos/twilio-aws-blueprint.git
   cd twilio-aws-blueprint
   ./setup.sh
   ```

2. Expose the app endpoints with **ngrok** in a standalone terminal:

   ```bash
   ngrok http 8000
   ```

   (Note: When running, this will output a **Forwarding URL** that looks like this: `https://abc123.ngrok.app`. Take note of this, as we will use it in the following steps.)

3. Update **.env** with your Twilio and AWS credentials, as well as the **ngrok Forwarding URL** emitted by the previous step:

   | Variable             | Description          | Example                    |
   | -------------------- | -------------------- | -------------------------- |
   | `TWILIO_ACCOUNT_SID` | Twilio Account SID   | `ACxxxxxxxxx`              |
   | `TWILIO_AUTH_TOKEN`  | Twilio Auth Token    | `your-auth-token`          |
   | `AWS_PROFILE`        | AWS CLI Profile      | `profile-name`             |
   | `AWS_REGION`         | AWS Region           | `us-east-1`                |
   | `EXTERNAL_URL`       | ngrok forwarding URL | `https://abc123.ngrok.app` |

4. Run the app:

   ```bash
   # Run directly
   ./dev.sh

   # Or with Docker
   docker-compose up --build
   ```

   (Note: If you already had the app running, you'll need to restart it to pick up the updated values from **.env**!)

5. [Create a new TwiML app](https://console.twilio.com/us1/develop/voice/manage/twiml-apps?frameUrl=%2Fconsole%2Fvoice%2Ftwiml%2Fapps%3Fx-target-region%3Dus1) in the Twilio Console with the following settings:

   - **Friendly Name**: Enter a name of your choosing.
   - **Voice Configuration Request URL**: `https://abc123.ngrok.app/call/twiml`
     - Note: Replace `https://abc123.ngrok.app` with the **ngrok Forwarding URL** from the previous steps.

6. [Configure a phone number](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming) to point to the TwiML app you just created.

7. Enable the **Predictive and Generative AI/ML Features Addendum** in [Twilio Voice Settings](https://console.twilio.com/us1/develop/voice/settings/general?frameUrl=%2Fconsole%2Fvoice%2Fsettings%3Fx-target-region%3Dus1)

8. Dial the configured phone number and chat away.

## Multi-Channel Implementation with TAC

The [`twilio-conversations`](https://github.com/twilio-demos/twilio-aws-blueprint/tree/twilio-conversations) branch provides an enhanced implementation using the [Twilio Agent Connect (TAC) SDK](https://github.com/twilio/twilio-agent-connect-python) with the following capabilities:

### Additional Features

- **Multi-Channel Support**: Voice, SMS, WhatsApp, RCS, and chat channels
- **Conversation Orchestrator**: Intelligent conversation routing and management
- **Memory Store**: Persistent user context and conversation history across sessions and channels
- **Cross-Channel Context**: User conversations persist across different communication channels
- **Simplified Integration**: Built-in channel handling and automatic memory injection into LLM prompts

### When to Use TAC

- **Multi-Channel**: If you need to support SMS, WhatsApp, chat, or multiple channels
- **Memory & Context**: If you need persistent user context across conversations
- **Orchestration**: If you need intelligent routing and conversation management
- **Voice-Only**: The main branch (ConversationRelay-only) is lighter and simpler for voice-only use cases

To get started with the TAC implementation:

```bash
git checkout twilio-conversations
./setup.sh
```

See the [TAC branch README](https://github.com/twilio-demos/twilio-aws-blueprint/tree/twilio-conversations) for detailed setup instructions.

## Production Deployment on AWS

## Environment Variables

### Required for Production

| Variable             | Description        | Example           |
| -------------------- | ------------------ | ----------------- |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | `ACxxxxxxxxx`     |
| `TWILIO_AUTH_TOKEN`  | Twilio Auth Token  | `your-auth-token` |
| `ENVIRONMENT`        | Environment name   | `prod`            |

### Optional Configuration

| Variable             | Description                                     | Default |
| -------------------- | ----------------------------------------------- | ------- |
| `LANGUAGE`           | Default language for recognition and responses. | `en-US` |
| `LOG_LEVEL`          | Logging level                                   | `INFO`  |
| `DTMF_MAX_DIGITS`    | Maximum number of digits accepted in DTMF input | `10`    |
| `DTMF_TIMEOUT`       | Timeout (in seconds) for DTMF input             | `3`     |
| `IDLE_MAX_ATTEMPTS`  | Maximum number of idle attempts before action   | `3`     |
| `IDLE_TIMEOUT`       | Idle timeout duration in seconds                | `20`    |
| `ERROR_MAX_ATTEMPTS` | Maximum number of error retries                 | `5`     |

### Twilio Conversational Intelligence Service (Optional)

You can enable Twilio Conversational Intelligence integration to add observability and analytics for AI agent conversations managed by ConversationRelay. This feature provides monitoring, analysis, and insights into agent interactions and performance. For more details, refer to the [Conversational Intelligence and ConversationRelay integration documentation](https://www.twilio.com/docs/conversational-intelligence/conversation-relay-integration).

| Variable                             | Description                                                                            | Default |
| ------------------------------------ | -------------------------------------------------------------------------------------- | ------- |
| `TWILIO_CONVERSATIONAL_INTELLIGENCE` | Conversational Intelligence Service SID or unique name for virtual agent observability | None    |

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
  initial_hints: Optional initial hints for speech recognition. Each hint is separated by `,` (comma)
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
    - `initial_hints` - The initial speech recognition hints to use by default (overrides the `initial_hints` from the language file)
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

## Important Notice

**This is a reference implementation/blueprint provided by the Solution Acceleration Architect team.** It is designed to help you quickly deploy a proof-of-concept (POC) Twilio ConversationRelay voice agent integrated with AWS services.

### Disclaimer

- This code is provided **as-is** without warranties or guarantees of any kind
- Twilio does **not** provide ongoing maintenance, updates, or support for this blueprint
- You are responsible for reviewing, testing, modifying, and maintaining the code for your use case
- Use at your own risk in production environments

### Your Responsibilities

Before deploying to production, you should:

- Review and understand all code and configurations
- Implement appropriate security measures for your requirements
- Perform thorough testing with your expected workloads
- Set up monitoring and alerting
- Establish your own maintenance and update procedures
- Ensure compliance with your organization's policies and regulations

## License

MIT License

Copyright (c) 2026 Twilio Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Support

This is a community-supported blueprint. Twilio does not provide official support for this code.
