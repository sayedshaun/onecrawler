from dataclasses import dataclass


@dataclass(slots=True)
class HumanBehaviorSettings:
    # Delay settings
    min_delay: float = 0.3
    max_delay: float = 1.2

    # Scroll settings
    max_scrolls: int = 50
    scroll_pause: float = 1.0

    # Mouse settings
    min_mouse_moves: int = 5
    max_mouse_moves: int = 15

    mouse_width: int = 1366
    mouse_height: int = 768

    min_mouse_sleep: float = 0.1
    max_mouse_sleep: float = 0.3

    min_mouse_steps: int = 5
    max_mouse_steps: int = 20
