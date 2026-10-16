import random
from src.config import GRID_WIDTH, GRID_HEIGHT, RIGHT, WONQ_MODE_POOP_THRESHOLD
from src.game_state import GameSettings, GameState
from src.snake import Snake
from src.food import Food
from src.poop import Poop


def reset_game_state(settings: GameSettings):
    """
    Resets the game to its initial state.

    Args:
        settings: The GameSettings object.

    Returns:
        A dictionary representing the initial state of the game.
    """
    snake = Snake()
    poops = []
    # Ensure the first food is not placed on the snake
    food_position = _place_item(snake.positions)
    food = Food(food_position)

    return {
        "snake": snake,
        "food": food,
        "poops": poops,
        "score": 0,
        "game_over": False,
        "shit_counter": 0,
    }


def _place_item(occupied_positions):
    """
    Finds a random empty position on the grid.

    Args:
        occupied_positions: A list of (x, y) tuples that are already taken.

    Returns:
        A tuple (x, y) for the new item's position.
    """
    position = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
    while position in occupied_positions:
        position = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
    return position


def update_game_state(game_data, settings: GameSettings):
    """
    Updates the game state for a single frame.

    Args:
        game_data: A dictionary containing the current game state.
        settings: The current GameSettings.

    Returns:
        The updated game_data dictionary.
    """
    if game_data["game_over"]:
        return game_data

    snake = game_data["snake"]
    food = game_data["food"]
    poops = game_data["poops"]
    score = game_data["score"]
    shit_counter = game_data["shit_counter"]

    # Move the snake
    snake.move()
    head = snake.get_head_position()

    # Check for food collision
    if head == food.position:
        snake.length += 1
        score += 1

        if settings.wonq_mode:
            shit_counter += 1
            if shit_counter >= WONQ_MODE_POOP_THRESHOLD:
                # Place poop at the new tail position
                poop_pos = snake.positions[-1]
                poops.append(Poop(poop_pos))
                shit_counter = 0

        # Place new food
        occupied_positions = snake.positions + [p.position for p in poops]
        food.position = _place_item(occupied_positions)

    # Check for game-ending collisions
    head_x, head_y = head
    # 1. Wall collision
    if not (0 <= head_x < GRID_WIDTH and 0 <= head_y < GRID_HEIGHT):
        game_data["game_over"] = True
    # 2. Self collision
    elif head in snake.positions[1:]:
        game_data["game_over"] = True
    # 3. Poop collision (in WonQ mode)
    elif settings.wonq_mode:
        for poop in poops:
            if head == poop.position:
                game_data["game_over"] = True
                break

    # Update game_data dictionary before returning
    game_data["score"] = score
    game_data["shit_counter"] = shit_counter

    return game_data