#!/bin/bash

# System Test Runner for Nextcloud Upload Daemon
# This script sets up a local Nextcloud instance and runs comprehensive system tests

set -e

echo "🚀 Starting Nextcloud Upload Daemon System Tests..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker and Docker Compose are available
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose plugin is not installed"
        print_error "Please install Docker Compose V2: https://docs.docker.com/compose/install/"
        exit 1
    fi

    print_status "Docker and Docker Compose are available"
}

# Start Nextcloud test instance
start_nextcloud() {
    print_status "Starting Nextcloud test instance..."
    
    # Stop any existing containers
    docker compose -f docker-compose.test.yml down 2>/dev/null || true
    
    # Start services
    docker compose -f docker-compose.test.yml up -d
    
    # Wait for services to be healthy
    print_status "Waiting for Nextcloud to be ready (this may take a few minutes)..."
    
    # Wait up to 5 minutes for Nextcloud to be ready
    timeout 300 bash -c '
        while true; do
            if curl -s -f http://localhost:8080/status.php >/dev/null 2>&1; then
                status=$(curl -s http://localhost:8080/status.php | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get(\"installed\", False) and not data.get(\"maintenance\", True))")
                if [ "$status" = "True" ]; then
                    echo "Nextcloud is ready!"
                    break
                fi
            fi
            echo "Still waiting for Nextcloud..."
            sleep 10
        done
    '
    
    print_status "Nextcloud is ready at http://localhost:8080"
    print_status "Admin credentials: admin / admin123"
}

# Stop Nextcloud test instance
stop_nextcloud() {
    print_status "Stopping Nextcloud test instance..."
    docker compose -f docker-compose.test.yml down
    
    # Optionally remove volumes (uncomment if you want clean slate each time)
    # docker compose -f docker-compose.test.yml down -v
}

# Run system tests
run_tests() {
    print_status "Running system tests..."
    
    # Make sure we have all dependencies
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Install dependencies if needed
    pip install -r requirements.txt >/dev/null 2>&1
    
    # Run the tests
    export CI=true
    python system_tests.py -v
    
    if [ $? -eq 0 ]; then
        print_status "✅ All system tests passed!"
    else
        print_error "❌ Some system tests failed!"
        return 1
    fi
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    stop_nextcloud
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    # Parse command line arguments
    SKIP_DOCKER=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-docker)
                SKIP_DOCKER=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--skip-docker] [--help]"
                echo ""
                echo "Options:"
                echo "  --skip-docker    Skip starting/stopping Docker containers (assume already running)"
                echo "  --help, -h      Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_docker
    
    # Start Nextcloud if not skipping Docker
    if [ "$SKIP_DOCKER" = false ]; then
        start_nextcloud
    else
        print_warning "Skipping Docker setup - assuming Nextcloud is already running"
    fi
    
    # Run tests
    run_tests
    
    print_status "🎉 System tests completed successfully!"
}

# Run main function
main "$@"