# Production Deployment Guide for drlal.com.au

This guide covers the complete production deployment setup for the Medical Text Processor application.

## 🚀 Quick Start

### Prerequisites on Production Server
- Ubuntu 20.04+ or similar Linux distribution
- Docker and Docker Compose installed
- Git installed
- Domain `drlal.com.au` pointing to server IP
- Ports 80, 443, and 22 open

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for Docker group to take effect
```

### 2. Application Deployment

```bash
# Clone repository
git clone https://github.com/your-username/your-repo.git /opt/medical-processor
cd /opt/medical-processor

# Copy and configure environment variables
cp .env.production .env
nano .env  # Edit with your actual values

# Create necessary directories
mkdir -p temp files/user_reports logs docker/nginx/sites-enabled
chmod 755 temp files/user_reports logs

# Enable nginx site
ln -sf /etc/nginx/sites-available/drlal.com.au docker/nginx/sites-enabled/drlal.com.au

# Deploy application
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
```

### 3. SSL Certificate Setup

Follow the detailed instructions in [SSL_SETUP.md](./SSL_SETUP.md)

## 🔧 Configuration

### GitHub Secrets Required

Set these secrets in your GitHub repository:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `DEPLOY_HOST` | Your server's IP or domain | `123.456.789.10` or `drlal.com.au` |
| `DEPLOY_USER` | SSH username | `root` or `ubuntu` |
| `DEPLOY_PATH` | Deployment path on server | `/opt/medical-processor` |
| `DEPLOY_PRIVATE_KEY` | SSH private key | `-----BEGIN OPENSSH PRIVATE KEY-----...` |

### Environment Variables (.env)

Create `.env` file on your production server:

```env
# MongoDB Configuration
MONGO_USERNAME=admin
MONGO_PASSWORD=your_secure_mongodb_password_here
MONGO_DATABASE=medical_processor

# API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Security
SECRET_KEY=your_super_secret_key_for_jwt_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Settings
NODE_ENV=production
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
```

## 🏗️ Architecture

The production setup includes:

- **FastAPI Application**: Python backend with AI processing
- **Nginx**: Reverse proxy with SSL termination and rate limiting  
- **MongoDB**: Database for user data and configurations
- **Docker Compose**: Container orchestration
- **Let's Encrypt**: Free SSL certificates with auto-renewal

## 🔒 Security Features

### Nginx Security
- Rate limiting (10 requests/second for API, 5 for general)
- SSL/TLS 1.2+ with secure ciphers
- Security headers (HSTS, CSP, X-Frame-Options)
- File upload size limits (100MB)

### Application Security
- JWT authentication
- User-specific data isolation
- Input validation and sanitization
- Error handling without information disclosure

## 📊 Monitoring

### Health Checks
- Application: `https://drlal.com.au/health`
- Nginx: Built-in health checks
- MongoDB: Built-in health checks

### Logs
```bash
# Application logs
docker logs medical-processor-app

# Nginx logs
docker logs medical-processor-nginx

# MongoDB logs
docker logs medical-processor-mongodb

# All services
docker-compose -f docker-compose.prod.yml logs -f
```

## 🔄 CI/CD Pipeline

The GitHub Actions workflow automatically:
1. Connects to your server via SSH
2. Pulls latest code from `main` branch
3. Builds and deploys Docker containers
4. Performs health checks
5. Cleans up old Docker images
6. Verifies deployment success

### Manual Deployment

```bash
# On your local machine, push to main branch
git push origin main

# Or trigger manual deployment from GitHub Actions tab
```

### Manual Server Commands

```bash
# On production server
cd /opt/medical-processor

# Update and restart
git pull origin main
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart specific service
docker-compose -f docker-compose.prod.yml restart app
```

## 🛠️ Maintenance

### SSL Certificate Renewal
Certificates auto-renew via cron job. Check status:
```bash
docker run --rm -v /etc/letsencrypt:/etc/letsencrypt certbot/certbot certificates
```

### Database Backup
```bash
# Backup MongoDB
docker exec medical-processor-mongodb mongodump --out /data/backup

# Copy backup from container
docker cp medical-processor-mongodb:/data/backup ./backup
```

### Updates
```bash
# Update application (automatic via CI/CD)
git push origin main

# Manual update
cd /opt/medical-processor
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
```

## 🐛 Troubleshooting

### Common Issues

1. **SSL Certificate Issues**
   - Check domain DNS settings
   - Verify ports 80/443 are open
   - Review Let's Encrypt logs

2. **Application Won't Start**
   - Check environment variables in `.env`
   - Verify API keys are valid
   - Review application logs

3. **Database Connection Issues**
   - Verify MongoDB password
   - Check network connectivity between containers
   - Review MongoDB logs

4. **File Upload Issues**
   - Check disk space
   - Verify directory permissions
   - Review nginx upload limits

### Performance Tuning

```bash
# Monitor resource usage
docker stats

# Check disk space
df -h

# Monitor logs for errors
docker-compose -f docker-compose.prod.yml logs -f | grep ERROR
```

## 📞 Support

For issues:
1. Check application logs
2. Review this documentation
3. Check GitHub Issues
4. Contact system administrator

Your production deployment should now be complete and operational at `https://drlal.com.au`!