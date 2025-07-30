"""
AST parsing functionality for Python code analysis.
"""

import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.interfaces import ICodeParser
from ..core.exceptions import ParseError
from ..core.models import CodeElement, ElementType, SourceLocation
from ..utils.file_utils import FileUtils
from ..utils.logging import logger
from ..config.settings import settings


class ParseResult:
    """Result of parsing a single file."""

    def __init__(self, file_path: Path, tree: Optional[ast.AST] = None, error: Optional[Exception] = None):
        self.file_path = file_path
        self.tree = tree
        self.error = error
        self.success = tree is not None


class ASTParser(ICodeParser):
    """Parser for Python AST analysis."""

    def __init__(self, file_utils: Optional[FileUtils] = None):
        self.file_utils = file_utils or FileUtils()
        self.config = settings.parsing

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a single Python file."""
        try:
            content = self.file_utils.read_file_safely(file_path, self.config.encoding_fallbacks)
            if content is None:
                return ParseResult(file_path, error=ParseError(str(file_path), "Could not read file"))

            tree = ast.parse(content, filename=str(file_path))
            logger.debug(f"Successfully parsed {file_path}")
            return ParseResult(file_path, tree=tree)

        except SyntaxError as e:
            error = ParseError(str(file_path), f"Syntax error: {e}", e)
            if self.config.skip_syntax_errors:
                logger.warning(f"Skipping file with syntax error: {file_path}")
                return ParseResult(file_path, error=error)
            else:
                raise error

        except Exception as e:
            error = ParseError(str(file_path), f"Unexpected error: {e}", e)
            logger.error(f"Error parsing {file_path}: {e}")
            return ParseResult(file_path, error=error)

    def parse_project(self, project_path: Path) -> List[ParseResult]:
        """Parse all Python files in a project."""
        python_files = self.file_utils.find_python_files(project_path)
        logger.info(f"Found {len(python_files)} Python files to parse")

        results = []

        if len(python_files) <= 1:
            # Single file or small project - parse sequentially
            for file_path in python_files:
                results.append(self.parse_file(file_path))
        else:
            # Multiple files - parse in parallel
            with ThreadPoolExecutor(max_workers=self.config.parallel_workers) as executor:
                future_to_file = {
                    executor.submit(self.parse_file, file_path): file_path
                    for file_path in python_files
                }

                for future in as_completed(future_to_file):
                    result = future.result()
                    results.append(result)

        successful = sum(1 for r in results if r.success)
        logger.info(f"Successfully parsed {successful}/{len(results)} files")

        return results


class ElementExtractor(ast.NodeVisitor):
    """Extracts code elements from AST."""

    def __init__(self, module_name: str, file_path: Path):
        self.module_name = module_name
        self.file_path = file_path
        self.elements: List[CodeElement] = []
        self.current_class: Optional[str] = None
        self.class_stack: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a class definition."""
        # Handle nested classes
        if self.class_stack:
            parent_class = self.class_stack[-1]
            full_class_name = f"{parent_class}.{node.name}"
        else:
            full_class_name = f"{self.module_name}.{node.name}"

        self.class_stack.append(full_class_name)
        previous_class = self.current_class
        self.current_class = full_class_name

        # Create class element
        element = CodeElement(
            id=full_class_name,
            name=node.name,
            full_name=full_class_name,
            element_type=ElementType.CLASS,
            module=self.module_name,
            source_location=SourceLocation(self.file_path, node.lineno),
            decorators=[self._extract_decorator_name(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node)
        )
        self.elements.append(element)

        # Visit children (methods, nested classes)
        self.generic_visit(node)

        # Restore context
        self.class_stack.pop()
        self.current_class = previous_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a function definition."""
        self._process_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an async function definition."""
        self._process_function(node, is_async=True)

    def _process_function(self, node, is_async: bool) -> None:
        """Process a function or method definition."""
        if self.current_class:
            # This is a method
            full_name = f"{self.current_class}.{node.name}"
            element_type = self._determine_method_type(node)
        else:
            # This is a module-level function
            full_name = f"{self.module_name}.{node.name}"
            element_type = ElementType.FUNCTION

        # Check for property decorator
        is_property = any(
            self._extract_decorator_name(d) == 'property'
            for d in node.decorator_list
        )

        element = CodeElement(
            id=full_name,
            name=node.name,
            full_name=full_name,
            element_type=ElementType.PROPERTY if is_property else element_type,
            module=self.module_name,
            source_location=SourceLocation(self.file_path, node.lineno),
            class_name=self.current_class,
            is_async=is_async,
            is_property=is_property,
            decorators=[self._extract_decorator_name(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node),
            complexity=self._calculate_complexity(node)
        )
        self.elements.append(element)

        # Visit function body for nested functions
        self.generic_visit(node)

    def _determine_method_type(self, node) -> ElementType:
        """Determine the type of a method."""
        if node.name in ('__init__', '__new__'):
            return ElementType.CONSTRUCTOR
        elif node.name.startswith('_') and not node.name.startswith('__'):
            return ElementType.PRIVATE_METHOD
        else:
            # Check decorators for special method types
            decorators = {self._extract_decorator_name(d) for d in node.decorator_list}

            if 'staticmethod' in decorators:
                return ElementType.STATIC_METHOD
            elif 'classmethod' in decorators:
                return ElementType.CLASS_METHOD
            else:
                return ElementType.METHOD

    def _extract_decorator_name(self, decorator) -> str:
        """Extract decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return self._get_attribute_name(decorator)
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                return self._get_attribute_name(decorator.func)
        return "unknown"

    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get full attribute name like module.decorator."""
        parts = []
        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return '.'.join(reversed(parts))

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Decision points that increase complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1

        return complexity
