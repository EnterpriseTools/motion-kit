# api/main.py
import os, uuid, json
from fastapi import FastAPI, UploadFile, File, Body, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from storage import save_upload, save_results, local_result_path, UPLOADS
from detector import run_detection   # <-- use original detector for now
from figma_service import get_figma_service
import pathlib

load_dotenv()
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
ENV = os.getenv("ENV", "dev")
PORT = int(os.getenv("PORT", "8000"))  # Railway uses 8080, local dev uses 8000

# Define cache path relative to the api directory
API_DIR = pathlib.Path(__file__).parent
CACHE_PATH = API_DIR / "figma_cache.json"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"ok": True, "env": ENV}

@app.post("/api/upload")
async def upload(
    video: UploadFile = File(...),
    mode: str = "all"  # 'taser', 'hawkeye', 'all'
):
    job_id = uuid.uuid4().hex[:12]
    file_bytes = await video.read()
    saved_path = save_upload(job_id, video.filename, file_bytes)

    # Run detection (YOLOv8 + ByteTrack) with mode-specific classes
    # Determine detection classes based on mode
    if mode == "taser":
        # Taser mode: detect both people and vehicles, but people are priority
        classes = (0, 2, 3, 5, 7)  # person, car, motorcycle, bus, truck
    elif mode == "hawkeye":
        # Hawkeye mode: detect both people and vehicles, but vehicles are priority
        classes = (0, 2, 3, 5, 7)  # person, car, motorcycle, bus, truck
    else:  # mode == "all"
        # All mode: detect everything
        classes = (0, 2, 3, 5, 7)  # person, car, motorcycle, bus, truck
    
    results = run_detection(
        saved_path,
        conf=0.25,        # start conservative; tune later
        sample_stride=2,  # process every 2nd frame for faster turnaround
        max_frames=900,   # ~30 sec @ 30fps/stride 2; remove for full video
        classes=classes
    )
    
    # Add mode to results for frontend processing
    results["mode"] = mode
    save_results(job_id, results)

    # Construct the base URL dynamically based on environment
    # Railway provides RAILWAY_PUBLIC_DOMAIN without https:// prefix
    base_url = (
        os.getenv("RAILWAY_PUBLIC_DOMAIN") or 
        os.getenv("PUBLIC_URL") or
        os.getenv("RAILWAY_STATIC_URL") or
        None
    )
    
    if base_url:
        # Railway provides domain without protocol, add https:// if missing
        if not base_url.startswith(('http://', 'https://')):
            base_url = f"https://{base_url}"
    else:
        # Fallback for local development
        base_url = f"http://127.0.0.1:{PORT}"

    return {
        "jobId": job_id,
        "resultUrl": f"{base_url}/api/results/{job_id}",
        "videoUrl": f"{base_url}/api/video/{job_id}",
        "status": "ready"
    }

@app.get("/api/results/{job_id}")
def get_results(job_id: str):
    path = local_result_path(job_id)
    if not os.path.exists(path):
        return {"error": "not found"}
    return __import__("json").load(open(path))

@app.get("/api/video/{job_id}")
def get_video(job_id: str):
    # Find the video file for this job_id
    for filename in os.listdir(UPLOADS):
        if filename.startswith(f"{job_id}_"):
            video_path = UPLOADS / filename
            if video_path.exists():
                return FileResponse(
                    video_path,
                    media_type="video/mp4",
                    headers={"Content-Disposition": f"inline; filename={filename}"}
                )
    raise HTTPException(status_code=404, detail="Video not found")

