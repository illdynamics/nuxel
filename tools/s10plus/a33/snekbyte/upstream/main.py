import sys
import pygame
from src.game_loop import run_game

def main():
    """Initializes Pygame and runs the game."""
    run_game()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()