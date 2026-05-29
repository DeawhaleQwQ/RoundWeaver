from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
import argparse
import asyncio
import json
import logging
import os
import re
import time
import uuid

from fastapi import Body, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from cs2demo.replay import (
    create_room_state,
    delete_room_state,
    ensure_replay_cache,
    latest_sandbox_state,
    list_demos,
    list_room_states,
    load_room_state,
    normalize_room_code,
    room_is_expired,
    parse_iso_datetime,
    purge_expired_rooms,
    project_paths,
    read_json,
    replay_cache_dir,
    resolve_demo_path,
    save_room_state,
    save_sandbox_state,
)
from cs2demo.tunnel import TunnelManager

LOGGER = logging.getLogger("cs2demo.server")
ROOMS: dict[str, dict[str, Any]] = {}
ROOM_CONNECTIONS: dict[str, dict[str, WebSocket]] = {}
ROOM_CONNECTION_IDS: dict[str, dict[str, str]] = {}
ROOM_SAVE_TASKS: dict[str, asyncio.Task] = {}
ROOM_PARTICIPANT_OFFLINE_TTL_SEC = 10 * 60
ROOM_IDLE_TTL_SEC = 2 * 60 * 60
ROOM_HEARTBEAT_TIMEOUT_SEC = 45
LOCAL_ONLY_WARNING = "当前链接只在本机可用，队友无法通过公网加入。请使用 --tunnel cloudflared 或设置 CS2PLUGIN_PUBLIC_BASE_URL。"


@dataclass(frozen=True)
class ServerSettings:
    host: str
    port: int
    public_base_url: str
    share_mode: str
    tunnel_provider: str
    tunnel_command: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def server_time_ms() -> int:
    return int(time.time() * 1000)


def app_config_path(paths: Any) -> Path:
    return paths.root / "config" / "app_config.json"


def read_app_config(paths: Any) -> dict[str, Any]:
    path = app_config_path(paths)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def cli_value(cli_values: Any | None, key: str) -> Any:
    if cli_values is None:
        return None
    if isinstance(cli_values, dict):
        return cli_values.get(key)
    return getattr(cli_values, key, None)


def sanitize_public_base_url(value: Any) -> str:
    if value is None:
        return ""
    url = str(value).strip().rstrip("/")
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("public_base_url must start with http:// or https://")
    return url


def normalize_tunnel_provider(value: Any) -> str:
    if value is None:
        return ""
    provider = str(value).strip().lower()
    if provider in {"", "0", "false", "none", "off", "local"}:
        return ""
    if provider != "cloudflared":
        raise ValueError(f"Unsupported tunnel provider: {value}")
    return provider


def coerce_port(value: Any, fallback: int) -> int:
    if value is None or value == "":
        return fallback
    port = int(value)
    if port <= 0 or port > 65535:
        raise ValueError(f"Invalid port: {value}")
    return port


def local_share_host(host: str) -> str:
    if host in {"0.0.0.0", "::", ""}:
        return "127.0.0.1"
    return host.strip("[]")


