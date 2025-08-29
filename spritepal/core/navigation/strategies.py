"""
Abstract navigation strategy interfaces and base implementations.

Provides the foundation for different sprite navigation algorithms using
the Strategy pattern for clean extensibility.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .data_structures import NavigationContext, NavigationHint, SpriteLocation
    from .region_map import SpriteRegionMap

from utils.logging_config import get_logger

logger = get_logger(__name__)

class AbstractNavigationStrategy(ABC):
    """
    Abstract base class for sprite navigation strategies.

    Implementations define how to find the next most likely sprite locations
    based on current position, learned patterns, and user preferences.
    """

    def __init__(self, name: str) -> None:
        """
        Initialize strategy with a unique name.

        Args:
            name: Human-readable strategy name
        """
        self.name = name
        self.enabled = True
        self._statistics = {
            "hints_generated": 0,
            "successful_predictions": 0,
            "accuracy": 0.0
        }

    @abstractmethod
    def find_next_sprites(
        self,
        context: NavigationContext,
        region_map: SpriteRegionMap,
        rom_data: bytes | None = None
    ) -> list[NavigationHint]:
        """
        Find next sprite locations based on current context.

        Args:
            context: Current navigation context with user preferences
            region_map: Known sprite locations and patterns
            rom_data: Optional ROM data for analysis

        Returns:
            List of navigation hints sorted by relevance
        """
        ...

    @abstractmethod
    def learn_from_discovery(
        self,
        hint: NavigationHint,
        actual_location: SpriteLocation | None
    ) -> None:
        """
        Learn from the results of a navigation hint.

        Args:
            hint: The hint that was provided
            actual_location: The sprite actually found (None if hint was wrong)
        """
        ...

    @abstractmethod
    def get_confidence_estimate(self, context: NavigationContext) -> float:
        """
        Estimate how confident this strategy is in the current context.

        Args:
            context: Current navigation context

        Returns:
            Confidence level (0.0 = no confidence, 1.0 = very confident)
        """
        ...

    def get_strategy_name(self) -> str:
        """Get the strategy name."""
        return self.name

    def is_enabled(self) -> bool:
        """Check if strategy is enabled."""
        return self.enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable this strategy."""
        self.enabled = enabled
        logger.debug(f"Strategy '{self.name}' {'enabled' if enabled else 'disabled'}")

    def get_statistics(self) -> dict[str, Any]:
        """Get performance statistics for this strategy."""
        return self._statistics.copy()

    def _update_statistics(self, success: bool) -> None:
        """Update performance statistics."""
        self._statistics["hints_generated"] += 1
        if success:
            self._statistics["successful_predictions"] += 1

        # Calculate accuracy
        if self._statistics["hints_generated"] > 0:
            self._statistics["accuracy"] = (
                self._statistics["successful_predictions"] /
                self._statistics["hints_generated"]
            )

    def reset_statistics(self) -> None:
        """Reset performance statistics."""
        self._statistics = {
            "hints_generated": 0,
            "successful_predictions": 0,
            "accuracy": 0.0
        }
        logger.debug(f"Reset statistics for strategy '{self.name}'")

