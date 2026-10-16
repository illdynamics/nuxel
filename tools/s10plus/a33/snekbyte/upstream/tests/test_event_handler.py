import unittest
from unittest.mock import Mock
import pygame
from src.event_handler import handle_playing_events, handle_menu_events, handle_settings_menu_events
from src.game_state import GameState, GameSettings
from src.config import UP, DOWN, LEFT, RIGHT, SPEED_LEVELS

# Mocking pygame.event.Event
def create_key_event(key_type, key):
    """Creates a mock pygame event for key presses."""
    event = Mock()
    event.type = key_type
    event.key = key
    return event

class TestEventHandler(unittest.TestCase):
    """Tests for the event_handler module."""

    def test_handle_playing_events_direction_change(self):
        """Test changing snake direction."""
        # Test UP
        event = create_key_event(pygame.KEYDOWN, pygame.K_UP)
        new_dir, quit_game = handle_playing_events(event, RIGHT)
        self.assertEqual(new_dir, UP)
        self.assertFalse(quit_game)

        # Test DOWN (from LEFT)
        event = create_key_event(pygame.KEYDOWN, pygame.K_DOWN)
        new_dir, quit_game = handle_playing_events(event, LEFT)
        self.assertEqual(new_dir, DOWN)
        self.assertFalse(quit_game)
        
        # Test LEFT
        event = create_key_event(pygame.KEYDOWN, pygame.K_LEFT)
        new_dir, quit_game = handle_playing_events(event, UP)
        self.assertEqual(new_dir, LEFT)
        self.assertFalse(quit_game)
        
        # Test RIGHT
        event = create_key_event(pygame.KEYDOWN, pygame.K_RIGHT)
        new_dir, quit_game = handle_playing_events(event, DOWN)
        self.assertEqual(new_dir, RIGHT)
        self.assertFalse(quit_game)

    def test_handle_playing_events_no_reverse(self):
        """Test that reversing direction is ignored."""
        event = create_key_event(pygame.KEYDOWN, pygame.K_DOWN)
        new_dir, quit_game = handle_playing_events(event, UP)
        self.assertEqual(new_dir, UP) # Should not change
        self.assertFalse(quit_game)

        event = create_key_event(pygame.KEYDOWN, pygame.K_LEFT)
        new_dir, quit_game = handle_playing_events(event, RIGHT)
        self.assertEqual(new_dir, RIGHT) # Should not change
        self.assertFalse(quit_game)
    
    def test_handle_playing_events_quit(self):
        """Test quit events."""
        # pygame.QUIT
        event_quit = Mock()
        event_quit.type = pygame.QUIT
        _, quit_game = handle_playing_events(event_quit, UP)
        self.assertTrue(quit_game)

        # K_q
        event_k_q = create_key_event(pygame.KEYDOWN, pygame.K_q)
        _, quit_game = handle_playing_events(event_k_q, UP)
        self.assertTrue(quit_game)

        # K_ESCAPE
        event_k_escape = create_key_event(pygame.KEYDOWN, pygame.K_ESCAPE)
        _, quit_game = handle_playing_events(event_k_escape, UP)
        self.assertTrue(quit_game)

    def test_handle_menu_events_navigation(self):
        """Test menu navigation up and down."""
        num_options = 3
        
        # Move down
        event = create_key_event(pygame.KEYDOWN, pygame.K_DOWN)
        selected_option, confirmed = handle_menu_events(event, num_options, 0)
        self.assertEqual(selected_option, 1)
        self.assertFalse(confirmed)
        
        # Move up
        event = create_key_event(pygame.KEYDOWN, pygame.K_UP)
        selected_option, confirmed = handle_menu_events(event, num_options, 1)
        self.assertEqual(selected_option, 0)
        self.assertFalse(confirmed)

    def test_handle_menu_events_wrapping(self):
        """Test menu navigation wrapping."""
        num_options = 3

        # Wrap down
        event = create_key_event(pygame.KEYDOWN, pygame.K_DOWN)
        selected_option, confirmed = handle_menu_events(event, num_options, 2)
        self.assertEqual(selected_option, 0)
        self.assertFalse(confirmed)

        # Wrap up
        event = create_key_event(pygame.KEYDOWN, pygame.K_UP)
        selected_option, confirmed = handle_menu_events(event, num_options, 0)
        self.assertEqual(selected_option, 2)
        self.assertFalse(confirmed)

    def test_handle_menu_events_confirm(self):
        """Test menu confirmation."""
        event = create_key_event(pygame.KEYDOWN, pygame.K_RETURN)
        selected_option, confirmed = handle_menu_events(event, 3, 1)
        self.assertEqual(selected_option, 1)
        self.assertTrue(confirmed)

    def test_handle_settings_menu_events_change_value(self):
        """Test changing a setting's value."""
        settings = GameSettings()
        initial_speed_index = settings.speed_index
        
        # Change speed up
        event = create_key_event(pygame.KEYDOWN, pygame.K_RIGHT)
        # Assuming speed is at index 0
        new_opt, new_state, quit_game = handle_settings_menu_events(event, settings, 0)
        self.assertEqual(new_opt, 0)
        self.assertIsNone(new_state)
        self.assertFalse(quit_game)
        self.assertEqual(settings.speed_index, (initial_speed_index + 1) % len(SPEED_LEVELS))
        
        # Change speed down
        event = create_key_event(pygame.KEYDOWN, pygame.K_LEFT)
        new_opt, new_state, quit_game = handle_settings_menu_events(event, settings, 0)
        self.assertEqual(new_opt, 0)
        self.assertIsNone(new_state)
        self.assertFalse(quit_game)
        self.assertEqual(settings.speed_index, initial_speed_index)

    def test_handle_settings_menu_events_toggle_wonq(self):
        """Test toggling WonQ mode."""
        settings = GameSettings()
        initial_wonq = settings.wonq_mode
        
        # Toggle with right arrow
        event = create_key_event(pygame.KEYDOWN, pygame.K_RIGHT)
        # Assuming WonQ mode is at index 1
        handle_settings_menu_events(event, settings, 1)
        self.assertNotEqual(settings.wonq_mode, initial_wonq)

        # Toggle back with left arrow
        event = create_key_event(pygame.KEYDOWN, pygame.K_LEFT)
        handle_settings_menu_events(event, settings, 1)
        self.assertEqual(settings.wonq_mode, initial_wonq)

    def test_handle_settings_menu_events_back_to_main(self):
        """Test returning to the main menu."""
        settings = GameSettings()
        event = create_key_event(pygame.KEYDOWN, pygame.K_RETURN)
        # Assuming "Back" is at index 2
        _, new_state, _ = handle_settings_menu_events(event, settings, 2)
        self.assertEqual(new_state, GameState.MAIN_MENU)

    def test_handle_settings_menu_escape(self):
        """Test exiting settings with ESCAPE."""
        settings = GameSettings()
        event = create_key_event(pygame.KEYDOWN, pygame.K_ESCAPE)
        _, new_state, _ = handle_settings_menu_events(event, settings, 0)
        self.assertEqual(new_state, GameState.MAIN_MENU)

if __name__ == '__main__':
    unittest.main()