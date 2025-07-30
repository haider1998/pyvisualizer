"""
File utilities for PyVisualizer.
"""

import os
import re
from pathlib import Path
from typing import List, Optional

from ..core.interfaces import IFileUtils
from ..core.exceptions import FileNotFoundError


class FileUtils(IFileUtils):
    """Utilities for file operations."""

    # Common patterns to exclude
    DEFAULT_EXCLUDE_PATTERNS = [
        r'\.git', r'\.svn', r'\.hg',  # Version control
        r'__pycache__', r'\.pytest_cache', r'\.mypy_cache',  # Python caches
        r'venv', r'env', r'virtualenv', r'\.venv',  # Virtual environments
        r'node_modules', r'bower_components',  # JS dependencies
        r'\.egg-info', r'\.eggs', r'dist', r'build',  # Python packaging
        r'\.tox', r'\.coverage', r'htmlcov',  # Testing
        r'site-packages',  # Installed packages
    ]

    def __init__(self, exclude_patterns: Optional[List[str]] = None):
        """Initialize with optional exclude patterns."""
        self.exclude_patterns = exclude_patterns or self.DEFAULT_EXCLUDE_PATTERNS
        self.exclude_regex = re.compile('|'.join(f'({pattern})' for pattern in self.exclude_patterns))

    def find_python_files(self, path: Path, exclude_patterns: Optional[List[str]] = None) -> List[Path]:
        """Find all Python files in a directory or return single file."""
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        python_files = []

        if path.is_file():
            if self.is_python_file(path):
                python_files = [path]
        elif path.is_dir():
            python_files = self._find_python_files_recursive(path, exclude_patterns)

        return sorted(python_files)

    def _find_python_files_recursive(self, directory: Path, exclude_patterns: Optional[List[str]]) -> List[Path]:
        """Recursively find Python files in a directory."""
        python_files = []

        # Use custom exclude patterns if provided
        exclude_regex = self.exclude_regex
        if exclude_patterns:
            combined_patterns = self.exclude_patterns + exclude_patterns
            exclude_regex = re.compile('|'.join(f'({pattern})' for pattern in combined_patterns))

        for root, dirs, files in os.walk(directory):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not exclude_regex.search(d)]

            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file

                    # Check if file path contains excluded patterns
                    if not exclude_regex.search(str(file_path)):
                        python_files.append(file_path)

        return python_files

    def is_python_file(self, path: Path) -> bool:
        """Check if a file is a Python file."""
        return path.suffix == '.py' and path.is_file()

    def get_module_name(self, file_path: Path, project_root: Path) -> str:
        """Get the module name from a file path relative to project root."""
        try:
            rel_path = file_path.relative_to(project_root)
        except ValueError:
            # File is not under project root
            rel_path = file_path

        # Convert path to module name
        module_parts = []
        current_path = rel_path.parent

        # Add file name without extension
        module_parts.insert(0, rel_path.stem)

        # Add package hierarchy
        while current_path and str(current_path) != '.':
            # Check for __init__.py to determine package boundaries
            init_path = project_root / current_path / '__init__.py'
            if init_path.exists():
                module_parts.insert(0, current_path.name)
            else:
                # Not a package, stop here
                break
            current_path = current_path.parent

        return '.'.join(module_parts)

    def read_file_safely(self, file_path: Path, encodings: Optional[List[str]] = None) -> Optional[str]:
        """Read a file with fallback encodings."""
        if encodings is None:
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']

        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
            except Exception:
                return None

        return None
