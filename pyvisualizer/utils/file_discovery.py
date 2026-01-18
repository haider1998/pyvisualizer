"""
File discovery and parsing utilities.

This module provides functions for discovering Python files in a project
and converting file paths to module names.
"""

import ast
import os
import logging
import concurrent.futures
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from pyvisualizer.core.analyzer import ModuleAnalyzer
from pyvisualizer.core.graph import FunctionCallVisitor

logger = logging.getLogger("pyvisualizer.discovery")


@lru_cache(maxsize=128)
def parse_python_file(file_path: str) -> Optional[ast.AST]:
    """Parse a Python file and return its AST."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return ast.parse(file.read(), filename=file_path)
    except SyntaxError as e:
        logger.warning(f"Syntax error in {file_path}: {e}")
        return None
    except (OSError, IOError) as e:
        logger.warning(f"Could not read file {file_path}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error parsing {file_path}: {e}")
        return None


def find_project_python_files(project_path: str) -> List[str]:
    """
    Find all Python files within the project directory only.
    
    Does not include external libraries (site-packages, etc.)
    """
    py_files: List[str] = []
    
    # Directories to exclude
    exclude_dirs = {
        '__pycache__', '.git', '.svn', '.hg', '.tox', '.nox',
        '.pytest_cache', '.mypy_cache', 'venv', 'env', '.venv', '.env',
        'node_modules', 'build', 'dist', '*.egg-info', 'site-packages',
        '.idea', '.vscode', 'htmlcov', 'coverage', '.coverage',
    }
    
    # Files to exclude
    exclude_files = {
        'setup.py', 'conftest.py',
    }

    if os.path.isfile(project_path) and project_path.endswith('.py'):
        return [project_path]

    for root, dirs, files in os.walk(project_path):
        # Filter out excluded directories
        dirs[:] = [
            d for d in dirs 
            if d not in exclude_dirs and not d.endswith('.egg-info')
        ]

        for file in files:
            if file.endswith('.py') and file not in exclude_files:
                py_files.append(os.path.join(root, file))

    logger.info(f"Found {len(py_files)} Python files in project")
    return py_files


def get_module_name(file_path: str, project_root: str) -> str:
    """
    Get the module name from a file path relative to project root.
    
    Handles both regular packages (with __init__.py) and namespace packages (PEP 420).
    """
    # Normalize paths
    file_path = os.path.abspath(file_path)
    project_root = os.path.abspath(project_root)

    # Get the relative path
    try:
        rel_path = os.path.relpath(file_path, project_root)
    except ValueError:
        # On Windows, relpath can fail if paths are on different drives
        rel_path = os.path.basename(file_path)

    # Convert path separators to module separators
    rel_path = rel_path.replace(os.sep, '/')

    # Build module name
    module_parts: List[str] = []
    current_path = os.path.dirname(rel_path)

    # Add file name without extension
    file_name = os.path.splitext(os.path.basename(rel_path))[0]
    module_parts.insert(0, file_name)

    # Add package hierarchy
    while current_path and current_path != '.':
        # Check for both regular packages with __init__.py and namespace packages (PEP 420)
        init_path = os.path.join(project_root, current_path, '__init__.py')
        
        # Check if this directory contains subdirectories that are packages
        full_dir_path = os.path.join(project_root, current_path)
        is_namespace = False
        if os.path.isdir(full_dir_path):
            try:
                is_namespace = any(
                    os.path.isdir(os.path.join(full_dir_path, d))
                    and os.path.exists(os.path.join(full_dir_path, d, '__init__.py'))
                    for d in os.listdir(full_dir_path)
                    if os.path.isdir(os.path.join(full_dir_path, d))
                )
            except (OSError, IOError):
                pass

        if os.path.isfile(init_path) or is_namespace:
            module_parts.insert(0, os.path.basename(current_path))

        current_path = os.path.dirname(current_path)

    return '.'.join(module_parts)


def analyze_project(
    py_files: List[str],
    project_root: str
) -> Tuple[Dict[str, ModuleAnalyzer], List[Dict]]:
    """
    Analyze all modules in the project and extract function calls.
    
    Returns:
        A tuple of (module_analyzers, all_calls) where:
        - module_analyzers: Dict mapping module names to their analyzers
        - all_calls: List of all function calls found
    """
    # First pass: analyze modules and collect class/function definitions
    module_analyzers: Dict[str, ModuleAnalyzer] = {}
    all_module_names: Set[str] = set()

    # Process files in parallel for better performance
    max_workers = min(os.cpu_count() or 4, 8)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # First, parse all files
        future_to_file = {
            executor.submit(parse_python_file, file_path): (
                file_path,
                get_module_name(file_path, project_root)
            )
            for file_path in py_files
        }

        # Collect results
        for future in concurrent.futures.as_completed(future_to_file):
            file_path, module_name = future_to_file[future]
            try:
                tree = future.result()
            except Exception as e:
                logger.warning(f"Error parsing {file_path}: {e}")
                continue
                
            all_module_names.add(module_name)

            if tree:
                logger.debug(f"Parsed module: {module_name}")
                module_analyzers[module_name] = ModuleAnalyzer(
                    module_name, file_path, tree, project_root
                )

    # Second pass: analyze function calls (needs to be sequential due to dependencies)
    all_calls: List[Dict] = []

    for module_name, analyzer in module_analyzers.items():
        logger.debug(f"Analyzing function calls in: {module_name}")
        visitor = FunctionCallVisitor(
            module_name,
            analyzer.file_path,
            analyzer,
            module_analyzers,
            all_module_names
        )
        visitor.visit(analyzer.tree)
        all_calls.extend(visitor.calls)

    return module_analyzers, all_calls
