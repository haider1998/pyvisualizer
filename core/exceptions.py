"""
Custom exceptions for the code visualization system.
"""


class PyVisualizerError(Exception):
    """Base exception for PyVisualizer."""
    pass


class ParseError(PyVisualizerError):
    """Error during code parsing."""

    def __init__(self, file_path: str, message: str, original_error: Exception = None):
        self.file_path = file_path
        self.original_error = original_error
        super().__init__(f"Error parsing {file_path}: {message}")


class AnalysisError(PyVisualizerError):
    """Error during code analysis."""
    pass


class VisualizationError(PyVisualizerError):
    """Error during visualization generation."""
    pass


class ConfigurationError(PyVisualizerError):
    """Error in configuration."""
    pass


class FileNotFoundError(PyVisualizerError):
    """File or directory not found."""
    pass


class UnsupportedFormatError(VisualizationError):
    """Unsupported visualization format."""
    pass
