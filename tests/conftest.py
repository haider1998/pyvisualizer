"""PyVisualizer test configuration."""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def sample_project_path():
    """Return path to the sample project."""
    return Path(__file__).parent.parent / "examples" / "sample_project"


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_python_code():
    """Simple Python code for testing."""
    return '''
class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, a, b):
        self.result = a + b
        return self.result
    
    def subtract(self, a, b):
        self.result = a - b
        return self.result


def main():
    calc = Calculator()
    calc.add(1, 2)
    calc.subtract(5, 3)


if __name__ == "__main__":
    main()
'''


@pytest.fixture
def temp_python_file(temp_output_dir, simple_python_code):
    """Create a temporary Python file for testing."""
    file_path = temp_output_dir / "test_module.py"
    file_path.write_text(simple_python_code)
    return file_path


@pytest.fixture
def temp_python_package(temp_output_dir, simple_python_code):
    """Create a temporary Python package for testing."""
    package_dir = temp_output_dir / "test_package"
    package_dir.mkdir()
    
    # Create __init__.py
    (package_dir / "__init__.py").write_text("")
    
    # Create main module
    (package_dir / "main.py").write_text(simple_python_code)
    
    # Create another module
    (package_dir / "utils.py").write_text('''
def helper_function():
    return "helper"

class UtilClass:
    def util_method(self):
        return helper_function()
''')
    
    return package_dir
