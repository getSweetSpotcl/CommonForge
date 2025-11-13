# 🚀 Deploy to Railway - Quick Guide

## In 5 Minutes

### Step 1: Commit & Push (2 min)

```bash
# Add all new files
git add .

# Commit
git commit -m "Add frontend UI and Railway deployment config"

# Push to GitHub
git push origin main
```

### Step 2: Deploy to Railway (2 min)

1. Go to **[railway.app](https://railway.app)**
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose **`CommonForge`**
5. Railway auto-detects Python and deploys!

### Step 3: Add PostgreSQL (30 sec)

1. In Railway project, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Done! `DATABASE_URL` is auto-set

### Step 4: Set Environment Variable (30 sec)

1. Click on your service → **"Variables"**
2. Add: `OPENAI_API_KEY` = `your-key-here`
3. Click **"Deploy"**

### Step 5: Access Your App! (30 sec)

Railway gives you a URL like: `https://commonforge-production-xxxx.railway.app`

**Open:**
- **Frontend:** `https://your-url.railway.app/app/`
- **API Docs:** `https://your-url.railway.app/docs`

---

## ✅ That's It!

Your app is now live on the internet! 🎉

---

## 🔍 What Was Deployed

All these files are configured for Railway:

- ✅ `Procfile` - Start command
- ✅ `railway.json` - Railway configuration
- ✅ `nixpacks.toml` - Build configuration
- ✅ `runtime.txt` - Python version
- ✅ `.railwayignore` - Files to exclude
- ✅ `requirements.txt` - Dependencies (with python-multipart)

---

## 🐛 If Something Goes Wrong

**Check logs:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# View logs
railway logs
```

**Or in Railway dashboard:**
1. Go to your service
2. Click **"Deployments"**
3. View **"Logs"**

---

## 📊 Test Your Deployment

```bash
# Replace with your Railway URL
export RAILWAY_URL="https://your-app.railway.app"

# Test health
curl $RAILWAY_URL/health

# Test API
curl $RAILWAY_URL/companies

# Open frontend
open $RAILWAY_URL/app/
```

---

## 💡 Pro Tips

### Custom Domain (Optional)

1. Railway project → **"Settings"** → **"Domains"**
2. Add your domain
3. Update DNS records

### Monitor Costs

1. Railway dashboard → **"Usage"**
2. Set up billing alerts
3. Monitor OpenAI usage separately

### Continuous Deployment

Every time you push to GitHub, Railway auto-deploys:

```bash
git commit -m "Your changes"
git push
# Railway deploys automatically!
```

---

## 🎯 Next Steps After Deployment

1. **Test the frontend:**
   - Upload `data/companies.csv`
   - Verify processing works
   - Check enriched results

2. **Set up monitoring:**
   - Check Railway metrics
   - Monitor OpenAI API usage
   - Set up alerts (optional)

3. **Share with stakeholders:**
   - Send them the Railway URL
   - They can upload CSV files
   - View enriched company data

---

## 📚 Full Deployment Guide

For detailed instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)

---

**Ready? Let's deploy!** 🚀

```bash
git add .
git commit -m "Add frontend and Railway config"
git push origin main
```

Then go to **[railway.app](https://railway.app)** and click **"New Project"**!
