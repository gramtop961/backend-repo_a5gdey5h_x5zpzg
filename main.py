import os
import json
import time
import uuid
from typing import Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:
    from database import db, create_document
except Exception:  # If database module fails for any reason
    db = None
    create_document = None

from schemas import Job, Clip

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fallback in-memory store when DB env is not configured
MEM_STORE_ENABLED = db is None
_mem_jobs: Dict[str, Dict[str, Any]] = {}


def save_job(doc: Dict[str, Any]) -> str:
    """Save job to DB if available, else memory, and return job_id."""
    if db is not None:
        # Mongo path
        from bson.objectid import ObjectId  # import locally to avoid dependency when no DB
        _id = db['job'].insert_one(doc).inserted_id
        return str(_id)
    # Memory path
    jid = uuid.uuid4().hex
    _mem_jobs[jid] = {**doc, "_id": jid}
    return jid


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    if db is not None:
        from bson.objectid import ObjectId
        return db['job'].find_one({"_id": ObjectId(job_id)})
    return _mem_jobs.get(job_id)


def update_job(job_id: str, updates: Dict[str, Any]):
    if db is not None:
        from bson.objectid import ObjectId
        db['job'].update_one({"_id": ObjectId(job_id)}, {"$set": updates})
        return
    if job_id in _mem_jobs:
        _mem_jobs[job_id].update(updates)


@app.get("/")
def read_root():
    return {"message": "ClipMaster backend is running"}


@app.get("/test")
def test_database():
    status = {
        "backend": "✅ Running",
        "database": "✅ Connected" if db is not None else "❌ Not Configured (using in-memory jobs)",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Connected" if db is not None else "Not Connected",
        "collections": db.list_collection_names() if db is not None else ["(memory) job"],
    }
    return status


# Demo processing timeline (in seconds)
PROCESS_SECONDS = 10


@app.post("/process")
async def process(
    file: Optional[UploadFile] = File(None),
    source_url: Optional[str] = Form(None),
    sources: Optional[str] = Form(None),
    clip_length: str = Form("auto"),
    aspect_ratio: str = Form("auto"),
    auto_highlights: str = Form("true"),
):
    # Validate at least one input
    link_list = []
    if sources:
        try:
            parsed = json.loads(sources)
            if isinstance(parsed, list):
                link_list = [str(x) for x in parsed if isinstance(x, str)]
        except Exception:
            pass
    if source_url and source_url not in link_list:
        link_list.append(source_url)

    if not file and len(link_list) == 0:
        raise HTTPException(status_code=400, detail="Provide a file or at least one link")

    source_type = 'file' if file else 'links'
    auto_h = str(auto_highlights).lower() in ("true", "1", "yes", "on")

    job_doc = Job(
        status='queued',
        progress=10,
        message='Queued for processing',
        source_type=source_type,
        original_filename=(file.filename if file else None),
        sources=(link_list if source_type == 'links' else None),
        clip_length=str(clip_length),
        aspect_ratio=str(aspect_ratio),
        auto_highlights=auto_h,
        clips=None,
    ).model_dump()

    job_id = save_job(job_doc)

    # store a timestamp to derive progress over time
    update_job(job_id, {"created_ts": time.time()})

    return {"job_id": job_id}


@app.get("/status/{job_id}")
async def status(job_id: str):
    doc = get_job(job_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")

    created_ts = float(doc.get('created_ts', time.time()))
    elapsed = max(0.0, time.time() - created_ts)

    if elapsed < PROCESS_SECONDS:
        pct = int(min(95, (elapsed / PROCESS_SECONDS) * 90) + 10)
        update_job(job_id, {
            'status': 'processing',
            'progress': pct,
            'message': 'Analyzing scenes, audio and generating captions…',
        })
        return {
            'status': 'processing',
            'progress': pct,
            'message': 'Working on your highlights…',
        }

    # Completed: create example clips if not already
    if not doc.get('clips'):
        ar = doc.get('aspect_ratio', 'auto')
        example_clips = [
            Clip(
                caption='Top moment with highest energy',
                duration=doc.get('clip_length') if doc.get('clip_length') != 'auto' else 30,
                aspect_ratio=ar,
                thumbnail_url='https://images.unsplash.com/photo-1504384308090-c894fdcc538d?q=80&w=1280&auto=format&fit=crop',
                download_url='https://file-examples.com/storage/fe0e7a8f6e2a6a5ef2d3b5f/2017/04/file_example_MP4_480_1_5MG.mp4',
            ).model_dump(),
            Clip(
                caption='Funny reaction with clean transcript',
                duration=20,
                aspect_ratio=ar,
                thumbnail_url='https://images.unsplash.com/photo-1524253482453-3fed8d2fe12b?q=80&w=1280&auto=format&fit=crop',
                download_url='https://file-examples.com/storage/fe0e7a8f6e2a6a5ef2d3b5f/2017/04/file_example_MP4_1280_10MG.mp4',
            ).model_dump(),
        ]
        update_job(job_id, {
            'status': 'completed',
            'progress': 100,
            'message': 'All done! Your clips are ready.',
            'clips': example_clips,
        })
        doc = get_job(job_id)

    return {
        'status': doc.get('status', 'completed'),
        'progress': int(doc.get('progress', 100)),
        'message': doc.get('message', ''),
        'clips': doc.get('clips', []),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
