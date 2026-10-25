
from fastapi import APIRouter, HTTPException

from app.storage import supabase, BUCKET

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("")
def list_published_videos():
    try:
        response = (
            supabase.table("videos")
            .select(
                "id,title,storage_path,content_type,"
                "created_at,mean_score,samples_analyzed"
            )
            .eq("status", "published")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        videos = []

        for row in response.data or []:
            signed = supabase.storage.from_(BUCKET).create_signed_url(
                row["storage_path"],
                3600,
            )

            playback_url = (
                signed.get("signedURL")
                or signed.get("signedUrl")
            )

            if not playback_url:
                raise RuntimeError("Could not generate a video URL.")

            videos.append({
                **row,
                "playback_url": playback_url,
            })

        return {"videos": videos}

    except Exception as exc:
        print(f"Could not load published videos: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not load published videos.",
        ) from exc
