"""
Function call graph construction.

This module provides the FunctionCallVisitor for extracting function calls
and building a call graph from analyzed Python modules.
"""

import ast
import logging
from typing import Dict, List, Set, Optional, Tuple, Any

import networkx as nx

from pyvisualizer.core.analyzer import ModuleAnalyzer

logger = logging.getLogger("pyvisualizer.graph")


class FunctionCallVisitor(ast.NodeVisitor):
    """AST visitor to extract function calls."""

    def __init__(
        self,
        module_name: str,
        file_path: str,
        module_analyzer: ModuleAnalyzer,
        all_modules: Dict[str, ModuleAnalyzer],
        all_module_names: Set[str]
    ):
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self.class_stack: List[str] = []  # Track nested classes
        self.function_stack: List[str] = []  # Track nested functions
        self.module_name = module_name
        self.file_path = file_path
        self.module_analyzer = module_analyzer
        self.all_modules = all_modules
        self.all_module_names = all_module_names
        self.calls: List[Dict[str, Any]] = []
        self.class_instances: Dict[str, str] = {}  # Maps variable names to class types
        self.current_class_vars: Dict[str, str] = {}  # Maps 'self.var' to their types in current class
        self.context_managers: Dict[str, str] = {}  # Track variables created in context managers

        # Cache to avoid repeated lookups
        self._method_cache: Dict[str, Optional[Tuple[str, Optional[str]]]] = {}
        self._class_cache: Dict[str, Optional[str]] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a class definition."""
        previous_class = self.current_class
        # Handle nested classes
        if self.class_stack:
            parent_class = self.class_stack[-1]
            self.current_class = f"{parent_class}.{node.name}"
        else:
            self.current_class = f"{self.module_name}.{node.name}"

        self.class_stack.append(self.current_class)
        previous_vars = self.current_class_vars.copy()
        self.current_class_vars = {}  # Reset for this class

        # Visit all children to find methods and assignments
        self.generic_visit(node)

        # Restore context
        self.class_stack.pop()
        self.current_class = previous_class
        self.current_class_vars = previous_vars

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a function definition."""
        self._visit_function_common(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an async function definition."""
        self._visit_function_common(node)

    def _visit_function_common(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Common handling for function and async function definitions."""
        parent_func = self.current_function

        # Build the full function name based on context
        if self.class_stack:
            self.current_function = f"{self.class_stack[-1]}.{node.name}"
        else:
            self.current_function = f"{self.module_name}.{node.name}"

        self.function_stack.append(self.current_function)

        # Process decorators before visiting the function body
        for decorator in node.decorator_list:
            self.visit(decorator)

        # Visit all children to find calls
        self.generic_visit(node)

        # Restore parent function context
        self.function_stack.pop()
        self.current_function = parent_func if self.function_stack else None

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit an assignment statement to track variables."""
        # Only process if we have a value that is potentially a class instance
        if isinstance(node.value, ast.Call):
            # Get the class name being instantiated
            class_name = self._extract_call_target(node.value)

            # Record the variable assignment
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    if class_name:
                        self.class_instances[var_name] = class_name
                elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                    # Handle self.var = something()
                    if target.value.id == 'self' and self.current_class:
                        var_name = f"self.{target.attr}"
                        if class_name:
                            self.current_class_vars[var_name] = class_name

        # Handle tuple unpacking and other assignment types
        elif isinstance(node.value, ast.Tuple):
            # Check each item in the tuple for potential class instances
            for i, elt in enumerate(node.value.elts):
                if isinstance(elt, ast.Call):
                    class_name = self._extract_call_target(elt)
                    if class_name and i < len(node.targets):
                        target = node.targets[i]
                        if isinstance(target, ast.Name):
                            self.class_instances[target.id] = class_name

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit an annotated assignment (variable with type hint)."""
        # Record type annotation
        if isinstance(node.target, ast.Name):
            var_name = node.target.id
            if node.annotation:
                # This is a type hint that can help with resolution
                annotation = self._process_annotation(node.annotation)
                if annotation:
                    self.class_instances[var_name] = annotation

        # If there's a value being assigned, process it as well
        if node.value and isinstance(node.value, ast.Call):
            class_name = self._extract_call_target(node.value)
            if class_name and isinstance(node.target, ast.Name):
                self.class_instances[node.target.id] = class_name

        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """Visit a with statement to track context managers."""
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                # The context manager expression is a call
                class_name = self._extract_call_target(item.context_expr)

                # If there's an optional_vars (the 'as' part)
                if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                    var_name = item.optional_vars.id
                    if class_name:
                        self.context_managers[var_name] = class_name
                        # Also add to class instances for method resolution
                        self.class_instances[var_name] = class_name

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit a function call."""
        if not self.current_function:
            # Skip calls outside of function definitions
            self.generic_visit(node)
            return

        # Extract call target and potential module/class context
        target_function, module_path = self._resolve_call(node)

        if target_function:
            self.record_call(self.current_function, target_function, node.lineno)

        # Don't forget to visit function arguments which might contain calls
        for arg in node.args:
            self.visit(arg)

        for keyword in node.keywords:
            self.visit(keyword.value)

    def _resolve_call(self, node: ast.Call) -> Tuple[Optional[str], Optional[str]]:
        """Resolve a function call to its fully qualified name if possible."""
        if isinstance(node.func, ast.Name):
            # Direct function call: function_name()
            func_name = node.func.id

            # Check if it's an imported name
            if func_name in self.module_analyzer.imports.import_map:
                imported_path = self.module_analyzer.imports.import_map[func_name]

                # Check if this points to a function in a module
                if '.' in imported_path:
                    module_path, func_name = imported_path.rsplit('.', 1)
                    # Look for this function in all modules
                    for m_name, analyzer in self.all_modules.items():
                        if m_name == module_path or m_name.endswith('.' + module_path):
                            target = f"{m_name}.{func_name}"
                            if target in analyzer.functions:
                                return target, module_path

                    # If we didn't find a direct match, this might be a module.function reference
                    return imported_path, None
                else:
                    # It's a module import with alias, but we can't resolve the function
                    return None, imported_path

            # Check if it's a local function in current module
            local_target = f"{self.module_name}.{func_name}"
            if local_target in self.module_analyzer.functions:
                return local_target, None

            # Check if it might be in any of the star-imported modules
            for star_module in self.module_analyzer.imports.star_imports:
                for m_name, analyzer in self.all_modules.items():
                    if m_name == star_module or m_name.endswith('.' + star_module):
                        candidate = f"{m_name}.{func_name}"
                        if candidate in analyzer.functions:
                            return candidate, star_module

            # If we can't resolve it, just return the name for later resolution
            return func_name, None

        elif isinstance(node.func, ast.Attribute):
            # Method or attribute call: object.method()
            if isinstance(node.func.value, ast.Name):
                obj_name = node.func.value.id
                method_name = node.func.attr

                # Handle self.method() calls
                if obj_name == 'self' and self.current_class:
                    # Self method call within a class
                    method_target = f"{self.current_class}.{method_name}"

                    # Check if the method exists in this class
                    if self.current_class in self.module_analyzer.classes:
                        if method_name in self.module_analyzer.classes[self.current_class]['methods']:
                            return method_target, None

                    # Method might be inherited, try to find it in base classes
                    class_info = self.module_analyzer.classes.get(self.current_class)
                    if class_info and class_info['bases']:
                        for base_class in class_info['bases']:
                            # Resolve the base class name to a full qualified name if needed
                            full_base_name = self._resolve_class_name(base_class)
                            if full_base_name:
                                base_target = f"{full_base_name}.{method_name}"
                                # Check if this method exists in any of the analyzers
                                for analyzer in self.all_modules.values():
                                    if base_target in analyzer.functions:
                                        return base_target, None

                    # Method might be inherited, but we'll still record the call
                    return method_target, None

                # Handle calls on class instances
                if obj_name in self.class_instances:
                    class_name = self.class_instances[obj_name]

                    # Cache key for performance
                    cache_key = f"{class_name}::{method_name}"
                    if cache_key in self._method_cache:
                        return self._method_cache[cache_key]

                    # Try to find the class definition
                    for m_name, analyzer in self.all_modules.items():
                        for c_name, c_info in analyzer.classes.items():
                            c_short_name = c_info['name']
                            if class_name.endswith('.' + c_short_name) or class_name == c_short_name:
                                # Found the class, now check for the method
                                if method_name in c_info['methods']:
                                    result = (f"{c_name}.{method_name}", None)
                                    self._method_cache[cache_key] = result
                                    return result

                                # Check base classes for inherited methods
                                for base_class in c_info.get('bases', []):
                                    full_base_name = self._resolve_class_name(base_class)
                                    if full_base_name:
                                        for analyzer2 in self.all_modules.values():
                                            if full_base_name in analyzer2.classes:
                                                base_info = analyzer2.classes[full_base_name]
                                                if method_name in base_info['methods']:
                                                    result = (f"{full_base_name}.{method_name}", None)
                                                    self._method_cache[cache_key] = result
                                                    return result

                    # If can't find exact method, return with class name for later resolution
                    result = (f"{class_name}.{method_name}", None)
                    self._method_cache[cache_key] = result
                    return result

                # Handle module method calls
                if obj_name in self.module_analyzer.imports.import_map:
                    module_path = self.module_analyzer.imports.import_map[obj_name]

                    # Check if this might be a module.function call
                    for m_name, analyzer in self.all_modules.items():
                        if m_name == module_path or m_name.endswith('.' + module_path):
                            target = f"{m_name}.{method_name}"
                            if target in analyzer.functions:
                                return target, module_path

                    # If not found, return for later resolution
                    return f"{module_path}.{method_name}", module_path

                # Check if this is a context manager variable
                if obj_name in self.context_managers:
                    class_name = self.context_managers[obj_name]
                    return f"{class_name}.{method_name}", None

            # Handle nested attribute access like module.submodule.function()
            elif isinstance(node.func.value, ast.Attribute):
                # Extract the full attribute chain
                parts = self._extract_attribute_chain(node.func)
                if len(parts) >= 2:
                    obj_path = '.'.join(parts[:-1])
                    method_name = parts[-1]

                    # Check if the parts correspond to a known module or class
                    for m_name, analyzer in self.all_modules.items():
                        # Check if the object path matches or ends with a module name
                        if m_name == obj_path or m_name.endswith('.' + obj_path):
                            target = f"{m_name}.{method_name}"
                            if target in analyzer.functions:
                                return target, obj_path

                    # Return best effort result for later resolution
                    return f"{obj_path}.{method_name}", obj_path

        return None, None

    def _resolve_class_name(self, class_name: str) -> Optional[str]:
        """Resolve a class name to its fully qualified name."""
        # Check cache first
        if class_name in self._class_cache:
            return self._class_cache[class_name]

        # If it's already a fully qualified name
        for m_name, analyzer in self.all_modules.items():
            if class_name in analyzer.classes:
                self._class_cache[class_name] = class_name
                return class_name

        # Check for imported classes
        if class_name in self.module_analyzer.imports.import_map:
            imported_path = self.module_analyzer.imports.import_map[class_name]
            self._class_cache[class_name] = imported_path
            return imported_path

        # Check if it's a local class in the current module
        local_class = f"{self.module_name}.{class_name}"
        if local_class in self.module_analyzer.classes:
            self._class_cache[class_name] = local_class
            return local_class

        # Try to find in star imports
        for star_module in self.module_analyzer.imports.star_imports:
            for m_name, analyzer in self.all_modules.items():
                if m_name == star_module or m_name.endswith('.' + star_module):
                    potential_class = f"{m_name}.{class_name}"
                    if potential_class in analyzer.classes:
                        self._class_cache[class_name] = potential_class
                        return potential_class

        # Not found
        self._class_cache[class_name] = None
        return None

    def _extract_call_target(self, call_node: ast.Call) -> Optional[str]:
        """Extract the target class or function being called."""
        if isinstance(call_node.func, ast.Name):
            # Direct call: ClassName()
            target_name = call_node.func.id

            # Check if it's an imported class
            if target_name in self.module_analyzer.imports.import_map:
                return self.module_analyzer.imports.import_map[target_name]

            # It might be a local class
            local_class = f"{self.module_name}.{target_name}"
            if local_class in self.module_analyzer.classes:
                return local_class

            # Otherwise, just return the name
            return target_name

        elif isinstance(call_node.func, ast.Attribute):
            # Qualified call: module.ClassName()
            parts = self._extract_attribute_chain(call_node.func)
            return '.'.join(parts) if parts else None

        return None

    def _extract_attribute_chain(self, node: ast.AST) -> List[str]:
        """Extract a chain of attribute access like module.submodule.function."""
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

    def _process_annotation(self, node: ast.AST) -> Optional[str]:
        """Process a type annotation and return a class name if possible."""
        if isinstance(node, ast.Name):
            # Simple annotation: MyClass
            return node.id
        elif isinstance(node, ast.Attribute):
            # Qualified annotation: module.MyClass
            parts = self._extract_attribute_chain(node)
            return '.'.join(parts) if parts else None
        elif isinstance(node, ast.Subscript):
            # Generic type: List[MyClass]
            # Just return the container type for now
            if isinstance(node.value, ast.Name):
                return node.value.id
            elif isinstance(node.value, ast.Attribute):
                parts = self._extract_attribute_chain(node.value)
                return '.'.join(parts) if parts else None
        return None

    def record_call(self, caller: str, callee: str, lineno: int) -> None:
        """Record a function call."""
        self.calls.append({
            'caller': caller,
            'callee': callee,
            'lineno': lineno
        })


def build_call_graph(
    module_analyzers: Dict[str, ModuleAnalyzer],
    all_calls: List[Dict[str, Any]]
) -> nx.DiGraph:
    """Build a call graph from the analyzed modules and calls."""
    from pyvisualizer.core.resolver import resolve_function_call

    G = nx.DiGraph()

    # Add nodes for all functions
    for module_name, analyzer in module_analyzers.items():
        for func_name, func_info in analyzer.functions.items():
            G.add_node(func_name, **{
                'name': func_info['name'],
                'module': module_name,
                'class': func_info.get('class'),
                'lineno': func_info.get('lineno', 0),
                'path': analyzer.file_path,
                'is_async': func_info.get('is_async', False),
                'is_property': func_info.get('is_property', False),
                'decorators': func_info.get('decorators', [])
            })

    # Build a lookup table for resolving function names
    function_lookup: Dict[str, List[str]] = {}
    for module_name, analyzer in module_analyzers.items():
        for func_name in analyzer.functions:
            # Extract the short name (without module/class)
            short_name = func_name.split('.')[-1]
            if short_name not in function_lookup:
                function_lookup[short_name] = []
            function_lookup[short_name].append(func_name)

    # Add edges for function calls
    for call in all_calls:
        caller = call['caller']
        callee = call['callee']
        lineno = call['lineno']

        # If caller and callee are both in the graph, add the edge directly
        if caller in G.nodes and callee in G.nodes:
            G.add_edge(caller, callee, lineno=lineno)
            continue

        # Try more advanced resolution
        resolved_callee = resolve_function_call(
            caller, callee, G, function_lookup, module_analyzers
        )
        if resolved_callee:
            G.add_edge(caller, resolved_callee, lineno=lineno)

    # Handle cycles by marking edges that form cycles
    try:
        cycles = list(nx.simple_cycles(G))
        for cycle in cycles:
            for i in range(len(cycle)):
                source = cycle[i]
                target = cycle[(i + 1) % len(cycle)]
                if G.has_edge(source, target):
                    G.edges[source, target]['is_cycle'] = True
    except Exception as e:
        logger.warning(f"Could not detect cycles: {str(e)}")

    return G
