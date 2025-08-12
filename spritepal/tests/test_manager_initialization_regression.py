"""
Integration test for manager initialization regression.

This test specifically targets the original error scenario where manager
initialization failed with "Could not find exhal executable" when launched
from the exhal-master directory.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.managers import get_extraction_manager, get_injection_manager, get_session_manager
from core.managers.exceptions import ManagerError


class TestManagerInitializationRegression(unittest.TestCase):
    """Test that manager initialization works from any working directory"""

    def setUp(self):
        """Set up test environment"""
        self.original_cwd = os.getcwd()
        self.spritepal_dir = Path(__file__).parent.parent
        
        # Clean up any existing manager singletons to ensure fresh initialization
        self._cleanup_manager_singletons()

    def tearDown(self):
        """Restore original state"""
        os.chdir(self.original_cwd)
        self._cleanup_manager_singletons()

    def _cleanup_manager_singletons(self):
        """Clean up manager singletons for isolated testing"""
        # Reset manager registry if it exists
        try:
            from core.managers import _manager_registry
            _manager_registry.clear()
        except (ImportError, AttributeError):
            pass

    def test_injection_manager_from_spritepal_directory(self):
        """Test that injection manager initializes from spritepal directory"""
        os.chdir(self.spritepal_dir)
        
        try:
            manager = get_injection_manager()
            self.assertIsNotNone(manager)
        except ManagerError as e:
            self.fail(f"Manager initialization failed from spritepal directory: {e}")

    def test_injection_manager_from_parent_directory(self):
        """Test that injection manager initializes from exhal-master directory (original bug scenario)"""
        parent_dir = self.spritepal_dir.parent
        os.chdir(parent_dir)
        
        try:
            manager = get_injection_manager()
            self.assertIsNotNone(manager)
        except ManagerError as e:
            self.fail(f"Manager initialization failed from parent directory: {e}")

    def test_extraction_manager_from_different_directories(self):
        """Test that extraction manager initializes from various directories"""
        test_dirs = [
            self.spritepal_dir,
            self.spritepal_dir.parent,
        ]
        
        for test_dir in test_dirs:
            if not test_dir.exists():
                continue
                
            with self.subTest(directory=str(test_dir)):
                os.chdir(test_dir)
                self._cleanup_manager_singletons()
                
                try:
                    manager = get_extraction_manager()
                    self.assertIsNotNone(manager)
                except ManagerError as e:
                    self.fail(f"Extraction manager initialization failed from {test_dir}: {e}")

    def test_all_managers_from_temp_directory(self):
        """Test that all managers initialize from a temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            self._cleanup_manager_singletons()
            
            try:
                # Test each manager type
                session_manager = get_session_manager()
                extraction_manager = get_extraction_manager()
                injection_manager = get_injection_manager()
                
                self.assertIsNotNone(session_manager)
                self.assertIsNotNone(extraction_manager)
                self.assertIsNotNone(injection_manager)
                
            except ManagerError as e:
                self.fail(f"Manager initialization failed from temp directory: {e}")

    def test_manager_initialization_multiple_times(self):
        """Test that manager initialization is consistent across multiple calls"""
        # Test from the problematic parent directory
        parent_dir = self.spritepal_dir.parent
        os.chdir(parent_dir)
        
        managers = []
        
        # Initialize managers multiple times (simulate multiple application startups)
        for i in range(3):
            self._cleanup_manager_singletons()
            
            try:
                manager = get_injection_manager()
                managers.append(manager)
            except ManagerError as e:
                self.fail(f"Manager initialization failed on attempt {i+1}: {e}")
        
        # All initializations should succeed
        self.assertEqual(len(managers), 3)
        for manager in managers:
            self.assertIsNotNone(manager)

    def test_original_error_scenario_fixed(self):
        """Test the exact scenario that caused the original 'Could not find exhal executable' error"""
        # This reproduces the original bug scenario:
        # 1. Application launched from exhal-master directory
        # 2. Manager initialization tries to initialize HALCompressor
        # 3. HALCompressor._find_tool uses relative paths
        # 4. Relative paths fail when working directory is not spritepal
        
        exhal_master_dir = self.spritepal_dir.parent
        os.chdir(exhal_master_dir)
        
        # This specific sequence was failing before the fix
        try:
            self._cleanup_manager_singletons()
            
            # This line was throwing: 
            # "ManagerError: Failed to initialize managers: Could not find exhal executable..."
            injection_manager = get_injection_manager()
            
            # Verify the manager is functional
            self.assertIsNotNone(injection_manager)
            self.assertTrue(hasattr(injection_manager, 'start_injection'))
            
        except ManagerError as e:
            if "Could not find exhal executable" in str(e):
                self.fail(
                    "The original 'Could not find exhal executable' error has regressed! "
                    f"Fix is not working properly: {e}"
                )
            else:
                # Other manager errors might be acceptable (e.g., missing dependencies)
                # but the specific exhal detection error should be fixed
                raise

    def test_working_directory_independence(self):
        """Test that manager initialization results are independent of working directory"""
        test_dirs = [
            self.spritepal_dir,
            self.spritepal_dir.parent,
        ]
        
        managers_by_dir = {}
        
        for test_dir in test_dirs:
            if not test_dir.exists():
                continue
                
            os.chdir(test_dir)
            self._cleanup_manager_singletons()
            
            try:
                manager = get_injection_manager()
                managers_by_dir[str(test_dir)] = manager
            except ManagerError as e:
                self.fail(f"Manager failed from {test_dir}: {e}")
        
        # All managers should be successfully created
        self.assertEqual(len(managers_by_dir), len([d for d in test_dirs if d.exists()]))
        
        # All managers should be functional (have the same interface)
        for dir_path, manager in managers_by_dir.items():
            with self.subTest(directory=dir_path):
                self.assertIsNotNone(manager)
                self.assertTrue(hasattr(manager, 'start_injection'))



if __name__ == '__main__':
    unittest.main()