# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Considerations

Cook is a configuration management tool that executes system commands with elevated privileges. This document outlines security considerations and best practices.

### Threat Model

Cook configs are **Python code** that runs with the same privileges as the cook process. This means:

 **Safe for:**
- Trusted infrastructure-as-code repositories
- Internal configuration management
- Development/testing environments
- Automated deployments with code review

❌ **NOT safe for:**
- Running untrusted third-party configs
- Accepting config code from users
- Public config repositories without review
- Unreviewed automated config generation

### Security Best Practices

#### 1. Code Review

**Always review Cook configs before running them.**

```bash
# Review before applying
cat server.py
cook plan server.py  # See what will change
cook apply server.py  # Apply after review
```

#### 2. Use Least Privilege

Run Cook with minimum required privileges:

```bash
# Prefer user-level operations
cook apply user-config.py

# Only use sudo when necessary
sudo cook apply system-config.py
```

#### 3. Validate Input

Never pass unsanitized user input to resources:

```python
# ❌ DANGEROUS - Command injection risk
user_input = sys.argv[1]  # Untrusted!
Exec("bad", command=f"echo {user_input}")

#  SAFE - Validate and sanitize
import re
user_input = sys.argv[1]
if re.match(r'^[a-zA-Z0-9_-]+$', user_input):
    File(f"/var/www/{user_input}", ensure="directory")
else:
    raise ValueError("Invalid input")
```

#### 4. Exec Resource Security

The `Exec` resource uses `shell=True` to support pipes and redirects. **Only use with trusted input.**

```python
#  SAFE - Hardcoded command
Exec("backup",
     command="tar czf /backup/data.tar.gz /var/data")

#  SAFE - Sanitized variables
backup_dir = "/var/data"  # Controlled by you
Exec("backup",
     command=f"tar czf /backup/data.tar.gz {backup_dir}")

# ❌ DANGEROUS - User input
filename = input("Enter filename: ")  # User input!
Exec("backup",
     command=f"tar czf {filename}")  # INJECTION RISK!
```

#### 5. File Permissions

Be careful with file permissions and ownership:

```python
# ❌ DANGEROUS - World-writable
File("/etc/app/config.conf",
     mode=0o666)  # Anyone can modify!

#  SAFE - Restricted permissions
File("/etc/app/config.conf",
     mode=0o644,  # Read-only for others
     owner="root",
     group="app")
```

#### 6. Secret Management

**Never hardcode secrets in Cook configs.**

```python
# ❌ DANGEROUS - Secrets in code
File("/etc/app/config.conf",
     content=f"api_key=sk_live_12345...")  # Secret in git!

#  SAFE - Use environment variables
import os
api_key = os.environ.get("API_KEY")
if not api_key:
    raise ValueError("API_KEY not set")

File("/etc/app/config.conf",
     content=f"api_key={api_key}")

#  BETTER - Use dedicated secret management
# - HashiCorp Vault
# - AWS Secrets Manager
# - Kubernetes Secrets
```

#### 7. Network Security

When using SSH transport, use key-based authentication:

```bash
#  SAFE - Key-based auth
cook apply server.py --host prod-1 --key ~/.ssh/id_ed25519

# ❌ AVOID - Password auth (if implemented)
cook apply server.py --host prod-1 --password "..."  # Logged in history!
```

### Resource-Specific Security

#### Package Resource

- Uses list arguments (no shell injection)
- Validates package names
- Uses package manager's built-in security

```python
# Safe - list arguments used internally
Package("nginx")
Package("python3", packages=["python3", "python3-pip"])
```

#### File Resource

- Validates paths
- Respects file permissions
- Template rendering is sandboxed (Jinja2)

```python
# Safe - template variables are escaped
File("/etc/nginx/site.conf",
     template="site.j2",
     vars={"domain": user_input})  # Jinja2 auto-escapes
```

#### Service Resource

- Uses list arguments (no shell injection)
- Only supports system service managers
- Validates service names

```python
# Safe - list arguments used
Service("nginx", running=True)
```

#### Exec Resource

- **Uses shell=True** - command injection risk
- Only use with trusted input
- Consider alternatives (Package, File, Service)

### Reporting Security Issues

**Please DO NOT open public issues for security vulnerabilities.**

Instead, email security issues to: [your-email@example.com]

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

### Security Updates

Subscribe to security announcements:
- GitHub Watch → Custom → Security alerts
- GitHub Releases (security patches marked)

### Audit Trail

When state persistence is implemented, Cook will track:
- Who applied changes (username, hostname)
- When changes were applied (timestamp)
- What changed (resource state diff)
- Which config file was used

This provides an audit trail for compliance and forensics.

### Defense in Depth

**Additional security layers:**

1. **File system permissions** - Restrict who can write Cook configs
2. **Git hooks** - Validate configs before commit
3. **CI/CD pipelines** - Automated review and testing
4. **Infrastructure policies** - OPA, Sentinel, etc.
5. **Network segmentation** - Limit where Cook can connect
6. **Monitoring** - Alert on unexpected changes

### Future Security Features

Planned security enhancements:

- [ ] Config signing and verification
- [ ] Dry-run mode with detailed output
- [ ] Resource allowlist/denylist
- [ ] Sandbox execution (Docker/Firecracker)
- [ ] Audit logging to syslog/journal
- [ ] Integration with secret managers
- [ ] RBAC for multi-user environments

### Comparison with Other Tools

| Tool | Execution Model | Security |
|------|----------------|----------|
| **Cook** | Python code (trusted) | Code review required |
| **Ansible** | YAML + Jinja2 | Safer (limited execution) |
| **Terraform** | HCL (declarative) | Safer (no arbitrary code) |
| **Chef** | Ruby code | Similar to Cook |
| **Puppet** | DSL | Safer (limited execution) |
| **Salt** | YAML + Jinja2 | Similar to Ansible |

**Trade-off:** Cook prioritizes flexibility (full Python) over sandboxing. This requires careful code review.

### Acknowledgments

We appreciate responsible disclosure. Security researchers who report valid vulnerabilities will be acknowledged (with permission) in:

- SECURITY.md
- Release notes
- Project README

Thank you for helping keep Cook secure!

---

**Last Updated:** December 27, 2024
**Next Review:** March 27, 2025
