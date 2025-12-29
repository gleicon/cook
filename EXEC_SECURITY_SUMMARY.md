# Exec Resource Security Implementation Summary

## Overview

Enhanced the `cook/resources/exec.py` module with comprehensive security features to prevent command injection, shell injection, and other attack vectors.

**Key Achievement: Secure by Default**
- `safe_mode=True` (default)
- `security_level='strict'` (default)
- Prominent warnings when security is disabled

## Implementation Details

### 1. Security Defaults (cook/resources/exec.py:125-126)

```python
safe_mode: bool = True,  # SECURE BY DEFAULT
security_level: str = "strict",  # STRICT BY DEFAULT
```

**Rationale:** Users must explicitly opt-out of security, not opt-in.

### 2. Security Violation Exception

```python
class SecurityViolation(Exception):
    """Raised when command fails security validation."""
    pass
```

Clear exception type for security-related failures.

### 3. Security Levels (cook/resources/exec.py:38-42)

```python
class SecurityLevel(Enum):
    NONE = "none"        # No validation (dangerous)
    WARN = "warn"        # Warn but allow
    STRICT = "strict"    # Block dangerous patterns (DEFAULT)
```

### 4. Dangerous Pattern Detection

#### Shell Metacharacters (cook/resources/exec.py:98-109)
- `;` - Command chaining
- `&&`, `||` - Conditional execution
- `|` - Pipes (allowed with `allow_pipes=True`)
- `$()`, `` ` `` - Command substitution
- `${` - Variable expansion
- `>`, `<` - Redirects (allowed with `allow_redirects=True`)
- `\n`, `\r` - Newline injection

#### Dangerous Commands (cook/resources/exec.py:111-122)
- `rm -rf /` - Recursive delete from root
- `dd if=/dev/` - Disk operations
- `mkfs.` - Format filesystem
- Fork bombs
- `chmod 777` - World-writable
- `curl|bash`, `wget|sh` - Pipe to shell
- `eval` - Eval injection
- `/dev/sd[a-z]` - Direct disk access

### 5. Input Validation

#### Command Validation (_check_command_security)
- Scans for dangerous patterns
- Detects dangerous command patterns
- Checks for shell variable references

#### Path Validation (_check_path_security)
- Command injection characters
- Directory traversal (`..`)
- Null byte injection

#### Environment Variable Validation (_check_env_security)
- Valid variable names (alphanumeric + underscore)
- Command injection in values

### 6. Safe Command Construction (_build_command)

Uses `shlex.quote()` to safely quote:
- Environment variable values
- Working directory paths

```python
quoted_value = shlex.quote(value)
env_parts.append(f"{key}={quoted_value}")
```

### 7. Warning System

#### Initialization Warning (cook/resources/exec.py:173-184)
When `safe_mode=False`, displays RED warning:
```
======================================================================
⚠️  SECURITY WARNING: Exec resource 'name' is running in UNSAFE MODE
======================================================================
  safe_mode=False disables security validation
  Command: ...
  This is DANGEROUS and should only be used with fully trusted input.
  Set safe_mode=True (default) for security validation.
======================================================================
```

#### Execution Warning (cook/resources/exec.py:386-387)
Before each execution in unsafe mode:
```
⚠️  EXECUTING IN UNSAFE MODE: resource_name
```

### 8. Non-Destructive Features

#### Dry Run Mode
```python
Exec("preview", command="./deploy.sh", dry_run=True)
```
Output:
```
[DRY RUN] Would execute for 'preview':
  Command: ./deploy.sh
  (Not executed - dry_run=True)
```

#### Preview Method
```python
exec_resource = Exec("cmd", command="...")
print(exec_resource.preview())  # See final command
```

#### Security Report
```python
report = exec_resource.get_security_report()
# Returns: {resource, command, security_level, safe_mode, issues, risk_level}
```

## Attack Vectors Mitigated

### 1. Command Injection
**Before:**
```python
Exec("bad", command=f"echo {user_input}")  # VULNERABLE
```
**After:**
```python
Exec("bad", command=f"echo {user_input}")  # BLOCKED by safe_mode
```

### 2. Environment Variable Injection
**Before:**
```python
Exec("bad", 
     command="printenv",
     environment={"VAR": "value; rm -rf /"})  # VULNERABLE
```
**After:**
```python
# BLOCKED: environment: Variable 'VAR' contains dangerous character ';'
```

### 3. Working Directory Injection
**Before:**
```python
Exec("bad",
     command="ls",
     cwd="/tmp; malicious")  # VULNERABLE
```
**After:**
```python
# BLOCKED: cwd: Path contains dangerous character ';'
```

### 4. Guard Command Injection
**Before:**
```python
Exec("bad",
     command="echo test",
     unless="false; malicious")  # VULNERABLE
```
**After:**
```python
# BLOCKED: unless: Contains dangerous pattern ';'
```

## Files Modified

1. **cook/resources/exec.py** (371 lines)
   - Added SecurityLevel enum
   - Added SecurityViolation exception
   - Changed defaults: safe_mode=True, security_level='strict'
   - Added _validate_security() method
   - Added _check_command_security() method
   - Added _check_path_security() method
   - Added _check_env_security() method
   - Added _build_command() with shlex.quote()
   - Added preview() method
   - Added get_security_report() method
   - Added warning messages

## Files Created

1. **examples/exec_security_demo.py** (298 lines)
   - Comprehensive security demonstration
   - 8 sections covering all security features
   - Tests for all attack vectors
   - Best practices examples

2. **EXEC_SECURITY.md** (500+ lines)
   - Complete security guide
   - Attack vectors and mitigations
   - Safe usage patterns
   - Migration guide
   - Security checklist

3. **EXEC_SECURITY_SUMMARY.md** (this file)
   - Implementation summary
   - Technical details

## Security Testing

All tests pass in the demo:

```bash
cd /Users/gleicon/code/python/cook
PYTHONPATH=/Users/gleicon/code/python/cook /opt/homebrew/bin/python3 examples/exec_security_demo.py
```

Results:
- ✓ Dry-run mode works
- ✓ Safe commands pass validation
- ✓ Dangerous patterns blocked by default
- ✓ Command injection blocked (`;`, `&&`, `||`)
- ✓ Command substitution blocked (`$()`, `` ` ``)
- ✓ Environment injection blocked
- ✓ Path injection blocked
- ✓ Curl|bash detected
- ✓ Warning system works
- ✓ Security levels work
- ✓ Preview works
- ✓ Security reports work

