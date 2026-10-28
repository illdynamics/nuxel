import pygame
import sys
import logging
from src import config
from src.game_state import GameState, GameSettings
from src.game_logic import reset_game_state, update_game_state
from src.ui import draw_game_screen, draw_main_menu, draw_settings_menu, draw_game_over_menu
from src.event_handler import handle_playing_events, handle_menu_events, handle_settings_menu_events

def run_game() -> None:
    """
    The main function that initializes Pygame, controls the game loop, and
    manages state transitions.

    This function contains the primary while-loop for the game. It handles
    switching between game states like the main menu, settings, playing, and
    game over screen. It delegates event handling and rendering to other
    modules based on the current game state.
    """
    pygame.init()
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption("SnekByte")
    clock = pygame.time.Clock()

    game_settings = GameSettings()
    current_state = GameState.MAIN_MENU

    game_data = {}

    # Menu state variables
    main_menu_selection = 0
    settings_menu_selection = 0
    game_over_menu_selection = 0

    while current_state != GameState.QUITTING:
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                current_state = GameState.QUITTING
                break
        if current_state == GameState.QUITTING:
            break

        if current_state == GameState.MAIN_MENU:
            for event in events:
                main_menu_selection, confirmed = handle_menu_events(event, 3, main_menu_selection)
                if confirmed:
                    if main_menu_selection == 0: # Play
                        game_data = reset_game_state(game_settings)
                        current_state = GameState.PLAYING
                    elif main_menu_selection == 1: # Settings
                        current_state = GameState.SETTINGS
                    elif main_menu_selection == 2: # Quit
                        current_state = GameState.QUITTING
            
            if current_state != GameState.QUITTING:
                draw_main_menu(screen, main_menu_selection)

        elif current_state == GameState.SETTINGS:
            for event in events:
                settings_menu_selection, new_state, should_quit = handle_settings_menu_events(event, game_settings, settings_menu_selection)
                if should_quit:
                    current_state = GameState.QUITTING
                elif new_state:
                    current_state = new_state
            
            if current_state != GameState.QUITTING:
                draw_settings_menu(screen, game_settings, settings_menu_selection)

        elif current_state == GameState.PLAYING:
            if game_data.get("game_over"):
                 current_state = GameState.GAME_OVER
                 continue

            for event in events:
                new_direction, quit_game = handle_playing_events(event, game_data["snake"].direction)
                if quit_game:
                    current_state = GameState.QUITTING
                    break
                if event.type == pygame.KEYDOWN:
                    game_data["snake"].turn(new_direction)
            
            if current_state == GameState.QUITTING:
                break
            
            game_data = update_game_state(game_data, game_settings)
            draw_game_screen(screen, game_data, game_settings)

        elif current_state == GameState.GAME_OVER:
            for event in events:
                game_over_menu_selection, confirmed = handle_menu_events(event, 2, game_over_menu_selection)
                if confirmed:
                    if game_over_menu_selection == 0: # Retry
                        game_data = reset_game_state(game_settings)
                        current_state = GameState.PLAYING
                    elif game_over_menu_selection == 1: # Main Menu
                        current_state = GameState.MAIN_MENU
            
            if current_state != GameState.QUITTING:
                draw_game_over_menu(screen, game_data.get("score", 0), game_over_menu_selection)
        
        pygame.display.flip()
        clock.tick(game_settings.get_speed())