def load_server_settings(paths: Any | None = None, cli_values: Any | None = None) -> ServerSettings:
    paths = paths or project_paths()
    config = read_app_config(paths)
    server_config = config.get("server", {}) if isinstance(config.get("server"), dict) else {}
    tunnel_config = config.get("tunnel", {}) if isinstance(config.get("tunnel"), dict) else {}

    host = cli_value(cli_values, "host") or os.getenv("CS2PLUGIN_HOST") or server_config.get("host") or "127.0.0.1"
    port = coerce_port(cli_value(cli_values, "port") or os.getenv("CS2PLUGIN_PORT") or server_config.get("port"), 8000)
    public_base_url = sanitize_public_base_url(
        cli_value(cli_values, "public_url")
        if cli_value(cli_values, "public_url") is not None
        else os.getenv("CS2PLUGIN_PUBLIC_BASE_URL")
        if os.getenv("CS2PLUGIN_PUBLIC_BASE_URL") is not None
        else server_config.get("public_base_url")
    )

    config_tunnel_provider = tunnel_config.get("provider", "cloudflared") if tunnel_config.get("enabled") else ""
    tunnel_provider = normalize_tunnel_provider(
        cli_value(cli_values, "tunnel")
        if cli_value(cli_values, "tunnel") is not None
        else os.getenv("CS2PLUGIN_TUNNEL")
        if os.getenv("CS2PLUGIN_TUNNEL") is not None
        else config_tunnel_provider
    )
    tunnel_command = str(tunnel_config.get("command") or "cloudflared")

    if public_base_url:
        share_mode = "public_url"
        tunnel_provider = ""
    elif tunnel_provider:
        share_mode = tunnel_provider
    else:
        share_mode = str(server_config.get("share_mode") or "local")
        if share_mode not in {"local", "public_url", "cloudflared"}:
            share_mode = "local"

    return ServerSettings(
        host=str(host),
        port=port,
        public_base_url=public_base_url,
        share_mode=share_mode,
        tunnel_provider=tunnel_provider,
        tunnel_command=tunnel_command,
    )


def room_public_state(room: dict[str, Any]) -> dict[str, Any]:
    state = dict(room)
    state["participants"] = dict(room.get("participants", {}))
    return state


def ensure_room_loaded(room_code: str, paths: Any) -> dict[str, Any]:
    code = normalize_room_code(room_code)
    room = ROOMS.get(code)
    if room is None:
        room = load_room_state(code, paths, idle_ttl_sec=ROOM_IDLE_TTL_SEC)
        ROOMS[code] = room
    elif room_is_expired(room, ROOM_IDLE_TTL_SEC):
        ROOMS.pop(code, None)
        ROOM_CONNECTIONS.pop(code, None)
        ROOM_CONNECTION_IDS.pop(code, None)
        delete_room_state(code, paths)
        raise KeyError(f"Unknown room_code: {room_code}")
    return room


def increment_room_version(room: dict[str, Any]) -> None:
    room["version"] = int(room.get("version") or 0) + 1
    now = utc_now_iso()
    room["updated_at"] = now
    room["last_activity_at"] = now


def room_participants(room: dict[str, Any]) -> dict[str, dict[str, Any]]:
    participants = room.setdefault("participants", {})
    if not isinstance(participants, dict):
        participants = {}
        room["participants"] = participants
    return participants


def normalize_identity_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def participant_identity_key(profile: dict[str, Any]) -> str:
    stable_client_id = normalize_identity_text(profile.get("client_id"))
    if stable_client_id:
        return f"client:{stable_client_id}"
    role = normalize_identity_text(profile.get("role") or "viewer")
    assigned_player_id = normalize_identity_text(profile.get("assigned_player_id"))
    if role == "player" and assigned_player_id:
        return f"player:{assigned_player_id}"
    display_name = normalize_identity_text(profile.get("display_name") or profile.get("name"))
    if display_name:
        return f"name:{display_name}"
    return ""


def find_existing_participant(room: dict[str, Any], profile: dict[str, Any]) -> str | None:
    participants = room_participants(room)
    identity_key = participant_identity_key(profile)
    assigned_player_id = normalize_identity_text(profile.get("assigned_player_id"))
    role = normalize_identity_text(profile.get("role") or "viewer")
    display_name = normalize_identity_text(profile.get("display_name") or profile.get("name"))
    for client_id, participant in participants.items():
        if identity_key and participant.get("identity_key") == identity_key:
            return client_id
    if role == "player" and assigned_player_id:
        for client_id, participant in participants.items():
            if normalize_identity_text(participant.get("role")) == "player" and normalize_identity_text(participant.get("assigned_player_id")) == assigned_player_id:
                return client_id
    if display_name:
        for client_id, participant in participants.items():
            if normalize_identity_text(participant.get("display_name")) == display_name:
                return client_id
    return None


