import sys
import pygame
from src.game_loop import run_game


def main():
    """Initializes Pygame and runs the game."""
    # The run_game function is expected to handle all aspects of the game loop,
    # including pygame initialization and shutdown.
    try:
        run_game()
    except Exception as e:
        # Basic error handling for this secondary entry point
        print(f"SnekByte encountered a fatal error: {e}", file=sys.stderr)
        pygame.quit()
        sys.exit(1)