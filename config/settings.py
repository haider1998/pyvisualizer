"""
Configuration management for PyVisualizer.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ParsingConfig:
    """Configuration for code parsing."""
    max_file_size_mb: int = 10
    timeout_seconds: int = 30
    parallel_workers: int = 4
    skip_syntax_errors: bool = True
    encoding_fallbacks: List[str] = None

    def __post_init__(self):
        if self.encoding_fallbacks is None:
            self.encoding_fallbacks = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']


@dataclass
class AnalysisConfig:
    """Configuration for code analysis."""
    max_nodes: int = 150
    max_depth: Optional[int] = None
    include_private: bool = True
    include_imports: bool = True
    detect_cycles: bool = True
    complexity_threshold: int = 10


@dataclass
class VisualizationConfig:
    """Configuration for visualization generation."""
    default_format: str = "html"
    include_styles: bool = True
    interactive: bool = True
    show_metrics: bool = True
    theme: str = "light"  # light, dark, auto


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[Path] = None
    max_file_size_mb: int = 100
    backup_count: int = 5


@dataclass
class Settings:
    """Main configuration class."""
    parsing: ParsingConfig = None
    analysis: AnalysisConfig = None
    visualization: VisualizationConfig = None
    logging: LoggingConfig = None

    def __post_init__(self):
        if self.parsing is None:
            self.parsing = ParsingConfig()
        if self.analysis is None:
            self.analysis = AnalysisConfig()
        if self.visualization is None:
            self.visualization = VisualizationConfig()
        if self.logging is None:
            self.logging = LoggingConfig()

    @classmethod
    def from_env(cls) -> 'Settings':
        """Create settings from environment variables."""
        return cls(
            parsing=ParsingConfig(
                max_file_size_mb=int(os.getenv('PV_MAX_FILE_SIZE_MB', 10)),
                timeout_seconds=int(os.getenv('PV_TIMEOUT_SECONDS', 30)),
                parallel_workers=int(os.getenv('PV_PARALLEL_WORKERS', 4)),
                skip_syntax_errors=os.getenv('PV_SKIP_SYNTAX_ERRORS', 'true').lower() == 'true'
            ),
            analysis=AnalysisConfig(
                max_nodes=int(os.getenv('PV_MAX_NODES', 150)),
                max_depth=int(os.getenv('PV_MAX_DEPTH')) if os.getenv('PV_MAX_DEPTH') else None,
                include_private=os.getenv('PV_INCLUDE_PRIVATE', 'true').lower() == 'true',
                include_imports=os.getenv('PV_INCLUDE_IMPORTS', 'true').lower() == 'true',
                detect_cycles=os.getenv('PV_DETECT_CYCLES', 'true').lower() == 'true'
            ),
            visualization=VisualizationConfig(
                default_format=os.getenv('PV_DEFAULT_FORMAT', 'html'),
                include_styles=os.getenv('PV_INCLUDE_STYLES', 'true').lower() == 'true',
                interactive=os.getenv('PV_INTERACTIVE', 'true').lower() == 'true',
                show_metrics=os.getenv('PV_SHOW_METRICS', 'true').lower() == 'true',
                theme=os.getenv('PV_THEME', 'light')
            ),
            logging=LoggingConfig(
                level=os.getenv('PV_LOG_LEVEL', 'INFO'),
                file_path=Path(os.getenv('PV_LOG_FILE')) if os.getenv('PV_LOG_FILE') else None
            )
        )


# Global settings instance
settings = Settings.from_env()
