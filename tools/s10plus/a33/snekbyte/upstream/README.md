# SnekByte

This is a classic snake game built with Python and Pygame, with a twist!

### Quickstart

1.  **Install Dependencies:**
    This will install `pygame`, the library used for the game.
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Game:**
    This command starts the game.
    ```bash
    python src/main.py
    ```

3.  **How to Play:**
    *   Use the **Arrow Keys** to change the snake's direction.
    *   Eat the food to grow longer and increase your score.
    *   Avoid running into the walls or the snake's own body.
    *   Press the **ESC key** to quit.

### WoNQ Mode

This game includes a special, challenging mode called "WoNQ Mode".

**How to activate WoNQ Mode:**
1.  From the main menu, select "Settings".
2.  Toggle "WoNQ Mode" to "On".

**What is WoNQ Mode?**
When playing in WoNQ Mode, the snake will drop a "poop" obstacle every time it eats 5 pieces of food. These poop obstacles are persistent and will end the game if the snake collides with them. Keep an eye on the "Poop-o-meter" in the UI to see how close you are to dropping a poop!

### How it Works

*   **`src/main.py`**: The entry point that initializes the game.
*   **`src/game_loop.py`**: Runs the main game loop.
*   **`src/game_logic.py`**: Contains the core game logic, including snake movement, collision detection, and the WoNQ mode mechanics.
*   **`src/game_state.py`**: Manages the game's state, including settings and the current screen (menu, playing, etc.).
*   **`src/ui.py`**: Handles all rendering, including the snake, food, score, and the WoNQ mode "Poop-o-meter".
*   **`src/poop.py`**: Defines the `Poop` class for the obstacles in WoNQ mode.
*   **`src/config.py`**: Stores game settings and constants.