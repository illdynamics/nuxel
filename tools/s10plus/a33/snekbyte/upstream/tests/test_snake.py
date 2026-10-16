import unittest
from unittest.mock import MagicMock
from src.snake import Snake
from src import config

class TestSnake(unittest.TestCase):
    """Tests for the Snake class."""

    def setUp(self):
        """Set up a new Snake object for each test."""
        self.snake = Snake()
        # Reset config to defaults for consistent tests
        config.GRID_WIDTH = 20
        config.GRID_HEIGHT = 20
        config.UP = (0, -1)
        config.DOWN = (0, 1)
        config.LEFT = (-1, 0)
        config.RIGHT = (1, 0)

    def test_initialization(self):
        """Test snake's initial state."""
        self.assertEqual(len(self.snake.positions), 1)
        self.assertEqual(self.snake.get_head_position(), (10, 10))
        self.assertEqual(self.snake.direction, config.RIGHT)
        self.assertEqual(self.snake.length, 1)
        self.assertFalse(self.snake.is_dead)

    def test_get_head_position(self):
        """Test the get_head_position method."""
        self.assertEqual(self.snake.get_head_position(), (10, 10))
        self.snake.move()
        self.assertEqual(self.snake.get_head_position(), (11, 10))

    def test_turn_valid(self):
        """Test turning in valid, non-opposite directions."""
        self.snake.turn(config.UP)
        self.assertEqual(self.snake.direction, config.UP)
        self.snake.turn(config.LEFT)
        self.assertEqual(self.snake.direction, config.LEFT)
        self.snake.turn(config.DOWN)
        self.assertEqual(self.snake.direction, config.DOWN)

    def test_turn_invalid_opposite_direction(self):
        """Test that the snake cannot turn 180 degrees."""
        initial_direction = self.snake.direction
        self.snake.turn(config.LEFT)  # Opposite of initial RIGHT
        self.assertEqual(self.snake.direction, initial_direction)

        self.snake.direction = config.UP
        self.snake.turn(config.DOWN)
        self.assertEqual(self.snake.direction, config.UP)
        
    def test_move(self):
        """Test the snake's movement."""
        initial_pos = self.snake.get_head_position()
        self.snake.move()
        new_pos = self.snake.get_head_position()
        self.assertEqual(new_pos, (initial_pos[0] + 1, initial_pos[1]))
        self.assertEqual(len(self.snake.positions), 1)

    def test_move_and_grow(self):
        """Test that the snake grows when its length is increased."""
        self.snake.length = 3
        self.snake.move()
        self.snake.move()
        self.assertEqual(len(self.snake.positions), 3)
        self.assertEqual(self.snake.positions, [(12, 10), (11, 10), (10, 10)])

    def test_reset(self):
        """Test resetting the snake to its initial state."""
        self.snake.length = 5
        self.snake.move()
        self.snake.turn(config.UP)
        self.snake.is_dead = True
        
        self.snake.reset()
        
        self.assertEqual(self.snake.length, 1)
        self.assertEqual(len(self.snake.positions), 1)
        self.assertEqual(self.snake.get_head_position(), (10, 10))
        self.assertEqual(self.snake.direction, config.RIGHT)
        self.assertFalse(self.snake.is_dead)

    def test_draw(self):
        """Test that the draw method calls the correct draw functions."""
        mock_surface = MagicMock()
        mock_surface.blit = MagicMock()
        
        self.snake.length = 3
        self.snake.move()
        self.snake.move()
        
        self.snake.draw(mock_surface)
        
        # Should be called once for each segment
        self.assertEqual(mock_surface.blit.call_count, len(self.snake.positions))

if __name__ == '__main__':
    unittest.main()