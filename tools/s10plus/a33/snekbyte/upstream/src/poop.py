import pygame
from src import config

class Poop:
    """
    Represents a persistent poop obstacle in WoNQ mode.
    """
    def __init__(self, position):
        """
        Initializes the poop at a given grid position.

        Args:
            position: A tuple (x, y) for the grid position.
        """
        self.position = position
        self.color = config.BROWN

    def draw(self, surface: pygame.Surface):
        """
        Draws the poop block on the screen.

        Args:
            surface: The pygame.Surface to draw on.
        """
        r = pygame.Rect(
            (self.position[0] * config.GRID_SIZE, self.position[1] * config.GRID_SIZE),
            (config.GRID_SIZE, config.GRID_SIZE)
        )
        pygame.draw.rect(surface, self.color, r)