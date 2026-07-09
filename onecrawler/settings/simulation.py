from dataclasses import dataclass


@dataclass(slots=True)
class HumanBehaviorSettings:
    """Configuration for simulating human interaction with a web page.

    Attributes:
        min_delay (float): Minimum delay in seconds between major actions.
        max_delay (float): Maximum delay in seconds between major actions.
        max_scrolls (int): Maximum number of scroll steps per page.
        scroll_pause (float): Pause in seconds between scroll steps.
        min_mouse_moves (int): Minimum number of mouse movements per action.
        max_mouse_moves (int): Maximum number of mouse movements per action.
        mouse_width (int): Width of the area for mouse movement simulation.
        mouse_height (int): Height of the area for mouse movement simulation.
        min_mouse_sleep (float): Minimum sleep time between mouse steps.
        max_mouse_sleep (float): Maximum sleep time between mouse steps.
        min_mouse_steps (int): Minimum steps per mouse movement.
        max_mouse_steps (int): Maximum steps per mouse movement.
    """

    min_delay: float = 0.3
    max_delay: float = 1.2

    max_scrolls: int = 50
    scroll_pause: float = 1.0

    min_mouse_moves: int = 5
    max_mouse_moves: int = 15

    mouse_width: int = 1366
    mouse_height: int = 768

    min_mouse_sleep: float = 0.1
    max_mouse_sleep: float = 0.3

    min_mouse_steps: int = 5
    max_mouse_steps: int = 20
