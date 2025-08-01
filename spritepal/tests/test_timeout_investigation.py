"""
Investigation of timeout failures in controller error handling.

This test isolates exactly where blocking occurs with invalid file paths.
"""

import sys
import time
from pathlib import Path

import pytest

# Add parent directory for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from tests.infrastructure import (
    TestApplicationFactory,
    qt_widget_test,
)

from spritepal.core.controller import ExtractionController
from spritepal.core.managers import (
    initialize_managers, 
    cleanup_managers, 
    get_extraction_manager,
)
from spritepal.ui.main_window import MainWindow


class TestTimeoutInvestigation:
    """Investigate exactly where blocking occurs with invalid file paths."""
    
    @pytest.fixture(autouse=True)
    def setup_test_infrastructure(self):
        """Set up testing infrastructure."""
        self.qt_app = TestApplicationFactory.get_application()
        
        yield
        
        cleanup_managers()
    
    def test_isolation_manager_validation_only(self):
        """Test ONLY manager validation - no controller, no worker."""
        print("=== TESTING MANAGER VALIDATION ONLY ===")
        
        initialize_managers(app_name="SpritePal-Test")
        manager = get_extraction_manager()
        
        # Test validation with invalid file paths
        invalid_params = {
            "vram_path": "/nonexistent/path.dmp", 
            "cgram_path": "/nonexistent/cgram.dmp",
            "output_base": "/invalid/output/path",
            "create_grayscale": True,
        }
        
        start_time = time.time()
        
        try:
            # This should fail QUICKLY with ValidationError
            manager.validate_extraction_params(invalid_params)
            pytest.fail("Validation should have failed with invalid file paths")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"Validation failed in {elapsed:.3f}s with: {e}")
            
            # Validation should be nearly instantaneous
            assert elapsed < 1.0, f"Validation took too long: {elapsed:.3f}s"
            assert "does not exist" in str(e), f"Should be file existence error: {e}"
    
    def test_isolation_controller_validation_step(self):
        """Test ONLY controller validation step - no worker creation."""
        print("=== TESTING CONTROLLER VALIDATION STEP ===")
        
        initialize_managers(app_name="SpritePal-Test")
        
        with qt_widget_test(MainWindow) as main_window:
            controller = ExtractionController(main_window)
            
            # Mock invalid params from main_window
            invalid_params = {
                "vram_path": "/nonexistent/path.dmp", 
                "cgram_path": "/nonexistent/cgram.dmp",
                "output_base": "/invalid/output/path",
                "create_grayscale": True,
            }
            
            # Mock the get_extraction_params method
            original_get_params = main_window.get_extraction_params
            main_window.get_extraction_params = lambda: invalid_params
            
            start_time = time.time()
            
            try:
                # This should call validation and fail fast
                controller.start_extraction()
                elapsed = time.time() - start_time
                print(f"Controller.start_extraction() completed in {elapsed:.3f}s")
                
                # Should complete quickly (either success or validation failure)  
                assert elapsed < 2.0, f"Controller took too long: {elapsed:.3f}s"
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"Controller failed in {elapsed:.3f}s with: {e}")
                assert elapsed < 2.0, f"Controller error took too long: {elapsed:.3f}s"
                
            finally:
                # Restore method
                main_window.get_extraction_params = original_get_params
    
    def test_isolation_direct_extract_from_vram(self):
        """Test calling extract_from_vram directly with invalid paths."""
        print("=== TESTING DIRECT extract_from_vram CALL ===")
        
        initialize_managers(app_name="SpritePal-Test")
        manager = get_extraction_manager()
        
        start_time = time.time()
        
        try:
            # This is where the blocking might occur
            manager.extract_from_vram(
                vram_path="/nonexistent/path.dmp",
                cgram_path="/nonexistent/cgram.dmp", 
                output_base="/invalid/output/path",
                create_grayscale=True,
            )
            pytest.fail("extract_from_vram should have failed")
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"extract_from_vram failed in {elapsed:.3f}s with: {e}")
            
            # This should also fail quickly
            assert elapsed < 5.0, f"extract_from_vram took too long: {elapsed:.3f}s"
    
    def test_isolation_worker_creation_only(self):
        """Test ONLY worker creation - no execution."""
        print("=== TESTING WORKER CREATION ONLY ===")
        
        initialize_managers(app_name="SpritePal-Test")
        
        from spritepal.core.workers.extraction import VRAMExtractionWorker
        
        invalid_params = {
            "vram_path": "/nonexistent/path.dmp",
            "cgram_path": "/nonexistent/cgram.dmp", 
            "output_base": "/invalid/output/path",
            "create_grayscale": True,
        }
        
        start_time = time.time()
        
        try:
            # Worker creation should be fast - just stores params
            worker = VRAMExtractionWorker(invalid_params)
            elapsed = time.time() - start_time
            print(f"Worker created in {elapsed:.3f}s")
            
            assert elapsed < 1.0, f"Worker creation took too long: {elapsed:.3f}s"
            assert worker is not None, "Worker should be created"
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"Worker creation failed in {elapsed:.3f}s with: {e}")
            assert elapsed < 1.0, f"Worker creation error took too long: {elapsed:.3f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])