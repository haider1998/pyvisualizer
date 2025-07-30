"""
Core domain models for the code visualization system.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
import uuid


class ElementType(Enum):
    """Types of code elements that can be analyzed."""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    PROPERTY = "property"
    CONSTRUCTOR = "constructor"
    ASYNC_METHOD = "async_method"
    STATIC_METHOD = "static_method"
    CLASS_METHOD = "class_method"
    PRIVATE_METHOD = "private_method"


class RelationshipType(Enum):
    """Types of relationships between code elements."""
    CALLS = "calls"
    INHERITS = "inherits"
    IMPORTS = "imports"
    CONTAINS = "contains"
    INSTANTIATES = "instantiates"
    DECORATES = "decorates"


@dataclass
class SourceLocation:
    """Source code location information."""
    file_path: Path
    line_number: int
    column: Optional[int] = None


@dataclass
class CodeElement:
    """Represents a code element (function, class, method, etc.)."""
    id: str
    name: str
    full_name: str
    element_type: ElementType
    module: str
    source_location: SourceLocation
    class_name: Optional[str] = None
    is_async: bool = False
    is_private: bool = False
    is_property: bool = False
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    complexity: int = 0

    def __post_init__(self):
        """Post-initialization processing."""
        if not self.id:
            self.id = str(uuid.uuid4())

        # Determine if private based on name
        if self.name.startswith('_') and not self.name.startswith('__'):
            self.is_private = True

        # Determine constructor
        if self.name in ('__init__', '__new__'):
            self.element_type = ElementType.CONSTRUCTOR


@dataclass
class Relationship:
    """Represents a relationship between code elements."""
    id: str
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    source_location: Optional[SourceLocation] = None
    metadata: Dict[str, any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class Module:
    """Represents a Python module."""
    name: str
    file_path: Path
    elements: List[CodeElement] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class CodeModel:
    """Complete model of analyzed code."""
    project_name: str
    project_path: Path
    modules: List[Module] = field(default_factory=list)
    elements: List[CodeElement] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    cycles: List[List[str]] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)

    def get_element_by_id(self, element_id: str) -> Optional[CodeElement]:
        """Get an element by its ID."""
        return next((e for e in self.elements if e.id == element_id), None)

    def get_elements_by_module(self, module_name: str) -> List[CodeElement]:
        """Get all elements in a specific module."""
        return [e for e in self.elements if e.module == module_name]

    def get_relationships_for_element(self, element_id: str) -> List[Relationship]:
        """Get all relationships involving an element."""
        return [r for r in self.relationships
                if r.source_id == element_id or r.target_id == element_id]


@dataclass
class VisualizationRequest:
    """Request for creating a visualization."""
    project_path: Path
    output_path: Path
    format: str = "html"
    include_modules: Optional[List[str]] = None
    exclude_modules: Optional[List[str]] = None
    max_depth: Optional[int] = None
    entry_point: Optional[str] = None
    max_nodes: int = 150
    show_private: bool = True
    show_imports: bool = True


@dataclass
class VisualizationResult:
    """Result of visualization generation."""
    success: bool
    output_path: Optional[Path] = None
    error_message: Optional[str] = None
    metrics: Dict[str, any] = field(default_factory=dict)
