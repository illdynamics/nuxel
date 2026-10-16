import pygame
from src import config


class Food:
    """
    Represents the food item in the game.

    This class manages the position and rendering of the food that the snake
    eats. The food's position is randomized by the game logic, and this class
    is responsible for drawing it on the screen.
    """

    def __init__(self, position: tuple[int, int]):
        """
        Initializes the food object at a given position.

        Args:
            position: The (x, y) grid coordinates for the food.
        """
        self.position = position
        self.color = config.FOOD_COLOR

    def draw(self, surface: pygame.Surface):
        """
        Draws the food item on the given Pygame surface.

        The food is represented as a colored square that fits within a
        single grid cell.

        Args:
            surface: The pygame.Surface to draw the food on.
        """
        r = pygame.Rect(
            (self.position[0] * config.GRID_SIZE, self.position[1] * config.GRID_SIZE),
            (config.GRID_SIZE, config.GRID_SIZE),
        )
        pygame.draw.rect(surface, self.color, r)
        pygame.draw.rect(surface, config.GRID_COLOR, r, 1)