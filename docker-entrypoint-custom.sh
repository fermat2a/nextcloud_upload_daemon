#!/bin/bash
# Copy custom config if it exists
if [ -f /tmp/custom-config.php ]; then
    cp /tmp/custom-config.php /var/www/html/config/config.php
    chown www-data:www-data /var/www/html/config/config.php
    echo "Custom config copied to /var/www/html/config/config.php"
fi

# Start the original entrypoint
exec /entrypoint.sh "$@"