class AbstractPatternStrategy(AbstractNavigationStrategy):
    """
    Base class for strategies that learn and use patterns.

    Provides common functionality for pattern-based navigation strategies.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._patterns: dict[str, Any] = {}
        self._learning_enabled = True

    @abstractmethod
    def _extract_patterns(self, region_map: SpriteRegionMap) -> dict[str, Any]:
        """
        Extract patterns from the region map.

        Args:
            region_map: Current sprite location data

        Returns:
            Dictionary of extracted patterns
        """
        ...

    @abstractmethod
    def _apply_patterns(
        self,
        patterns: dict[str, Any],
        context: NavigationContext
    ) -> list[NavigationHint]:
        """
        Apply learned patterns to generate navigation hints.

        Args:
            patterns: Previously learned patterns
            context: Current navigation context

        Returns:
            List of navigation hints based on patterns
        """
        ...

    def get_patterns(self) -> dict[str, Any]:
        """Get currently learned patterns."""
        return self._patterns.copy()

    def set_learning_enabled(self, enabled: bool) -> None:
        """Enable or disable pattern learning."""
        self._learning_enabled = enabled
        logger.debug(f"Pattern learning {'enabled' if enabled else 'disabled'} for '{self.name}'")

    def is_learning_enabled(self) -> bool:
        """Check if pattern learning is enabled."""
        return self._learning_enabled

    def clear_patterns(self) -> None:
        """Clear all learned patterns."""
        self._patterns.clear()
        logger.info(f"Cleared patterns for strategy '{self.name}'")

class AbstractSimilarityStrategy(AbstractNavigationStrategy):
    """
    Base class for similarity-based navigation strategies.

    Provides common functionality for content similarity analysis.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._similarity_threshold = 0.7
        self._max_comparisons = 100

    @abstractmethod
    def _calculate_similarity(
        self,
        sprite1: SpriteLocation,
        sprite2: SpriteLocation
    ) -> float:
        """
        Calculate similarity between two sprites.

        Args:
            sprite1: First sprite for comparison
            sprite2: Second sprite for comparison

        Returns:
            Similarity score (0.0 = completely different, 1.0 = identical)
        """
        ...

    @abstractmethod
    def _find_similar_sprites(
        self,
        target_sprite: SpriteLocation,
        region_map: SpriteRegionMap
    ) -> list[tuple[SpriteLocation, float]]:
        """
        Find sprites similar to the target sprite.

        Args:
            target_sprite: Sprite to find similarities for
            region_map: Known sprite locations

        Returns:
            List of (sprite, similarity_score) tuples sorted by similarity
        """
        ...

    def get_similarity_threshold(self) -> float:
        """Get current similarity threshold."""
        return self._similarity_threshold

    def set_similarity_threshold(self, threshold: float) -> None:
        """
        Set similarity threshold.

        Args:
            threshold: Minimum similarity score (0.0 to 1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be in [0,1], got {threshold}")

        self._similarity_threshold = threshold
        logger.debug(f"Set similarity threshold to {threshold} for '{self.name}'")

    def get_max_comparisons(self) -> int:
        """Get maximum number of similarity comparisons."""
        return self._max_comparisons

    def set_max_comparisons(self, max_comparisons: int) -> None:
        """
        Set maximum number of similarity comparisons.

        Args:
            max_comparisons: Maximum comparisons per operation
        """
        if max_comparisons <= 0:
            raise ValueError(f"Max comparisons must be positive, got {max_comparisons}")

        self._max_comparisons = max_comparisons
        logger.debug(f"Set max comparisons to {max_comparisons} for '{self.name}'")

class StrategyRegistry:
    """
    Registry for managing navigation strategies.

    Provides centralized management of available strategies with
    dynamic registration and configuration.
    """

    def __init__(self) -> None:
        self._strategies: dict[str, AbstractNavigationStrategy] = {}
        self._default_strategy: str | None = None

    def register_strategy(self, strategy: AbstractNavigationStrategy) -> None:
        """
        Register a navigation strategy.

        Args:
            strategy: Strategy instance to register
        """
        name = strategy.get_strategy_name()
        if name in self._strategies:
            logger.warning(f"Overriding existing strategy '{name}'")

        self._strategies[name] = strategy
        logger.info(f"Registered navigation strategy '{name}'")

        # Set as default if no default exists
        if self._default_strategy is None:
            self._default_strategy = name

    def unregister_strategy(self, name: str) -> None:
        """
        Unregister a navigation strategy.

        Args:
            name: Name of strategy to unregister
        """
        if name not in self._strategies:
            logger.warning(f"Strategy '{name}' not found for unregistration")
            return

        del self._strategies[name]
        logger.info(f"Unregistered navigation strategy '{name}'")

        # Update default if necessary
        if self._default_strategy == name:
            self._default_strategy = next(iter(self._strategies.keys()), None)

    def get_strategy(self, name: str) -> AbstractNavigationStrategy | None:
        """
        Get a strategy by name.

        Args:
            name: Strategy name

        Returns:
            Strategy instance or None if not found
        """
        return self._strategies.get(name)

    def get_all_strategies(self) -> dict[str, AbstractNavigationStrategy]:
        """Get all registered strategies."""
        return self._strategies.copy()

    def get_enabled_strategies(self) -> dict[str, AbstractNavigationStrategy]:
        """Get only enabled strategies."""
        return {
            name: strategy
            for name, strategy in self._strategies.items()
            if strategy.is_enabled()
        }

    def get_default_strategy(self) -> AbstractNavigationStrategy | None:
        """Get the default strategy."""
        if self._default_strategy:
            return self._strategies.get(self._default_strategy)
        return None

    def set_default_strategy(self, name: str) -> None:
        """
        Set the default strategy.

        Args:
            name: Name of strategy to set as default
        """
        if name not in self._strategies:
            raise ValueError(f"Strategy '{name}' not registered")

        self._default_strategy = name
        logger.info(f"Set default strategy to '{name}'")

    def get_strategy_names(self) -> list[str]:
        """Get names of all registered strategies."""
        return list(self._strategies.keys())

    def clear_all_strategies(self) -> None:
        """Clear all registered strategies."""
        self._strategies.clear()
        self._default_strategy = None
        logger.info("Cleared all navigation strategies")

# Global strategy registry instance
_strategy_registry = StrategyRegistry()

def get_strategy_registry() -> StrategyRegistry:
    """Get the global strategy registry."""
    return _strategy_registry
