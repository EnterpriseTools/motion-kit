import os, json, pathlib
from typing import Dict, Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
UPLOADS = ROOT / "uploads"
RESULTS = ROOT / "results"
UPLOADS.mkdir(exist_ok=True)
RESULTS.mkdir(exist_ok=True)

def save_upload(job_id: str, filename: str, file_bytes) -> str:
    dest = UPLOADS / f"{job_id}_{filename}"
    with open(dest, "wb") as f:
        f.write(file_bytes)
    return str(dest)

def save_results(job_id: str, data: Dict[str, Any]) -> str:
    dest = RESULTS / f"{job_id}.json"
    with open(dest, "w") as f:
        json.dump(data, f)
    return str(dest)

def local_result_path(job_id: str) -> str:
    return str(RESULTS / f"{job_id}.json")
