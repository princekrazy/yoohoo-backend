
import os
import tempfile
from pathlib import Path
from fastapi import UploadFile, File
import asyncio
import csv
import shutil
import uuid
from fastapi import Form
from app.storage import supabase, BUCKET
import subprocess
import sys
from statistics import mean
from app.routes.videos import router as videos_router
from dotenv import load_dotenv
import cv2
import time
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, HTTPException 

load_dotenv()

app = FastAPI(
    title="Yoohoo API",
    description="Backend for a video authenticity platform",
    version="0.1.0",
)
# Allow requests from your frontend
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://frontend-six-fawn-29.vercel.app/",

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos_router)


MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_SAMPLED_FRAMES = 12
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}
SYNTHETIC_THRESHOLD = 0.30


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Yoohoo API"}


def inspect_video(video_path: str) -> dict:
    """Read video metadata and sample frames for later analysis."""
    cap = cv2.VideoCapture(video_path)

    try:
        if not cap.isOpened():
            raise ValueError("Could not decode the uploaded video.")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps <= 0 or frame_count <= 0:
            raise ValueError("Video has invalid duration or frame metadata.")

        duration = frame_count / fps
        timestamps = []

        # Sample approximately one frame per second, with a limit.
        sample_count = min(
            max(1, int(duration) + 1),
            MAX_SAMPLED_FRAMES,
        )

        for i in range(sample_count):
            timestamp = min(float(i), max(0.0, duration - 0.05))
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)

            success, frame = cap.read()

            if success and frame is not None:
                timestamps.append(round(timestamp, 2))

        if not timestamps:
            raise ValueError("No readable video frames were found.")

        return {
            "duration_seconds": round(duration, 2),
            "fps": round(fps, 2),
            "frame_count": frame_count,
            "sampled_frames": len(timestamps),
            "sampled_timestamps": timestamps,
        }
    finally:
        cap.release()


NVIDIA_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "vendor"
    / "nvidia-synthetic-video-detector"
    / "scripts"
    / "v1"
    / "synthetic-video-detector.py"
)


