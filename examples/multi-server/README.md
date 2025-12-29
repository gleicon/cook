# Multi-Server: PostgreSQL Database

PostgreSQL database server configuration for multi-tier applications.

## Files

- `database.py` - PostgreSQL server configuration

## Usage

Local:

```bash
sudo cook apply database.py
```

Remote:

```bash
cook apply database.py --host db.example.com --user admin --sudo
```

With environment variables:

```bash
DB_NAME=myapp DB_USER=myappuser DB_PASSWORD=secure_pass \
cook apply database.py --sudo
```

## Configuration

Environment variables:

- `DB_NAME` - Database name (default: appdb)
- `DB_USER` - Database user (default: appuser)
- `DB_PASSWORD` - Password (default: secure_password_change_me)
- `ALLOWED_HOSTS` - CIDR blocks for access (default: private networks)

## Operations

1. Installs PostgreSQL
2. Creates database and user
3. Grants privileges
4. Configures remote access (pg_hba.conf)
5. Enables network listening (postgresql.conf)
6. Starts PostgreSQL service

## Security

- Environment variables for credentials (no hardcoded passwords)
- Host-based authentication
- Network access restrictions
- SSL/TLS recommended for production

## Connecting

```bash
psql -h db.example.com -U appuser -d appdb
```

Connection string:

```
postgresql://appuser:password@db.example.com:5432/appdb
```

## Future

Can be extended with:
- Load balancer (HAProxy/Nginx)
- Web servers (Nginx + PHP/Node.js)
- Automated deployment scripts
- Monitoring and backups
