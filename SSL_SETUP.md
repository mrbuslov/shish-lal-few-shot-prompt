# SSL Certificate Setup for drlal.com.au

This document explains how to set up SSL certificates using Let's Encrypt for your production deployment.

## Prerequisites

1. Domain `drlal.com.au` should be pointing to your server's IP address
2. Ports 80 and 443 should be open on your server
3. Docker and Docker Compose should be installed

## Initial Setup (First Time Only)

### Step 1: Start Services Without SSL

First, temporarily modify the nginx configuration to work without SSL:

```bash
# On your production server
cd /path/to/your/project

# Create a temporary nginx config for initial cert generation
cp docker/nginx/sites-available/drlal.com.au docker/nginx/sites-available/drlal.com.au.backup

# Create temporary HTTP-only config
cat > docker/nginx/sites-available/drlal.com.au << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name drlal.com.au www.drlal.com.au;

    # Let's Encrypt ACME challenge location
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        try_files $uri =404;
    }

    # Temporarily allow all traffic for initial setup
    location / {
        proxy_pass http://app:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

### Step 2: Generate SSL Certificates

```bash
# Generate certificates for your domain
docker run --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/lib/letsencrypt:/var/lib/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  certbot/certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d drlal.com.au \
  -d www.drlal.com.au
```

### Step 3: Restore Full Nginx Configuration

```bash
# Restore the full nginx configuration with SSL
cp docker/nginx/sites-available/drlal.com.au.backup docker/nginx/sites-available/drlal.com.au

# Restart nginx to apply SSL configuration
docker-compose -f docker-compose.prod.yml restart nginx

# Test SSL configuration
docker exec medical-processor-nginx nginx -t

# Check if everything is working
curl -I https://drlal.com.au/health
```

## Certificate Renewal

Let's Encrypt certificates expire every 90 days. Set up automatic renewal:

### Option 1: Cron Job (Recommended)

```bash
# Add to root's crontab
sudo crontab -e

# Add this line (runs twice daily):
0 12,24 * * * docker run --rm -v /etc/letsencrypt:/etc/letsencrypt -v /var/lib/letsencrypt:/var/lib/letsencrypt -v /path/to/your/project/certbot/www:/var/www/certbot certbot/certbot renew --webroot --webroot-path=/var/www/certbot && docker-compose -f /path/to/your/project/docker-compose.prod.yml restart nginx
```

### Option 2: Manual Renewal

```bash
# Renew certificates manually
docker run --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/lib/letsencrypt:/var/lib/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  certbot/certbot renew \
  --webroot \
  --webroot-path=/var/www/certbot

# Restart nginx to load new certificates
docker-compose -f docker-compose.prod.yml restart nginx
```

## Troubleshooting

### Check Certificate Status
```bash
# Check certificate information
docker run --rm -v /etc/letsencrypt:/etc/letsencrypt certbot/certbot certificates

# Test certificate renewal (dry run)
docker run --rm -v /etc/letsencrypt:/etc/letsencrypt -v /var/lib/letsencrypt:/var/lib/letsencrypt -v $(pwd)/certbot/www:/var/www/certbot certbot/certbot renew --dry-run --webroot --webroot-path=/var/www/certbot
```

### Check Nginx Configuration
```bash
# Test nginx configuration
docker exec medical-processor-nginx nginx -t

# Reload nginx configuration without restart
docker exec medical-processor-nginx nginx -s reload

# Check nginx logs
docker logs medical-processor-nginx
```

### Common Issues

1. **Domain not pointing to server**: Verify DNS settings
2. **Firewall blocking**: Ensure ports 80 and 443 are open
3. **nginx configuration errors**: Check nginx logs for syntax errors
4. **Certificate path issues**: Verify the certificate files exist in `/etc/letsencrypt/live/drlal.com.au/`

### SSL Test

Test your SSL configuration:
```bash
# Test SSL with curl
curl -I https://drlal.com.au

# Check SSL rating (optional)
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=drlal.com.au
```

## Security Notes

1. The nginx configuration includes strong SSL settings (TLS 1.2+, secure ciphers)
2. HSTS header is enabled for enhanced security
3. Rate limiting is configured to prevent abuse
4. Security headers are set for protection against common attacks

Your SSL setup should now be complete and secure!