def analyze_with_nvidia(video_path: str) -> dict:
    """Run NVIDIA's detector and aggregate its sample scores."""
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY is not configured.")

    if not NVIDIA_SCRIPT.is_file():
        raise RuntimeError(f"Detector script not found: {NVIDIA_SCRIPT}")

    # NVIDIA's tested client requires MP4 input.
    if Path(video_path).suffix.lower() != ".mp4":
        raise ValueError(
            "NVIDIA detection currently requires MP4 videos."
        )

    with tempfile.TemporaryDirectory() as directory:
        work_dir = Path(directory)
        input_video = work_dir / "upload.mp4"
        shutil.copyfile(video_path, input_video)

        command = [
            sys.executable,
            str(NVIDIA_SCRIPT),
            "--preview-mode",
            "--target", "grpc.nvcf.nvidia.com:443",
            "--function-id",
            "847b6e53-0133-452d-ab85-d7acf3ace723",
            "--api-key", api_key,
            "--video-input", str(input_video),
            "--save-csv",
        ]

        try:
            result = subprocess.run(
                command,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("NVIDIA detection timed out.") from exc

        csv_path = work_dir / "upload.csv"

        if (
            result.returncode != 0
            or "Detection completed successfully!" not in result.stdout
            or not csv_path.is_file()
        ):
            # Collect diagnostic output without exposing the API key.
            stdout = (result.stdout or "").replace(api_key, "[REDACTED]")
            stderr = (result.stderr or "").replace(api_key, "[REDACTED]")

            details = (
                f"Exit code: {result.returncode}\n"
                f"STDOUT:\n{stdout[-2500:] or '(empty)'}\n"
                f"STDERR:\n{stderr[-2500:] or '(empty)'}"
            )

            raise RuntimeError(f"NVIDIA detection failed.\n{details}")

        with csv_path.open(newline="", encoding="utf-8") as csv_file:
            rows = list(csv.DictReader(csv_file))

        scores = [float(row["probability"]) for row in rows]

        if not scores:
            raise RuntimeError("NVIDIA returned no detection scores.")

        return {
            "mean_probability": round(mean(scores), 6),
            "min_probability": round(min(scores), 6),
            "max_probability": round(max(scores), 6),
            "samples_analyzed": len(scores),
        }



@app.post("/api/videos/analyze")
async def analyze_video(
    title: str = Form(...),
    file: UploadFile = File(...),
):
    started = time.perf_counter()
    print("[upload] Request received", flush=True)
    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported video format.",
        )

    temp_path = None

    try:
        # Stream to a temporary file while enforcing the size limit.
        size = 0

        with tempfile.NamedTemporaryFile(
            suffix=extension, delete=False
        ) as temp:
            temp_path = temp.name

            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                size += len(chunk)

                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Video exceeds the 100 MB limit.",
                    )

                temp.write(chunk)
        print(
            f"[upload] File saved: {size / (1024 * 1024):.1f} MB "
            f"in {time.perf_counter() - started:.1f}s",
            flush=True,
        )

        if size == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        try:
            print("[upload] Inspecting video...", flush=True)
            metadata = inspect_video(temp_path)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        print(
            f"[upload] Video inspection complete "
            f"({time.perf_counter() - started:.1f}s elapsed)",
            flush=True,
        )       

       
        if extension != ".mp4":
            raise HTTPException(
                status_code=400,
                detail="AI analysis currently supports MP4 videos only.",
            )
        print("[upload] Starting NVIDIA analysis...", flush=True)
        nvidia_started = time.perf_counter()

        try:
            detection = await asyncio.to_thread(
                analyze_with_nvidia, temp_path
            )
        except (RuntimeError, ValueError) as exc:
            print(f"[upload] NVIDIA failed: {exc}", flush=True)
            raise HTTPException(
                status_code=502,
                detail=str(exc),
            ) from exc
        finally:
            print(
                f"[upload] NVIDIA call finished after "
                f"{time.perf_counter() - nvidia_started:.1f}s",
                flush=True,
            )

        print(
            f"[upload] NVIDIA score: {detection['mean_probability']}",
            flush=True,
        )


        score = detection["mean_probability"]
        rejected = score >= SYNTHETIC_THRESHOLD

        if rejected:
            return {
                "status": "rejected",
                "filename": Path(file.filename or "video.mp4").name,
                "file_size_bytes": size,
                "video": metadata,
                "detection": {
                    "model_integrated": True,
                    **detection,
                    "threshold": SYNTHETIC_THRESHOLD,
                    "decision": "reject",
                    "message": (
                        "This video appears likely to be AI-generated "
                        "and was rejected."
                    ),
                },
            }

        # Only approved videos are stored and published.
        video_id = str(uuid.uuid4())
        storage_path = f"{video_id}/original.mp4"
        title = title.strip()

        if not title or len(title) > 150:
            raise HTTPException(
                status_code=400,
                detail="Title must be 1–150 characters.",
            )

        try:
            # Upload the actual MP4 to Supabase Storage.
            print("[upload] Uploading to Supabase Storage...", flush=True)
            storage_started = time.perf_counter()
            with open(temp_path, "rb") as video_file:
                supabase.storage.from_(BUCKET).upload(
                    path=storage_path,
                    file=video_file,
                    file_options={
                        "content-type": "video/mp4",
                        "upsert": "false",
                    },
                )
            print(
                f"[upload] Storage upload finished in "
                f"{time.perf_counter() - storage_started:.1f}s",
                flush=True,
            )

            print("[upload] Inserting database record...", flush=True)

            # Save the matching video record to PostgreSQL.
            supabase.table("videos").insert({
                "id": video_id,
                "title": title,
                "original_filename": Path(
                    file.filename or "video.mp4"
                ).name,
                "storage_path": storage_path,
                "content_type": "video/mp4",
                "file_size_bytes": size,
                "mean_score": detection["mean_probability"],
                "min_score": detection["min_probability"],
                "max_score": detection["max_probability"],
                "samples_analyzed": detection["samples_analyzed"],
                "status": "published",
            }).execute()
            print("[upload] Database insert complete", flush=True)

        except Exception as exc:
            # Avoid leaving an orphaned Storage object if saving fails.
            try:
                supabase.storage.from_(BUCKET).remove([storage_path])
            except Exception:
                pass

            print(f"Could not persist approved video: {exc}")
            raise HTTPException(
                status_code=500,
                detail=(
                    "The video passed analysis but could not be saved. "
                    "Check the backend logs and database schema."
                ),
            ) from exc
        print(
            f"[upload] SUCCESS — total time: "
            f"{time.perf_counter() - started:.1f}s",
            flush=True,
        )
        

        return {
            "status": "approved",
            "id": video_id,
            "filename": Path(file.filename or "video.mp4").name,
            "file_size_bytes": size,
            "video": metadata,
            "detection": {
                "model_integrated": True,
                **detection,
                "threshold": SYNTHETIC_THRESHOLD,
                "decision": "accept",
                "message": (
                    "Your video passed the demo's detection threshold "
                    "and was saved for publication."
                ),
            },
        }


    finally:
        await file.close()

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
