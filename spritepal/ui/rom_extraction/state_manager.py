"""
State management for ROM extraction workflow
Provides a state machine to manage extraction operations and prevent conflicts
"""

from enum import Enum, auto
from typing import ClassVar

from PyQt6.QtCore import QObject, pyqtSignal


class ExtractionState(Enum):
    """States for the extraction workflow"""
    IDLE = auto()                    # No operation in progress
    LOADING_ROM = auto()             # Loading ROM file
    SCANNING_SPRITES = auto()        # Scanning for sprite locations
    PREVIEWING_SPRITE = auto()       # Loading sprite preview
    SEARCHING_SPRITE = auto()        # Searching for next/prev sprite
    EXTRACTING = auto()              # Performing extraction
    ERROR = auto()                   # Error state


class ExtractionStateManager(QObject):
    """Manages extraction workflow state and transitions"""

    # Signals
    state_changed = pyqtSignal(ExtractionState, ExtractionState)  # old_state, new_state

    # Valid state transitions
    VALID_TRANSITIONS: ClassVar[dict[ExtractionState, set[ExtractionState]]] = {
        ExtractionState.IDLE: {
            ExtractionState.LOADING_ROM,
            ExtractionState.SCANNING_SPRITES,
            ExtractionState.PREVIEWING_SPRITE,
            ExtractionState.SEARCHING_SPRITE,
            ExtractionState.EXTRACTING,
        },
        ExtractionState.LOADING_ROM: {
            ExtractionState.IDLE,
            ExtractionState.ERROR,
        },
        ExtractionState.SCANNING_SPRITES: {
            ExtractionState.IDLE,
            ExtractionState.ERROR,
        },
        ExtractionState.PREVIEWING_SPRITE: {
            ExtractionState.IDLE,
            ExtractionState.ERROR,
            ExtractionState.SEARCHING_SPRITE,  # Can search while preview loads
        },
        ExtractionState.SEARCHING_SPRITE: {
            ExtractionState.IDLE,
            ExtractionState.ERROR,
            ExtractionState.PREVIEWING_SPRITE,  # Preview after finding
        },
        ExtractionState.EXTRACTING: {
            ExtractionState.IDLE,
            ExtractionState.ERROR,
        },
        ExtractionState.ERROR: {
            ExtractionState.IDLE,  # Reset to idle from error
        },
    }

    # States that block new operations
    BLOCKING_STATES: ClassVar[set[ExtractionState]] = {
        ExtractionState.LOADING_ROM,
        ExtractionState.SCANNING_SPRITES,
        ExtractionState.EXTRACTING,
    }

    def __init__(self) -> None:
        super().__init__()
        self._current_state = ExtractionState.IDLE
        self._error_message: str | None = None

    @property
    def current_state(self) -> ExtractionState:
        """Get current state"""
        return self._current_state

    @property
    def is_busy(self) -> bool:
        """Check if a blocking operation is in progress"""
        return self._current_state in self.BLOCKING_STATES

    @property
    def can_extract(self) -> bool:
        """Check if extraction can be started"""
        return self._current_state == ExtractionState.IDLE

    @property
    def can_preview(self) -> bool:
        """Check if preview can be started"""
        return self._current_state in {ExtractionState.IDLE, ExtractionState.SEARCHING_SPRITE}

    @property
    def can_search(self) -> bool:
        """Check if search can be started"""
        return self._current_state in {ExtractionState.IDLE, ExtractionState.PREVIEWING_SPRITE}

    @property
    def can_scan(self) -> bool:
        """Check if sprite scanning can be started"""
        return self._current_state == ExtractionState.IDLE

    @property
    def error_message(self) -> str | None:
        """Get error message if in error state"""
        return self._error_message if self._current_state == ExtractionState.ERROR else None

    def transition_to(self, new_state: ExtractionState, error_message: str | None = None) -> bool:
        """
        Attempt to transition to a new state

        Args:
            new_state: Target state
            error_message: Error message if transitioning to ERROR state

        Returns:
            True if transition was successful, False otherwise
        """
        # Check if transition is valid
        if new_state not in self.VALID_TRANSITIONS.get(self._current_state, set()):
            return False

        old_state = self._current_state
        self._current_state = new_state

        # Handle error state
        if new_state == ExtractionState.ERROR:
            self._error_message = error_message
        else:
            self._error_message = None

        # Emit state change signal
        self.state_changed.emit(old_state, new_state)

        return True

    def reset(self) -> None:
        """Reset to idle state"""
        self.transition_to(ExtractionState.IDLE)

    def start_loading_rom(self) -> bool:
        """Start loading ROM operation"""
        return self.transition_to(ExtractionState.LOADING_ROM)

    def finish_loading_rom(self, success: bool = True, error: str | None = None) -> bool:
        """Finish loading ROM operation"""
        if success:
            return self.transition_to(ExtractionState.IDLE)
        return self.transition_to(ExtractionState.ERROR, error)

    def start_scanning(self) -> bool:
        """Start sprite scanning operation"""
        return self.transition_to(ExtractionState.SCANNING_SPRITES)

    def finish_scanning(self, success: bool = True, error: str | None = None) -> bool:
        """Finish sprite scanning operation"""
        if success:
            return self.transition_to(ExtractionState.IDLE)
        return self.transition_to(ExtractionState.ERROR, error)

    def start_preview(self) -> bool:
        """Start sprite preview operation"""
        return self.transition_to(ExtractionState.PREVIEWING_SPRITE)

    def finish_preview(self, success: bool = True, error: str | None = None) -> bool:
        """Finish sprite preview operation"""
        if success:
            return self.transition_to(ExtractionState.IDLE)
        return self.transition_to(ExtractionState.ERROR, error)

    def start_search(self) -> bool:
        """Start sprite search operation"""
        return self.transition_to(ExtractionState.SEARCHING_SPRITE)

    def finish_search(self, success: bool = True, error: str | None = None) -> bool:
        """Finish sprite search operation"""
        if success:
            return self.transition_to(ExtractionState.IDLE)
        return self.transition_to(ExtractionState.ERROR, error)

    def start_extraction(self) -> bool:
        """Start extraction operation"""
        return self.transition_to(ExtractionState.EXTRACTING)

    def finish_extraction(self, success: bool = True, error: str | None = None) -> bool:
        """Finish extraction operation"""
        if success:
            return self.transition_to(ExtractionState.IDLE)
        return self.transition_to(ExtractionState.ERROR, error)
