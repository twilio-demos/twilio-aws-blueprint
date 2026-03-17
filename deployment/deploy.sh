#!/bin/bash
set -e

# Configuration
STACK_NAME="twilio-conversation-relay"
SERVICE_NAME="twilio-conversation-relay"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-default}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required environment variables are set
check_env_vars() {
    echo_info "Checking required environment variables..."
    
    if [ -z "$TWILIO_ACCOUNT_SID" ]; then
        echo_error "TWILIO_ACCOUNT_SID environment variable is required"
        exit 1
    fi
    
    if [ -z "$TWILIO_AUTH_TOKEN" ]; then
        echo_error "TWILIO_AUTH_TOKEN environment variable is required"
        exit 1
    fi
    
    echo_info "Environment variables check passed"
}

# Check if AWS CLI is installed and configured
check_aws_cli() {
    echo_info "Checking AWS CLI..."
    
    if ! command -v aws &> /dev/null; then
        echo_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if AWS credentials are available (either via profile, env vars, or IAM role)
    if ! aws sts get-caller-identity --profile $AWS_PROFILE &> /dev/null; then
        echo_error "AWS CLI is not properly configured."
        echo_error "Please configure credentials using one of these methods:"
        echo_error "1. Run 'aws configure' to set up default profile"
        echo_error "2. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
        echo_error "3. Use IAM roles (if running on EC2)"
        echo_error "4. Set AWS_PROFILE to use a specific configured profile"
        exit 1
    fi
    
    echo_info "AWS CLI check passed"
}

# Get AWS Account ID
get_account_id() {
    ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)
    echo_info "AWS Account ID: $ACCOUNT_ID"
}

# Create ECR repository and get login token
setup_ecr() {
    echo_info "Setting up ECR repository..."
    
    # Set ECR URI
    ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$SERVICE_NAME"
    
    # Check if ECR repository exists, create if it doesn't
    if ! aws ecr describe-repositories --repository-names $SERVICE_NAME --region $AWS_REGION --profile $AWS_PROFILE &> /dev/null; then
        echo_info "Creating ECR repository: $SERVICE_NAME"
        aws ecr create-repository \
            --repository-name $SERVICE_NAME \
            --region $AWS_REGION \
            --profile $AWS_PROFILE &> /dev/null || {
            echo_error "Failed to create ECR repository"
            exit 1
        }
    else
        echo_info "ECR repository already exists: $ECR_URI"
    fi
    
    # Login to ECR
    echo_info "Logging into ECR..."
    if ! aws ecr get-login-password --region $AWS_REGION --profile $AWS_PROFILE | \
        docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com; then
        echo_error "Failed to login to ECR"
        exit 1
    fi
}

# Build and push Docker image
build_and_push() {
    echo_info "Building Docker image for linux/amd64 platform..."
    
    # Build the image with explicit platform for ECS Fargate compatibility
    if ! docker build --platform linux/amd64 -t $SERVICE_NAME:latest .; then
        echo_error "Failed to build Docker image"
        exit 1
    fi
    
    # Tag the image for ECR
    echo_info "Tagging image for ECR..."
    if ! docker tag $SERVICE_NAME:latest $ECR_URI:latest; then
        echo_error "Failed to tag Docker image"
        exit 1
    fi
    
    echo_info "Pushing Docker image to ECR..."
    if ! docker push $ECR_URI:latest; then
        echo_error "Failed to push Docker image to ECR"
        echo_error "Make sure you're logged into ECR and the repository exists"
        exit 1
    fi
    
    echo_info "Docker image pushed successfully"
}

