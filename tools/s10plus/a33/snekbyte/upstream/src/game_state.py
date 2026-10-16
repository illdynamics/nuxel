from enum import Enum, auto
from dataclasses import dataclass
from src.config import SPEED_LEVELS, DEFAULT_SPEED_INDEX, DEFAULT_WONQ_MODE

class GameState(Enum):
    """Enumeration for the different game states."""
    MAIN_MENU = auto()
    SETTINGS = auto()
    PLAYING = auto()
    GAME_OVER = auto()
    QUITTING = auto()

@dataclass
class GameSettings:
    """Dataclass to hold game settings."""
    speed_index: int = DEFAULT_SPEED_INDEX
    wonq_mode: bool = DEFAULT_WONQ_MODE

    def get_speed(self) -> int:
        """Returns the current speed (FPS) based on the index."""
        return SPEED_LEVELS[self.speed_index]

    def change_speed(self, delta: int):
        """Changes the speed index, wrapping around if necessary."""
        num_levels = len(SPEED_LEVELS)
        self.speed_index = (self.speed_index + delta + num_levels) % num_levels

    def toggle_wonq_mode(self):
        """Toggles the WonQ mode on or off."""
        self.wonq_mode = not self.wonq_mode