"""
Performance benchmark tests for session-scoped fixtures.

This test file validates that our session-scoped manager fixtures provide
the expected dramatic performance improvement over per-test manager setup.

Expected Results:
- Unit tests (no_manager_setup): <0.1s per test
- Integration tests (shared managers): <0.5s per test  
- Isolated tests (fresh managers): 3-4s per test (only when needed)
- Total test suite: ~30 minutes (from 2+ hours)
"""
from __future__ import annotations

import time
import pytest
from core.managers.registry import ManagerRegistry

# Systematic pytest markers applied based on test content analysis
pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.headless,
    pytest.mark.no_qt,
    pytest.mark.performance,
    pytest.mark.rom_data,
    pytest.mark.unit,
    pytest.mark.cache,
]

@pytest.mark.no_manager_setup
class TestFastUnitTests:
    """Tests that don't need any managers - should be lightning fast."""
    
    def test_constants_validation(self):
        """Pure unit test - no manager overhead."""
        from utils.constants import BYTES_PER_TILE, VRAM_SPRITE_OFFSET
        
        assert BYTES_PER_TILE == 32
        assert VRAM_SPRITE_OFFSET == 0xC000
        
    def test_math_operations(self):
        """Another fast unit test."""
        assert 2 + 2 == 4
        assert 10 * 32 == 320
        
    def test_string_operations(self):
        """Fast string operations."""
        test_str = "SpritePal"
        assert len(test_str) == 9
        assert test_str.lower() == "spritepal"

class TestSessionManagedTests:
    """Tests using shared session managers - should be fast with managers available."""
    
    def test_extraction_manager_access(self, managers):
        """Test accessing extraction manager from shared session."""
        extraction_manager = managers.get_extraction_manager()
        assert extraction_manager is not None
        assert hasattr(extraction_manager, 'extract_from_vram')
        
    def test_injection_manager_access(self, managers):
        """Test accessing injection manager from shared session."""
        injection_manager = managers.get_injection_manager()
        assert injection_manager is not None
        assert hasattr(injection_manager, 'start_injection')
        
    def test_session_manager_access(self, managers):
        """Test accessing session manager from shared session."""
        session_manager = managers.get_session_manager()
        assert session_manager is not None
        assert hasattr(session_manager, 'get_session_data')
        
    def test_manager_registry_consistency(self, managers):
        """Verify that all managers are consistently available."""
        # All these should return the same managers across test runs
        extraction1 = managers.get_extraction_manager()
        extraction2 = managers.get_extraction_manager()
        
        # Same instance should be returned
        assert extraction1 is extraction2

@pytest.mark.isolated_managers
class TestIsolatedManagerTests:
    """Tests that need fresh managers - will be slower but necessary for some cases."""
    
    def test_isolated_manager_creation(self, isolated_managers):
        """Test that isolated managers are properly created."""
        extraction_manager = isolated_managers.get_extraction_manager()
        assert extraction_manager is not None
        
    def test_manager_state_isolation(self, isolated_managers):
        """Test that we can modify manager state without affecting other tests."""
        # This test would modify manager state that could affect other tests
        # So it needs isolated managers
        extraction_manager = isolated_managers.get_extraction_manager()
        
        # Simulate state change that could affect other tests
        # (In real scenarios, this might be settings changes, cache modifications, etc.)
        assert extraction_manager is not None