# Deploy CloudFormation stack
deploy_stack() {
    echo_info "Deploying CloudFormation stack..."
    
    # Prepare base parameters
    PARAMETERS="ServiceName=$SERVICE_NAME TwilioAccountSid=$TWILIO_ACCOUNT_SID TwilioAuthToken=$TWILIO_AUTH_TOKEN"
    
    # Add SSL parameters if provided
    if [ -n "$CERTIFICATE_ARN" ]; then
        PARAMETERS="$PARAMETERS CertificateArn=$CERTIFICATE_ARN"
        echo_info "SSL certificate provided: $CERTIFICATE_ARN"
    fi
    
    if [ -n "$DOMAIN_NAME" ]; then
        PARAMETERS="$PARAMETERS DomainName=$DOMAIN_NAME"
        echo_info "Domain name provided: $DOMAIN_NAME"
    fi
    
    if [ -n "$ENVIRONMENT" ]; then
        PARAMETERS="$PARAMETERS Environment=$ENVIRONMENT"
    fi

    # Add agent configuration parameters
    if [ -n "$AGENT_RUNNER_TYPE" ]; then
        PARAMETERS="$PARAMETERS AgentRunnerType=$AGENT_RUNNER_TYPE"
        echo_info "Agent runner type: $AGENT_RUNNER_TYPE"
    fi

    if [ -n "$BEDROCK_MODEL" ]; then
        PARAMETERS="$PARAMETERS BedrockModel=$BEDROCK_MODEL"
    fi

    if [ -n "$BEDROCK_REGION" ]; then
        PARAMETERS="$PARAMETERS BedrockRegion=$BEDROCK_REGION"
    fi

    if [ -n "$BEDROCK_TEMPERATURE" ]; then
        PARAMETERS="$PARAMETERS BedrockTemperature=$BEDROCK_TEMPERATURE"
    fi

    if [ -n "$BEDROCK_MAX_TOKENS" ]; then
        PARAMETERS="$PARAMETERS BedrockMaxTokens=$BEDROCK_MAX_TOKENS"
    fi

    if [ -n "$FORCE_VALIDATION" ]; then
        PARAMETERS="$PARAMETERS ForceValidation=$FORCE_VALIDATION"
    fi

    aws cloudformation deploy \
        --template-file deployment/cloudformation-template.yaml \
        --stack-name $STACK_NAME \
        --parameter-overrides $PARAMETERS \
        --capabilities CAPABILITY_IAM \
        --region $AWS_REGION \
        --profile $AWS_PROFILE
    
    if [ $? -eq 0 ]; then
        echo_info "CloudFormation stack deployed successfully"
        
        # Wait for ECS service to stabilize
        echo_info "Waiting for ECS service to become stable..."
        aws ecs wait services-stable \
            --cluster $SERVICE_NAME-cluster \
            --services $SERVICE_NAME \
            --region $AWS_REGION \
            --profile $AWS_PROFILE
            
        if [ $? -eq 0 ]; then
            echo_info "ECS service is now stable"
        else
            echo_warn "ECS service may still be starting up. Check the AWS console for status."
        fi
    else
        echo_error "CloudFormation deployment failed"
        echo_error "Check the AWS CloudFormation console for detailed error information"
        exit 1
    fi
}

# Force ECS service update to use new Docker image
update_ecs_service() {
    echo_info "Forcing ECS service update to use new Docker image..."
    
    # Force new deployment of the service
    aws ecs update-service \
        --cluster $SERVICE_NAME-cluster \
        --service $SERVICE_NAME \
        --force-new-deployment \
        --region $AWS_REGION \
        --profile $AWS_PROFILE &> /dev/null
        
    if [ $? -eq 0 ]; then
        echo_info "ECS service update initiated"
        
        # Wait for the service to stabilize with new tasks
        echo_info "Waiting for new tasks to become healthy..."
        aws ecs wait services-stable \
            --cluster $SERVICE_NAME-cluster \
            --services $SERVICE_NAME \
            --region $AWS_REGION \
            --profile $AWS_PROFILE
            
        if [ $? -eq 0 ]; then
            echo_info "ECS service successfully updated with new image"
        else
            echo_warn "ECS service update may still be in progress. Check AWS console for status."
        fi
    else
        echo_warn "Failed to force ECS service update. Service may update automatically."
    fi
}

