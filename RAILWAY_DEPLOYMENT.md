# Railway Deployment Guide - Product Importer

## Quick Fix for Current Issue

Your worker is crashing because it can't find the database. Here's the immediate fix:

### Step 1: Check Database Connection
1. Go to your Railway dashboard
2. Find your `product-importer-worker` service
3. Click on "Variables" tab
4. Verify these variables exist:
   - `DATABASE_URL` (should reference your PostgreSQL service)
   - `REDIS_URL` (should reference your Redis service)

### Step 2: Link Database Variables
If the variables are missing:
1. Click "New Variable" → "Add Reference"
2. Select your PostgreSQL service
3. Choose `DATABASE_URL` from the dropdown
4. Repeat for Redis → `REDIS_URL`

### Step 3: Fix the Root User Warning
The "running as root" warning will be fixed by redeploying with the updated Dockerfile:

1. Commit and push the changes:
   ```bash
   git add Dockerfile railway.json README.md render.yaml
   git commit -m "Fix: Run Celery worker as non-root user"
   git push
   ```

2. Railway will automatically redeploy both services

### Step 4: Verify Deployment
After redeployment, check the logs:
- ✅ No more "DATABASE_URL not set" errors
- ✅ No more "running as root" warnings
- ✅ Worker shows: `celery@... ready`

---

## Full Railway Setup (For New Deployments)

### Architecture Overview
```
┌─────────────────────────────────────────────────────┐
│                  Railway Project                     │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────┐      ┌──────────────────┐   │
│  │   PostgreSQL     │◄─────┤   Web Service    │   │
│  │   Database       │      │   (FastAPI)      │   │
│  └──────────────────┘      └──────────────────┘   │
│           ▲                         │              │
│           │                         │              │
│           │                         ▼              │
│  ┌──────────────────┐      ┌──────────────────┐   │
│  │     Redis        │◄─────┤  Worker Service  │   │
│  │   (Message Queue)│      │   (Celery)       │   │
│  └──────────────────┘      └──────────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 1. Create Railway Project
```bash
# Install Railway CLI (optional)
npm i -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init
```

Or use the web interface at https://railway.app

### 2. Add Services

#### PostgreSQL
- Click "New" → "Database" → "PostgreSQL"
- Railway creates it automatically
- No configuration needed

#### Redis
- Click "New" → "Database" → "Redis"
- Railway creates it automatically
- No configuration needed

#### Web Service (FastAPI)
- Click "New" → "GitHub Repo"
- Select your repository
- Configure:
  - **Name**: `product-importer-web`
  - **Root Directory**: `/` (or leave empty)
  - **Build Command**: Auto-detected (uses Dockerfile)
  - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  
- **Environment Variables**:
  - Add Reference → PostgreSQL → `DATABASE_URL`
  - Add Reference → Redis → `REDIS_URL`
  
- **Settings**:
  - Enable "Public Networking"
  - Railway will provide a public URL

#### Worker Service (Celery)
- Click "New" → "GitHub Repo" (same repo)
- Configure:
  - **Name**: `product-importer-worker`
  - **Root Directory**: `/` (or leave empty)
  - **Build Command**: Auto-detected (uses Dockerfile)
  - **Start Command**: `celery -A app.celery_app worker --loglevel=info --concurrency=4 --max-memory-per-child=200000`
  
- **Environment Variables**:
  - Add Reference → PostgreSQL → `DATABASE_URL`
  - Add Reference → Redis → `REDIS_URL`
  
- **Settings**:
  - Do NOT enable public networking (internal service only)

### 3. Deploy
Railway will automatically deploy when you push to your repository.

Manual deployment:
```bash
railway up
```

### 4. Monitor Deployment

#### Check Web Service Logs
Look for:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:$PORT
```

#### Check Worker Service Logs
Look for:
```
[2025-11-22 00:30:00,000: INFO/MainProcess] celery@... ready.
[tasks]
  . app.tasks.import_csv_task
  . app.tasks.trigger_webhooks
```

### 5. Access Your Application
- Click on the web service
- Click "Settings" → "Networking"
- Copy the public URL
- Visit the URL in your browser

---

## Environment Variables Reference

