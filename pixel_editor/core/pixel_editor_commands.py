"""
Delta-based undo/redo system using Command pattern for the pixel editor.

This module implements a memory-efficient undo/redo system that stores only the
changes (deltas) rather than full image copies. Commands can be compressed for
long-term storage to further reduce memory usage.
"""

# Standard library imports
import pickle
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

# Third-party imports
import numpy as np

if TYPE_CHECKING:
    from .pixel_editor_widgets import PixelCanvas


class UndoCommand(ABC):
    """Abstract base class for all undo commands.

    Each command represents a reversible operation on the canvas.
    Commands can be compressed to reduce memory usage for older operations.
    """

    def __init__(self) -> None:
        """Initialize command with timestamp and compression state."""
        self.timestamp: datetime = datetime.now(timezone.utc)
        self.compressed: bool = False
        self._compressed_data: Optional[bytes] = None

    @abstractmethod
    def execute(self, canvas: "PixelCanvas") -> None:
        """Apply this command to the canvas.

        Args:
            canvas: The PixelCanvas instance to modify
        """

    @abstractmethod
    def unexecute(self, canvas: "PixelCanvas") -> None:
        """Revert this command on the canvas.

        Args:
            canvas: The PixelCanvas instance to restore
        """

    @abstractmethod
    def get_memory_size(self) -> int:
        """Return approximate memory usage in bytes.

        Returns:
            Estimated memory usage including overhead
        """

    def compress(self) -> None:
        """Compress command data for long-term storage.

        Converts internal data to compressed bytes to reduce memory usage.
        Original data is cleared after compression.
        """
        if not self.compressed:
            data = self._get_compress_data()
            self._compressed_data = zlib.compress(pickle.dumps(data))
            self._clear_uncompressed_data()
            self.compressed = True

    def decompress(self) -> None:
        """Decompress command data for execution.

        Restores internal data from compressed bytes when the command
        needs to be executed or unexecuted.
        """
        if self.compressed and self._compressed_data:
            data = pickle.loads(zlib.decompress(self._compressed_data))
            self._restore_from_compressed(data)
            self._compressed_data = None
            self.compressed = False

    @abstractmethod
    def _get_compress_data(self) -> Any:
        """Get data to be compressed.

        Returns:
            Data structure containing all information needed to restore command
        """

    @abstractmethod
    def _clear_uncompressed_data(self) -> None:
        """Clear uncompressed data after compression."""

    @abstractmethod
    def _restore_from_compressed(self, data: Any) -> None:
        """Restore state from compressed data.

        Args:
            data: The decompressed data structure
        """

    def to_dict(self) -> dict[str, Any]:
        """Serialize command to dictionary for save/load support.

        Returns:
            Dictionary representation of the command
        """
        return {
            "type": self.__class__.__name__,
            "timestamp": self.timestamp.isoformat(),
            "compressed": self.compressed,
            "data": self._get_compress_data() if not self.compressed else None,
            "compressed_data": (
                self._compressed_data.hex() if self._compressed_data else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UndoCommand":
        """Deserialize command from dictionary.

        Args:
            data: Dictionary representation of the command

        Returns:
            Reconstructed command instance
        """
        # This would be implemented by subclasses
        raise NotImplementedError("Subclasses must implement from_dict")


@dataclass
class DrawPixelCommand(UndoCommand):
    """Command for single pixel changes.

    Stores the position and color change for a single pixel modification.
    This is the most memory-efficient command for isolated pixel edits.
    """

    x: int = 0
    y: int = 0
    old_color: int = 0
    new_color: int = 0

    def __post_init__(self) -> None:
        """Initialize parent class after dataclass initialization."""
        super().__init__()

    def execute(self, canvas: "PixelCanvas") -> None:
        """Apply pixel color change."""
        if (
            canvas.image_data is not None
            and 0 <= self.x < canvas.image_data.shape[1]
            and 0 <= self.y < canvas.image_data.shape[0]
        ):
            canvas.image_data[self.y, self.x] = self.new_color

    def unexecute(self, canvas: "PixelCanvas") -> None:
        """Restore original pixel color."""
        if (
            canvas.image_data is not None
            and 0 <= self.x < canvas.image_data.shape[1]
            and 0 <= self.y < canvas.image_data.shape[0]
        ):
            canvas.image_data[self.y, self.x] = self.old_color

    def get_memory_size(self) -> int:
        """Calculate memory usage."""
        if self.compressed and self._compressed_data:
            return len(self._compressed_data) + 64
        # 4 ints (x, y, old_color, new_color) + overhead
        return 4 * 4 + 64  # ~80 bytes

    def _get_compress_data(self) -> tuple[int, int, int, int]:
        """Get pixel data for compression."""
        return (self.x, self.y, self.old_color, self.new_color)

    def _clear_uncompressed_data(self) -> None:
        """No need to clear primitive types."""

    def _restore_from_compressed(self, data: tuple[int, int, int, int]) -> None:
        """Restore pixel data from compressed format."""
        self.x, self.y, self.old_color, self.new_color = data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DrawPixelCommand":
        """Create command from dictionary."""
        cmd = cls()
        cmd.timestamp = datetime.fromisoformat(data["timestamp"])
        cmd.compressed = data["compressed"]

        if data["compressed"]:
            cmd._compressed_data = bytes.fromhex(data["compressed_data"])
        else:
            cmd.x, cmd.y, cmd.old_color, cmd.new_color = data["data"]

        return cmd


@dataclass
class DrawLineCommand(UndoCommand):
    """Command for line drawing operations.

    Stores all pixels affected by a line drawing operation, including
    their original colors for proper undo functionality.
    """

    pixels: list[tuple[int, int, int]] = field(
        default_factory=list
    )  # [(x, y, old_color), ...]
    new_color: int = 0

    def __post_init__(self) -> None:
        """Initialize parent class after dataclass initialization."""
        super().__init__()

    def execute(self, canvas: "PixelCanvas") -> None:
        """Apply new color to all line pixels."""
        if canvas.image_data is None:
            return

        for x, y, _ in self.pixels:
            if (
                0 <= x < canvas.image_data.shape[1]
                and 0 <= y < canvas.image_data.shape[0]
            ):
                canvas.image_data[y, x] = self.new_color

    def unexecute(self, canvas: "PixelCanvas") -> None:
        """Restore original colors for all line pixels."""
        if canvas.image_data is None:
            return

        for x, y, old_color in self.pixels:
            if (
                0 <= x < canvas.image_data.shape[1]
                and 0 <= y < canvas.image_data.shape[0]
            ):
                canvas.image_data[y, x] = old_color

    def get_memory_size(self) -> int:
        """Calculate memory usage."""
        if self.compressed and self._compressed_data:
            return len(self._compressed_data) + 64
        # Each pixel: 3 ints (12 bytes) + list overhead
        return len(self.pixels) * 12 + 64

    def _get_compress_data(self) -> tuple[list[tuple[int, int, int]], int]:
        """Get line data for compression."""
        return (self.pixels, self.new_color)

    def _clear_uncompressed_data(self) -> None:
        """Clear pixel list after compression."""
        self.pixels = []

    def _restore_from_compressed(
        self, data: tuple[list[tuple[int, int, int]], int]
    ) -> None:
        """Restore line data from compressed format."""
        self.pixels, self.new_color = data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DrawLineCommand":
        """Create command from dictionary."""
        cmd = cls()
        cmd.timestamp = datetime.fromisoformat(data["timestamp"])
        cmd.compressed = data["compressed"]

        if data["compressed"]:
            cmd._compressed_data = bytes.fromhex(data["compressed_data"])
        else:
            cmd.pixels, cmd.new_color = data["data"]

        return cmd


@dataclass
class FloodFillCommand(UndoCommand):
    """Command for flood fill operations.

    Stores the affected region and original pixel data in a sparse format
    to minimize memory usage for large filled areas.
    """

    affected_region: tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, width, height
    old_data: Optional[np.ndarray] = None  # Only the affected region
    new_color: int = 0

    def __post_init__(self) -> None:
        """Initialize parent class after dataclass initialization."""
        super().__init__()

    def execute(self, canvas: "PixelCanvas") -> None:
        """Apply flood fill to affected region."""
        if canvas.image_data is None or self.old_data is None:
            return

        x, y, w, h = self.affected_region

        # Fill the region with new color where old data was affected
        for dy in range(h):
            for dx in range(w):
                px, py = x + dx, y + dy
                if (
                    0 <= px < canvas.image_data.shape[1]
                    and 0 <= py < canvas.image_data.shape[0]
                ):
                    # Use 255 as sentinel for "not affected"
                    if self.old_data[dy, dx] != 255:
                        canvas.image_data[py, px] = self.new_color

    def unexecute(self, canvas: "PixelCanvas") -> None:
        """Restore original data in affected region."""
        if canvas.image_data is None or self.old_data is None:
            return

        x, y, w, h = self.affected_region

        # Restore old data
        for dy in range(h):
            for dx in range(w):
                px, py = x + dx, y + dy
                if (
                    0 <= px < canvas.image_data.shape[1]
                    and 0 <= py < canvas.image_data.shape[0]
                ) and self.old_data[dy, dx] != 255:
                    canvas.image_data[py, px] = self.old_data[dy, dx]

    def get_memory_size(self) -> int:
        """Calculate memory usage."""
        if self.compressed and self._compressed_data:
            return len(self._compressed_data) + 64
        if self.old_data is not None:
            return self.old_data.nbytes + 64
        return 64

    def _get_compress_data(
        self,
    ) -> tuple[tuple[int, int, int, int], Optional[np.ndarray], int]:
        """Get flood fill data for compression."""
        return (self.affected_region, self.old_data, self.new_color)

    def _clear_uncompressed_data(self) -> None:
        """Clear numpy array after compression."""
        self.old_data = None

    def _restore_from_compressed(
        self, data: tuple[tuple[int, int, int, int], Optional[np.ndarray], int]
    ) -> None:
        """Restore flood fill data from compressed format."""
        self.affected_region, self.old_data, self.new_color = data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FloodFillCommand":
        """Create command from dictionary."""
        cmd = cls()
        cmd.timestamp = datetime.fromisoformat(data["timestamp"])
        cmd.compressed = data["compressed"]

        if data["compressed"]:
            cmd._compressed_data = bytes.fromhex(data["compressed_data"])
        else:
            region, old_data_list, new_color = data["data"]
            cmd.affected_region = tuple(region)
            if old_data_list is not None:
                # Reconstruct numpy array from list
                x, y, w, h = cmd.affected_region
                cmd.old_data = np.array(old_data_list, dtype=np.uint8).reshape((h, w))
            cmd.new_color = new_color

        return cmd


class BatchCommand(UndoCommand):
    """Groups multiple commands executed together.

    Used for operations that generate multiple individual commands,
    such as continuous drawing strokes or complex multi-step operations.
    """

    def __init__(self, commands: Optional[list[UndoCommand]] = None) -> None:
        """Initialize with optional list of commands.

        Args:
            commands: Initial list of commands to batch
        """
        super().__init__()
        self.commands: list[UndoCommand] = commands or []

    def add_command(self, command: UndoCommand) -> None:
        """Add a command to the batch.

        Args:
            command: Command to add to the batch
        """
        self.commands.append(command)

    def execute(self, canvas: "PixelCanvas") -> None:
        """Execute all commands in order."""
        for cmd in self.commands:
            if cmd.compressed:
                cmd.decompress()
            cmd.execute(canvas)

    def unexecute(self, canvas: "PixelCanvas") -> None:
        """Undo all commands in reverse order."""
        for cmd in reversed(self.commands):
            if cmd.compressed:
                cmd.decompress()
            cmd.unexecute(canvas)

    def get_memory_size(self) -> int:
        """Calculate total memory usage of all commands."""
        return sum(cmd.get_memory_size() for cmd in self.commands) + 64

    def compress(self) -> None:
        """Compress all individual commands."""
        # First compress individual commands
        for cmd in self.commands:
            if not cmd.compressed:
                cmd.compress()
        # Then compress the batch itself
        super().compress()

    def _get_compress_data(self) -> list[UndoCommand]:
        """Get command list for compression."""
        return self.commands

    def _clear_uncompressed_data(self) -> None:
        """Commands are already compressed individually."""

    def _restore_from_compressed(self, data: list[UndoCommand]) -> None:
        """Restore command list from compressed format."""
        self.commands = data

    def to_dict(self) -> dict[str, Any]:
        """Serialize batch command to dictionary."""
        base_dict = super().to_dict()
        if not self.compressed:
            base_dict["commands"] = [cmd.to_dict() for cmd in self.commands]
        return base_dict

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchCommand":
        """Create batch command from dictionary."""
        cmd = cls()
        cmd.timestamp = datetime.fromisoformat(data["timestamp"])
        cmd.compressed = data["compressed"]

        if data["compressed"]:
            cmd._compressed_data = bytes.fromhex(data["compressed_data"])
        else:
            # Reconstruct commands from their dictionaries
            cmd.commands = []
            for cmd_data in data.get("commands", []):
                cmd_type = cmd_data["type"]
                if cmd_type == "DrawPixelCommand":
                    cmd.commands.append(DrawPixelCommand.from_dict(cmd_data))
                elif cmd_type == "DrawLineCommand":
                    cmd.commands.append(DrawLineCommand.from_dict(cmd_data))
                elif cmd_type == "FloodFillCommand":
                    cmd.commands.append(FloodFillCommand.from_dict(cmd_data))
                elif cmd_type == "BatchCommand":
                    cmd.commands.append(BatchCommand.from_dict(cmd_data))

        return cmd


class UndoManager:
    """Manages undo/redo operations with automatic compression.

    Maintains a stack of commands with a current index pointer.
    Automatically compresses older commands to reduce memory usage.
    """

    def __init__(self, max_commands: int = 100, compression_age: int = 20) -> None:
        """Initialize the undo manager.

        Args:
            max_commands: Maximum number of commands to retain
            compression_age: Commands older than this many steps are compressed
        """
        self.command_stack: list[UndoCommand] = []
        self.current_index: int = -1
        self.max_commands: int = max_commands
        self.compression_age: int = compression_age

    def execute_command(self, command: UndoCommand, canvas: "PixelCanvas") -> None:
        """Execute a new command and add to history.

        Args:
            command: Command to execute
            canvas: Canvas to apply command to
        """
        # Remove any commands after current index (clear redo stack)
        if self.current_index < len(self.command_stack) - 1:
            self.command_stack = self.command_stack[: self.current_index + 1]

        # Execute the command
        command.execute(canvas)

        # Add to stack
        self.command_stack.append(command)
        self.current_index += 1

        # Enforce maximum size
        if len(self.command_stack) > self.max_commands:
            self.command_stack.pop(0)
            self.current_index -= 1

        # Compress old commands
        self._compress_old_commands()

    def undo(self, canvas: "PixelCanvas") -> bool:
        """Undo the last command.

        Args:
            canvas: Canvas to restore

        Returns:
            True if undo was successful, False if nothing to undo
        """
        if self.current_index >= 0:
            command = self.command_stack[self.current_index]

            # Decompress if needed
            if command.compressed:
                command.decompress()

            command.unexecute(canvas)
            self.current_index -= 1
            return True
        return False

    def redo(self, canvas: "PixelCanvas") -> bool:
        """Redo the next command.

        Args:
            canvas: Canvas to apply command to

        Returns:
            True if redo was successful, False if nothing to redo
        """
        if self.current_index < len(self.command_stack) - 1:
            self.current_index += 1
            command = self.command_stack[self.current_index]

            # Decompress if needed
            if command.compressed:
                command.decompress()

            command.execute(canvas)
            return True
        return False

    def _compress_old_commands(self) -> None:
        """Compress commands older than compression_age."""
        compress_before = max(0, self.current_index - self.compression_age)

        for i in range(compress_before):
            if not self.command_stack[i].compressed:
                self.command_stack[i].compress()

    def get_memory_usage(self) -> dict[str, Any]:
        """Get current memory usage statistics.

        Returns:
            Dictionary with memory usage information
        """
        total = sum(cmd.get_memory_size() for cmd in self.command_stack)
        compressed = sum(1 for cmd in self.command_stack if cmd.compressed)

        return {
            "total_bytes": total,
            "total_mb": total / (1024 * 1024),
            "command_count": len(self.command_stack),
            "compressed_count": compressed,
            "current_index": self.current_index,
            "can_undo": self.current_index >= 0,
            "can_redo": self.current_index < len(self.command_stack) - 1,
        }

    def clear(self) -> None:
        """Clear all undo/redo history."""
        self.command_stack.clear()
        self.current_index = -1

    def save_history(self) -> list[dict[str, Any]]:
        """Serialize command history for saving.

        Returns:
            List of serialized commands
        """
        return [cmd.to_dict() for cmd in self.command_stack]

    def load_history(
        self, history: list[dict[str, Any]], canvas: "PixelCanvas"
    ) -> None:
        """Load command history from serialized data.

        Args:
            history: List of serialized commands
            canvas: Canvas to validate commands against
        """
        self.clear()

        for cmd_data in history:
            cmd_type = cmd_data["type"]

            if cmd_type == "DrawPixelCommand":
                cmd = DrawPixelCommand.from_dict(cmd_data)
            elif cmd_type == "DrawLineCommand":
                cmd = DrawLineCommand.from_dict(cmd_data)
            elif cmd_type == "FloodFillCommand":
                cmd = FloodFillCommand.from_dict(cmd_data)
            elif cmd_type == "BatchCommand":
                cmd = BatchCommand.from_dict(cmd_data)
            else:
                continue  # Skip unknown command types

            self.command_stack.append(cmd)

        # Set current index to end of loaded history
        self.current_index = len(self.command_stack) - 1
