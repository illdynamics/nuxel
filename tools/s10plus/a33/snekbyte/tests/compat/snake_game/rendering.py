"""Test-only rendering adapter matching the vendored upstream test contract."""
import pygame

from .config import BLOCK_SIZE


def adapt_game_state_for_rendering(game_state):
    return {
        "snake_body": [pygame.Rect(p.x, p.y, BLOCK_SIZE, BLOCK_SIZE)
                       for p in game_state.snake.body],
        "food_pos": pygame.Rect(game_state.food.position.x, game_state.food.position.y,
                                BLOCK_SIZE, BLOCK_SIZE),
        "score": game_state.score,
    }
