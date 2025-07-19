"""
Sprite configuration loader for SpritePal
Loads sprite locations from external configuration files
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, Optional, List

from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SpriteConfig:
    """Configuration for a single sprite location"""
    name: str
    offset: int
    description: str
    compressed: bool
    estimated_size: int
    palette_indices: Optional[List[int]] = None


class SpriteConfigLoader:
    """Loads and manages sprite location configurations"""
    
    DEFAULT_CONFIG_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "config",
        "sprite_locations.json"
    )
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize sprite config loader.
        
        Args:
            config_path: Path to configuration file (uses default if None)
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config_data = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load sprite configuration from JSON file"""
        if not os.path.exists(self.config_path):
            logger.warning(f"Sprite config not found: {self.config_path}")
            return
        
        try:
            with open(self.config_path, 'r') as f:
                self.config_data = json.load(f)
            logger.info(f"Loaded sprite config: {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load sprite config: {e}")
    
    def get_game_sprites(self, rom_title: str, rom_checksum: int) -> Dict[str, SpriteConfig]:
        """
        Get sprite configurations for a specific game.
        
        Args:
            rom_title: ROM title from header
            rom_checksum: ROM checksum
            
        Returns:
            Dictionary of sprite name to SpriteConfig
        """
        sprites = {}
        
        if "games" not in self.config_data:
            return sprites
        
        # Find matching game
        for game_name, game_data in self.config_data["games"].items():
            # Check if title matches
            if game_name.upper() not in rom_title.upper():
                continue
            
            # Check if checksum matches any known version
            checksums = game_data.get("checksums", {})
            checksum_match = False
            
            for version, expected_checksum in checksums.items():
                # Parse checksum (could be hex string or int)
                if isinstance(expected_checksum, str):
                    expected = int(expected_checksum, 16) if expected_checksum.startswith("0x") else int(expected_checksum)
                else:
                    expected = expected_checksum
                
                if rom_checksum == expected:
                    checksum_match = True
                    logger.info(f"Matched ROM: {game_name} ({version})")
                    break
            
            if checksum_match or not checksums:  # Allow no checksum for testing
                # Load sprite configurations
                for sprite_name, sprite_data in game_data.get("sprites", {}).items():
                    offset_str = sprite_data.get("offset", "0x0")
                    offset = int(offset_str, 16) if offset_str.startswith("0x") else int(offset_str)
                    
                    sprites[sprite_name] = SpriteConfig(
                        name=sprite_name,
                        offset=offset,
                        description=sprite_data.get("description", ""),
                        compressed=sprite_data.get("compressed", True),
                        estimated_size=sprite_data.get("estimated_size", 8192),
                        palette_indices=sprite_data.get("palette_indices", None)
                    )
                
                break  # Found matching game
        
        return sprites
    
    def get_all_known_sprites(self) -> Dict[str, Dict[str, SpriteConfig]]:
        """
        Get all known sprite configurations for all games.
        
        Returns:
            Dictionary of game name to sprite configurations
        """
        all_sprites = {}
        
        if "games" not in self.config_data:
            return all_sprites
        
        for game_name, game_data in self.config_data["games"].items():
            sprites = {}
            
            for sprite_name, sprite_data in game_data.get("sprites", {}).items():
                offset_str = sprite_data.get("offset", "0x0")
                offset = int(offset_str, 16) if offset_str.startswith("0x") else int(offset_str)
                
                sprites[sprite_name] = SpriteConfig(
                    name=sprite_name,
                    offset=offset,
                    description=sprite_data.get("description", ""),
                    compressed=sprite_data.get("compressed", True),
                    estimated_size=sprite_data.get("estimated_size", 8192),
                    palette_indices=sprite_data.get("palette_indices", None)
                )
            
            all_sprites[game_name] = sprites
        
        return all_sprites
    
    def add_custom_sprite(self, game_name: str, sprite_name: str, 
                         offset: int, description: str = "", 
                         compressed: bool = True, estimated_size: int = 8192) -> None:
        """
        Add a custom sprite location (runtime only, not saved).
        
        Args:
            game_name: Name of the game
            sprite_name: Name of the sprite
            offset: ROM offset
            description: Sprite description
            compressed: Whether sprite is compressed
            estimated_size: Estimated size in bytes
        """
        if "games" not in self.config_data:
            self.config_data["games"] = {}
        
        if game_name not in self.config_data["games"]:
            self.config_data["games"][game_name] = {"sprites": {}}
        
        self.config_data["games"][game_name]["sprites"][sprite_name] = {
            "offset": f"0x{offset:X}",
            "description": description,
            "compressed": compressed,
            "estimated_size": estimated_size
        }
        
        logger.info(f"Added custom sprite: {game_name} - {sprite_name} at 0x{offset:X}")
    
    def save_config(self, output_path: Optional[str] = None) -> None:
        """
        Save current configuration to file.
        
        Args:
            output_path: Path to save to (uses original path if None)
        """
        save_path = output_path or self.config_path
        
        try:
            with open(save_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)
            logger.info(f"Saved sprite config: {save_path}")
        except Exception as e:
            logger.error(f"Failed to save sprite config: {e}")