@app.post("/api/figma/sync")
async def sync_figma_designs():
    """Fetch latest designs from Figma and cache them."""
    try:
        figma_service = get_figma_service()
        if not figma_service:
            raise HTTPException(status_code=500, detail="Figma service not configured. Please set FIGMA_API_TOKEN and FIGMA_FILE_ID environment variables.")
        
        # Fetch components from Figma
        components = figma_service.fetch_components()
        
        # Fetch PNG/SVG data for components that need it
        for component in components:
            if component.type == 'crosshair':
                # Fetch as PNG for crosshairs (with transparent background)
                png_data = figma_service.fetch_component_png(component.id)
                if png_data:
                    component.svg_data = png_data  # Store as base64 PNG data URL
            elif component.type == 'tracking-dot':
                # Fetch as SVG for tracking dots
                svg_data = figma_service.fetch_component_svg(component.id)
                if svg_data:
                    import base64
                    component.svg_data = base64.b64encode(svg_data.encode()).decode()
        
        # Convert to visual settings format
        visual_settings = figma_service.convert_to_visual_settings(components)
        
        # Get diagnostics from the sync process
        diagnostics = figma_service.get_diagnostics_summary()
        
        # Cache the results
        cache_data = {
            'components': [
                {
                    'id': comp.id,
                    'name': comp.name,
                    'type': comp.type,
                    'styles': comp.styles,
                    'svg_data': comp.svg_data,
                    'bounds': comp.bounds
                }
                for comp in components
            ],
            'visual_settings': visual_settings,
            'crosshair_images': {
                'default': None,
                'active': None,
                'defaultSize': None,
                'activeSize': None
            }
        }
        
        # Find and store crosshair images with their sizes
        for comp in components:
            if comp.type == 'crosshair':
                name_lower = comp.name.lower()
                if 'crosshair-default' in name_lower and comp.svg_data:
                    cache_data['crosshair_images']['default'] = comp.svg_data
                    # Store the width from Figma bounds
                    if comp.bounds and 'width' in comp.bounds:
                        cache_data['crosshair_images']['defaultSize'] = comp.bounds['width']
                elif 'crosshair-active' in name_lower and comp.svg_data:
                    cache_data['crosshair_images']['active'] = comp.svg_data
                    # Store the width from Figma bounds
                    if comp.bounds and 'width' in comp.bounds:
                        cache_data['crosshair_images']['activeSize'] = comp.bounds['width']
        
        # Fetch Body-Tracker variant component
        body_tracker_data = figma_service.fetch_component_variants('Body-Tracker')
        if body_tracker_data and 'variants' in body_tracker_data:
            cache_data['body_tracker'] = {
                'component_id': body_tracker_data['component_id'],
                'variants': {}
            }
            
            # Store each variant's properties and fetch PNG images
            for variant_name, variant_info in body_tracker_data['variants'].items():
                properties = variant_info.get('properties', {})
                bounds = variant_info.get('bounds', {})
                variant_id = variant_info.get('id')
                
                # Fetch PNG image for this variant (like we do for crosshairs)
                png_data = None
                if variant_id:
                    png_data = figma_service.fetch_component_png(variant_id)
                
                cache_data['body_tracker']['variants'][variant_name] = {
                    'properties': properties,
                    'bounds': bounds,
                    'image': png_data  # Store the PNG image data
                }
        else:
            # Add empty structure if not found
            cache_data['body_tracker'] = {
                'component_id': None,
                'variants': {}
            }
        
        # Save to cache file
        with open(CACHE_PATH, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        return {
            "status": "success",
            "components_found": len(components),
            "components": cache_data['components'],  # Include the actual components array
            "visual_settings": visual_settings,
            "crosshair_images": cache_data['crosshair_images'],
            "body_tracker": cache_data['body_tracker'],
            "warnings": diagnostics,
            "message": f"Successfully synced {len(components)} components from Figma" + (f" with {len(diagnostics)} warnings" if diagnostics else "")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync Figma designs: {str(e)}")

@app.get("/api/figma/designs")
def get_figma_designs():
    """Get cached Figma design data."""
    try:
        with open(CACHE_PATH, 'r') as f:
            cache_data = json.load(f)
        
        return {
            "status": "success",
            "data": cache_data
        }
    except FileNotFoundError:
        return {
            "status": "no_cache",
            "message": "No cached Figma designs found. Please sync first."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cached designs: {str(e)}")

@app.post("/api/figma/apply")
async def apply_figma_design(request_data: dict):
    """Apply a specific Figma design preset to visual settings."""
    try:
        design_name = request_data.get('design_name')
        if not design_name:
            raise HTTPException(status_code=400, detail="design_name is required")
        
        # Get cached designs
        with open(CACHE_PATH, 'r') as f:
            cache_data = json.load(f)
        
        # Find components matching the design name
        matching_components = [
            comp for comp in cache_data['components']
            if design_name.lower() in comp['name'].lower()
        ]
        
        if not matching_components:
            raise HTTPException(status_code=404, detail=f"No components found matching design '{design_name}'")
        
        # Convert matching components to visual settings
        figma_service = get_figma_service()
        if not figma_service:
            raise HTTPException(status_code=500, detail="Figma service not configured")
        
        # Recreate component objects for conversion
        from figma_service import FigmaComponent
        components = [
            FigmaComponent(
                id=comp['id'],
                name=comp['name'],
                type=comp['type'],
                styles=comp['styles'],
                svg_data=comp.get('svg_data'),
                bounds=comp.get('bounds')
            )
            for comp in matching_components
        ]
        
        visual_settings = figma_service.convert_to_visual_settings(components)
        
        return {
            "status": "success",
            "visual_settings": visual_settings,
            "applied_components": len(matching_components)
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No cached Figma designs found. Please sync first.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply Figma design: {str(e)}")
