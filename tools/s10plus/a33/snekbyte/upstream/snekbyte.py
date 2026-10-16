import argparse
import logging
import sys
import pygame
from .utils import constants as const
from .utils.logger import setup_logging
from src.game_loop import run_game as run_pygame_game

class App:
    """
    The main application class for the SnekByte game.
    Manages game states, rendering, and user input.
    """
    def __init__(self, args: argparse.Namespace):
        """
        Initializes the App.

        Args:
            args: Command-line arguments parsed by argparse.
        """
        pygame.init()
        pygame.display.set_caption("SnekByte")
        self.screen = pygame.display.set_mode((const.SCREEN_WIDTH, const.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.current_state = "main_menu"

        self.wonq_mode = args.wonq
        self.speed_level = const.DEFAULT_SPEED_INDEX
        
        # Load fonts
        try:
            self.title_font = pygame.font.Font(None, 74)
            self.menu_font = pygame.font.Font(None, 50)
            self.ascii_font = pygame.font.Font(pygame.font.get_default_font(), 18) # A monospaced font
        except IOError:
            logging.error("Font file not found. Using default pygame font.")
            self.title_font = pygame.font.Font(None, 74)
            self.menu_font = pygame.font.Font(None, 50)
            self.ascii_font = pygame.font.Font(None, 18)
            
        self.snekbyte_ascii_art = const.SNEKBYTE_ASCII_ART.split('\n')


    def _render_text(self, text: str, font: pygame.font.Font, color: tuple, center_pos: tuple):
        """
        Renders text on the screen at a specified center position.

        Args:
            text: The string to render.
            font: The pygame Font object to use.
            color: The color of the text.
            center_pos: A tuple (x, y) for the center of the text rectangle.
        """
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=center_pos)
        self.screen.blit(text_surface, text_rect)

    def _draw_main_menu(self, selected_option: int):
        """
        Renders the main menu screen, including the title and options.

        Args:
            selected_option: The index of the currently highlighted menu item.
        """
        self.screen.fill(const.BLACK)

        # Draw ASCII Art Title
        for i, line in enumerate(self.snekbyte_ascii_art):
            self._render_text(line, self.ascii_font, const.GREEN, (const.SCREEN_WIDTH // 2, 50 + i * 15))
        
        menu_items = ["Play Game", "Settings", f"{'Deactivate' if self.wonq_mode else 'Activate'} --wonq mode", "Quit"]
        
        for i, item in enumerate(menu_items):
            color = const.GREEN if i == selected_option else const.WHITE
            self._render_text(item, self.menu_font, color, (const.SCREEN_WIDTH // 2, 350 + i * 60))
            
        pygame.display.flip()

    def show_main_menu(self):
        """Handles the logic and rendering for the main menu state."""
        selected_option = 0
        num_options = 4

        while self.current_state == "main_menu":
            self._draw_main_menu(selected_option)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.current_state = None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected_option = (selected_option - 1) % num_options
                    elif event.key == pygame.K_DOWN:
                        selected_option = (selected_option + 1) % num_options
                    elif event.key == pygame.K_RETURN:
                        if selected_option == 0: # Play Game
                            self.current_state = "playing"
                        elif selected_option == 1: # Settings
                            self.current_state = "settings"
                        elif selected_option == 2: # Toggle WonQ
                            self.wonq_mode = not self.wonq_mode
                        elif selected_option == 3: # Quit
                            self.running = False
                            self.current_state = None
            self.clock.tick(const.FPS)


    def _draw_settings_menu(self, selected_option: int):
        """
        Renders the settings menu screen.

        Args:
            selected_option: The index of the currently highlighted setting.
        """
        self.screen.fill(const.BLACK)
        self._render_text("Settings", self.title_font, const.WHITE, (const.SCREEN_WIDTH // 2, 100))
        
        # Speed setting
        speed_color = const.GREEN if selected_option == 0 else const.WHITE
        speed_text = f"Speed: < {const.SPEED_NAMES[self.speed_level]} >"
        self._render_text(speed_text, self.menu_font, speed_color, (const.SCREEN_WIDTH // 2, 250))
        
        # Back option
        back_color = const.GREEN if selected_option == 1 else const.WHITE
        self._render_text("Back", self.menu_font, back_color, (const.SCREEN_WIDTH // 2, 350))
        
        pygame.display.flip()


    def show_settings_menu(self):
        """Handles the logic and rendering for the settings menu state."""
        selected_option = 0
        num_options = 2

        while self.current_state == "settings":
            self._draw_settings_menu(selected_option)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.current_state = None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected_option = (selected_option - 1) % num_options
                    elif event.key == pygame.K_DOWN:
                        selected_option = (selected_option + 1) % num_options
                    elif event.key == pygame.K_LEFT:
                        if selected_option == 0: # Speed
                            self.speed_level = (self.speed_level - 1) % len(const.SPEEDS)
                    elif event.key == pygame.K_RIGHT:
                        if selected_option == 0: # Speed
                           self.speed_level = (self.speed_level + 1) % len(const.SPEEDS)
                    elif event.key == pygame.K_RETURN:
                        if selected_option == 1: # Back
                            self.current_state = "main_menu"
                    elif event.key == pygame.K_ESCAPE:
                        self.current_state = "main_menu"
            self.clock.tick(const.FPS)
            
    def run(self):
        """The main loop of the application, which delegates to state handlers."""
        while self.running:
            if self.current_state == "main_menu":
                self.show_main_menu()
            elif self.current_state == "settings":
                self.show_settings_menu()
            elif self.current_state == "playing":
                # This will be replaced by the actual game loop in a later task
                logging.info(f"Starting game with Speed: {const.SPEED_NAMES[self.speed_level]} and WonQ mode: {self.wonq_mode}")
                game_result = run_pygame_game(self.screen, self.clock, self.speed_level, self.wonq_mode)
                self.current_state = "main_menu" # Return to menu after game over

        pygame.quit()
        sys.exit()