import unittest
from src.game_state import GameSettings
from src.config import SPEED_LEVELS, DEFAULT_SPEED_INDEX, DEFAULT_WONQ_MODE

class TestGameSettings(unittest.TestCase):
    """Tests for the GameSettings class."""

    def setUp(self):
        """Set up a new GameSettings object for each test."""
        self.settings = GameSettings()

    def test_initialization(self):
        """Test that GameSettings initializes with default values."""
        self.assertEqual(self.settings.speed_index, DEFAULT_SPEED_INDEX)
        self.assertEqual(self.settings.wonq_mode, DEFAULT_WONQ_MODE)
        self.assertEqual(self.settings.get_speed(), SPEED_LEVELS[DEFAULT_SPEED_INDEX])

    def test_get_speed(self):
        """Test the get_speed method."""
        for i, speed in enumerate(SPEED_LEVELS):
            self.settings.speed_index = i
            self.assertEqual(self.settings.get_speed(), speed)

    def test_change_speed_increase(self):
        """Test increasing the speed index."""
        initial_index = self.settings.speed_index
        self.settings.change_speed(1)
        expected_index = (initial_index + 1) % len(SPEED_LEVELS)
        self.assertEqual(self.settings.speed_index, expected_index)

    def test_change_speed_decrease(self):
        """Test decreasing the speed index."""
        initial_index = self.settings.speed_index
        self.settings.change_speed(-1)
        expected_index = (initial_index - 1 + len(SPEED_LEVELS)) % len(SPEED_LEVELS)
        self.assertEqual(self.settings.speed_index, expected_index)

    def test_change_speed_wraps_around_increase(self):
        """Test that increasing speed wraps around to the start."""
        self.settings.speed_index = len(SPEED_LEVELS) - 1
        self.settings.change_speed(1)
        self.assertEqual(self.settings.speed_index, 0)

    def test_change_speed_wraps_around_decrease(self):
        """Test that decreasing speed wraps around to the end."""
        self.settings.speed_index = 0
        self.settings.change_speed(-1)
        self.assertEqual(self.settings.speed_index, len(SPEED_LEVELS) - 1)

    def test_toggle_wonq_mode(self):
        """Test toggling the wonq_mode."""
        initial_mode = self.settings.wonq_mode
        self.settings.toggle_wonq_mode()
        self.assertEqual(self.settings.wonq_mode, not initial_mode)
        self.settings.toggle_wonq_mode()
        self.assertEqual(self.settings.wonq_mode, initial_mode)

if __name__ == '__main__':
    unittest.main()