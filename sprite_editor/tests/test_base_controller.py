#!/usr/bin/env python3
"""
Test suite for BaseController
"""

from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QObject

from sprite_editor.controllers.base_controller import BaseController


class TestController(BaseController):
    """Test implementation of BaseController with signal connection tracking"""

    def __init__(self, model=None, view=None, parent=None):
        self.connect_signals_called = 0
        super().__init__(model, view, parent)

    def connect_signals(self):
        """Track when connect_signals is called"""
        self.connect_signals_called += 1


class TestBaseController:
    """Test BaseController functionality"""

    def test_init_with_model_and_view(self):
        """Test initialization with both model and view"""
        model = MagicMock()
        view = MagicMock()

        controller = TestController(model, view)

        assert controller.model == model
        assert controller.view == view
        assert controller.connect_signals_called == 1

    def test_init_without_model(self):
        """Test initialization without model"""
        view = MagicMock()

        controller = TestController(None, view)

        assert controller.model is None
        assert controller.view == view
        assert controller.connect_signals_called == 0

    def test_init_without_view(self):
        """Test initialization without view"""
        model = MagicMock()

        controller = TestController(model, None)

        assert controller.model == model
        assert controller.view is None
        assert controller.connect_signals_called == 0

    def test_init_without_model_and_view(self):
        """Test initialization without model and view"""
        controller = TestController()

        assert controller.model is None
        assert controller.view is None
        assert controller.connect_signals_called == 0

    def test_set_model_with_existing_view(self):
        """Test setting model when view already exists"""
        view = MagicMock()
        controller = TestController(None, view)
        assert controller.connect_signals_called == 0

        model = MagicMock()
        controller.set_model(model)

        assert controller.model == model
        assert controller.connect_signals_called == 1

    def test_set_model_without_view(self):
        """Test setting model when view doesn't exist"""
        controller = TestController()
        assert controller.connect_signals_called == 0

        model = MagicMock()
        controller.set_model(model)

        assert controller.model == model
        assert controller.connect_signals_called == 0

    def test_set_view_with_existing_model(self):
        """Test setting view when model already exists"""
        model = MagicMock()
        controller = TestController(model, None)
        assert controller.connect_signals_called == 0

        view = MagicMock()
        controller.set_view(view)

        assert controller.view == view
        assert controller.connect_signals_called == 1

    def test_set_view_without_model(self):
        """Test setting view when model doesn't exist"""
        controller = TestController()
        assert controller.connect_signals_called == 0

        view = MagicMock()
        controller.set_view(view)

        assert controller.view == view
        assert controller.connect_signals_called == 0

    def test_connect_signals_base_implementation(self):
        """Test that base connect_signals does nothing"""
        controller = BaseController()
        # Should not raise any exception
        controller.connect_signals()

    def test_inheritance_from_qobject(self):
        """Test that BaseController inherits from QObject"""
        controller = BaseController()
        assert isinstance(controller, QObject)

    def test_properties(self):
        """Test model and view properties"""
        model = MagicMock()
        view = MagicMock()
        controller = BaseController(model, view)

        assert controller.model == model
        assert controller.view == view

        # Test property setters don't exist (read-only properties)
        with pytest.raises(AttributeError):
            controller.model = MagicMock()

        with pytest.raises(AttributeError):
            controller.view = MagicMock()

    def test_parent_parameter(self):
        """Test parent parameter is passed to QObject"""
        parent = QObject()
        controller = BaseController(parent=parent)

        assert controller.parent() == parent
