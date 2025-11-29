#!/bin/bash
# Reload nginx configuration

# Send SIGHUP to nginx master process to reload config
sudo kill -HUP $(cat /home/rodrigo/agentic/nginx.pid)

echo "Nginx configuration reloaded successfully"
