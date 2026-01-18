"""
Function call resolution utilities.

This module provides advanced heuristics for resolving function calls
to their fully qualified names.
"""

from typing import Dict, List, Optional

import networkx as nx

from pyvisualizer.core.analyzer import ModuleAnalyzer


def resolve_function_call(
    caller: str,
    callee: str,
    G: nx.DiGraph,
    function_lookup: Dict[str, List[str]],
    module_analyzers: Dict[str, ModuleAnalyzer]
) -> Optional[str]:
    """Resolve a function call using advanced heuristics."""
    # If caller is in graph but callee needs resolution
    if caller in G.nodes:
        # Check if callee is a fully qualified name that might match with a prefix
        for node in G.nodes:
            if node.endswith('.' + callee) or node == callee:
                return node

        # Try to resolve by short name
        short_name = callee.split('.')[-1]
        if short_name in function_lookup:
            # If there's only one function with this name, use it
            if len(function_lookup[short_name]) == 1:
                return function_lookup[short_name][0]

            # Multiple options - try to find the best match
            # First try classes in the same module or package
            caller_parts = caller.split('.')
            caller_module = caller_parts[0]

            # If caller is a method, get its class
            caller_class = None
            if len(caller_parts) >= 3:  # module.class.method
                caller_class = '.'.join(caller_parts[:-1])

            # 1. Try to find methods in the same class
            if caller_class:
                for candidate in function_lookup[short_name]:
                    candidate_parts = candidate.split('.')
                    if len(candidate_parts) >= 3:  # module.class.method
                        candidate_class = '.'.join(candidate_parts[:-1])
                        if candidate_class == caller_class:
                            return candidate

            # 2. Try to find functions in the same module
            for candidate in function_lookup[short_name]:
                if candidate.startswith(caller_module + '.'):
                    return candidate

            # 3. For super() calls, try to find in base classes
            if 'super' in callee.lower():
                # Get the caller's class info if available
                for module_name, analyzer in module_analyzers.items():
                    if caller_class and caller_class in analyzer.classes:
                        class_info = analyzer.classes[caller_class]
                        for base_class in class_info.get('bases', []):
                            for candidate in function_lookup[short_name]:
                                if base_class in candidate:
                                    return candidate

            # 4. Default: return the first match as a fallback
            return function_lookup[short_name][0]

    return None


def filter_by_modules(G: nx.DiGraph, included_modules: List[str]) -> nx.DiGraph:
    """Filter graph to only include specified modules."""
    nodes_to_keep = []
    for node in G.nodes():
        module = G.nodes[node].get('module', '')
        if any(module.startswith(included) for included in included_modules):
            nodes_to_keep.append(node)
    return G.subgraph(nodes_to_keep).copy()


def filter_by_depth(
    G: nx.DiGraph,
    root_function: str,
    max_depth: int = 2
) -> nx.DiGraph:
    """Filter graph to only include functions within a certain call depth."""
    if root_function not in G.nodes:
        # Try to find a matching function
        for node in G.nodes:
            if node.endswith(root_function) or root_function in node:
                root_function = node
                break
        else:
            # No match found, return empty graph
            return nx.DiGraph()

    # BFS to find nodes within depth limit
    nodes_to_include = {root_function}
    current_level = {root_function}

    for _ in range(max_depth):
        next_level = set()
        for node in current_level:
            # Get successors (callee functions)
            for successor in G.successors(node):
                if successor not in nodes_to_include:
                    nodes_to_include.add(successor)
                    next_level.add(successor)
            # Get predecessors (caller functions)
            for predecessor in G.predecessors(node):
                if predecessor not in nodes_to_include:
                    nodes_to_include.add(predecessor)
                    next_level.add(predecessor)
        current_level = next_level

    return G.subgraph(nodes_to_include).copy()
