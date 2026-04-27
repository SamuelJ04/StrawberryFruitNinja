# states.py
from enum import Enum, auto

class MachineState(Enum):
    IDLE = auto()
    RUNNING = auto()
    STOPPED = auto()
    ERROR = auto()