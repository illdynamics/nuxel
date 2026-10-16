import pygame
from typing import List, Tuple
from src import config

class Snake:
    """
    Represents the snake entity in the game.

    This class manages the snake's position, movement, growth, and rendering.
    It keeps track of the segments of the snake's body and its current direction.
    """
    def __init__(self) -> None:
        """
        Initializes the snake with a default starting position, length, and direction.
        The snake starts in the center of the screen, moving to the right.
        """
        self.reset()

    def get_head_position(self) -> Tuple[int, int]:
        """
        Returns the current grid coordinates of the snake's head.

        Returns:
            A tuple (x, y) representing the position of the head segment.
        """
        return self.positions[0]

    def turn(self, point: Tuple[int, int]) -> None:
        """
        Changes the snake's direction, preventing it from immediately reversing.

        For example, if the snake is moving right (1, 0), it cannot turn
        left (-1, 0).

        Args:
            point: A tuple (dx, dy) representing the new direction vector.
                   Example: (0, -1) for UP.
        """
        if self.length > 1 and (point[0] * -1, point[1] * -1) == self.direction:
            return
        else:
            self.direction = point

    def move(self) -> None:
        """
        Moves the snake one step forward in its current direction.

        It calculates the new head position and updates the list of body segments.
        If the snake has not grown, the last segment is removed.
        """
        cur = self.get_head_position()
        x, y = self.direction
        new_head = (cur[0] + x, cur[1] + y)

        self.positions.insert(0, new_head)
        if len(self.positions) > self.length:
            self.positions.pop()

    def reset(self) -> None:
        """
        Resets the snake to its initial state.

        This is used when starting a new game. It restores the snake to its
        default length, position, and direction.
        """
        self.length = 1
        self.positions = [(config.GRID_WIDTH // 2, config.GRID_HEIGHT // 2)]
        self.direction = config.RIGHT
        self.score = 0

    def draw(self, surface: pygame.Surface) -> None:
        """
        Draws all segments of the snake on the given Pygame surface.

        Args:
            surface: The pygame.Surface to draw the snake on.
        """
        for p in self.positions:
            r = pygame.Rect((p[0] * config.GRID_SIZE, p[1] * config.GRID_SIZE), (config.GRID_SIZE, config.GRID_SIZE))
            pygame.draw.rect(surface, config.GREEN, r)
            pygame.draw.rect(surface, config.GRAY, r, 1)

    def handle_keys(self) -> None:
        """
        DEPRECATED: Handles user input for snake movement. Logic moved to event_handler.py.
        
        This method is no longer used and is kept for historical context.
        Event handling is now managed in the event_handler.py module and applied 
        in the main game loop, which provides a better separation of concerns.
        """
        pass