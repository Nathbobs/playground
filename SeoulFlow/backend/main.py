import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from .pipeline import run_pipeline, state

_VIDEOS_DIR = Path(__file__).parent / "videos"

app = FastAPI(title="SeoulFlow")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_pipeline_task: asyncio.Task | None = None


class StartRequest(BaseModel):
    video_path: str  # filename only, e.g. "test.mp4" — resolved under backend/videos/ server-side


@app.post("/start")
async def start(req: StartRequest):
    global _pipeline_task
    if state.running:
        return JSONResponse({"message": "Already running"})

    # Resolve and validate before starting the task so errors surface immediately
    resolved = (_VIDEOS_DIR / req.video_path).resolve()
    if not resolved.is_relative_to(_VIDEOS_DIR.resolve()):
        raise HTTPException(status_code=400, detail="video_path must not escape the videos directory")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"Video not found: {req.video_path}")

    _pipeline_task = asyncio.create_task(run_pipeline(str(resolved)))
    return {"message": "Pipeline started", "video_path": str(resolved)}


@app.get("/status")
async def status():
    return {
        "total_vehicles": state.total_vehicles,
        "stationary": state.stationary,
        "moving": state.moving,
        "congestion_score": round(state.congestion_score, 3),
        "status": state.status,
        "fps": round(state.fps, 1),
    }


@app.post("/stop")
async def stop():
    global _pipeline_task
    state.running = False
    if _pipeline_task:
        _pipeline_task.cancel()
        try:
            await _pipeline_task
        except asyncio.CancelledError:
            pass
        _pipeline_task = None
    return {"message": "Pipeline stopped"}


@app.get("/preview")
async def preview():
    async def _frames():
        while state.running:
            frame = state.latest_frame
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            await asyncio.sleep(0.04)  # ~25 fps cap on preview stream

    return StreamingResponse(
        _frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
