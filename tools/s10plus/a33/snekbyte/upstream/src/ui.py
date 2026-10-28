import pygame
from src import config
from src.game_state import GameSettings

def _get_font(size):
    """Helper function to get a font object."""
    return pygame.font.Font(None, size)

def draw_text(screen, text, font, color, center_x, y):
    """Renders text centered on the screen at a given y-coordinate."""
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(center_x, y))
    screen.blit(text_surface, text_rect)

def draw_grid(screen):
    """Draws the grid lines on the screen."""
    for x in range(0, config.SCREEN_WIDTH, config.GRID_SIZE):
        pygame.draw.line(screen, config.GRAY, (x, 0), (x, config.SCREEN_HEIGHT))
    for y in range(0, config.SCREEN_HEIGHT, config.GRID_SIZE):
        pygame.draw.line(screen, config.GRAY, (0, y), (config.SCREEN_WIDTH, y))

def draw_game_screen(screen, game_data, settings: GameSettings):
    """
    Draws all elements for the main game screen.

    Args:
        screen: The pygame Surface to draw on.
        game_data: The dictionary containing the current game state.
        settings: The current GameSettings object.
    """
    screen.fill(config.BLACK)
    draw_grid(screen)
    game_data["snake"].draw(screen)
    game_data["food"].draw(screen)
    if settings.wonq_mode:
        for poop in game_data["poops"]:
            poop.draw(screen)
    draw_game_ui(screen, game_data["score"], game_data["shit_counter"], settings)

def draw_game_ui(screen, score, shit_counter, settings: GameSettings):
    """
    Draws the UI overlay on the game screen (score, etc.).

    Args:
        screen: The pygame Surface to draw on.
        score: The player's current score.
        shit_counter: The current count towards the next shit piece.
        settings: The current GameSettings object.
    """
    font = _get_font(config.UI_FONT_SIZE)
    score_text = f"Score: {score}"
    draw_text(screen, score_text, font, config.UI_TEXT_COLOR, 70, 20)
    
    if settings.wonq_mode:
        poop_text = f"Poop-o-meter: {shit_counter}/{config.WONQ_MODE_POOP_THRESHOLD}"
        draw_text(screen, poop_text, font, config.UI_TEXT_COLOR, config.SCREEN_WIDTH - 150, 20)

def draw_main_menu(screen, selected_option):
    """
    Draws the main menu screen.

    Args:
        screen: The pygame Surface to draw on.
        selected_option: The index of the currently selected menu item.
    """
    screen.fill(config.UI_BG_COLOR)
    title_font = _get_font(config.MENU_TITLE_FONT_SIZE)
    option_font = _get_font(config.MENU_OPTION_FONT_SIZE)
    
    draw_text(screen, "SnekByte", title_font, config.WHITE, config.SCREEN_WIDTH // 2, 100)
    
    options = ["Play", "Settings", "Quit"]
    for i, option in enumerate(options):
        color = config.UI_HIGHLIGHT_COLOR if i == selected_option else config.UI_TEXT_COLOR
        draw_text(screen, option, option_font, color, config.SCREEN_WIDTH // 2, 300 + i * 70)

def draw_settings_menu(screen, settings: GameSettings, selected_option: int):
    """
    Draws the settings menu screen.

    Args:
        screen: The pygame Surface to draw on.
        settings: The current GameSettings object.
        selected_option: The index of the currently selected setting.
    """
    screen.fill(config.UI_BG_COLOR)
    title_font = _get_font(config.MENU_TITLE_FONT_SIZE)
    option_font = _get_font(config.MENU_OPTION_FONT_SIZE)
    
    draw_text(screen, "Settings", title_font, config.WHITE, config.SCREEN_WIDTH // 2, 100)
    
    # Speed Setting
    speed_color = config.UI_HIGHLIGHT_COLOR if selected_option == 0 else config.UI_TEXT_COLOR
    speed_text = f"Speed: < {settings.get_speed()} >"
    draw_text(screen, speed_text, option_font, speed_color, config.SCREEN_WIDTH // 2, 300)

    # WonQ Mode Setting
    wonq_color = config.UI_HIGHLIGHT_COLOR if selected_option == 1 else config.UI_TEXT_COLOR
    wonq_status = "ON" if settings.wonq_mode else "OFF"
    wonq_text = f"WonQ Mode: < {wonq_status} >"
    draw_text(screen, wonq_text, option_font, wonq_color, config.SCREEN_WIDTH // 2, 370)

def draw_game_over_menu(screen, score, selected_option):
    """
    Draws the game over menu screen.

    Args:
        screen: The pygame Surface to draw on.
        score: The final score to display.
        selected_option: The index of the currently selected menu item.
    """
    screen.fill(config.UI_BG_COLOR)
    title_font = _get_font(config.MENU_TITLE_FONT_SIZE)
    score_font = _get_font(config.SCORE_FONT_SIZE)
    option_font = _get_font(config.MENU_OPTION_FONT_SIZE)

    draw_text(screen, "Game Over", title_font, config.WHITE, config.SCREEN_WIDTH // 2, 100)
    draw_text(screen, f"Final Score: {score}", score_font, config.GOLD, config.SCREEN_WIDTH // 2, 200)

    options = ["Retry", "Main Menu"]
    for i, option in enumerate(options):
        color = config.UI_HIGHLIGHT_COLOR if i == selected_option else config.UI_TEXT_COLOR
        draw_text(screen, option, option_font, color, config.SCREEN_WIDTH // 2, 350 + i * 70)