def participant_payload(client_id: str, message: dict[str, Any]) -> dict[str, Any]:
    now = utc_now_iso()
    name = str(message.get("display_name") or message.get("name") or f"User {client_id[:4]}")[:40]
    return {
        "client_id": client_id,
        "display_name": name,
        "role": message.get("role") or "viewer",
        "assigned_player_id": message.get("assigned_player_id"),
        "identity_key": participant_identity_key(message),
        "online": True,
        "joined_at": now,
        "last_seen_at": now,
    }


def register_participant(room: dict[str, Any], profile: dict[str, Any], connection_id: str) -> str:
    participants = room_participants(room)
    client_id = find_existing_participant(room, profile) or normalize_identity_text(profile.get("client_id")) or uuid.uuid4().hex[:12]
    existing = participants.get(client_id, {}) if isinstance(participants.get(client_id), dict) else {}
    payload = participant_payload(client_id, profile)
    payload["joined_at"] = existing.get("joined_at") or payload["joined_at"]
    payload["connection_id"] = connection_id
    participants[client_id] = {**existing, **payload}
    room["last_activity_at"] = utc_now_iso()
    return client_id


def mark_participant_offline(room: dict[str, Any], client_id: str, connection_id: str | None = None) -> bool:
    participant = room_participants(room).get(client_id)
    if not participant:
        return False
    if connection_id and participant.get("connection_id") != connection_id:
        return False
    if not participant.get("online"):
        return False
    participant["online"] = False
    participant["last_seen_at"] = utc_now_iso()
    participant.pop("connection_id", None)
    increment_room_version(room)
    return True


