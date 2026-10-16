import unittest
from unittest.mock import patch
from src.game_logic import reset_game_state, update_game_state, _place_item
from src.game_state import GameSettings
from src.snake import Snake
from src.food import Food
from src.poop import Poop
from src import config

class TestGameLogic(unittest.TestCase):
    """Tests for the main game_logic module."""

    def setUp(self):
        """Set up common variables for tests."""
        self.settings = GameSettings()

    def test_reset_game_state(self):
        """Test that the game state is reset correctly."""
        game_data = reset_game_state(self.settings)
        
        self.assertIsInstance(game_data['snake'], Snake)
        self.assertEqual(game_data['snake'].get_head_position(), (10, 10))
        self.assertIn('food', game_data)
        self.assertIn('poops', game_data)
        self.assertEqual(game_data['poops'], [])
        self.assertEqual(game_data['score'], 0)
        self.assertEqual(game_data['shit_counter'], 0)
        self.assertFalse(game_data['game_over'])

    @patch('src.game_logic.random.randint')
    def test_place_item(self, mock_randint):
        """Test that _place_item places an item in an empty spot."""
        mock_randint.side_effect = [5, 5, 6, 6] # First attempt (5,5) is occupied
        
        occupied = [(5, 5)]
        pos = _place_item(occupied)
        
        self.assertEqual(pos, (6, 6))
        self.assertNotIn(pos, occupied)

    def test_update_game_state_move(self):
        """Test basic snake movement."""
        game_data = reset_game_state(self.settings)
        initial_pos = game_data['snake'].get_head_position()
        
        game_data = update_game_state(game_data, self.settings)
        
        new_pos = game_data['snake'].get_head_position()
        self.assertEqual(new_pos, (initial_pos[0] + 1, initial_pos[1]))
        self.assertFalse(game_data['game_over'])

    def test_update_game_state_eat_food(self):
        """Test what happens when the snake eats food."""
        game_data = reset_game_state(self.settings)
        snake = game_data['snake']
        
        # Place food right in front of the snake
        food_pos = (snake.get_head_position()[0] + 1, snake.get_head_position()[1])
        game_data['food'] = Food(food_pos)
        initial_length = snake.length
        initial_score = game_data['score']

        game_data = update_game_state(game_data, self.settings)
        
        self.assertEqual(snake.length, initial_length + 1)
        self.assertEqual(game_data['score'], initial_score + 1)
        # A new food should be placed somewhere else
        self.assertNotEqual(game_data['food'].position, food_pos)

    @patch('src.game_logic.GRID_HEIGHT', 20)
    @patch('src.game_logic.GRID_WIDTH', 20)
    def test_update_game_state_hit_wall(self):
        """Test collision with a wall."""
        game_data = reset_game_state(self.settings)
        snake = game_data['snake']
        
        # Position snake at the right edge, moving right
        snake.positions = [(19, 10)]
        snake.direction = config.RIGHT
        
        game_data = update_game_state(game_data, self.settings)
        
        self.assertTrue(game_data['game_over'])

    @patch('src.game_logic.GRID_HEIGHT', 20)
    @patch('src.game_logic.GRID_WIDTH', 20)
    def test_update_game_state_hit_self(self):
        """Test collision with self."""
        game_data = reset_game_state(self.settings)
        snake = game_data['snake']
        
        # Create a snake that will hit itself
        snake.positions = [(10, 11), (10, 10), (11, 10), (11, 11)]
        snake.length = 4
        snake.direction = config.RIGHT

        game_data = update_game_state(game_data, self.settings)
        self.assertTrue(game_data['game_over'])

    def test_wonq_mode_poop_generation(self):
        """Test poop generation in WonQ mode."""
        self.settings.wonq_mode = True
        game_data = reset_game_state(self.settings)
        game_data['shit_counter'] = config.WONQ_MODE_POOP_THRESHOLD - 1
        
        # Place food to be eaten
        food_pos = (game_data['snake'].get_head_position()[0] + 1, game_data['snake'].get_head_position()[1])
        game_data['food'] = Food(food_pos)

        game_data = update_game_state(game_data, self.settings)
        
        self.assertEqual(len(game_data['poops']), 1)
        self.assertEqual(game_data['shit_counter'], 0)

    def test_wonq_mode_hit_poop(self):
        """Test collision with poop in WonQ mode."""
        self.settings.wonq_mode = True
        game_data = reset_game_state(self.settings)
        snake = game_data['snake']
        
        # Place poop in front of the snake
        poop_pos = (snake.get_head_position()[0] + 1, snake.get_head_position()[1])
        game_data['poops'].append(Poop(poop_pos))
        
        game_data = update_game_state(game_data, self.settings)
        
        self.assertTrue(game_data['game_over'])

if __name__ == '__main__':
    unittest.main()