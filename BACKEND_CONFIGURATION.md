# Backend Configuration Summary

This document outlines all environment-based configuration in the backend to ensure no hard-coded values.

## Environment Variables

All configuration is driven by environment variables, with sensible defaults for local development.

### Required Environment Variables

#### Production (Railway)
```bash
# Application Environment
ENV=production
PORT=8080

# URLs and Origins
FRONTEND_ORIGIN=https://your-vercel-app.vercel.app

# Railway provides RAILWAY_PUBLIC_DOMAIN automatically (no need to set manually)
# It will be: motion-kit-production.up.railway.app (without https://)

# Figma Integration (Optional)
FIGMA_API_TOKEN=your_figma_token_here
FIGMA_FILE_ID=your_figma_file_id_here

# YOLO Configuration
YOLO_WEIGHTS=yolov8n.pt
YOLO_DEVICE=cpu
```

**Note**: Railway automatically provides `RAILWAY_PUBLIC_DOMAIN` as a system variable. You don't need to set it manually!

#### Local Development
```bash
# Application Environment (defaults if not set)
ENV=dev
PORT=8000

# URLs and Origins (defaults if not set)
FRONTEND_ORIGIN=http://localhost:5173

# Figma Integration (Optional)
FIGMA_API_TOKEN=your_figma_token_here
FIGMA_FILE_ID=your_figma_file_id_here

# YOLO Configuration
YOLO_WEIGHTS=yolov8n.pt
YOLO_DEVICE=cpu
```

## Configuration Details

### Port Configuration
- **Production (Railway)**: PORT=8080 (required by Railway)
- **Local Development**: PORT=8000 (default if not set)
- The backend dynamically uses the PORT environment variable

### URL Construction
The backend constructs URLs dynamically based on environment:

```python
# Production: Uses RAILWAY_PUBLIC_DOMAIN (automatically provided by Railway)
# Railway provides the domain without https:// prefix
base_url = os.getenv("RAILWAY_PUBLIC_DOMAIN")  # e.g., "motion-kit-production.up.railway.app"
if base_url and not base_url.startswith('http'):
    base_url = f"https://{base_url}"  # Add protocol

# Local Development: Constructs from PORT
base_url = f"http://127.0.0.1:{PORT}"
```

**Important**: Railway automatically provides the `RAILWAY_PUBLIC_DOMAIN` variable. The backend automatically adds the `https://` protocol prefix.

### CORS Configuration
CORS is configured to allow:
- The primary `FRONTEND_ORIGIN` from environment variable
- `http://localhost:5173` (local frontend dev)
- `http://127.0.0.1:5173` (alternative local frontend)

### File Paths
All file paths use proper path resolution relative to the project structure:

```python
# Storage paths (from storage.py)
ROOT = pathlib.Path(__file__).resolve().parent.parent
UPLOADS = ROOT / "uploads"
RESULTS = ROOT / "results"

# Cache path (from main.py)
API_DIR = pathlib.Path(__file__).parent
CACHE_PATH = API_DIR / "figma_cache.json"
```

No hard-coded string paths like `"uploads/"` or `"figma_cache.json"` in the code.

## Railway Deployment Checklist

When deploying to Railway, ensure these environment variables are set:

- [x] `RAILWAY_PUBLIC_DOMAIN` - Automatically provided by Railway ✅
- [ ] `ENV=production`
- [ ] `PORT=8080`
- [ ] `FRONTEND_ORIGIN` (your Vercel URL)
- [ ] `FIGMA_API_TOKEN` (if using Figma integration)
- [ ] `FIGMA_FILE_ID` (if using Figma integration)
- [ ] `YOLO_WEIGHTS=yolov8n.pt`
- [ ] `YOLO_DEVICE=cpu`

**Good news**: Railway automatically provides `RAILWAY_PUBLIC_DOMAIN`! You only need to set the others.

## Vercel Frontend Configuration

The frontend needs to know the backend URL via:

```bash
VITE_API=https://your-railway-app.up.railway.app
```

This should match your `RAILWAY_PUBLIC_DOMAIN` value.

## Local Development

For local development, you can:
1. Use defaults (no .env file needed)
2. Create a `.env` file in the project root with custom values

Example local `.env`:
```bash
ENV=dev
PORT=8000
FRONTEND_ORIGIN=http://localhost:5173
FIGMA_API_TOKEN=your_token_here
FIGMA_FILE_ID=your_file_id_here
YOLO_WEIGHTS=yolov8n.pt
YOLO_DEVICE=cpu
```

## API Endpoints Base URL

The `/api/upload` endpoint returns URLs for results and video:
- Production: `https://your-railway-domain.up.railway.app/api/results/{job_id}`
- Local: `http://127.0.0.1:8000/api/results/{job_id}`

These are constructed dynamically based on environment.

## Troubleshooting

### Error: "RAILWAY_PUBLIC_DOMAIN environment variable not set in production"
This error should no longer occur - Railway automatically provides this variable. If you see it, check that Railway hasn't changed their system variables.

### CORS Errors
Ensure `FRONTEND_ORIGIN` in Railway matches your Vercel deployment URL exactly (including https://).

### Wrong PORT
- Railway requires PORT=8080
- Local development defaults to PORT=8000
- The Dockerfile exposes port 8080 and the CMD uses ${PORT} variable

## No Hard-Coded Values

The following are **NO LONGER** hard-coded:
- ❌ `"https://motion-kit-production.up.railway.app"` - Now uses `RAILWAY_PUBLIC_DOMAIN`
- ❌ `"http://127.0.0.1:8000"` - Now uses `f"http://127.0.0.1:{PORT}"`
- ❌ `"figma_cache.json"` - Now uses `CACHE_PATH` with proper path resolution
- ❌ Port 8000 - Now uses `PORT` environment variable

All URLs, ports, and paths are now configurable via environment variables! 🎉

