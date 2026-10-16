import unittest
import pygame
import sys
import os
from collections import namedtuple

# Add project root to path to allow imports from snake_game
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from snake_game.rendering import adapt_game_state_for_rendering
from snake_game.core import GameState, Direction
from snake_game.config import SCREEN_WIDTH, SCREEN_HEIGHT, BLOCK_SIZE

# The Point named tuple is defined in core.py, but we redefine it here
# to avoid issues if core.py is not fully implemented yet.
Point = namedtuple('Point', 'x y')

class TestRenderingAdapter(unittest.TestCase):

    def setUp(self):
        """Initialize pygame and set up a dummy game state."""
        pygame.init()
        # Create a GameState instance for testing
        self.game_state = GameState(width=SCREEN_WIDTH, height=SCREEN_HEIGHT, block_size=BLOCK_SIZE)

        # Manually set the state for predictable testing
        # The snake's head is at (40, 40)
        self.game_state.snake.body = [Point(40, 40), Point(20, 40), Point(0, 40)]
        self.game_state.snake.direction = Direction.RIGHT
        self.game_state.food.position = Point(100, 100)
        self.game_state.score = 5

    def test_adapter_conversion(self):
        """
        Test that the adapter correctly converts a GameState object 
        to a dictionary suitable for rendering.
        """
        rendering_dict = adapt_game_state_for_rendering(self.game_state)

        # Check that all required keys are present
        self.assertIn('snake_body', rendering_dict)
        self.assertIn('food_pos', rendering_dict)
        self.assertIn('score', rendering_dict)

        # Check the score value
        self.assertEqual(rendering_dict['score'], 5)

        # Check the food position and type
        expected_food_rect = pygame.Rect(100, 100, BLOCK_SIZE, BLOCK_SIZE)
        self.assertIsInstance(rendering_dict['food_pos'], pygame.Rect)
        self.assertEqual(rendering_dict['food_pos'], expected_food_rect)

        # Check the snake body contents and types
        expected_snake_rects = [
            pygame.Rect(40, 40, BLOCK_SIZE, BLOCK_SIZE),
            pygame.Rect(20, 40, BLOCK_SIZE, BLOCK_SIZE),
            pygame.Rect(0, 40, BLOCK_SIZE, BLOCK_SIZE)
        ]
        self.assertIsInstance(rendering_dict['snake_body'], list)
        self.assertEqual(len(rendering_dict['snake_body']), 3)
        
        # Ensure each element is a Rect and matches the expected value
        for i, rect in enumerate(rendering_dict['snake_body']):
            self.assertIsInstance(rect, pygame.Rect)
            self.assertEqual(rect, expected_snake_rects[i])

    def tearDown(self):
        """Quit pygame after tests."""
        pygame.quit()

if __name__ == '__main__':
    unittest.main()