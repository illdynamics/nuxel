import pygame

# Screen dimensions
GRID_WIDTH = 20
GRID_HEIGHT = 20
GRID_SIZE = 30
SCREEN_WIDTH = GRID_WIDTH * GRID_SIZE
SCREEN_HEIGHT = GRID_HEIGHT * GRID_SIZE

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (213, 50, 80)
GREEN = (0, 255, 0)
BLUE = (50, 153, 213)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (40, 40, 40)

BACKGROUND_COLOR = BLACK
SNAKE_COLOR = GREEN
FOOD_COLOR = RED
POOP_COLOR = (139, 69, 19)  # SaddleBrown
GRID_COLOR = DARK_GRAY
TEXT_COLOR = WHITE
SELECTED_COLOR = GREEN
DISABLED_COLOR = GRAY

# Game settings
DEFAULT_SPEED_INDEX = 1  # Corresponds to "Normal" speed (15 FPS)
SPEED_LEVELS = [("Slow", 10), ("Normal", 15), ("Fast", 25), ("Insane", 40)]
DEFAULT_WONQ_MODE = False
WONQ_MODE_POOP_THRESHOLD = 5  # Score needed to drop a poop

# Directions (Vectors)
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# Initial Snake State
INITIAL_SNAKE_LENGTH = 3
# Note: Position is just the head, the body is generated from it
INITIAL_SNAKE_POSITION = (GRID_WIDTH // 2, GRID_HEIGHT // 2)
INITIAL_SNAKE_DIRECTION = RIGHT