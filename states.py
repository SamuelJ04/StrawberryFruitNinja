# states.py
from enum import Enum, auto

class MachineState(Enum):
    IDLE = auto()
    SEARCHING = auto()
    POSITIONING = auto()
    READY_TO_CUT = auto()
    CUTTING = auto()
    RESETTING = auto()
    STOPPED = auto()
    ERROR = auto()