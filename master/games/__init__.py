"""Game Studio Package (`master/games/`): GAME-01..GAME-10."""

from games.api import router
from games.studio import (
    CANVAS2D_ENGINE_JS,
    GAME_GENRE_TEMPLATES,
    SIMPLE_3D_TEMPLATE_HTML,
    build_game_bundle,
    generate_gdd,
    generate_procedural_assets,
    package_game,
    run_automated_bot_playtest,
    run_game_eval,
    validate_level_solvability,
)

__all__ = [
    "CANVAS2D_ENGINE_JS",
    "GAME_GENRE_TEMPLATES",
    "SIMPLE_3D_TEMPLATE_HTML",
    "build_game_bundle",
    "generate_gdd",
    "generate_procedural_assets",
    "package_game",
    "router",
    "run_automated_bot_playtest",
    "run_game_eval",
    "validate_level_solvability",
]