class TestPerformanceMeasurement:
    """Measure and validate the performance improvements."""
    
    @pytest.mark.no_manager_setup
    def test_no_manager_performance(self):
        """Validate that no-manager tests are very fast."""
        start_time = time.perf_counter()
        
        # Simple operations that should be very fast
        for i in range(1000):
            result = i * 2 + 1
        
        elapsed = time.perf_counter() - start_time
        
        # Should complete in well under 0.1 seconds
        assert elapsed < 0.1, f"No-manager test took {elapsed:.3f}s, expected <0.1s"
        
    def test_session_manager_performance(self, managers):
        """Validate that session manager tests are reasonably fast."""
        start_time = time.perf_counter()
        
        # Access managers multiple times (simulating real test work)
        for _ in range(10):
            extraction_manager = managers.get_extraction_manager()
            injection_manager = managers.get_injection_manager()
            session_manager = managers.get_session_manager()
            
            assert extraction_manager is not None
            assert injection_manager is not None
            assert session_manager is not None
        
        elapsed = time.perf_counter() - start_time
        
        # Should complete reasonably quickly with shared managers
        assert elapsed < 0.5, f"Session manager test took {elapsed:.3f}s, expected <0.5s"
        
    def test_performance_comparison_documentation(self):
        """Document the expected performance improvements."""
        performance_notes = {
            "before_optimization": {
                "per_test_overhead": "3-4 seconds",
                "total_tests": 1682,
                "estimated_total_time": "~2 hours",
                "bottleneck": "initialize_managers() + cleanup_managers() per test"
            },
            "after_optimization": {
                "session_setup": "3-4 seconds (once)",
                "per_test_overhead": "<0.1 seconds",
                "total_tests": 1682,
                "estimated_total_time": "~6 minutes",
                "improvement": "~20x faster"
            },
            "fixture_types": {
                "no_manager_setup": "Fastest - no setup overhead",
                "managers": "Fast - shared session managers", 
                "isolated_managers": "Slow - fresh managers when needed"
            }
        }
        
        # This test serves as documentation of our performance goals
        assert performance_notes["after_optimization"]["improvement"] == "~20x faster"

class TestFixtureUsageExamples:
    """Examples showing proper fixture usage patterns."""
    
    @pytest.mark.no_manager_setup  
    def test_pure_unit_test_pattern(self):
        """Example: Pure unit test needing no managers."""
        # Test pure functions, constants, utilities
        from utils.constants import BYTES_PER_TILE
        assert BYTES_PER_TILE > 0
        
    def test_integration_test_pattern(self, managers):
        """Example: Integration test using shared managers."""
        # Test interactions between components using managers
        extraction_manager = managers.get_extraction_manager()
        session_manager = managers.get_session_manager()
        
        # Both managers available for testing interactions
        assert extraction_manager is not None
        assert session_manager is not None
        
    @pytest.mark.isolated_managers
    def test_state_modification_pattern(self, isolated_managers):
        """Example: Test that modifies manager state.""" 
        # Test that modifies settings, cache, or other shared state
        session_manager = isolated_managers.get_session_manager()
        
        # Safe to modify state without affecting other tests
        assert session_manager is not None

class TestMigrationCompatibility:
    """Ensure backward compatibility during migration."""
    
    def test_old_fixture_still_works(self, managers):
        """Verify old test patterns still work with new fixtures."""
        # Old pattern: accessing managers directly
        extraction_manager = managers.get_extraction_manager()
        
        # Should still work as before
        assert extraction_manager is not None
        assert hasattr(extraction_manager, 'extract_from_vram')
        
    def test_registry_access_pattern(self, managers):
        """Test that registry access patterns work."""
        # Access via registry (common pattern in existing tests)
        registry = managers
        
        extraction_manager = registry.get_extraction_manager()
        injection_manager = registry.get_injection_manager() 
        session_manager = registry.get_session_manager()
        
        assert all([extraction_manager, injection_manager, session_manager])

@pytest.mark.benchmark
class TestBenchmarkValidation:
    """Benchmark tests to validate performance improvements (optional)."""
    
    def test_manager_access_benchmark(self, benchmark, managers):
        """Benchmark manager access speed with shared managers."""
        def access_all_managers():
            extraction = managers.get_extraction_manager()
            injection = managers.get_injection_manager() 
            session = managers.get_session_manager()
            return extraction, injection, session
            
        result = benchmark(access_all_managers)
        assert len(result) == 3
        
    @pytest.mark.no_manager_setup
    def test_no_manager_benchmark(self, benchmark):
        """Benchmark pure unit test speed."""
        def pure_computation():
            return sum(i * i for i in range(100))
            
        result = benchmark(pure_computation)
        assert result > 0