def prune_room_presence(room: dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    changed = False
    participants = room_participants(room)
    for client_id in list(participants):
        participant = participants[client_id]
        last_seen = parse_iso_datetime(participant.get("last_seen_at")) or parse_iso_datetime(participant.get("joined_at")) or now
        age_sec = (now - last_seen).total_seconds()
        if participant.get("online") and age_sec > ROOM_HEARTBEAT_TIMEOUT_SEC:
            participant["online"] = False
            participant.pop("connection_id", None)
            changed = True
        if not participant.get("online") and age_sec > ROOM_PARTICIPANT_OFFLINE_TTL_SEC:
            participants.pop(client_id, None)
            changed = True
    if changed:
        increment_room_version(room)
    return changed


def online_participant_count(room: dict[str, Any]) -> int:
    return sum(1 for participant in room_participants(room).values() if participant.get("online"))


async def broadcast_room(room_code: str, message: dict[str, Any], exclude_client_id: str | None = None) -> None:
    room = ROOMS.get(room_code)
    dead_clients = []
    for client_id, websocket in list(ROOM_CONNECTIONS.get(room_code, {}).items()):
        if client_id == exclude_client_id:
            continue
        try:
            await websocket.send_json(message)
        except Exception:
            dead_clients.append(client_id)
    changed = False
    for client_id in dead_clients:
        connection_id = ROOM_CONNECTION_IDS.get(room_code, {}).pop(client_id, None)
        ROOM_CONNECTIONS.get(room_code, {}).pop(client_id, None)
        if room and mark_participant_offline(room, client_id, connection_id):
            changed = True
    if changed and room:
        save_room_state(room, project_paths())
        await broadcast_room(room_code, {"type": "participant_update", "version": room["version"], "participants": room_participants(room)})


def save_room_debounced(room_code: str, paths: Any, delay: float = 0.75) -> None:
    existing = ROOM_SAVE_TASKS.get(room_code)
    if existing and not existing.done():
        existing.cancel()

    async def delayed_save() -> None:
        try:
            await asyncio.sleep(delay)
            room = ROOMS.get(room_code)
            if room:
                save_room_state(room, paths)
        except asyncio.CancelledError:
            return

    ROOM_SAVE_TASKS[room_code] = asyncio.create_task(delayed_save())


def default_playback_for_demo(demo_id: str, payload: dict[str, Any], paths: Any) -> dict[str, Any]:
    manifest_path = ensure_replay_cache(demo_id, paths=paths)
    manifest = read_json(manifest_path)
    rounds = manifest.get("rounds", [])
    indexed_rounds = {int(row.get("round")): row for row in rounds if row.get("round") is not None}
    if not indexed_rounds:
        raise KeyError(f"No rounds for demo_id: {demo_id}")
    selected_round = payload.get("round_number")
    try:
        selected_round = int(selected_round) if selected_round is not None else next(iter(indexed_rounds))
    except (TypeError, ValueError):
        selected_round = next(iter(indexed_rounds))
    if selected_round not in indexed_rounds:
        selected_round = next(iter(indexed_rounds))
    round_path = replay_cache_dir(demo_id, paths) / "rounds" / f"{selected_round}.json"
    round_data = read_json(round_path) if round_path.exists() else {}
    frames = round_data.get("frames", [])
    first_tick = frames[0].get("tick") if frames else round_data.get("start_tick") or indexed_rounds[selected_round].get("start_tick")
    last_tick = frames[-1].get("tick") if frames else round_data.get("end_tick") or indexed_rounds[selected_round].get("end_tick")
    try:
        selected_tick = int(payload.get("tick")) if payload.get("tick") is not None else int(first_tick or 0)
    except (TypeError, ValueError):
        selected_tick = int(first_tick or 0)
    if first_tick is not None:
        selected_tick = max(int(first_tick), selected_tick)
    if last_tick is not None:
        selected_tick = min(int(last_tick), selected_tick)
    now = utc_now_iso()
    return {"round_number": selected_round, "tick": selected_tick, "is_playing": False, "updated_at": now, "server_time_ms": server_time_ms()}


def compact_playback_payload(room: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    playback = dict(room.get("playback", {}))
    if "round_number" in payload:
        playback["round_number"] = payload.get("round_number")
    if "tick" in payload:
        playback["tick"] = payload.get("tick")
    if "is_playing" in payload:
        playback["is_playing"] = bool(payload.get("is_playing"))
    playback["updated_at"] = utc_now_iso()
    playback["server_time_ms"] = server_time_ms()
    return playback


def apply_room_message(room: dict[str, Any], client_id: str, message: dict[str, Any]) -> tuple[dict[str, Any] | None, bool, bool]:
    message_type = message.get("type")
    payload = message.get("payload") or {}
    participant = room_participants(room).get(client_id)
    if participant:
        participant["last_seen_at"] = utc_now_iso()
        room["last_activity_at"] = participant["last_seen_at"]

    if message_type == "heartbeat":
        return {"type": "heartbeat_ack", "server_time_ms": server_time_ms()}, False, False

    if message_type == "playback_control":
        room["mode"] = "replay"
        room["playback"] = compact_playback_payload(room, payload)
        increment_room_version(room)
        return {"type": "state_update", "patch_type": message_type, "version": room["version"], "payload": {"playback": room["playback"], "mode": room["mode"]}}, True, False

    if message_type == "switch_demo":
        demo_id = str(payload.get("demo_id") or "")
        if not demo_id:
            return None, False, False
        playback = default_playback_for_demo(demo_id, payload, project_paths())
        room["demo_id"] = demo_id
        room["title"] = payload.get("title") or f"{demo_id} R{playback['round_number']}"
        room["mode"] = "replay"
        room["playback"] = playback
        room["sandbox"] = {"active": False, "source_round_number": playback["round_number"], "source_tick": playback["tick"], "source_frame_index": 0, "currentTick": playback["tick"], "playing": False, "tokens": [], "annotations": [], "planned_utilities": []}
        increment_room_version(room)
        return {"type": "state_update", "patch_type": message_type, "version": room["version"], "payload": {"demo_id": demo_id, "title": room["title"], "mode": room["mode"], "playback": room["playback"], "sandbox": room["sandbox"]}}, True, False

    if message_type == "enter_sandbox":
        sandbox = dict(payload.get("sandbox") or payload)
        sandbox["active"] = True
        sandbox.setdefault("tokens", [])
        sandbox.setdefault("annotations", [])
        sandbox.setdefault("planned_utilities", [])
        sandbox.setdefault("currentTick", sandbox.get("source_tick"))
        sandbox.setdefault("playing", False)
        room["mode"] = "sandbox"
        room["sandbox"] = sandbox
        increment_room_version(room)
        return {"type": "state_update", "patch_type": message_type, "version": room["version"], "payload": {"mode": room["mode"], "sandbox": room["sandbox"]}}, True, False

    if message_type == "resume_replay":
        room["mode"] = "replay"
        sandbox = dict(room.get("sandbox", {}))
        sandbox["active"] = False
        room["sandbox"] = sandbox
        if payload:
            room["playback"] = compact_playback_payload(room, payload)
        increment_room_version(room)
        return {"type": "state_update", "patch_type": message_type, "version": room["version"], "payload": {"mode": room["mode"], "sandbox": room["sandbox"], "playback": room.get("playback")}}, True, False

    if message_type == "move_token":
        token_id = str(payload.get("token_id") or payload.get("steamid") or payload.get("id") or "")
        sandbox = room.setdefault("sandbox", {})
        token_rows = sandbox.get("tokens") or sandbox.get("objects") or []
        for token in token_rows:
            if str(token.get("steamid") or token.get("id") or token.get("name")) == token_id:
                if "radar_x" in payload:
                    token["radar_x"] = payload.get("radar_x")
                if "radar_y" in payload:
                    token["radar_y"] = payload.get("radar_y")
                break
        sandbox["currentTick"] = payload.get("currentTick", sandbox.get("currentTick"))
        increment_room_version(room)
        return {"type": "state_update", "patch_type": message_type, "version": room["version"], "payload": payload}, False, True

    if message_type == "create_object":
        obj = payload.get("object") or payload
        obj.setdefault("id", uuid.uuid4().hex[:12])
        room.setdefault("sandbox", {}).setdefault("annotations", []).append(obj)
        increment_room_version(room)
        return {"type": "state_update", "patch_type": message_type, "version": room["version"], "payload": {"object": obj}}, True, False

    if message_type == "delete_object":
        object_id = str(payload.get("object_id") or payload.get("id") or "")
        sandbox = room.setdefault("sandbox", {})
        sandbox["annotations"] = [annotation for annotation in sandbox.get("annotations", []) if str(annotation.get("id") or annotation.get("annotation_id") or "") != object_id]
        increment_room_version(room)
        return {"type": "state_update", "patch_type": message_type, "version": room["version"], "payload": {"object_id": object_id}}, True, False

    if message_type == "create_utility":
        utility = payload.get("utility") or payload
        sandbox = room.setdefault("sandbox", {})
        sandbox.setdefault("planned_utilities", []).append(utility)
        sandbox["nextUtilityThrowTick"] = payload.get("nextUtilityThrowTick", utility.get("detonate_tick", sandbox.get("nextUtilityThrowTick") or sandbox.get("source_tick")))
        increment_room_version(room)
        return {"type": "state_update", "patch_type": message_type, "version": room["version"], "payload": {"utility": utility, "currentTick": sandbox.get("currentTick"), "nextUtilityThrowTick": sandbox.get("nextUtilityThrowTick")}}, True, False

    if message_type == "clear_utilities":
        sandbox = room.setdefault("sandbox", {})
        sandbox["planned_utilities"] = []
        sandbox["nextUtilityThrowTick"] = sandbox.get("source_tick", sandbox.get("currentTick"))
        increment_room_version(room)
        return {"type": "state_update", "patch_type": message_type, "version": room["version"], "payload": {"nextUtilityThrowTick": sandbox.get("nextUtilityThrowTick")}}, True, False

    if message_type == "reset_sandbox_to_source":
        sandbox = room.setdefault("sandbox", {})
        sandbox["tokens"] = payload.get("tokens", sandbox.get("tokens", []))
        sandbox["currentTick"] = payload.get("currentTick", sandbox.get("source_tick"))
        sandbox["playing"] = False
        increment_room_version(room)
        return {"type": "state_update", "patch_type": message_type, "version": room["version"], "payload": {"sandbox": sandbox}}, True, False

    if message_type == "sandbox_time_control":
        sandbox = room.setdefault("sandbox", {})
        if "currentTick" in payload:
            sandbox["currentTick"] = payload.get("currentTick")
        if "playing" in payload:
            sandbox["playing"] = bool(payload.get("playing"))
        sandbox["server_time_ms"] = server_time_ms()
        increment_room_version(room)
        return {"type": "state_update", "patch_type": message_type, "version": room["version"], "payload": {"currentTick": sandbox.get("currentTick"), "playing": sandbox.get("playing"), "server_time_ms": sandbox.get("server_time_ms")}}, True, False

    if message_type == "cursor":
        return {"type": "cursor", "client_id": client_id, "payload": payload}, False, False

    return None, False, False


def share_status_payload(app: FastAPI) -> dict[str, Any]:
    settings: ServerSettings = app.state.share_settings
    public_base_url = str(getattr(app.state, "public_base_url", "") or "")
    public_ready = bool(public_base_url)
    local_base_url = f"http://{local_share_host(settings.host)}:{settings.port}"
    tunnel_status = dict(getattr(app.state, "tunnel_status", {}) or {})
    share_mode = str(getattr(app.state, "share_mode", settings.share_mode) or "local") if public_ready else "local"
    message = "公网分享已启用。" if public_ready else LOCAL_ONLY_WARNING
    return {
        "public_ready": public_ready,
        "public_base_url": public_base_url,
        "share_mode": share_mode,
        "local_base_url": local_base_url,
        "message": message,
        "warning": None if public_ready else LOCAL_ONLY_WARNING,
        "tunnel": tunnel_status,
    }


def build_room_share_payload(app: FastAPI, room_code: str) -> dict[str, Any]:
    code = normalize_room_code(room_code)
    status = share_status_payload(app)
    base_url = status["public_base_url"] if status["public_ready"] else status["local_base_url"]
    room_path = f"/r/{quote(code, safe='')}"
    share_url = f"{base_url}{room_path}"
    payload = {
        "room_code": code,
        "share_url": share_url,
        "join_url": share_url,
        "public_ready": status["public_ready"],
        "share_mode": status["share_mode"],
    }
    if not status["public_ready"]:
        payload["warning"] = LOCAL_ONLY_WARNING
    return payload


def create_app(settings: ServerSettings | None = None) -> FastAPI:
    paths = project_paths()
    settings = settings or load_server_settings(paths)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.public_base_url = settings.public_base_url
        app.state.share_mode = settings.share_mode if settings.public_base_url else "local"
        app.state.tunnel_status = {
            "provider": settings.tunnel_provider or None,
            "running": False,
            "error": None,
        }
        app.state.tunnel_manager = None
        if settings.tunnel_provider and not settings.public_base_url:
            manager = TunnelManager(settings.tunnel_provider, settings.tunnel_command, f"http://127.0.0.1:{settings.port}")
            app.state.tunnel_manager = manager
            app.state.tunnel_status = {"provider": settings.tunnel_provider, "running": False, "error": None}
            try:
                public_url = await manager.start()
                app.state.public_base_url = public_url
                app.state.share_mode = settings.tunnel_provider
                app.state.tunnel_status = {"provider": settings.tunnel_provider, "running": True, "error": None, "public_base_url": public_url}
                LOGGER.info("Public share URL: %s", public_url)
            except Exception as exc:
                app.state.public_base_url = ""
                app.state.share_mode = "local"
                app.state.tunnel_status = {"provider": settings.tunnel_provider, "running": False, "error": str(exc)}
                LOGGER.warning("Cloudflared tunnel unavailable: %s", exc)
        try:
            yield
        finally:
            manager = getattr(app.state, "tunnel_manager", None)
            if manager is not None:
                await manager.stop()

    app = FastAPI(title="CS2 Dust2 Replay", version="0.4.0", lifespan=lifespan)
    app.state.share_settings = settings
    app.state.public_base_url = settings.public_base_url
    app.state.share_mode = settings.share_mode if settings.public_base_url else "local"
    app.state.tunnel_status = {"provider": settings.tunnel_provider or None, "running": False, "error": None}
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.mount("/assets", StaticFiles(directory=paths.assets_dir), name="assets")
    app.mount("/static", StaticFiles(directory=paths.web_dir), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(paths.web_dir / "index.html")

    @app.get("/r/{room_code}")
    def room_entry(room_code: str) -> FileResponse:
        try:
            normalize_room_code(room_code)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return FileResponse(paths.web_dir / "index.html")

    @app.get("/api/share/status")
    def api_share_status() -> dict[str, Any]:
        return share_status_payload(app)

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

    @app.get("/api/rooms")
    def api_rooms() -> dict[str, Any]:
        purge_expired_rooms(paths, ROOM_IDLE_TTL_SEC)
        status = share_status_payload(app)
        if status["public_ready"]:
            return {"rooms": [], "public_listing_disabled": True}
        return {"rooms": list_room_states(paths, idle_ttl_sec=ROOM_IDLE_TTL_SEC), "public_listing_disabled": False}

    @app.post("/api/rooms")
    def api_create_room(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        try:
            demo_id = payload.get("demo_id")
            if not demo_id:
                raise KeyError("demo_id is required")
            room = create_room_state(
                demo_id,
                round_number=payload.get("round_number"),
                tick=payload.get("tick"),
                title=payload.get("title"),
                paths=paths,
            )
            ROOMS[room["room_code"]] = room
            share_payload = build_room_share_payload(app, room["room_code"])
            return {"ok": True, "created": True, "room": room_public_state(room), **share_payload}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/rooms/{room_code}")
    def api_room(room_code: str) -> dict[str, Any]:
        try:
            room = ensure_room_loaded(room_code, paths)
            if prune_room_presence(room):
                save_room_state(room, paths)
            share_payload = build_room_share_payload(app, room["room_code"])
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"room": room_public_state(room), **share_payload}

    @app.post("/api/rooms/{room_code}/save")
    def api_save_room(room_code: str) -> dict[str, Any]:
        try:
            room = ensure_room_loaded(room_code, paths)
            prune_room_presence(room)
            saved = save_room_state(room, paths)
            ROOMS[saved["room_code"]] = saved
            share_payload = build_room_share_payload(app, saved["room_code"])
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"saved": True, "room": room_public_state(saved), **share_payload}

    @app.post("/api/rooms/{room_code}/snapshot")
    def api_room_snapshot(room_code: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        try:
            room = ensure_room_loaded(room_code, paths)
            prune_room_presence(room)
            if "demo_id" in payload:
                demo_id = str(payload.get("demo_id") or "")
                if not demo_id:
                    raise KeyError("demo_id is required")
                room["demo_id"] = demo_id
                room["playback"] = default_playback_for_demo(demo_id, payload.get("playback") or payload, paths)
                room["mode"] = "replay"
                room["sandbox"] = {"active": False, "source_round_number": room["playback"]["round_number"], "source_tick": room["playback"]["tick"], "source_frame_index": 0, "currentTick": room["playback"]["tick"], "playing": False, "tokens": [], "annotations": [], "planned_utilities": []}
            if "playback" in payload and "demo_id" not in payload:
                room["playback"] = payload["playback"]
            if "sandbox" in payload:
                room["sandbox"] = payload["sandbox"]
            if "mode" in payload:
                room["mode"] = payload["mode"]
            increment_room_version(room)
            saved = save_room_state(room, paths)
            ROOMS[saved["room_code"]] = saved
            share_payload = build_room_share_payload(app, saved["room_code"])
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"saved": True, "room": room_public_state(saved), **share_payload}

    @app.websocket("/ws/rooms/{room_code}")
    async def ws_room(websocket: WebSocket, room_code: str) -> None:
        try:
            room = ensure_room_loaded(room_code, paths)
        except KeyError:
            await websocket.close(code=4404)
            return

        code = normalize_room_code(str(room.get("room_code") or room_code))
        prune_room_presence(room)
        await websocket.accept()
        client_id = ""
        connection_id = uuid.uuid4().hex
        try:
            join_message = await websocket.receive_json()
            if join_message.get("type") != "join_room":
                await websocket.close(code=4400)
                return
            profile = join_message.get("payload") or {}
            existing_client_id = find_existing_participant(room, profile)
            current_online = online_participant_count(room)
            max_participants = int(room.get("settings", {}).get("max_participants", 5))
            if current_online >= max_participants and not (existing_client_id and room_participants(room).get(existing_client_id, {}).get("online")):
                await websocket.close(code=4409)
                return
            client_id = register_participant(room, profile, connection_id)
            connections = ROOM_CONNECTIONS.setdefault(code, {})
            connection_ids = ROOM_CONNECTION_IDS.setdefault(code, {})
            old_socket = connections.get(client_id)
            if old_socket and old_socket is not websocket:
                connection_ids.pop(client_id, None)
                connections.pop(client_id, None)
                await old_socket.close(code=4410)
            connections[client_id] = websocket
            connection_ids[client_id] = connection_id
            increment_room_version(room)
            save_room_state(room, paths)
            participants = room_participants(room)
            await websocket.send_json({"type": "room_snapshot", "client_id": client_id, "room": room_public_state(room), "server_time_ms": server_time_ms()})
            await broadcast_room(code, {"type": "participant_update", "version": room["version"], "participants": participants}, exclude_client_id=client_id)

            while True:
                message = await websocket.receive_json()
                outbound, immediate_save, debounce_save = apply_room_message(room, client_id, message)
                if outbound:
                    outbound.setdefault("server_time_ms", server_time_ms())
                    outbound.setdefault("client_id", client_id)
                    if outbound.get("type") == "heartbeat_ack":
                        await websocket.send_json(outbound)
                    else:
                        await broadcast_room(code, outbound, exclude_client_id=client_id)
                        if outbound.get("type") != "cursor":
                            await websocket.send_json(outbound)
                if immediate_save:
                    save_room_state(room, paths)
                elif debounce_save:
                    save_room_debounced(code, paths)
        except WebSocketDisconnect:
            pass
        finally:
            if client_id:
                if ROOM_CONNECTION_IDS.get(code, {}).get(client_id) == connection_id:
                    ROOM_CONNECTIONS.get(code, {}).pop(client_id, None)
                    ROOM_CONNECTION_IDS.get(code, {}).pop(client_id, None)
                if mark_participant_offline(room, client_id, connection_id):
                    save_room_state(room, paths)
                    await broadcast_room(code, {"type": "participant_update", "version": room["version"], "participants": room_participants(room)})

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the CS2 Dust2 replay web app.")
    parser.add_argument("--host", default=None, help="Bind host, default from config/env or 127.0.0.1.")
    parser.add_argument("--port", type=int, default=None, help="Bind port, default from config/env or 8000.")
    parser.add_argument("--public-url", default=None, help="Public base URL used for room share links.")
    parser.add_argument("--tunnel", choices=["cloudflared"], default=None, help="Start a public quick tunnel provider.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    paths = project_paths()
    settings = load_server_settings(paths, parse_args())
    LOGGER.info("Serving CS2 replay on http://%s:%s", settings.host, settings.port)
    if settings.public_base_url:
        LOGGER.info("Public share URL: %s", settings.public_base_url)
    elif settings.tunnel_provider:
        LOGGER.info("Starting %s tunnel for public share links", settings.tunnel_provider)
    else:
        LOGGER.info(LOCAL_ONLY_WARNING)
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
