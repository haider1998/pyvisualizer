"""Tests for the analyzer module."""

import ast
import pytest

from pyvisualizer.core.analyzer import ImportInfo, ImportCollector, ModuleAnalyzer


class TestImportInfo:
    """Tests for ImportInfo named tuple."""
    
    def test_create_import_info(self):
        info = ImportInfo(module="os", name="path", alias="path")
        assert info.module == "os"
        assert info.name == "path"
        assert info.alias == "path"
        assert info.is_star is False
    
    def test_create_star_import(self):
        info = ImportInfo(module="os", name="*", alias="*", is_star=True)
        assert info.is_star is True


class TestImportCollector:
    """Tests for ImportCollector class."""
    
    def test_simple_import(self):
        code = "import os"
        tree = ast.parse(code)
        collector = ImportCollector("test_module", "/test")
        collector.visit(tree)
        
        assert "os" in collector.import_map
        assert "os" in collector.direct_imports
    
    def test_import_with_alias(self):
        code = "import numpy as np"
        tree = ast.parse(code)
        collector = ImportCollector("test_module", "/test")
        collector.visit(tree)
        
        assert "np" in collector.import_map
        assert collector.import_map["np"] == "numpy"
    
    def test_from_import(self):
        code = "from os import path"
        tree = ast.parse(code)
        collector = ImportCollector("test_module", "/test")
        collector.visit(tree)
        
        assert "path" in collector.import_map
        assert collector.import_map["path"] == "os.path"
    
    def test_from_import_with_alias(self):
        code = "from os.path import join as pjoin"
        tree = ast.parse(code)
        collector = ImportCollector("test_module", "/test")
        collector.visit(tree)
        
        assert "pjoin" in collector.import_map
        assert collector.import_map["pjoin"] == "os.path.join"
    
    def test_star_import(self):
        code = "from os import *"
        tree = ast.parse(code)
        collector = ImportCollector("test_module", "/test")
        collector.visit(tree)
        
        assert "os" in collector.star_imports


class TestModuleAnalyzer:
    """Tests for ModuleAnalyzer class."""
    
    def test_analyze_function(self):
        code = '''
def hello():
    print("Hello")
'''
        tree = ast.parse(code)
        analyzer = ModuleAnalyzer("test_module", "/test/module.py", tree, "/test")
        
        assert "test_module.hello" in analyzer.functions
        func_info = analyzer.functions["test_module.hello"]
        assert func_info["name"] == "hello"
        assert func_info["class"] is None
    
    def test_analyze_async_function(self):
        code = '''
async def fetch_data():
    pass
'''
        tree = ast.parse(code)
        analyzer = ModuleAnalyzer("test_module", "/test/module.py", tree, "/test")
        
        assert "test_module.fetch_data" in analyzer.functions
        func_info = analyzer.functions["test_module.fetch_data"]
        assert func_info["is_async"] is True
    
    def test_analyze_class(self):
        code = '''
class MyClass:
    def method(self):
        pass
'''
        tree = ast.parse(code)
        analyzer = ModuleAnalyzer("test_module", "/test/module.py", tree, "/test")
        
        assert "test_module.MyClass" in analyzer.classes
        class_info = analyzer.classes["test_module.MyClass"]
        assert class_info["name"] == "MyClass"
        assert "method" in class_info["methods"]
    
    def test_analyze_class_with_inheritance(self):
        code = '''
class Parent:
    pass

class Child(Parent):
    pass
'''
        tree = ast.parse(code)
        analyzer = ModuleAnalyzer("test_module", "/test/module.py", tree, "/test")
        
        child_info = analyzer.classes["test_module.Child"]
        assert "Parent" in child_info["bases"]
    
    def test_analyze_property_decorator(self):
        code = '''
class MyClass:
    @property
    def value(self):
        return self._value
'''
        tree = ast.parse(code)
        analyzer = ModuleAnalyzer("test_module", "/test/module.py", tree, "/test")
        
        method_info = analyzer.classes["test_module.MyClass"]["methods"]["value"]
        assert method_info["is_property"] is True
    
    def test_analyze_type_annotations(self):
        code = '''
def add(a: int, b: int) -> int:
    return a + b
'''
        tree = ast.parse(code)
        analyzer = ModuleAnalyzer("test_module", "/test/module.py", tree, "/test")
        
        func_info = analyzer.functions["test_module.add"]
        assert func_info["return_annotation"] is not None
        assert "a" in func_info["arg_types"]
        assert "b" in func_info["arg_types"]
