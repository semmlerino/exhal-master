#!/usr/bin/env python3
"""
Base controller class for MVC pattern
Provides common functionality for all controllers
"""

from PyQt6.QtCore import QObject


class BaseController(QObject):
    """Base class for controllers in MVC pattern"""
    
    def __init__(self, model=None, view=None, parent=None):
        super().__init__(parent)
        self._model = model
        self._view = view
        
        if model and view:
            self.connect_signals()
    
    def set_model(self, model):
        """Set the model for this controller"""
        self._model = model
        if self._model and self._view:
            self.connect_signals()
    
    def set_view(self, view):
        """Set the view for this controller"""
        self._view = view
        if self._model and self._view:
            self.connect_signals()
    
    def connect_signals(self):
        """Connect signals between model and view (to be overridden)"""
        pass
    
    @property
    def model(self):
        """Get the associated model"""
        return self._model
    
    @property
    def view(self):
        """Get the associated view"""
        return self._view