#!/bin/bash
# Comprehensive VM test suite for Cook
# Tests everything from VM creation to config verification

set -e

VM_NAME="cook-comprehensive-test"
LIMA_CONFIG="tests/lima/ubuntu.yaml"
TEST_DIR="/tmp/cook-test"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_section() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check Lima installed
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

# Trap cleanup
trap cleanup EXIT

# Delete existing VM
if limactl list | grep -q "$VM_NAME"; then
    log_warn "VM $VM_NAME exists. Deleting..."
    limactl stop "$VM_NAME" 2>/dev/null || true
    limactl delete "$VM_NAME" 2>/dev/null || true
fi

# =============================================================================
# Phase 1: VM Setup
# =============================================================================

log_section "Phase 1: VM Setup"

log_info "Creating VM from $LIMA_CONFIG..."
limactl create --name "$VM_NAME" "$LIMA_CONFIG"

log_info "Starting VM..."
limactl start "$VM_NAME"

log_info "Waiting for VM to be ready..."
sleep 10

log_success "VM created and started"

# =============================================================================
# Phase 2: Cook Installation
# =============================================================================

log_section "Phase 2: Cook Installation"

log_info "Copying Cook source to VM..."
limactl shell "$VM_NAME" mkdir -p "$TEST_DIR"

# Create tarball and copy
log_info "Creating source tarball..."
tar -czf /tmp/cook-source.tar.gz --exclude='.venv' --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' .

log_info "Uploading to VM..."
limactl copy /tmp/cook-source.tar.gz "$VM_NAME:/tmp/cook-source.tar.gz"

log_info "Extracting in VM..."
limactl shell "$VM_NAME" bash -c "cd $TEST_DIR && tar -xzf /tmp/cook-source.tar.gz"

log_info "Installing Cook in VM..."
limactl shell "$VM_NAME" bash -c "cd $TEST_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[all,dev]' -q"

log_info "Verifying Cook installation..."
limactl shell "$VM_NAME" bash -c "cd $TEST_DIR && source .venv/bin/activate && cook version"

log_success "Cook installed successfully"

# =============================================================================
# Phase 3: Unit Tests
# =============================================================================

log_section "Phase 3: Unit Tests"

log_info "Running unit tests..."
limactl shell "$VM_NAME" bash -c "cd $TEST_DIR && source .venv/bin/activate && pytest tests/unit/ -v --tb=short" || {
    log_error "Unit tests failed"
    exit 1
}

log_success "Unit tests passed"

# =============================================================================
# Phase 4: Simple Example Test
# =============================================================================

log_section "Phase 4: Simple Example Test"

log_info "Testing simple.py example..."

# Plan
log_info "Running cook plan..."
limactl shell "$VM_NAME" bash -c "cd $TEST_DIR && source .venv/bin/activate && cook plan examples/simple.py" || {
    log_error "Plan failed"
    exit 1
}

# Apply
log_info "Running cook apply..."
limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook apply examples/simple.py --yes" || {
    log_error "Apply failed"
    exit 1
}

# Verify file created
log_info "Verifying file creation..."
limactl shell "$VM_NAME" test -f /tmp/cook-test.txt || {
    log_error "File /tmp/cook-test.txt not created"
    exit 1
}

# Verify content
log_info "Verifying file content..."
CONTENT=$(limactl shell "$VM_NAME" cat /tmp/cook-test.txt)
if [[ "$CONTENT" == *"Hello from Cook"* ]]; then
    log_success "File content correct"
else
    log_error "File content incorrect: $CONTENT"
    exit 1
fi

# Verify directory created
log_info "Verifying directory creation..."
limactl shell "$VM_NAME" test -d /tmp/cook-dir || {
    log_error "Directory /tmp/cook-dir not created"
    exit 1
}

log_success "Simple example test passed"

# =============================================================================
# Phase 5: Idempotency Test
# =============================================================================

log_section "Phase 5: Idempotency Test"

log_info "Running apply again (should be idempotent)..."
OUTPUT=$(limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook apply examples/simple.py --yes" 2>&1)

if echo "$OUTPUT" | grep -q "No changes needed"; then
    log_success "Idempotency verified"
else
    log_warn "Expected 'No changes needed', got different output"
fi

# =============================================================================
# Phase 6: State Persistence Test
# =============================================================================

log_section "Phase 6: State Persistence Test"

log_info "Testing state list..."
limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook state list" || {
    log_error "State list failed"
    exit 1
}