# Get service URL and endpoints
get_service_url() {
    echo_info "Getting deployment information..."
    
    # Get all stack outputs
    OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --profile $AWS_PROFILE \
        --query 'Stacks[0].Outputs')
    
    # Extract specific URLs
    SERVICE_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="ServiceURL") | .OutputValue')
    WEBHOOK_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="TwilioWebhookURL") | .OutputValue')
    WEBSOCKET_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="WebSocketURL") | .OutputValue')
    LOAD_BALANCER_DNS=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="LoadBalancerDNS") | .OutputValue')
    
    echo ""
    echo "🚀 Deployment Complete!"
    echo "======================"
    echo "🌐 Service URL: $SERVICE_URL"
    echo "📞 Twilio Webhook URL: $WEBHOOK_URL"
    echo "🔌 WebSocket URL: $WEBSOCKET_URL"
    echo "⚖️  Load Balancer DNS: $LOAD_BALANCER_DNS"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Configure your Twilio webhook URL: $WEBHOOK_URL"
    echo "2. Test health check: curl $SERVICE_URL"
    echo "3. Test TwiML endpoint: curl -X POST $WEBHOOK_URL"
    
    if [ -n "$DOMAIN_NAME" ] && [ -n "$CERTIFICATE_ARN" ]; then
        echo "4. Update DNS to point $DOMAIN_NAME to $LOAD_BALANCER_DNS"
    elif [ -z "$CERTIFICATE_ARN" ]; then
        echo "4. For production, configure SSL certificate:"
        echo "   export CERTIFICATE_ARN=\"arn:aws:acm:region:account:certificate/cert-id\""
        echo "   export DOMAIN_NAME=\"api.yourdomain.com\""
        echo "   ./deployment/deploy.sh"
    fi
}

# Main deployment function
main() {
    echo_info "Starting deployment of Twilio ConversationRelay to AWS Fargate..."
    
    # Pre-deployment checks
    check_env_vars
    check_aws_cli
    get_account_id
    
    # ECR setup
    setup_ecr
    
    # Build and push Docker image
    build_and_push
    
    # Deploy infrastructure (or update if already exists)
    deploy_stack
    
    # If stack already existed, force ECS service update to use new image
    if aws cloudformation describe-stacks --stack-name $STACK_NAME --profile $AWS_PROFILE &> /dev/null; then
        update_ecs_service
    fi
    
    # Get service information
    get_service_url
    
    echo_info "Deployment completed successfully! 🚀"
    echo_warn "Note: It may take a few minutes for the service to be fully available."
    echo_warn "For production use with HTTPS, you'll need to set up SSL/TLS certificate."
}

# Help function
show_help() {
    echo "Twilio ConversationRelay AWS Fargate Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Environment Variables (required):"
    echo "  TWILIO_ACCOUNT_SID    Your Twilio Account SID"
    echo "  TWILIO_AUTH_TOKEN     Your Twilio Auth Token"
    echo ""
    echo "Environment Variables (optional):"
    echo "  AWS_REGION              AWS region (default: us-east-1)"
    echo "  AWS_PROFILE             AWS profile (default: default)"
    echo "  DOMAIN_NAME             Custom domain (e.g., api.yourdomain.com)"
    echo "  CERTIFICATE_ARN         ACM certificate ARN for HTTPS"
    echo "  ENVIRONMENT             Environment name (default: development)"
    echo "  AGENT_RUNNER_TYPE       Agent type: strands, langgraph, openai (default: strands)"
    echo "  BEDROCK_MODEL           Bedrock model ID (default: claude-haiku-4-5)"
    echo "  BEDROCK_REGION          Bedrock region (default: us-east-2)"
    echo "  BEDROCK_TEMPERATURE     Model temperature 0-1 (default: 0)"
    echo "  BEDROCK_MAX_TOKENS      Max tokens (default: 4000)"
    echo "  FORCE_VALIDATION        Twilio validation: true/false (default: false)"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  Basic deployment:"
    echo "    export TWILIO_ACCOUNT_SID=AC..."
    echo "    export TWILIO_AUTH_TOKEN=..."
    echo "    ./deploy.sh"
    echo ""
    echo "  Production with custom domain:"
    echo "    export TWILIO_ACCOUNT_SID=AC..."
    echo "    export TWILIO_AUTH_TOKEN=..."
    echo "    export DOMAIN_NAME=owl-bank.deepakjayanna.net"
    echo "    export CERTIFICATE_ARN=arn:aws:acm:..."
    echo "    export AGENT_RUNNER_TYPE=strands"
    echo "    ./deploy.sh"
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main
        ;;
esac
