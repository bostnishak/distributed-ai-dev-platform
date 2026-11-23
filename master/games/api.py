"""FastAPI router for Game Studio (`master/games/`): GAME-01..GAME-10 (SEC-22 Compliant)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import config
from access_control import require_local_or_admin
from games.studio import (
    GAME_GENRE_TEMPLATES,
    build_game_bundle,
    package_game,
    run_automated_bot_playtest,
    validate_level_solvability,
)

router = APIRouter(prefix="/api/games", tags=["games"])
_LOCAL_OR_ADMIN = [Depends(require_local_or_admin)]


class GameBuildReq(BaseModel):
    prompt: str = Field(..., min_length=2)
    genre: str = "snake_classic"
    package_target: str | None = None


class LevelCheckReq(BaseModel):
    grid: list[str]


@router.get("/genres")
async def api_list_genres():
    return {
        "count": len(GAME_GENRE_TEMPLATES),
        "genres": [{"id": k, "title": v["title"], "controls": v["controls"]} for k, v in GAME_GENRE_TEMPLATES.items()],
    }


@router.post("/build", dependencies=_LOCAL_OR_ADMIN)
async def api_build_game(body: GameBuildReq):
    try:
        bundle = build_game_bundle(body.prompt, genre=body.genre)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    playtest = run_automated_bot_playtest(bundle)
    pkg = None
    if body.package_target:
        pkg = package_game(bundle, output_dir=Path(config.DATA_DIR) / "games_out", target=body.package_target)
    return {
        "artifact_id": bundle["artifact_id"],
        "genre": bundle["genre"],
        "gdd": bundle["gdd"],
        "playtest": playtest,
        "package": pkg,
    }


@router.post("/level/validate", dependencies=_LOCAL_OR_ADMIN)
async def api_validate_level(body: LevelCheckReq):
    return validate_level_solvability(body.grid)
