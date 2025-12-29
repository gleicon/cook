"""
WordPress installation with nginx, MySQL, and PHP.
A complete LEMP stack configuration.
"""
from cook import File, Package, Service, Exec

# Database configuration
DB_NAME = "wordpress"
DB_USER = "wpuser"
DB_PASSWORD = "wppass123"
DB_ROOT_PASSWORD = "rootpass123"

print("Installing WordPress with nginx, MySQL, and PHP")

# System Update

print("\nStep 1: Updating system packages")
Exec("apt-update",
     command="apt-get update",
     creates="/var/lib/apt/periodic/update-success-stamp")

# Install Packages

print("\nStep 2: Installing LEMP stack packages")

# Web server
Package("nginx")

# Database
Package("mysql-server")

# PHP and extensions
Package([
    "php-fpm",
    "php-mysql",
    "php-curl",
    "php-gd",
    "php-mbstring",
    "php-xml",
    "php-xmlrpc",
    "php-zip",
])

# Utilities
Package(["curl", "wget", "unzip"])

# MySQL Configuration

print("\nStep 3: Configuring MySQL database")

# Create database and user
mysql_setup = Exec("mysql-setup",
    command=f"""
mysql -e "CREATE DATABASE IF NOT EXISTS {DB_NAME};"
mysql -e "CREATE USER IF NOT EXISTS '{DB_USER}'@'localhost' IDENTIFIED BY '{DB_PASSWORD}';"
mysql -e "GRANT ALL PRIVILEGES ON {DB_NAME}.* TO '{DB_USER}'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"
""",
    unless=f"mysql -e 'USE {DB_NAME};' 2>/dev/null"
)

# PHP Configuration

print("\nStep 4: Configuring PHP")

# PHP-FPM configuration
File("/etc/php/8.1/fpm/pool.d/www.conf",
     content="""
[www]
user = www-data
group = www-data
listen = /run/php/php8.1-fpm.sock
listen.owner = www-data
listen.group = www-data
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
""",
     mode=0o644)

# WordPress Installation

print("\nStep 5: Installing WordPress")

# Download WordPress
Exec("download-wordpress",
     command="wget -O /tmp/wordpress.zip https://wordpress.org/latest.zip",
     creates="/tmp/wordpress.zip")

# Extract WordPress
Exec("extract-wordpress",
     command="unzip -q /tmp/wordpress.zip -d /var/www/",
     creates="/var/www/wordpress")

# Set permissions
Exec("wordpress-permissions",
     command="chown -R www-data:www-data /var/www/wordpress",
     unless="[ $(stat -c '%U' /var/www/wordpress) = 'www-data' ]")

# WordPress configuration
File("/var/www/wordpress/wp-config.php",
     content=f"""<?php
define('DB_NAME', '{DB_NAME}');
define('DB_USER', '{DB_USER}');
define('DB_PASSWORD', '{DB_PASSWORD}');
define('DB_HOST', 'localhost');
define('DB_CHARSET', 'utf8');
define('DB_COLLATE', '');

define('AUTH_KEY',         'put your unique phrase here');
define('SECURE_AUTH_KEY',  'put your unique phrase here');
define('LOGGED_IN_KEY',    'put your unique phrase here');
define('NONCE_KEY',        'put your unique phrase here');
define('AUTH_SALT',        'put your unique phrase here');
define('SECURE_AUTH_SALT', 'put your unique phrase here');
define('LOGGED_IN_SALT',   'put your unique phrase here');
define('NONCE_SALT',       'put your unique phrase here');

$table_prefix = 'wp_';
define('WP_DEBUG', false);

if ( ! defined( 'ABSPATH' ) ) {{
    define( 'ABSPATH', __DIR__ . '/' );
}}

require_once ABSPATH . 'wp-settings.php';
""",
     mode=0o644,
     owner="www-data",
     group="www-data")

# Nginx Configuration

print("\nStep 6: Configuring nginx")

# Remove default site
Exec("remove-default-nginx",
     command="rm -f /etc/nginx/sites-enabled/default",
     onlyif="[ -f /etc/nginx/sites-enabled/default ]")

# WordPress nginx config
nginx_config = File("/etc/nginx/sites-available/wordpress",
     content="""
server {
    listen 80;
    server_name localhost;

    root /var/www/wordpress;
    index index.php index.html;

    access_log /var/log/nginx/wordpress-access.log;
    error_log /var/log/nginx/wordpress-error.log;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \\.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\\.ht {
        deny all;
    }

    location = /favicon.ico {
        log_not_found off;
        access_log off;
    }

    location = /robots.txt {
        log_not_found off;
        access_log off;
        allow all;
    }

    location ~* \\.(css|gif|ico|jpeg|jpg|js|png)$ {
        expires max;
        log_not_found off;
    }
}
""",
     mode=0o644)

# Enable site
Exec("enable-wordpress-site",
     command="ln -sf /etc/nginx/sites-available/wordpress /etc/nginx/sites-enabled/wordpress",
     creates="/etc/nginx/sites-enabled/wordpress")

# Start Services

print("\nStep 7: Starting services")

# Start and enable MySQL
Service("mysql", running=True, enabled=True)

# Start and enable PHP-FPM
Service("php8.1-fpm", running=True, enabled=True)

# Start and enable nginx (reload when config changes)
Service("nginx",
        running=True,
        enabled=True,
        reload_on=[nginx_config])

print("\n WordPress installation complete!")
print("\nAccess WordPress at: http://localhost:8080")
print("Database: wordpress")
print("DB User: wpuser")
print("DB Password: wppass123")
