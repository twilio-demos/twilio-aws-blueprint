#!/bin/bash

# Setup script for Twilio ConversationRelay Voice Agent
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo ""
echo "🚀 Twilio ConversationRelay Voice Agent Setup"
echo "============================================="
echo ""

# Check prerequisites
echo_info "Checking prerequisites..."

if ! command_exists python3; then
    echo_error "Python 3 is not installed. Please install Python 3.13 first."
    exit 1
fi

if ! command_exists pip; then
    echo_error "pip is not installed. Please install pip first."
    exit 1
fi

if ! command_exists docker; then
    echo_warn "Docker is not installed. You'll need it for deployment."
    echo_warn "Install Docker from: https://docs.docker.com/get-docker/"
fi

if ! command_exists aws; then
    echo_warn "AWS CLI is not installed. You'll need it for deployment."
    echo_warn "Install AWS CLI from: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
fi

echo_success "Basic prerequisites check completed"
echo ""

# Setup Python environment
echo_info "Setting up Python environment..."

if [ ! -d "venv" ]; then
    echo_info "Creating virtual environment..."
    python3 -m venv venv
    echo_success "Virtual environment created"
fi

echo_info "Activating virtual environment..."
source venv/bin/activate

echo_info "Installing Python dependencies..."
pip install -r requirements.txt

echo_success "Python environment setup completed"
echo ""

# Setup environment file
echo_info "Setting up environment configuration..."

if [ ! -f ".env" ]; then
    echo_info "Creating .env file from template..."
    cp .env.example .env
    echo_success ".env file created"
    echo ""
    echo_warn "⚠️  IMPORTANT: Please edit the .env file with your credentials:"
    echo "1. Set your TWILIO_ACCOUNT_SID"
    echo "2. Set your TWILIO_AUTH_TOKEN"
    echo "3. Configure AWS credentials and region (see options below)"
    echo ""
else
    echo_warn ".env file already exists. Please verify your configuration."
    echo ""
fi

# Check existing AWS profiles
if command_exists aws; then
    echo_info "Existing AWS profiles:"
    aws configure list-profiles 2>/dev/null || echo "  No profiles found"
    echo ""
fi

# AWS Configuration
echo_info "AWS Configuration Options:"
echo ""
echo "Option 1: AWS CLI Profile Configuration (Recommended)"
echo "  # Use existing profile from the list output above, if present"
echo ""
echo "  # Or create a new profile for this project:"
echo "  aws configure sso"
echo ""
echo "  # Then set AWS_PROFILE and AWS_REGION in your .env file"
echo ""
echo "Option 2: Access Key"
echo "  export AWS_ACCESS_KEY_ID=\"your-access-key\""
echo "  export AWS_SECRET_ACCESS_KEY=\"your-secret-key\""
echo "  export AWS_REGION=\"us-east-1\""
echo ""

# Test local setup
echo_info "Testing local setup..."

echo_info "You can now test the application locally:"
echo "1. Edit the .env file with your Twilio and AWS credentials"
echo "2. Run: ./dev.sh"
echo "3. Test: curl http://localhost:8000/"
echo ""

echo_info "For Docker testing:"
echo "1. Run: docker-compose up --build"
echo "2. Test: curl http://localhost:8000/"
echo ""

echo_info "For AWS deployment:"
echo "1. Configure AWS credentials (see options above)"
echo "2. Edit .env with your Twilio credentials"
echo "3. Run: ./deployment/deploy.sh"
echo ""

echo_success "🎉 Setup completed! Please configure your credentials in the .env file."
echo ""
echo "📚 For detailed instructions, see README.md"
