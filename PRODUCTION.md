# Production Deployment Guide

## Quick Start

### 1. Install Dependencies

```bash
# Activate your conda environment
conda activate scribe-inference

# Install all dependencies including gunicorn
pip install -r requirements.txt

# Install the package in development mode (fixes import issues)
pip install -e .
```

### 2. Configure Environment

Make sure your `.env` file contains all required variables:
```env
PORT=61016
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_key
OPENAI_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
```

### 3. Run the Application

**Development Mode:**
```bash
./run_dev.sh
# or
python -m app.main
```

**Production Mode:**
```bash
./run_prod.sh
```

## Production Deployment Options

### Option 1: Direct Gunicorn (Simple)

```bash
gunicorn -w 4 -b 0.0.0.0:61016 app.main:app --timeout 300
```

**Parameters:**
- `-w 4`: Number of worker processes (adjust based on CPU cores)
- `-b 0.0.0.0:61016`: Bind address and port
- `--timeout 300`: Request timeout (5 minutes for long LLM operations)

### Option 2: Gunicorn + Nginx (Recommended)

1. **Run Gunicorn on localhost:**
   ```bash
   gunicorn -w 4 -b 127.0.0.1:61016 app.main:app --timeout 300
   ```

2. **Configure Nginx** (`/etc/nginx/sites-available/scribe`):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       client_max_body_size 100M;  # Allow large PDF uploads

       location / {
           proxy_pass http://127.0.0.1:61016;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # Timeouts for long-running requests
           proxy_connect_timeout 300s;
           proxy_send_timeout 300s;
           proxy_read_timeout 300s;
       }
   }
   ```

3. **Enable the site:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/scribe /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

### Option 3: Systemd Service (Linux Servers)

Create `/etc/systemd/system/scribe-backend.service`:

```ini
[Unit]
Description=Scribe Inference Backend
After=network.target

[Service]
User=your-username
Group=www-data
WorkingDirectory=/path/to/inference-backend
Environment="PATH=/path/to/conda/envs/scribe-inference/bin"
ExecStart=/path/to/conda/envs/scribe-inference/bin/gunicorn -w 4 -b 127.0.0.1:61016 app.main:app --timeout 300
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable scribe-backend
sudo systemctl start scribe-backend
sudo systemctl status scribe-backend
```

View logs:
```bash
sudo journalctl -u scribe-backend -f
```

### Option 4: Docker

Create a `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 61016

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:61016", "app.main:app", "--timeout", "300"]
```

Build and run:
```bash
docker build -t scribe-backend .
docker run -d -p 61016:61016 --env-file .env scribe-backend
```

## Environment Variables

You can customize the production server with these environment variables:

```bash
export WORKERS=4              # Number of Gunicorn workers
export PORT=61016             # Server port
export TIMEOUT=300            # Request timeout in seconds
export BIND=0.0.0.0:61016    # Bind address
```

## Monitoring & Logs

### View Logs
```bash
# Access logs
tail -f logs/access.log

# Error logs
tail -f logs/error.log
```

### Health Check
```bash
curl http://localhost:61016/health
```

Expected response:
```json
{"status": "healthy", "server_status": "idle"}
```

## Performance Tuning

### Worker Count
- Formula: `(2 × CPU_cores) + 1`
- For a 4-core machine: 9 workers
- Adjust based on memory and workload

### Timeout
- Default: 300 seconds (5 minutes)
- Increase if you have longer-running LLM operations
- Monitor with `--log-level debug`

### File Upload Limits
- Nginx: Set `client_max_body_size` (default: 100M)
- Gunicorn: Set `--limit-request-line` if needed

## Security Checklist

- [ ] Use HTTPS with SSL certificates (Let's Encrypt)
- [ ] Review CORS settings in `app/main.py` (currently allows all origins)
- [ ] Secure API keys in `.env` file (never commit to git)
- [ ] Set up firewall rules (only allow ports 80, 443)
- [ ] Use Nginx rate limiting to prevent abuse
- [ ] Regular security updates: `pip install --upgrade -r requirements.txt`
- [ ] Set up proper file permissions on `Data/` directory

## Troubleshooting

### Import Errors
If you get `ModuleNotFoundError: No module named 'app'`:
```bash
# Solution 1: Install in development mode
pip install -e .

# Solution 2: Run as module
python -m app.main

# Solution 3: Set PYTHONPATH
export PYTHONPATH=/path/to/inference-backend:$PYTHONPATH
```

### Port Already in Use
```bash
# Find process using port 61016
lsof -i :61016

# Kill the process
kill -9 <PID>
```

### Memory Issues
- Reduce worker count
- Monitor with: `ps aux | grep gunicorn`
- Consider using `--worker-class gevent` for better concurrency

## Backup & Maintenance

### Backup Important Data
```bash
# Backup Data directory
tar -czf data-backup-$(date +%Y%m%d).tar.gz Data/

# Backup environment configuration
cp .env .env.backup
```

### Update Dependencies
```bash
pip install --upgrade -r requirements.txt
```

## Support

For issues, check:
1. Application logs: `logs/error.log`
2. System logs (if using systemd): `journalctl -u scribe-backend`
3. Nginx logs: `/var/log/nginx/error.log`



