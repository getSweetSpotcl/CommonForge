# Railway Deployment Guide

## 🚀 Deploy CommonForge to Railway

### Prerequisites

1. **Railway Account:** Sign up at [railway.app](https://railway.app)
2. **GitHub Account:** Your code should be in a GitHub repository
3. **OpenAI API Key:** From [platform.openai.com](https://platform.openai.com/api-keys)

---

## 📋 Step-by-Step Deployment

### Step 1: Prepare Your Repository

```bash
# Make sure all changes are committed
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### Step 2: Create New Railway Project

1. Go to [railway.app](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your **CommonForge** repository
5. Railway will automatically detect it's a Python app

### Step 3: Add PostgreSQL Database

1. In your Railway project dashboard
2. Click **"+ New"**
3. Select **"Database"**
4. Choose **"PostgreSQL"**
5. Railway will provision a database and set `DATABASE_URL` automatically

### Step 4: Configure Environment Variables

In Railway project settings → **Variables**, add:

```bash
# Required
OPENAI_API_KEY=sk-proj-your-actual-key-here

# Optional (these have defaults)
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=1000
SCRAPER_TIMEOUT=10
SCRAPER_MAX_RETRIES=3
MAX_WEBSITE_TEXT_LENGTH=3000
CONCURRENT_LLM_CALLS=3
LOG_LEVEL=INFO
```

**Note:** `DATABASE_URL` is automatically set by Railway when you add PostgreSQL.

### Step 5: Deploy

Railway will automatically deploy when you push to GitHub!

```bash
# Make any changes
git add .
git commit -m "Your changes"
git push

# Railway auto-deploys!
```

### Step 6: Initialize Database

After first deployment:

```bash
# Option 1: Using Railway CLI
railway run python -c "from src.db import init_db; init_db()"

# Option 2: Will auto-initialize on first API call
# Just access your app URL and it will create tables
```

---

## 🌐 Access Your Deployed App

Railway will provide a public URL like: `https://your-app.railway.app`

**Endpoints:**
- **Frontend:** `https://your-app.railway.app/app/`
- **API Docs:** `https://your-app.railway.app/docs`
- **Health Check:** `https://your-app.railway.app/health`

---

## 🔧 Railway CLI (Optional)

Install Railway CLI for easier management:

```bash
# Install
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# View logs
railway logs

# Run commands
railway run python -m src.pipeline data/companies.csv

# Open dashboard
railway open
```

---

## 📊 Monitor Your Deployment

### View Logs

In Railway dashboard:
1. Go to your service
2. Click **"Deployments"**
3. Click on the active deployment
4. View **"Logs"** tab

### Check Metrics

- **CPU Usage**
- **Memory Usage**
- **Network Traffic**
- **Build Time**

---

## 🐛 Troubleshooting

### Deployment Fails

**Check build logs:**
```bash
railway logs
```

**Common issues:**
- Missing `requirements.txt`
- Python version mismatch
- Missing environment variables

**Fix:**
```bash
# Ensure all files are committed
git status
git add .
git commit -m "Fix deployment"
git push
```

### Database Connection Fails

**Verify DATABASE_URL:**
1. Go to Railway dashboard
2. PostgreSQL service → **Variables**
3. Copy `DATABASE_URL`
4. Make sure it's set in your app service variables

**Format should be:**
```
postgresql://user:pass@host:port/database
```

### App Crashes on Startup

**Check logs for errors:**
```bash
railway logs --tail 100
```

**Common causes:**
- Missing `OPENAI_API_KEY`
- Database not initialized
- Port binding issues (Railway auto-sets `PORT`)

**Fix:**
- Verify all environment variables
- Check that start command is correct: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`

### Frontend Not Loading

**Check static files are included:**
```bash
# Verify frontend/ directory is in repo
ls frontend/

# Should show: index.html
```

**Check mount path in code:**
- Frontend should be mounted at `/app`
- Access at: `https://your-app.railway.app/app/`

---

## 🔐 Security Best Practices

### Environment Variables

✅ **DO:**
- Store API keys in Railway environment variables
- Use Railway's built-in secret management
- Never commit `.env` to git

❌ **DON'T:**
- Hard-code API keys in code
- Commit sensitive data
- Share your Railway tokens

### Database

✅ **DO:**
- Use Railway-provided PostgreSQL
- Enable connection pooling if needed
- Regular backups (Railway Pro feature)

### API

✅ **DO:**
- Use HTTPS (Railway provides automatically)
- Enable CORS properly (already configured)
- Monitor API usage and costs

---

## 💰 Cost Estimation

### Railway Pricing (as of 2024)

**Free Tier:**
- $5 free credits per month
- Good for development/testing
- Enough for small deployments

**Pro Plan ($20/month):**
- $20 credits included
- Better for production
- Priority support

**Estimated Usage:**
- **API Server:** ~$5-10/month
- **PostgreSQL:** ~$5/month
- **Total:** ~$10-15/month for light usage

**OpenAI Costs (separate):**
- ~$0.01-0.02 per company enriched
- 100 companies = ~$1-2
- Set usage limits in OpenAI dashboard

---

## 🔄 Continuous Deployment

Railway automatically deploys when you push to GitHub:

```bash
# Make changes
vim src/api/main.py

# Commit and push
git add .
git commit -m "Add new feature"
git push

# Railway auto-deploys in ~1-2 minutes
```

**Monitor deployment:**
1. Go to Railway dashboard
2. Watch build logs
3. Check deployment status
4. Test deployed app

---

## 📈 Scaling

### Horizontal Scaling

Railway supports automatic scaling:
1. Go to project settings
2. Enable **"Auto-scaling"**
3. Set min/max replicas
4. Railway handles load balancing

### Vertical Scaling

Increase resources:
1. Project settings → **"Resources"**
2. Adjust CPU/Memory limits
3. Restart service

### Database Scaling

For production:
1. Consider Railway Pro for better PostgreSQL
2. Enable connection pooling
3. Add read replicas if needed

---

## ✅ Deployment Checklist

Before going live:

- [ ] All code committed to GitHub
- [ ] PostgreSQL database added in Railway
- [ ] `OPENAI_API_KEY` environment variable set
- [ ] `DATABASE_URL` automatically set by Railway
- [ ] First deployment successful
- [ ] Database tables initialized
- [ ] Frontend accessible at `/app/`
- [ ] API docs accessible at `/docs`
- [ ] Health check returns 200
- [ ] Sample data processed successfully
- [ ] Logs show no errors
- [ ] Custom domain configured (optional)

---

## 🌟 Production Tips

### 1. Use Custom Domain

1. Go to project → **"Settings"** → **"Domains"**
2. Add your custom domain
3. Update DNS records as shown
4. Enable HTTPS (automatic)

### 2. Set Up Monitoring

```bash
# Install Sentry for error tracking (optional)
pip install sentry-sdk[fastapi]
```

Add to `src/api/main.py`:
```python
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    environment="production"
)
```

### 3. Enable Backups

Railway Pro includes automatic database backups:
- Daily snapshots
- Point-in-time recovery
- One-click restore

### 4. Set Up Alerts

In Railway dashboard:
- Enable deployment notifications (Slack/Discord/Email)
- Set up uptime monitoring
- Configure error alerts

---

## 📚 Additional Resources

- **Railway Docs:** https://docs.railway.app
- **Railway Discord:** https://discord.gg/railway
- **Railway Status:** https://status.railway.app
- **CommonForge Docs:** See [README.md](README.md)

---

## 🆘 Need Help?

1. **Railway Issues:**
   - Check [Railway Docs](https://docs.railway.app)
   - Ask in [Railway Discord](https://discord.gg/railway)
   - Check status page

2. **App Issues:**
   - Check Railway logs: `railway logs`
   - Review [README.md](README.md) troubleshooting section
   - Test locally first

3. **OpenAI Issues:**
   - Check [OpenAI Status](https://status.openai.com)
   - Verify API key and credits
   - Review usage limits

---

**You're ready to deploy!** 🚀

```bash
git push origin main
# Watch it deploy in Railway dashboard!
```
