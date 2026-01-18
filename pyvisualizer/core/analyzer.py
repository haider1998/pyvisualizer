"""
AST-based code analysis for Python projects.

This module provides classes for collecting imports and analyzing module definitions
using Python's Abstract Syntax Trees (AST).
"""

import ast
import logging
from typing import Dict, List, Set, Optional, Any, NamedTuple

logger = logging.getLogger("pyvisualizer.analyzer")


class ImportInfo(NamedTuple):
    """Data structure to store information about imported names."""
    module: str
    name: str
    alias: str
    is_star: bool = False


class ImportCollector(ast.NodeVisitor):
    """AST visitor to collect all imports before function analysis."""

    def __init__(self, current_module: str, project_root: str):
        self.current_module = current_module
        self.project_root = project_root
        self.import_map: Dict[str, str] = {}  # Maps imported names to their module
        self.import_from_map: Dict[str, Set[str]] = {}  # Maps module names to the set of names imported from them
        self.direct_imports: Set[str] = set()  # Set of directly imported modules
        self.all_modules: Set[str] = set()  # All modules encountered
        self.star_imports: Set[str] = set()  # Modules from which * was imported
        # Store import information with more details
        self.imports: List[ImportInfo] = []  # List of ImportInfo objects
        # Cache to avoid resolving the same modules repeatedly
        self.resolved_modules: Dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> None:
        """Process import statements."""
        for name in node.names:
            module_name = name.name
            alias = name.asname or module_name

            # Record the import
            self.import_map[alias] = module_name
            self.direct_imports.add(module_name)
            self.all_modules.add(module_name)

            # Add to detailed imports list
            self.imports.append(ImportInfo(module_name, module_name, alias))

            # Also record the module components for qualified name resolution
            parts = module_name.split('.')
            for i in range(1, len(parts) + 1):
                partial_module = '.'.join(parts[:i])
                self.all_modules.add(partial_module)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Process from-import statements."""
        if node.module is not None or node.level > 0:
            # Handle relative imports by resolving the relative path
            if node.level > 0:
                module_name = self._resolve_relative_import(node.module, node.level)
            else:
                module_name = node.module

            self.all_modules.add(module_name)

            if module_name not in self.import_from_map:
                self.import_from_map[module_name] = set()

            for name in node.names:
                if name.name == '*':
                    # Import all names - we'll need to resolve this later
                    self.import_from_map[module_name].add('*')
                    self.star_imports.add(module_name)
                    self.imports.append(ImportInfo(module_name, '*', '*', True))
                else:
                    imported_name = name.name
                    alias = name.asname or imported_name

                    # Record this specific import
                    self.import_map[alias] = f"{module_name}.{imported_name}"
                    self.import_from_map[module_name].add(imported_name)
                    self.imports.append(ImportInfo(module_name, imported_name, alias))

        self.generic_visit(node)

    def _resolve_relative_import(self, module_name: Optional[str], level: int) -> str:
        """Resolve a relative import to an absolute module path."""
        if level == 0:
            return module_name or ""

        # Get the current package parts
        parts = self.current_module.split('.')

        # For relative imports, go up 'level' packages
        if len(parts) < level:
            logger.warning(f"Invalid relative import in {self.current_module}: level {level} too high")
            # Return best effort
            package = ""
        else:
            package = '.'.join(parts[:-level])

        # Add the specified module if any
        if module_name:
            if package:
                return f"{package}.{module_name}"
            return module_name
        return package


class ModuleAnalyzer:
    """Manages analysis of an entire module including imports and function definitions."""

    def __init__(self, module_name: str, file_path: str, tree: ast.AST, project_root: str):
        self.module_name = module_name
        self.file_path = file_path
        self.tree = tree
        self.project_root = project_root
        self.imports = ImportCollector(module_name, project_root)
        self.imports.visit(tree)

        # Maps class names to their definitions with inheritance info
        self.classes: Dict[str, Dict[str, Any]] = {}
        # Maps function/method names to their definitions
        self.functions: Dict[str, Dict[str, Any]] = {}
        # Maps class variables and function variables to what they reference
        self.variable_map: Dict[str, str] = {}
        # Track all method calls
        self.calls: List[Dict[str, Any]] = []
        # Track decorator usage
        self.decorators: Dict[str, List[Dict[str, Any]]] = {}
        # Track type annotations
        self.type_annotations: Dict[str, Dict[str, Any]] = {}

        # Process class and function definitions
        self._collect_definitions()

    def _collect_definitions(self) -> None:
        """Collect all class and function definitions from the module."""
        class_stack: List[str] = []  # Track nested classes

        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                # Build full class name with proper nesting
                parent_prefix = f"{class_stack[-1]}." if class_stack else self.module_name + "."
                full_class_name = f"{parent_prefix}{node.name}"
                class_stack.append(full_class_name)

                # Process inheritance
                base_classes: List[str] = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_classes.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        # Handle module.Class inheritance
                        parts = self._extract_attribute_chain(base)
                        if parts:
                            base_classes.append('.'.join(parts))

                self.classes[full_class_name] = {
                    'name': node.name,
                    'module': self.module_name,
                    'bases': base_classes,
                    'methods': {},
                    'node': node,
                    'decorators': [self._process_decorator(d) for d in node.decorator_list]
                }

                # Collect methods in the class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_name = f"{full_class_name}.{item.name}"

                        # Check if this is a property
                        is_property = any(
                            d.id == 'property' if isinstance(d, ast.Name) else False
                            for d in item.decorator_list
                        )

                        self.classes[full_class_name]['methods'][item.name] = {
                            'name': item.name,
                            'full_name': method_name,
                            'node': item,
                            'is_async': isinstance(item, ast.AsyncFunctionDef),
                            'is_property': is_property,
                            'decorators': [self._process_decorator(d) for d in item.decorator_list],
                            'return_annotation': self._process_annotation(item.returns) if item.returns else None
                        }

                        # Extract argument types if available
                        arg_types: Dict[str, Dict[str, Any]] = {}
                        for arg in item.args.args:
                            if arg.annotation:
                                arg_types[arg.arg] = self._process_annotation(arg.annotation)

                        # Also add to functions map for consistency
                        self.functions[method_name] = {
                            'name': item.name,
                            'module': self.module_name,
                            'class': full_class_name,
                            'full_name': method_name,
                            'lineno': item.lineno,
                            'node': item,
                            'is_async': isinstance(item, ast.AsyncFunctionDef),
                            'is_property': is_property,
                            'decorators': [self._process_decorator(d) for d in item.decorator_list],
                            'return_annotation': self._process_annotation(item.returns) if item.returns else None,
                            'arg_types': arg_types
                        }

                # After processing the class, remove it from the stack
                class_stack.pop()

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not class_stack:
                # Skip methods, we handle them above
                func_name = f"{self.module_name}.{node.name}"

                # Extract argument types if available
                arg_types = {}
                for arg in node.args.args:
                    if arg.annotation:
                        arg_types[arg.arg] = self._process_annotation(arg.annotation)

                self.functions[func_name] = {
                    'name': node.name,
                    'module': self.module_name,
                    'class': None,
                    'full_name': func_name,
                    'lineno': node.lineno,
                    'node': node,
                    'is_async': isinstance(node, ast.AsyncFunctionDef),
                    'is_property': False,
                    'decorators': [self._process_decorator(d) for d in node.decorator_list],
                    'return_annotation': self._process_annotation(node.returns) if node.returns else None,
                    'arg_types': arg_types
                }

    def _extract_attribute_chain(self, node: ast.AST) -> List[str]:
        """Extract a chain of attribute access like module.submodule.Class."""
        parts: List[str] = []

        # Handle the base case of a Name node
        if isinstance(node, ast.Name):
            return [node.id]

        # Handle Attribute nodes recursively
        elif isinstance(node, ast.Attribute):
            # Get the value parts recursively
            value_parts = self._extract_attribute_chain(node.value)
            # Add the attribute
            return value_parts + [node.attr]

        return parts

    def _process_decorator(self, node: ast.AST) -> Dict[str, Any]:
        """Process a decorator node and extract information."""
        if isinstance(node, ast.Name):
            # Simple decorator: @decorator_name
            return {'type': 'name', 'name': node.id}
        elif isinstance(node, ast.Call):
            # Decorator with arguments: @decorator(args)
            if isinstance(node.func, ast.Name):
                return {'type': 'call', 'name': node.func.id, 'args': self._extract_call_args(node)}
            elif isinstance(node.func, ast.Attribute):
                # Qualified decorator: @module.decorator(args)
                parts = self._extract_attribute_chain(node.func)
                return {'type': 'call', 'name': '.'.join(parts), 'args': self._extract_call_args(node)}
        elif isinstance(node, ast.Attribute):
            # Qualified decorator: @module.decorator
            parts = self._extract_attribute_chain(node)
            return {'type': 'name', 'name': '.'.join(parts)}

        # Default for unknown decorator types
        return {'type': 'unknown'}

    def _extract_call_args(self, call_node: ast.Call) -> Dict[str, Any]:
        """Extract arguments from a function call."""
        args: Dict[str, Any] = {}

        # Process positional arguments
        if call_node.args:
            args['positional'] = [
                self._extract_arg_value(arg) for arg in call_node.args
            ]

        # Process keyword arguments
        if call_node.keywords:
            args['keywords'] = {
                kw.arg: self._extract_arg_value(kw.value) for kw in call_node.keywords if kw.arg
            }

        return args

    def _extract_arg_value(self, node: ast.AST) -> Any:
        """Extract a simple value from an AST node if possible."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return f"variable:{node.id}"
        elif isinstance(node, ast.Attribute):
            parts = self._extract_attribute_chain(node)
            return '.'.join(parts)
        # For other types, return a placeholder
        return "complex_value"

    def _process_annotation(self, node: ast.AST) -> Dict[str, Any]:
        """Process a type annotation node."""
        if isinstance(node, ast.Name):
            # Simple annotation: int, str, etc.
            return {'type': 'name', 'name': node.id}
        elif isinstance(node, ast.Attribute):
            # Qualified annotation: module.Class
            parts = self._extract_attribute_chain(node)
            return {'type': 'name', 'name': '.'.join(parts)}
        elif isinstance(node, ast.Subscript):
            # Generic type: List[int], Dict[str, int], etc.
            if isinstance(node.value, ast.Name):
                container = node.value.id
            elif isinstance(node.value, ast.Attribute):
                parts = self._extract_attribute_chain(node.value)
                container = '.'.join(parts)
            else:
                container = "unknown"

            # Extract the parameters if possible
            params: List[Dict[str, Any]] = []
            slice_value = node.slice

            if isinstance(slice_value, ast.Tuple):
                for elt in slice_value.elts:
                    params.append(self._process_annotation(elt))
            else:
                params.append(self._process_annotation(slice_value))

            return {'type': 'subscript', 'container': container, 'params': params}

        # For other types, return a placeholder
        return {'type': 'unknown'}
