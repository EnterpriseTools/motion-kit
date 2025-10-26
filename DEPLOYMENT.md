# Deployment Guide: Vercel (Frontend) + Railway (Backend)

This project is configured for split deployment:
- **Frontend**: Vercel
- **Backend**: Railway (Python FastAPI with ML)

## Railway Setup (Backend)

### 1. Create Railway Project
1. Go to [Railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose this repository

### 2. Configure Railway Environment Variables

Add these in Railway dashboard under "Variables":

```
FRONTEND_ORIGIN=https://your-vercel-app.vercel.app
ENV=production
FIGMA_API_TOKEN=your_figma_token_here
FIGMA_FILE_ID=your_figma_file_id_here
YOLO_WEIGHTS=yolov8n.pt
YOLO_DEVICE=cpu
PORT=8000
```

### 3. Configure Build Settings

Railway should auto-detect the configuration from `railway.toml` and `Procfile`.

**Root Directory**: Keep as `/` (project root)
**Build Command**: Handled by nixpacks (see `nixpacks.toml`)
**Start Command**: `cd api && uvicorn main:app --host 0.0.0.0 --port $PORT`

### 4. Add Railway Volume (Optional but Recommended)

For persistent storage of uploads/results:
1. Go to Railway project settings
2. Add a volume at `/app/uploads` and `/app/results`

### 5. Get Your Railway URL

After deployment, Railway will provide a URL like:
`https://motion-kit-production.up.railway.app`

---

## Vercel Setup (Frontend)

### 1. Import Project to Vercel
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "Add New..." → "Project"
3. Import your GitHub repository

### 2. Configure Vercel Settings

Use these settings (as shown in screenshot):

- **Framework Preset**: Vite
- **Root Directory**: `./` (or set to `frontend`)
- **Build Command**: `cd frontend && npm run build`
- **Output Directory**: `frontend/dist`
- **Install Command**: `cd frontend && npm install`

Or if Root Directory is `frontend`:
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### 3. Add Vercel Environment Variables

Add this in Vercel dashboard under "Environment Variables":

```
VITE_API=https://your-railway-app.up.railway.app
```

⚠️ **Important**: Update `frontend/src/App.jsx`:

```javascript
const API = import.meta.env.VITE_API || "http://127.0.0.1:8000";
```

### 4. Deploy

Click "Deploy" - Vercel will automatically build and deploy your frontend.

---

## Post-Deployment Steps

### 1. Update CORS in Backend

Update `api/main.py` to allow your Vercel domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    # ... rest of config
)
```

### 2. Update Railway Environment

After deploying to Vercel, update Railway's `FRONTEND_ORIGIN`:
```
FRONTEND_ORIGIN=https://your-app.vercel.app
```

### 3. Test the Connection

1. Visit your Vercel URL
2. Try uploading a video
3. Check Railway logs for API calls

---

## Local Development

For local development, keep using:
```bash
npm run dev
```

This starts both servers locally:
- Frontend: http://localhost:5173
- Backend: http://127.0.0.1:8000

---

## Troubleshooting

### Railway Deployment Fails
- Check logs: `railway logs`
- Ensure all dependencies are in `api/requirements.txt`
- Verify Python version compatibility

### Vercel Build Fails
- Check build logs in Vercel dashboard
- Ensure `frontend/package.json` has `build` script
- Verify all npm dependencies are listed

### CORS Errors
- Update `FRONTEND_ORIGIN` in Railway
- Update CORS origins in `api/main.py`
- Redeploy Railway after changes

### API Connection Issues
- Verify `VITE_API` environment variable in Vercel
- Check Railway URL is correct
- Test Railway API directly: `https://your-railway-url.up.railway.app/api/health`

---

## Cost Estimation

### Vercel (Free Tier)
- ✅ Hobby plan: Free for personal projects
- ✅ 100GB bandwidth/month
- ✅ Unlimited deployments

### Railway (Starter Tier)
- 💰 ~$5-20/month depending on usage
- ✅ 500 hours execution time
- ✅ Persistent storage
- ✅ Better for ML workloads

---

## Architecture Diagram

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       ├─────────────────┐
       │                 │
       v                 v
┌──────────────┐  ┌──────────────┐
│    Vercel    │  │   Railway    │
│  (Frontend)  │  │  (Backend)   │
│              │  │              │
│  React/Vite  │  │  FastAPI     │
│              │  │  YOLOv8      │
│              │  │  OpenCV      │
└──────────────┘  └──────────────┘
```

---

## Next Steps

1. ✅ Push code to GitHub
2. ✅ Deploy backend to Railway
3. ✅ Deploy frontend to Vercel
4. ✅ Update environment variables
5. ✅ Test end-to-end
6. 🎉 Share with users!

