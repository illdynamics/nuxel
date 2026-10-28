import unittest
from unittest.mock import patch, Mock
import pygame
import sys
import os
from copy import deepcopy

# Add project root to path to allow imports from snake_game
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from snake_game.input_handling import handle_input
from snake_game.core import Direction, Snake

class TestInputHandling(unittest.TestCase):

    def setUp(self):
        """Set up a mock snake object for tests."""
        # The handle_input function is expected to call snake.change_direction
        self.mock_snake = Mock(spec=Snake)

    @patch('pygame.event.get')
    def test_quit_event(self, mock_event_get):
        """Test that the game quits on a QUIT event."""
        mock_event_get.return_value = [pygame.event.Event(pygame.QUIT)]
        quit_game = handle_input(self.mock_snake)
        self.assertTrue(quit_game)
        self.mock_snake.change_direction.assert_not_called()

    @patch('pygame.event.get')
    def test_escape_key(self, mock_event_get):
        """Test that the game quits on an ESCAPE key press."""
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        mock_event_get.return_value = [event]
        quit_game = handle_input(self.mock_snake)
        self.assertTrue(quit_game)
        self.mock_snake.change_direction.assert_not_called()

    @patch('pygame.event.get')
    def test_direction_change_up(self, mock_event_get):
        """Test changing direction to UP."""
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)
        mock_event_get.return_value = [event]
        quit_game = handle_input(self.mock_snake)
        self.assertFalse(quit_game)
        self.mock_snake.change_direction.assert_called_once_with(Direction.UP)

    @patch('pygame.event.get')
    def test_direction_change_down(self, mock_event_get):
        """Test changing direction to DOWN."""
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)
        mock_event_get.return_value = [event]
        quit_game = handle_input(self.mock_snake)
        self.assertFalse(quit_game)
        self.mock_snake.change_direction.assert_called_once_with(Direction.DOWN)

    @patch('pygame.event.get')
    def test_direction_change_left(self, mock_event_get):
        """Test changing direction to LEFT."""
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
        mock_event_get.return_value = [event]
        quit_game = handle_input(self.mock_snake)
        self.assertFalse(quit_game)
        self.mock_snake.change_direction.assert_called_once_with(Direction.LEFT)

    @patch('pygame.event.get')
    def test_direction_change_right(self, mock_event_get):
        """Test changing direction to RIGHT."""
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        mock_event_get.return_value = [event]
        quit_game = handle_input(self.mock_snake)
        self.assertFalse(quit_game)
        self.mock_snake.change_direction.assert_called_once_with(Direction.RIGHT)

    @patch('pygame.event.get')
    def test_no_relevant_event(self, mock_event_get):
        """Test that nothing happens for non-relevant key presses."""
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
        mock_event_get.return_value = [event]
        quit_game = handle_input(self.mock_snake)
        self.assertFalse(quit_game)
        self.mock_snake.change_direction.assert_not_called()

    @patch('pygame.event.get')
    def test_no_events(self, mock_event_get):
        """Test that nothing happens when there are no events."""
        mock_event_get.return_value = []
        quit_game = handle_input(self.mock_snake)
        self.assertFalse(quit_game)
        self.mock_snake.change_direction.assert_not_called()

if __name__ == '__main__':
    # Pygame needs to be initialized to create events, even for testing
    pygame.init()
    unittest.main()
    pygame.quit()