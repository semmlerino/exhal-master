#!/usr/bin/env python3
"""
Base model class with observable properties
Provides change notification support for MVC pattern
"""

from PyQt6.QtCore import QObject, pyqtSignal


class ObservableProperty:
    """Property descriptor that emits signals on change"""
    
    def __init__(self, initial_value=None):
        self.value = initial_value
        self.name = None
    
    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f'_{name}'
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, self.value)
    
    def __set__(self, obj, value):
        old_value = getattr(obj, self.private_name, self.value)
        if old_value != value:
            setattr(obj, self.private_name, value)
            # Emit the property_changed signal
            signal_name = f'{self.name}_changed'
            if hasattr(obj, signal_name):
                signal = getattr(obj, signal_name)
                signal.emit(value)
            # Also emit general changed signal
            if hasattr(obj, 'property_changed'):
                obj.property_changed.emit(self.name, value)


class BaseModel(QObject):
    """Base class for observable models"""
    
    # General property change signal
    property_changed = pyqtSignal(str, object)  # property_name, new_value
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def get_property(self, name):
        """Get a property value by name"""
        return getattr(self, name, None)
    
    def set_property(self, name, value):
        """Set a property value by name"""
        if hasattr(self, name):
            setattr(self, name, value)
    
    def to_dict(self):
        """Convert model to dictionary (for serialization)"""
        result = {}
        for attr_name in dir(self):
            attr = getattr(self.__class__, attr_name, None)
            if isinstance(attr, ObservableProperty):
                result[attr_name] = getattr(self, attr_name)
        return result
    
    def from_dict(self, data):
        """Load model from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)