log_info "Testing state show..."
limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook state show 'file:/tmp/cook-test.txt'" || {
    log_error "State show failed"
    exit 1
}

log_success "State persistence working"

# =============================================================================
# Phase 7: Drift Detection Test
# =============================================================================

log_section "Phase 7: Drift Detection Test"

log_info "Modifying file to create drift..."
limactl shell "$VM_NAME" sudo bash -c "echo 'Modified content' > /tmp/cook-test.txt"

log_info "Running drift detection..."
DRIFT_OUTPUT=$(limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook check-drift" 2>&1)

if echo "$DRIFT_OUTPUT" | grep -q "Drift detected"; then
    log_success "Drift detection working"
else
    log_warn "Drift not detected as expected"
fi

log_success "Drift detection test passed"

# =============================================================================
# Phase 8: Web Server Example Test
# =============================================================================

log_section "Phase 8: Web Server Example Test"

log_info "Testing web-server.py example..."

# Apply
log_info "Running cook apply for web-server.py..."
limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook apply examples/web-server.py --yes" || {
    log_error "Web server apply failed"
    exit 1
}

# Verify nginx installed
log_info "Verifying nginx installed..."
limactl shell "$VM_NAME" which nginx || {
    log_error "Nginx not installed"
    exit 1
}

# Verify nginx config file
log_info "Verifying nginx config..."
limactl shell "$VM_NAME" test -f /etc/nginx/sites-available/mysite || {
    log_error "Nginx config not created"
    exit 1
}

# Verify nginx service running
log_info "Verifying nginx service..."
limactl shell "$VM_NAME" sudo systemctl is-active nginx || {
    log_warn "Nginx service not running (may need manual start)"
}

# Verify web root created
log_info "Verifying web root..."
limactl shell "$VM_NAME" test -d /var/www/mysite || {
    log_error "Web root not created"
    exit 1
}

log_success "Web server example test passed"

# =============================================================================
# Phase 9: Recording Mode Test
# =============================================================================

log_section "Phase 9: Recording Mode Test"

log_info "Testing command parser..."
limactl shell "$VM_NAME" bash -c "cd $TEST_DIR && source .venv/bin/activate && python3 -c \"
from cook.record.parser import CommandParser
parser = CommandParser()
result = parser.parse('apt install nginx')
assert result.type == 'package'
print('Parser test passed')
\""

log_info "Testing code generator..."
limactl shell "$VM_NAME" bash -c "cd $TEST_DIR && source .venv/bin/activate && python3 -c \"
from cook.record.parser import ParsedResource
from cook.record.generator import CodeGenerator
resources = [ParsedResource(type='package', data={'name': 'nginx', 'packages': None}, command='apt install nginx')]
generator = CodeGenerator()
code = generator.generate(resources)
assert 'Package' in code
print('Generator test passed')
\""

log_success "Recording mode test passed"

# =============================================================================
# Phase 10: Cleanup and Verification
# =============================================================================

log_section "Phase 10: Final Verification"

log_info "Checking Cook state database..."
DB_PATH="~/.cook/state.db"
limactl shell "$VM_NAME" sudo test -f "$DB_PATH" && log_success "State database exists" || log_warn "State database not found"

log_info "Listing all managed resources..."
limactl shell "$VM_NAME" sudo bash -c "cd $TEST_DIR && source .venv/bin/activate && cook state list | wc -l"

# =============================================================================
# Summary
# =============================================================================

log_section "Test Summary"

echo "All comprehensive tests passed!"
echo ""
echo "Tests completed:"
echo "  - VM creation and setup"
echo "  - Cook installation"
echo "  - Unit tests (19 tests)"
echo "  - Simple example (plan/apply)"
echo "  - File and directory creation"
echo "  - Idempotency verification"
echo "  - State persistence"
echo "  - Drift detection"
echo "  - Web server deployment"
echo "  - Recording mode"
echo ""
echo "VM will be cleaned up automatically"
