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

### Option 1: Quick Deployment (HTTP Only)

For development or testing without SSL:

```bash
./deployment/deploy.sh
```

Required environment variables:

- `TWILIO_ACCOUNT_SID`: Your Twilio Account SID
- `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token

### Option 2: Production Deployment with SSL/TLS

For production Twilio webhooks (HTTPS required):

#### Step 1: Setup SSL Certificate

**Option A: AWS Certificate Manager (ACM)**

```bash
# Request a certificate for your domain
aws acm request-certificate
  --domain-name api.yourdomain.com
  --validation-method DNS
  --region us-east-1

# Note the certificate ARN from the output
```

**Option B: Import existing certificate**

```bash
aws acm import-certificate
  --certificate file://certificate.pem
  --private-key file://private-key.pem
  --certificate-chain file://certificate-chain.pem
  --region us-east-1
```

#### Step 2: Deploy with SSL

```bash
export TWILIO_ACCOUNT_SID="your-account-sid"
export TWILIO_AUTH_TOKEN="your-auth-token"
export CERTIFICATE_ARN="arn:aws:acm:region:account:certificate/certificate-id"
export DOMAIN_NAME="api.yourdomain.com"  # Optional

./deployment/deploy.sh
```

#### Step 3: DNS Configuration

Point your domain to the load balancer:

```bash
# Get the load balancer DNS name
aws cloudformation describe-stacks
  --stack-name twilio-conversation-relay
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue'
  --output text

# Create CNAME record: api.yourdomain.com → alb-dns-name
```

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

### CloudWatch Logs

```bash
# View application logs
aws logs tail /ecs/twilio-conversation-relay --follow
```

### Environment Management

Use `src/utils/env.py` for configuration:

```python
from src/utils/env import get_env_var

api_key = get_env_var("CUSTOM_API_KEY", required=True)
```

## Security

### Webhook Validation

All Twilio webhooks are validated using request signatures:

- HTTP webhooks: Automatic validation in middleware
- WebSocket connections: Signature validation during handshake

### AWS Security

- ECS tasks run with minimal IAM permissions
- Secrets stored in Systems Manager Parameter Store
- Security groups restrict network access
- Container runs as non-root user

## Troubleshooting

### Common Issues

1. **Webhook validation failures**:

   ```bash
   # Check Twilio signature validation
   curl -X POST https://api.yourdomain.com/call/twiml
     -H "X-Twilio-Signature: invalid"
     -d "test=data"
   # Should return 403 Forbidden
   ```

2. **WebSocket connection issues**:

   ```bash
   # Test WebSocket endpoint
   wscat -c wss://api.yourdomain.com/ws
   ```

3. **Container startup issues**:
   ```bash
   # Check ECS task logs
   aws logs tail /ecs/twilio-conversation-relay --follow
   ```

### Deployment Issues

1. **SSL certificate problems**:

   ```bash
   # Verify certificate status
   aws acm describe-certificate --certificate-arn your-cert-arn
   ```

2. **Load balancer health checks**:
   ```bash
   # Check target group health
   aws elbv2 describe-target-health --target-group-arn your-tg-arn
   ```

### Optimization Tips

1. **Right-size containers**: Monitor CPU/memory usage
2. **Use Spot capacity**: For non-critical workloads
3. **Scale based on demand**: Configure auto-scaling policies
4. **Optimize logs retention**: Set appropriate CloudWatch retention

## License

[Add your license information here]

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review CloudWatch logs
3. Open an issue in the repository
