"""Neon Arcade Space Defender — Entry Point."""

from game.engine import NeonArcadeApp


def main() -> None:
    app = NeonArcadeApp()
    app.run()


if __name__ == "__main__":
    main()
