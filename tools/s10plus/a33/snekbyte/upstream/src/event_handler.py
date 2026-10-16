import pygame
from pygame.locals import K_UP, K_DOWN, K_LEFT, K_RIGHT, K_ESCAPE, K_RETURN, K_q
from typing import Tuple, Optional
from src.game_state import GameState, GameSettings
from src.config import SPEED_LEVELS, UP, DOWN, LEFT, RIGHT as DIR_RIGHT

def handle_playing_events(event: pygame.event.Event, current_direction: Tuple[int, int]) -> Tuple[Tuple[int, int], bool]:
    """
    Handles keyboard input during the 'PLAYING' state to control the snake.

    Args:
        event: The pygame event to process, expected to be a KEYDOWN event.
        current_direction: The current direction vector of the snake, e.g., (0, -1) for UP.

    Returns:
        A tuple containing:
        - The new direction vector for the snake.
        - A boolean indicating if the game should quit (e.g., if ESC is pressed).
    """
    if event.type == pygame.KEYDOWN:
        if event.key == K_UP:
            return UP, False
        elif event.key == K_DOWN:
            return DOWN, False
        elif event.key == K_LEFT:
            return LEFT, False
        elif event.key == K_RIGHT:
            return DIR_RIGHT, False
        elif event.key in [K_ESCAPE, K_q]:
            return current_direction, True
    return current_direction, False


def handle_menu_events(event: pygame.event.Event, num_options: int, selected_option: int) -> Tuple[int, bool]:
    """
    Handles generic menu navigation events (up, down, select) for any menu.

    Args:
        event: The pygame event to process.
        num_options: The total number of options available in the menu.
        selected_option: The index of the currently selected option.

    Returns:
        A tuple containing:
        - The updated selected_option index.
        - A boolean, `confirmed_selection`, which is True if the Enter key
          was pressed, indicating the selection was confirmed.
    """
    confirmed_selection = False
    if event.type == pygame.KEYDOWN:
        if event.key == K_UP:
            selected_option = (selected_option - 1 + num_options) % num_options
        elif event.key == K_DOWN:
            selected_option = (selected_option + 1) % num_options
        elif event.key == K_RETURN:
            confirmed_selection = True
    return selected_option, confirmed_selection

def handle_settings_menu_events(event: pygame.event.Event, game_settings: GameSettings, selected_option: int) -> Tuple[int, Optional[GameState], bool]:
    """
    Handles events for the settings menu, allowing value changes and navigation.

    This handles changing settings like speed and WonQ mode using left/right keys,
    navigating the menu with up/down keys, and confirming/exiting with Enter/Escape.

    Args:
        event: The pygame event to process.
        game_settings: The current GameSettings object, which will be modified.
        selected_option: The index of the currently selected setting.

    Returns:
        A tuple containing:
        - The updated selected_option index.
        - An optional new_game_state (e.g., returning to MAIN_MENU).
        - A boolean indicating if the application should quit.
    """
    if event.type == pygame.KEYDOWN:
        if event.key in [K_ESCAPE, K_q]:
            return selected_option, GameState.MAIN_MENU, False
        elif event.key == K_UP:
            selected_option = (selected_option - 1 + 2) % 2
        elif event.key == K_DOWN:
            selected_option = (selected_option + 1) % 2
        elif event.key == K_LEFT:
            if selected_option == 0:  # Speed
                game_settings.change_speed(-1)
            elif selected_option == 1: # WonQ Mode
                game_settings.toggle_wonq_mode()
        elif event.key == K_RIGHT:
            if selected_option == 0:  # Speed
                game_settings.change_speed(1)
            elif selected_option == 1: # WonQ Mode
                game_settings.toggle_wonq_mode()
        elif event.key == K_RETURN:
             if selected_option == 1: # WonQ Mode
                game_settings.toggle_wonq_mode()

    return selected_option, None, False