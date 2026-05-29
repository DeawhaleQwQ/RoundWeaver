from __future__ import annotations

from pathlib import Path
from typing import Any
import logging

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from cs2demo.replay import (
    ensure_replay_cache,
    latest_sandbox_state,
    list_demos,
    project_paths,
    read_json,
    replay_cache_dir,
    resolve_demo_path,
    save_sandbox_state,
)

LOGGER = logging.getLogger("cs2demo.server")


def create_app() -> FastAPI:
    paths = project_paths()
    app = FastAPI(title="CS2 Dust2 Replay", version="0.3.0")
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.mount("/assets", StaticFiles(directory=paths.assets_dir), name="assets")
    app.mount("/static", StaticFiles(directory=paths.web_dir), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(paths.web_dir / "index.html")

    @app.get("/api/demos")
    def api_demos() -> dict[str, Any]:
        demos = list_demos(paths)
        return {"demos": demos, "default_demo_id": "test_dust2" if any(d["demo_id"] == "test_dust2" for d in demos) else (demos[0]["demo_id"] if demos else None)}

    @app.post("/api/demos/{demo_id}/prepare")
    def api_prepare(
        demo_id: str,
        force: bool = Query(False),
        tick_interval: int = Query(8, ge=1),
        tick_rate: float = Query(64.0, gt=0),
        scope: str = Query("auto", pattern="^(auto|both|T|CT)$"),
        utility_trajectory_mode: str = Query("auto", pattern="^(auto|precise|approximate)$"),
    ) -> dict[str, Any]:
        try:
            demo_path = resolve_demo_path(demo_id, paths)
            manifest_path = ensure_replay_cache(demo_id, tick_interval=tick_interval, tick_rate=tick_rate, scope=scope, force=force, paths=paths, trajectory_mode=utility_trajectory_mode)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "ready": True,
            "demo_id": demo_id,
            "demo_path": str(demo_path.relative_to(paths.root)),
            "replay_url": f"/api/demos/{demo_id}/replay.json",
            "manifest_path": str(manifest_path.relative_to(paths.root)),
        }

    @app.get("/api/demos/{demo_id}/replay.json")
    def api_replay(demo_id: str) -> JSONResponse:
        try:
            manifest_path = ensure_replay_cache(demo_id, paths=paths)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return JSONResponse(read_json(manifest_path))

    @app.get("/api/demos/{demo_id}/rounds/{round_number}")
    def api_round(demo_id: str, round_number: int) -> JSONResponse:
        try:
            ensure_replay_cache(demo_id, paths=paths)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        round_path = replay_cache_dir(demo_id, paths) / "rounds" / f"{round_number}.json"
        if not round_path.exists():
            raise HTTPException(status_code=404, detail=f"Round not found: {round_number}")
        return JSONResponse(read_json(round_path))

    @app.get("/api/demos/{demo_id}/sandbox/latest")
    def api_sandbox_latest(demo_id: str) -> dict[str, Any]:
        try:
            state = latest_sandbox_state(demo_id, paths)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if state is None:
            return {"exists": False, "state": None}
        return {"exists": True, "state": state}

    @app.post("/api/demos/{demo_id}/sandbox")
    def api_sandbox_save(demo_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        try:
            return save_sandbox_state(demo_id, payload, paths)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    uvicorn.run(create_app(), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
