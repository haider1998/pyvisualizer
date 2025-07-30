"""
Extract function calls and relationships from AST.
"""

import ast
from typing import Dict, List, Optional, Set, Tuple

from ..core.models import CodeElement, Relationship, RelationshipType, SourceLocation
from ..utils.logging import logger


class CallExtractor(ast.NodeVisitor):
    """Extracts function calls and relationships from AST."""

    def __init__(self, module_name: str, file_path, elements: List[CodeElement]):
        self.module_name = module_name
        self.file_path = file_path
        self.elements = elements
        self.relationships: List[Relationship] = []

        # Build lookup maps for faster access
        self.element_map = {e.full_name: e for e in elements}
        self.name_to_elements = {}
        for element in elements:
            name = element.name
            if name not in self.name_to_elements:
                self.name_to_elements[name] = []
            self.name_to_elements[name].append(element)

        # Context tracking
        self.current_element: Optional[CodeElement] = None
        self.current_class: Optional[str] = None
        self.class_stack: List[str] = []
        self.function_stack: List[str] = []

        # Variable tracking for method resolution
        self.local_variables: Dict[str, str] = {}  # var_name -> type/class
        self.imports: Dict[str, str] = {}  # alias -> full_name

    def extract_relationships(self) -> List[Relationship]:
        """Extract all relationships from the AST."""
        tree = self._get_ast_for_module()
        if tree:
            self.visit(tree)
        return self.relationships

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        # Build full class name
        if self.class_stack:
            parent_class = self.class_stack[-1]
            full_class_name = f"{parent_class}.{node.name}"
        else:
            full_class_name = f"{self.module_name}.{node.name}"

        self.class_stack.append(full_class_name)
        previous_class = self.current_class
        self.current_class = full_class_name

        # Find the corresponding element
        class_element = self.element_map.get(full_class_name)
        if class_element:
            previous_element = self.current_element
            self.current_element = class_element

            # Process inheritance relationships
            for base in node.bases:
                base_name = self._extract_name_from_node(base)
                if base_name:
                    target_element = self._resolve_element(base_name)
                    if target_element:
                        self._add_relationship(
                            class_element.id,
                            target_element.id,
                            RelationshipType.INHERITS,
                            SourceLocation(self.file_path, node.lineno)
                        )

            # Visit class body
            self.generic_visit(node)
            self.current_element = previous_element

        # Restore context
        self.class_stack.pop()
        self.current_class = previous_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self._process_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self._process_function(node)

    def _process_function(self, node) -> None:
        """Process function or method definition."""
        # Build full function name
        if self.current_class:
            full_name = f"{self.current_class}.{node.name}"
        else:
            full_name = f"{self.module_name}.{node.name}"

        # Find the corresponding element
        function_element = self.element_map.get(full_name)
        if function_element:
            previous_element = self.current_element
            self.current_element = function_element
            self.function_stack.append(full_name)

            # Visit function body to find calls
            self.generic_visit(node)

            self.function_stack.pop()
            self.current_element = previous_element

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call."""
        if not self.current_element:
            return

        # Extract the target of the call
        target_name = self._extract_call_target(node)
        if target_name:
            target_element = self._resolve_element(target_name)
            if target_element and target_element.id != self.current_element.id:
                self._add_relationship(
                    self.current_element.id,
                    target_element.id,
                    RelationshipType.CALLS,
                    SourceLocation(self.file_path, node.lineno)
                )

        # Continue visiting arguments
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment to track variable types."""
        if isinstance(node.value, ast.Call):
            # Track class instantiations
            class_name = self._extract_call_target(node.value)
            if class_name:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.local_variables[target.id] = class_name
                    elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                        if target.value.id == 'self':
                            self.local_variables[f"self.{target.attr}"] = class_name

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for name in node.names:
            alias = name.asname or name.name
            self.imports[alias] = name.name

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from-import statement."""
        if node.module:
            for name in node.names:
                alias = name.asname or name.name
                self.imports[alias] = f"{node.module}.{name.name}"

    def _extract_call_target(self, call_node: ast.Call) -> Optional[str]:
        """Extract the target function/method being called."""
        if isinstance(call_node.func, ast.Name):
            # Direct function call: func()
            return call_node.func.id

        elif isinstance(call_node.func, ast.Attribute):
            # Method call: obj.method()
            if isinstance(call_node.func.value, ast.Name):
                obj_name = call_node.func.value.id
                method_name = call_node.func.attr

                # Handle self.method() calls
                if obj_name == 'self' and self.current_class:
                    return f"{self.current_class}.{method_name}"

                # Handle calls on known variables
                if obj_name in self.local_variables:
                    class_name = self.local_variables[obj_name]
                    return f"{class_name}.{method_name}"

                # Handle module.function() calls
                if obj_name in self.imports:
                    module_name = self.imports[obj_name]
                    return f"{module_name}.{method_name}"

                return f"{obj_name}.{method_name}"

            elif isinstance(call_node.func.value, ast.Attribute):
                # Nested attribute: module.submodule.func()
                return self._extract_name_from_node(call_node.func)

        return None

    def _extract_name_from_node(self, node: ast.AST) -> Optional[str]:
        """Extract a dotted name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._extract_name_from_node(node.value)
            if value_name:
                return f"{value_name}.{node.attr}"
        return None

    def _resolve_element(self, name: str) -> Optional[CodeElement]:
        """Resolve a name to a code element."""
        # Try exact match first
        if name in self.element_map:
            return self.element_map[name]

        # Try partial matches (just the function/class name)
        if '.' in name:
            short_name = name.split('.')[-1]
        else:
            short_name = name

        if short_name in self.name_to_elements:
            candidates = self.name_to_elements[short_name]

            # If only one candidate, use it
            if len(candidates) == 1:
                return candidates[0]

            # Multiple candidates - try to find best match
            # Prefer elements in the same module
            same_module = [c for c in candidates if c.module == self.module_name]
            if same_module:
                return same_module[0]

            # Otherwise, return the first candidate
            return candidates[0]

        return None

    def _add_relationship(self, source_id: str, target_id: str,
                          relationship_type: RelationshipType,
                          location: SourceLocation) -> None:
        """Add a relationship between elements."""
        relationship = Relationship(
            id=f"{source_id}->{target_id}",
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            source_location=location
        )
        self.relationships.append(relationship)

    def _get_ast_for_module(self) -> Optional[ast.AST]:
        """Get the AST for the current module."""
        # This would typically be passed in or retrieved from a cache
        # For now, we'll assume it's available through some mechanism
        # In a real implementation, this would be provided by the parser
        return None  # Placeholder
