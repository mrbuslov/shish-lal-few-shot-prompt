#!/bin/bash
set -e

DOMAIN="yourscribe.com.au"
EMAIL="admin@yourscribe.com.au"  # Change this to your email

echo "🔒 Setting up SSL certificates for $DOMAIN"

# Generate certificate using certbot
echo "📋 Generating SSL certificate..."
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email $EMAIL \
  --agree-tos \
  --no-eff-email \
  -d $DOMAIN \
  -d www.$DOMAIN

# Update nginx configuration to use HTTPS
echo "🔧 Updating nginx configuration to use HTTPS..."
cat > docker/nginx/sites-available/$DOMAIN << 'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name yourscribe.com.au www.yourscribe.com.au;

    # Let's Encrypt ACME challenge location
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        try_files $uri =404;
    }

    # Redirect all HTTP requests to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourscribe.com.au www.yourscribe.com.au;

    # SSL Certificate paths (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourscribe.com.au/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourscribe.com.au/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/yourscribe.com.au/chain.pem;

    # OCSP Stapling
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Root directory for static files
    root /var/www;

    # Logging
    access_log /var/log/nginx/yourscribe.access.log main;
    error_log /var/log/nginx/yourscribe.error.log warn;

    # Static files
    location /static/ {
        alias /var/www/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
        
        # Enable gzip for static content
        gzip_static on;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://app:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
        access_log off;
    }

    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://app:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings for large file uploads and processing
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffer settings for large requests
        proxy_buffering on;
        proxy_buffer_size 8k;
        proxy_buffers 16 8k;
        proxy_busy_buffers_size 16k;
    }

    # Auth endpoints
    location /auth/ {
        limit_req zone=general burst=10 nodelay;
        
        proxy_pass http://app:8000/auth/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Main application routes
    location / {
        limit_req zone=general burst=15 nodelay;
        
        proxy_pass http://app:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Enable buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Security headers for all responses
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; style-src 'self' 'unsafe-inline' blob:; img-src 'self' data: https: blob:; font-src 'self' data: https: blob:; media-src 'self' blob: data:; object-src 'none'; base-uri 'self'; form-action 'self'; connect-src 'self' https: wss: ws: blob:; worker-src 'self' blob:; child-src 'self' blob:; frame-src 'none'; frame-ancestors 'none';" always;
    add_header Permissions-Policy "camera=(self), microphone=(self), geolocation=(self), payment=(), usb=(), magnetometer=(), gyroscope=(), speaker=(self), vibrate=(self), fullscreen=(self), autoplay=(self), encrypted-media=(self), picture-in-picture=(self)" always;

    # Error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
    
    location = /50x.html {
        root /usr/share/nginx/html;
        internal;
    }
}
EOF

# Reload nginx configuration
echo "🔄 Reloading nginx..."
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo "✅ SSL setup complete for $DOMAIN"
echo "🌐 Your site should now be available at https://$DOMAIN"