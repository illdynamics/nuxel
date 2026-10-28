"""Test-only compatibility types for the vendored upstream tests.

Only the shapes the tests import/construct are provided; the real rules live in
`src.*` and are exercised by test_game_logic.py/test_snake.py.
"""
from enum import Enum


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


class _SnakeBody(object):
    def __init__(self):
        self.body = []
        self.direction = None


class _Food(object):
    def __init__(self):
        self.position = None


class GameState(object):
    def __init__(self, width=800, height=600, block_size=20):
        self.width = width
        self.height = height
        self.block_size = block_size
        self.snake = _SnakeBody()
        self.food = _Food()
        self.score = 0


class Snake(object):
    """The `change_direction` contract the input test mocks."""
    def __init__(self):
        self.direction = None

    def change_direction(self, direction):
        self.direction = direction


Food = _Food
