#!/bin/bash
# Automated test runner for Cook using Lima VM
# Creates clean Ubuntu VM, runs tests, reports results

set -e

VM_NAME="cook-test"
LIMA_CONFIG="tests/lima/ubuntu.yaml"
TEST_DIR="/tmp/cook-test"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Lima is installed
if ! command -v limactl &> /dev/null; then
    log_error "Lima not installed. Install with: brew install lima"
    exit 1
fi

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    limactl stop "$VM_NAME" 2>/dev/null || true
    limactl delete "$VM_NAME" 2>/dev/null || true
}

# Set up trap for cleanup on exit
trap cleanup EXIT

# Check if VM already exists
if limactl list | grep -q "$VM_NAME"; then
    log_warn "VM $VM_NAME already exists. Deleting..."
    limactl stop "$VM_NAME" 2>/dev/null || true
    limactl delete "$VM_NAME" 2>/dev/null || true
fi

# Create and start VM
log_info "Creating VM from $LIMA_CONFIG..."
limactl create --name "$VM_NAME" "$LIMA_CONFIG"

log_info "Starting VM..."
limactl start "$VM_NAME"

# Wait for VM to be ready
log_info "Waiting for VM to be ready..."
sleep 5

# Copy Cook source to VM
log_info "Copying Cook source to VM..."
limactl shell "$VM_NAME" mkdir -p "$TEST_DIR"
limactl copy . "$VM_NAME:$TEST_DIR/"

# Install Cook in VM
log_info "Installing Cook in VM..."
limactl shell "$VM_NAME" bash -c "cd $TEST_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[all]'"

# Run unit tests
log_info "Running unit tests..."
limactl shell "$VM_NAME" bash -c "cd $TEST_DIR && source .venv/bin/activate && pytest tests/unit/ -v" || {
    log_error "Unit tests failed"
    exit 1
}

# Run integration tests
log_info "Running integration tests..."
limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && pytest tests/integration/ -v" || {
    log_error "Integration tests failed"
    exit 1
}

# Test example configs
log_info "Testing example configs..."
limactl shell "$VM_NAME" bash -c "cd $TEST_DIR && source .venv/bin/activate && cook plan examples/simple.py" || {
    log_error "Example plan failed"
    exit 1
}

limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook apply examples/simple.py --yes" || {
    log_error "Example apply failed"
    exit 1
}

# Test idempotency
log_info "Testing idempotency..."
limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook apply examples/simple.py --yes" || {
    log_error "Idempotency test failed"
    exit 1
}

# Test drift detection
log_info "Testing drift detection..."
limactl shell "$VM_NAME" bash -c "echo 'Modified' > /tmp/cook-test.txt"
limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook check-drift" || {
    log_warn "Drift detection test completed with drift (expected)"
}

# Test state commands
log_info "Testing state commands..."
limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook state list"
limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook state show 'file:/tmp/cook-test.txt'"

log_info "All tests passed!"
log_info "VM will be cleaned up automatically"
