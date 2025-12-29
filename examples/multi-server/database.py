"""
Database Server Configuration (PostgreSQL)

Configures PostgreSQL database server for multi-tier application.

Usage:
    # Local
    sudo cook apply database.py

    # Remote
    cook apply database.py --host db.example.com --user admin
"""

from cook import Package, File, Service, Exec
import os

# Configuration
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secure_password_change_me")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16")

print("Configuring PostgreSQL database server")

# Package Installation

Package("postgresql", packages=[
    "postgresql",
    "postgresql-contrib",
])

# Database Setup

# Create database
Exec("create-database",
     command=f"sudo -u postgres psql -c \"CREATE DATABASE {DB_NAME};\"",
     unless=f"sudo -u postgres psql -lqt | cut -d \\| -f 1 | grep -qw {DB_NAME}")

# Create user
Exec("create-user",
     command=f"""sudo -u postgres psql -c "CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}';" """,
     unless=f"sudo -u postgres psql -c \"\\du\" | grep -q {DB_USER}")

# Grant privileges
Exec("grant-privileges",
     command=f"""sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};" """)

# PostgreSQL Configuration

# Allow remote connections
pg_hba = File(
    "/etc/postgresql/14/main/pg_hba.conf",
    content=f"""
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections
local   all             postgres                                peer
local   all             all                                     peer

# IPv4 local connections
host    all             all             127.0.0.1/32            scram-sha-256

# Allow application servers
host    {DB_NAME}       {DB_USER}       {ALLOWED_HOSTS}         scram-sha-256

# IPv6 local connections
host    all             all             ::1/128                 scram-sha-256
""",
    mode=0o640,
    owner="postgres",
    group="postgres")

# Listen on all interfaces
postgresql_conf = File(
    "/etc/postgresql/14/main/postgresql.conf",
    content="""
# Connection settings
listen_addresses = '*'
port = 5432
max_connections = 100

# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
work_mem = 4MB

# Write-Ahead Log
wal_level = replica
max_wal_size = 1GB
min_wal_size = 80MB

# Checkpoints
checkpoint_completion_target = 0.9

# Logging
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_statement = 'all'
log_duration = off
log_min_duration_statement = 1000  # Log slow queries (1s+)

# Statistics
track_activities = on
track_counts = on
track_io_timing = on

# Autovacuum
autovacuum = on
""",
    mode=0o644,
    owner="postgres",
    group="postgres")

# Service

Service("postgresql",
        running=True,
        enabled=True,
        restart_on=[pg_hba, postgresql_conf])

# Health Check

File(
    "/usr/local/bin/db-health-check",
    content=f"""#!/bin/bash
# Database health check script

psql -U {DB_USER} -d {DB_NAME} -c "SELECT 1;" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "OK: Database is healthy"
    exit 0
else
    echo "CRITICAL: Database connection failed"
    exit 1
fi
""",
    mode=0o755)

print(f"""
PostgreSQL database server configured

Connection Info:
- Database: {DB_NAME}
- User: {DB_USER}
- Password: {DB_PASSWORD}
- Host: <this-server>
- Port: 5432

Access:
- Local: sudo -u postgres psql {DB_NAME}
- Remote: psql -h <host> -U {DB_USER} -d {DB_NAME}

Management:
- Status: sudo systemctl status postgresql
- Restart: sudo systemctl restart postgresql
- Logs: sudo tail -f /var/log/postgresql/postgresql-*.log

Health Check:
- Run: /usr/local/bin/db-health-check

Allowed Hosts:
{ALLOWED_HOSTS}

SECURITY:
- Change database password in production
- Restrict allowed_hosts to specific IPs
- Set up SSL/TLS connections
- Configure automated backups
- Set up replication for HA
""")
