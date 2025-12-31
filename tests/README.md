# Cook Testing

## Quick Start

```bash
pytest tests/unit/                  # Unit tests
sudo pytest tests/integration/      # Integration tests
./scripts/run-vm-tests.sh           # VM tests (Lima)
```

## Structure

```sh
tests/
├── unit/                   # Fast, isolated tests
├── integration/            # System tests (requires sudo)
├── lima/                   # VM configurations
└── fixtures/               # Test data
```

## Unit Tests

Fast tests, no special permissions.

```bash
pytest tests/unit/
pytest tests/unit/test_resources.py
pytest tests/unit/test_resources.py::TestFileResource::test_file_check_missing
pytest tests/unit/ --cov=cook --cov-report=html
```

## Integration Tests

System interaction tests, requires sudo.

```bash
sudo pytest tests/integration/
sudo pytest tests/integration/ -v -s
```

## Lima VM Tests

Clean Ubuntu environment.

```bash
./scripts/run-vm-tests.sh

# Manual
limactl create --name cook-test tests/lima/ubuntu.yaml
limactl start cook-test
limactl copy . cook-test:/tmp/cook/
limactl shell cook-test
cd /tmp/cook
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[all]'
pytest tests/
limactl stop cook-test
limactl delete cook-test
```

## Adding Tests

Unit tests (`tests/unit/test_*.py`):
- Test individual functions
- Mock external dependencies
- Should run in < 1 second

Integration tests (`tests/integration/test_*.py`):
- Test full workflows
- Use real filesystem/packages
- May require sudo

## Test Patterns

```python
class TestFeature:
    def setup_method(self):
        self.temp_file = tempfile.mktemp()

    def teardown_method(self):
        if os.path.exists(self.temp_file):
            os.unlink(self.temp_file)

@pytest.mark.parametrize("command,expected", [
    ("apt install nginx", "package"),
    ("systemctl start nginx", "service"),
])
def test_parse(command, expected):
    parser = CommandParser()
    result = parser.parse(command)
    assert result.type == expected
```

## Debugging

```bash
pytest tests/ -v -s              # Verbose
pytest tests/ -x                 # Stop on first failure
pytest tests/ --pdb              # Debugger on failure
pytest tests/ --cov=cook --cov-report=term-missing
```

## Performance

Target times:

- Unit tests: < 10 seconds
- Integration tests: < 2 minutes
- VM tests: < 10 minutes

Mark slow tests:

```python
@pytest.mark.slow
def test_slow_operation():
    pass
```

Skip slow tests:

```bash
pytest -m "not slow"
```

## Coverage

Minimum targets:

- Core resources: 80%
- CLI: 70%
- Overall: 75%

```bash
pytest tests/ --cov=cook --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

Permission errors:

```bash
sudo -E pytest tests/integration/
```

Lima networking:

```bash
limactl stop cook-test
limactl start cook-test
```

Clean state:

```bash
rm -rf ~/.cook/
rm -f /tmp/cook-test*
```
