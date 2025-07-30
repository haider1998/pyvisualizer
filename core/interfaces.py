"""
Abstract interfaces for the code visualization system.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from .models import CodeModel, VisualizationRequest, VisualizationResult


class ICodeParser(ABC):
    """Interface for parsing code files."""

    @abstractmethod
    def parse_file(self, file_path: Path) -> Optional[any]:
        """Parse a single code file."""
        pass

    @abstractmethod
    def parse_project(self, project_path: Path) -> List[any]:
        """Parse all files in a project."""
        pass


class ICodeAnalyzer(ABC):
    """Interface for analyzing code and building models."""

    @abstractmethod
    def analyze_project(self, project_path: Path) -> CodeModel:
        """Analyze a project and return a code model."""
        pass


class IVisualizer(ABC):
    """Interface for generating visualizations."""

    @abstractmethod
    def create_visualization(self, model: CodeModel, request: VisualizationRequest) -> VisualizationResult:
        """Create a visualization from a code model."""
        pass

    @abstractmethod
    def supports_format(self, format: str) -> bool:
        """Check if this visualizer supports the given format."""
        pass


class ICycleDetector(ABC):
    """Interface for detecting cycles in code relationships."""

    @abstractmethod
    def detect_cycles(self, model: CodeModel) -> List[List[str]]:
        """Detect cycles in the code model."""
        pass


class IFileUtils(ABC):
    """Interface for file operations."""

    @abstractmethod
    def find_python_files(self, path: Path, exclude_patterns: Optional[List[str]] = None) -> List[Path]:
        """Find Python files in a directory."""
        pass

    @abstractmethod
    def is_python_file(self, path: Path) -> bool:
        """Check if a file is a Python file."""
        pass
