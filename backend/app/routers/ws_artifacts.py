"""
WebSocket endpoint for real-time artifact generation progress.

Pattern:
  1. Client connects: ws://localhost:8001/ws/artifact/{task_id}
  2. Server polls Celery result backend every 2s
  3. Server emits: { progress_pct, stage, eta_seconds, state }
  4. On SUCCESS: emits artifact data and closes connection
  5. On FAILURE: emits error and closes connection
  6. Client-side timeout: 180s (matches Celery task_time_limit)

Stage labels map to ArtifactSovereignAgent node pipeline:
  0-30%:  "Research Node: Loading knowledge corpus…"
  30-50%: "Research Node: Analysing domains…"
  50-75%: "Synthesis Node: Assembling content…"
  75-90%: "Adversarial Node: Generating questions…"
  90-100%: "Finalising artifact…"

⚠️ CAPACITY FLAG: Each active WS connection holds a FastAPI async task.
  For 50 concurrent users × 30s per artifact = 50 open WS connections × 30s.
  uvicorn handles this fine with asyncio (no thread-per-connection overhead).
  Migration trigger: >200 concurrent WS connections → AWS API Gateway WebSockets.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])

_POLL_INTERVAL_S = 2.0    # poll Celery every 2 seconds
_MAX_WAIT_S      = 180    # 3-minute timeout matches Celery task_time_limit


@router.websocket("/ws/artifact/{task_id}")
async def artifact_progress_ws(websocket: WebSocket, task_id: str):
    """
    Real-time artifact generation progress via WebSocket.
    Polls Celery result backend every 2s and broadcasts state.

    Message format (server → client):
      { "state": str, "progress_pct": int, "stage": str, "eta_seconds": int }

    Final message on success:
      { "state": "SUCCESS", "progress_pct": 100, "result": { artifact, cert } }
    """
    await websocket.accept()
    logger.info("[WS] Client connected for task %s", task_id)

    try:
        elapsed = 0.0

        while elapsed < _MAX_WAIT_S:
            state_data = await _poll_task(task_id)
            await websocket.send_text(json.dumps(state_data))

            if state_data["state"] in ("SUCCESS", "FAILURE"):
                break

            await asyncio.sleep(_POLL_INTERVAL_S)
            elapsed += _POLL_INTERVAL_S

        if elapsed >= _MAX_WAIT_S:
            await websocket.send_text(json.dumps({
                "state":        "TIMEOUT",
                "progress_pct": 0,
                "stage":        "Generation timed out. Please try again.",
                "eta_seconds":  0,
            }))

    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected from task %s", task_id)
    except Exception as exc:
        logger.error("[WS] Error on task %s: %s", task_id, exc)
        try:
            await websocket.send_text(json.dumps({
                "state": "ERROR",
                "stage": str(exc),
                "progress_pct": 0,
            }))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("[WS] Connection closed for task %s", task_id)


async def _poll_task(task_id: str) -> dict:
    """Poll Celery result backend for task state. Returns normalized state dict."""
    try:
        from celery.result import AsyncResult
        from backend.app.workers.celery_app import celery_app

        ar = AsyncResult(task_id, app=celery_app)
        state = ar.state

        if state == "PENDING":
            return {
                "state":        "PENDING",
                "progress_pct": 0,
                "stage":        "Queued — waiting for worker…",
                "eta_seconds":  30,
            }

        if state == "PROGRESS":
            meta = ar.info or {}
            pct  = meta.get("progress_pct", 0)
            msg  = meta.get("message", "Processing…")
            return {
                "state":        "PROGRESS",
                "progress_pct": pct,
                "stage":        msg,
                "eta_seconds":  max(0, int((100 - pct) / 100 * 30)),
            }

        if state == "SUCCESS":
            result = ar.result or {}
            return {
                "state":        "SUCCESS",
                "progress_pct": 100,
                "stage":        "Artifact generated successfully.",
                "eta_seconds":  0,
                "result":       result,
            }

        if state == "FAILURE":
            return {
                "state":        "FAILURE",
                "progress_pct": 0,
                "stage":        f"Generation failed: {ar.info}",
                "eta_seconds":  0,
            }

        return {"state": state, "progress_pct": 0, "stage": "Unknown state", "eta_seconds": 30}

    except Exception as exc:
        logger.warning("[WS] Celery poll failed for %s: %s", task_id, exc)
        # Return a fallback that doesn't break the WS loop
        return {
            "state":        "PENDING",
            "progress_pct": 0,
            "stage":        "Connecting to task queue…",
            "eta_seconds":  30,
        }
