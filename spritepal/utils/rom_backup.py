"""
ROM backup utilities for SpritePal
"""

import os
import shutil
from datetime import datetime, timezone

from spritepal.utils.logging_config import get_logger
from spritepal.utils.rom_exceptions import ROMBackupError

logger = get_logger(__name__)


class ROMBackupManager:
    """Manages ROM backups before modifications"""

    # Maximum number of backups to keep per ROM
    MAX_BACKUPS_PER_ROM = 10

    @classmethod
    def create_backup(cls, rom_path: str, backup_dir: str | None = None) -> str:
        """
        Create a timestamped backup of ROM file.

        Args:
            rom_path: Path to ROM file to backup
            backup_dir: Directory for backups (default: same as ROM)

        Returns:
            Path to backup file

        Raises:
            ROMBackupError: If backup creation fails
        """
        if not os.path.exists(rom_path):
            raise ROMBackupError(f"ROM file not found: {rom_path}")

        # Determine backup directory
        if backup_dir is None:
            backup_dir = os.path.dirname(rom_path)

        # Create backup subdirectory
        backup_subdir = os.path.join(backup_dir, "spritepal_backups")
        os.makedirs(backup_subdir, exist_ok=True)

        # Generate backup filename
        rom_name = os.path.basename(rom_path)
        rom_base, rom_ext = os.path.splitext(rom_name)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"{rom_base}_backup_{timestamp}{rom_ext}"
        backup_path = os.path.join(backup_subdir, backup_name)

        try:
            # Copy ROM to backup
            shutil.copy2(rom_path, backup_path)
            logger.info(f"Created backup: {backup_name}")

            # Clean up old backups
            cls._cleanup_old_backups(backup_subdir, rom_base, rom_ext)

            return backup_path

        except Exception as e:
            raise ROMBackupError(f"Failed to create backup: {e}") from e

    @classmethod
    def _cleanup_old_backups(cls, backup_dir: str, rom_base: str, rom_ext: str) -> None:
        """Remove old backups keeping only the most recent ones"""
        try:
            # Find all backups for this ROM
            backups = []

            for file in os.listdir(backup_dir):
                if file.startswith(f"{rom_base}_backup_") and file.endswith(rom_ext):
                    file_path = os.path.join(backup_dir, file)
                    mtime = os.path.getmtime(file_path)
                    backups.append((mtime, file_path))

            # Sort by modification time (newest first)
            backups.sort(reverse=True)

            # Remove old backups
            for _, backup_path in backups[cls.MAX_BACKUPS_PER_ROM :]:
                os.remove(backup_path)
                logger.info(f"Removed old backup: {os.path.basename(backup_path)}")

        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")

    @classmethod
    def get_latest_backup(
        cls, rom_path: str, backup_dir: str | None = None
    ) -> str | None:
        """
        Get the most recent backup for a ROM.

        Returns:
            Path to latest backup or None if no backups exist
        """
        if backup_dir is None:
            backup_dir = os.path.dirname(rom_path)

        backup_subdir = os.path.join(backup_dir, "spritepal_backups")
        if not os.path.exists(backup_subdir):
            return None

        rom_name = os.path.basename(rom_path)
        rom_base, rom_ext = os.path.splitext(rom_name)

        latest_backup = None
        latest_mtime = 0

        try:
            for file in os.listdir(backup_subdir):
                if file.startswith(f"{rom_base}_backup_") and file.endswith(rom_ext):
                    file_path = os.path.join(backup_subdir, file)
                    mtime = os.path.getmtime(file_path)
                    if mtime > latest_mtime:
                        latest_mtime = mtime
                        latest_backup = file_path
        except Exception:
            pass

        return latest_backup

    @classmethod
    def restore_backup(cls, backup_path: str, target_path: str) -> None:
        """
        Restore a backup to target location.

        Args:
            backup_path: Path to backup file
            target_path: Path to restore to

        Raises:
            ROMBackupError: If restore fails
        """
        if not os.path.exists(backup_path):
            raise ROMBackupError(f"Backup file not found: {backup_path}")

        try:
            shutil.copy2(backup_path, target_path)
            logger.info(f"Restored backup to: {target_path}")
        except Exception as e:
            raise ROMBackupError(f"Failed to restore backup: {e}") from e

    @classmethod
    def list_backups(
        cls, rom_path: str, backup_dir: str | None = None
    ) -> list[dict]:
        """
        List all backups for a ROM.

        Returns:
            List of backup info dicts with keys: path, size, timestamp
        """
        if backup_dir is None:
            backup_dir = os.path.dirname(rom_path)

        backup_subdir = os.path.join(backup_dir, "spritepal_backups")
        if not os.path.exists(backup_subdir):
            return []

        rom_name = os.path.basename(rom_path)
        rom_base, rom_ext = os.path.splitext(rom_name)

        backups = []

        try:
            for file in os.listdir(backup_subdir):
                if file.startswith(f"{rom_base}_backup_") and file.endswith(rom_ext):
                    file_path = os.path.join(backup_subdir, file)
                    stat = os.stat(file_path)

                    # Extract timestamp from filename
                    timestamp_str = file[len(f"{rom_base}_backup_") : -len(rom_ext)]

                    backups.append(
                        {
                            "path": file_path,
                            "filename": file,
                            "size": stat.st_size,
                            "mtime": stat.st_mtime,
                            "timestamp_str": timestamp_str,
                            "date": datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                        }
                    )
        except Exception as e:
            logger.warning(f"Failed to list backups: {e}")

        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x["mtime"], reverse=True)

        return backups