## Backwards Compatibility

### Breaking Change
Existing code with dangerous patterns will now fail by default.

### Migration Path

**Option 1: Fix the code (recommended)**
```python
# Old (now blocked)
Exec("old", command="echo test && ls")

# New
Exec("echo", command="echo test")
Exec("list", command="ls")
```

**Option 2: Explicitly allow patterns**
```python
Exec("cmd", 
     command="ps aux | grep nginx",
     allow_pipes=True)  # Explicit opt-in
```

**Option 3: Disable safe mode (not recommended)**
```python
Exec("legacy",
     command="complex && command",
     safe_mode=False)  # Shows RED warnings
```

## Performance Impact

- Minimal: Validation runs once at initialization
- No runtime overhead after validation
- Dry-run mode has zero execution cost

## Security Principles Applied

1. **Secure by Default** - Users must opt-out, not opt-in
2. **Defense in Depth** - Multiple validation layers
3. **Fail Secure** - Block on suspicious patterns
4. **Clear Warnings** - Prominent RED warnings when unsafe
5. **Non-Destructive Testing** - dry_run and preview modes
6. **Least Privilege** - Validate all inputs
7. **Visibility** - Security reports for auditing

## Threat Model

### In Scope
- Command injection via parameters
- Shell metacharacter exploitation
- Environment variable injection
- Path traversal
- Guard command injection

### Out of Scope
- TOCTOU (Time-of-check/Time-of-use) races
- Privilege escalation (depends on sudo/setuid)
- Network-based attacks
- Social engineering

## Future Enhancements

Potential additions:
- [ ] Command allowlist/denylist
- [ ] Regex-based command validation
- [ ] Integration with secret managers
- [ ] Audit logging to syslog
- [ ] Sandbox execution (containers)
- [ ] Rate limiting for exec resources
- [ ] Command signature verification

## References

- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
- [CWE-88: Argument Injection](https://cwe.mitre.org/data/definitions/88.html)
- Python `shlex.quote()` documentation
- SECURITY.md (project security policy)

## Testing Commands

```bash
# Run security demo
cd /Users/gleicon/code/python/cook
PYTHONPATH=$(pwd) /opt/homebrew/bin/python3 examples/exec_security_demo.py

# Test specific attack vector
PYTHONPATH=$(pwd) /opt/homebrew/bin/python3 -c "
from cook import Exec
try:
    Exec('test', command='echo test; rm -rf /')
except Exception as e:
    print(f'Blocked: {type(e).__name__}')
"
```

## Conclusion

The Exec resource is now **secure by default** with comprehensive protection against command injection attacks. Users must explicitly opt-out of security features and receive prominent warnings when doing so.

This implementation follows security best practices and provides multiple layers of defense while maintaining flexibility for legitimate use cases.

---

**Implementation Date:** December 29, 2024  
**Python Version:** 3.13.2  
**Status:** Complete and tested
