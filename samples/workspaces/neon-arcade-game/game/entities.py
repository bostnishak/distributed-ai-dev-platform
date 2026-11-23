"""Player, Bullet, and Enemy data structures."""

from dataclasses import dataclass


@dataclass
class Player:
    x: float
    y: float
    width: int = 44
    height: int = 20
    speed: float = 8.0
    lives: int = 3


@dataclass
class Bullet:
    x: float
    y: float
    speed: float = 11.0


@dataclass
class Enemy:
    x: float
    y: float
    size: int = 26
    speed: float = 2.4
