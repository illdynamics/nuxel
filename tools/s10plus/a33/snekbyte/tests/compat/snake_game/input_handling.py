"""Test-only input adapter matching the vendored upstream test contract."""
import pygame

from .core import Direction


def handle_input(snake):
    """Return True when the game should quit; otherwise update the snake."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
        if event.type != pygame.KEYDOWN:
            continue
        if event.key == pygame.K_ESCAPE:
            return True
        mapping = {
            pygame.K_UP: Direction.UP,
            pygame.K_DOWN: Direction.DOWN,
            pygame.K_LEFT: Direction.LEFT,
            pygame.K_RIGHT: Direction.RIGHT,
        }
        if event.key in mapping:
            snake.change_direction(mapping[event.key])
    return False
