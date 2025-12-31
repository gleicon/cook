# Core Concepts

Cook is built around a few core concepts that make configuration management predictable and testable.

## Resources

Resources represent desired system state. Each resource type manages a specific aspect of the system.

## Check-Plan-Apply Pattern

Cook uses a three-phase execution model:

1. **Check**: Inspect current system state
2. **Plan**: Compare current to desired state
3. **Apply**: Execute changes to reach desired state

This pattern enables:

- Dry-run mode (plan without apply)
- Drift detection
- Predictable changes

## Idempotency

Resources are idempotent. Running the same configuration multiple times produces the same result.

## Transport

Transport abstracts local vs remote execution. The same configuration works locally or over SSH.

## State Tracking

Optional state persistence enables:

- Resource history
- Drift detection
- Change auditing

## Platform Detection

Cook automatically detects the operating system and adjusts behavior accordingly.
