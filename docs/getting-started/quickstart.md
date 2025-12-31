# Quick Start

This guide walks through creating your first Cook configuration.

## Your First Configuration

Create a file named `server.py`:

```python
from cook import File, Package, Service

# Install nginx
Package("nginx")

# Configure nginx
File("/etc/nginx/nginx.conf",
     content="""
     events { worker_connections 1024; }
     http {
         server {
             listen 80;
             location / {
                 return 200 'Hello from Cook';
             }
         }
     }
     """,
     mode=0o644)

# Ensure nginx is running
Service("nginx", running=True, enabled=True)
```

## Preview Changes

See what Cook will do without making changes:

```bash
sudo cook plan server.py
```

Output:

```
Planning resources...

[Package] nginx
  Action: create
  Changes:
    type: None → nginx

[File] /etc/nginx/nginx.conf
  Action: create
  Changes:
    content: None → <content>
    mode: None → 0o644

[Service] nginx
  Action: update
  Changes:
    running: False → True
    enabled: False → True

Summary: 3 resources, 3 changes
```

## Apply Configuration

Execute the changes:

```bash
sudo cook apply server.py
```

Output:

```
Applying changes...

[Package] nginx: Installing
[File] /etc/nginx/nginx.conf: Creating
[Service] nginx: Starting and enabling

Complete: 3 resources applied successfully
```

## Verify

Check that nginx is running:

```bash
curl http://localhost
```

Expected output:

```
Hello from Cook
```

## Idempotency

Run apply again:

```bash
sudo cook plan server.py
```

Output:

```
No changes needed
```

Cook detects that the system already matches the desired state.

## Make Changes

Edit `server.py` to change the response:

```python
File("/etc/nginx/nginx.conf",
     content="""
     events { worker_connections 1024; }
     http {
         server {
             listen 80;
             location / {
                 return 200 'Updated response';
             }
         }
     }
     """,
     mode=0o644)
```

Plan and apply:

```bash
sudo cook plan server.py
sudo cook apply server.py
```

Cook updates only the changed file and reloads nginx.

## See also

- [Core Concepts](concepts.md)
- [Resource Reference](../resources/index.md)
- [Examples](../examples/minimidia.md)