### Required Variables (Auto-configured by Railway)

| Variable | Source | Description |
|----------|--------|-------------|
| `DATABASE_URL` | PostgreSQL Service | Full database connection string |
| `REDIS_URL` | Redis Service | Redis connection string |
| `PORT` | Railway | Auto-assigned port (web service only) |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | From DATABASE_URL | Database host (for docker-compose) |
| `DB_PORT` | From DATABASE_URL | Database port (for docker-compose) |

---

## Troubleshooting

### Worker Crashes Immediately

**Symptom**: Worker service shows "Crashed" status

**Common Causes**:
1. Missing `DATABASE_URL` environment variable
2. Missing `REDIS_URL` environment variable
3. Database not ready when worker starts

**Solution**:
```bash
# Check environment variables
railway variables

# Ensure DATABASE_URL and REDIS_URL are set
# They should reference the PostgreSQL and Redis services
```

### "Running as Root" Warning

**Symptom**: Logs show security warning about running as root

**Solution**: Already fixed in the updated Dockerfile. Redeploy to apply:
```bash
git push  # Railway auto-deploys
```

### Database Connection Refused

**Symptom**: `connection refused` or `could not connect to server`

**Causes**:
1. PostgreSQL service not running
2. DATABASE_URL not properly linked
3. Network issue between services

**Solution**:
1. Check PostgreSQL service status
2. Verify DATABASE_URL in worker variables
3. Ensure all services are in the same Railway project

### Redis Connection Failed

**Symptom**: `Error connecting to Redis`

**Solution**:
1. Check Redis service status
2. Verify REDIS_URL in worker variables
3. Check Redis is in the same Railway project

### High Memory Usage

**Symptom**: Worker crashes with memory errors

**Solution**: Reduce concurrency or memory limit:
```bash
# Update start command to:
celery -A app.celery_app worker --loglevel=info --concurrency=2 --max-memory-per-child=150000
```

---

## Scaling Considerations

### Free Tier Limits
- 500 hours/month execution time (shared across all services)
- $5 free credit/month
- After free credit: ~$0.000231/minute

### Recommended Configuration

**For Free Tier**:
- Web: 1 instance, 512MB RAM
- Worker: 1 instance, 512MB RAM, concurrency=2
- PostgreSQL: Shared instance
- Redis: Shared instance

**For Production**:
- Web: 2+ instances, 1GB RAM each
- Worker: 2+ instances, 2GB RAM each, concurrency=4
- PostgreSQL: Dedicated instance
- Redis: Dedicated instance

### Horizontal Scaling
To add more workers:
1. Duplicate the worker service
2. Railway will load-balance automatically
3. All workers share the same Redis queue

---

## Monitoring

### View Logs
```bash
# Web service logs
railway logs --service product-importer-web

# Worker service logs
railway logs --service product-importer-worker
```

### Metrics
Railway provides built-in metrics:
- CPU usage
- Memory usage
- Network traffic
- Request count

Access via: Service → Metrics tab

---

## Updating the Application

### Via Git Push (Recommended)
```bash
git add .
git commit -m "Update application"
git push
```
Railway automatically redeploys.

### Via Railway CLI
```bash
railway up
```

### Rollback
```bash
# View deployments
railway deployments

# Rollback to previous deployment
railway rollback <deployment-id>
```

---

## Cost Optimization

### Tips to Reduce Costs
1. **Use sleep mode**: Railway can pause services when inactive
2. **Optimize worker concurrency**: Lower concurrency = less memory
3. **Batch operations**: Process multiple items per task
4. **Monitor usage**: Check Railway dashboard regularly

### Expected Costs (After Free Tier)
- **Light usage** (< 10K requests/month): ~$5-10/month
- **Medium usage** (< 100K requests/month): ~$20-30/month
- **Heavy usage** (> 100K requests/month): ~$50-100/month

---

## Support

### Railway Support
- Documentation: https://docs.railway.app
- Discord: https://discord.gg/railway
- Status: https://status.railway.app

### Application Issues
Check the logs first:
```bash
railway logs
```

Common log locations:
- Web service: Uvicorn logs
- Worker service: Celery logs
- Database: PostgreSQL logs (in PostgreSQL service)
