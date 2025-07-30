"""
Build graph structures from code models.
"""

import networkx as nx
from typing import Dict, List, Set

from ..core.models import CodeModel, CodeElement, Relationship, RelationshipType
from ..utils.logging import logger


class GraphBuilder:
    """Builds NetworkX graphs from code models."""

    def build_call_graph(self, model: CodeModel) -> nx.DiGraph:
        """Build a directed graph of function calls."""
        G = nx.DiGraph()

        # Add nodes for all elements
        for element in model.elements:
            G.add_node(element.id, **{
                'name': element.name,
                'full_name': element.full_name,
                'element_type': element.element_type.value,
                'module': element.module,
                'class_name': element.class_name,
                'is_async': element.is_async,
                'is_private': element.is_private,
                'is_property': element.is_property,
                'complexity': element.complexity,
                'file_path': str(element.source_location.file_path),
                'line_number': element.source_location.line_number
            })

        # Add edges for relationships
        for relationship in model.relationships:
            if relationship.relationship_type == RelationshipType.CALLS:
                G.add_edge(
                    relationship.source_id,
                    relationship.target_id,
                    relationship_type=relationship.relationship_type.value,
                    line_number=relationship.source_location.line_number if relationship.source_location else 0
                )

        logger.info(f"Built call graph with {len(G.nodes())} nodes and {len(G.edges())} edges")
        return G

    def build_inheritance_graph(self, model: CodeModel) -> nx.DiGraph:
        """Build a directed graph of class inheritance."""
        G = nx.DiGraph()

        # Add nodes for classes only
        for element in model.elements:
            if element.element_type.value == 'class':
                G.add_node(element.id, **{
                    'name': element.name,
                    'full_name': element.full_name,
                    'module': element.module,
                    'file_path': str(element.source_location.file_path)
                })

        # Add inheritance edges
        for relationship in model.relationships:
            if relationship.relationship_type == RelationshipType.INHERITS:
                if relationship.source_id in G.nodes() and relationship.target_id in G.nodes():
                    G.add_edge(relationship.source_id, relationship.target_id)

        return G

    def build_module_dependency_graph(self, model: CodeModel) -> nx.DiGraph:
        """Build a graph of module dependencies."""
        G = nx.DiGraph()

        # Get all modules
        modules = {element.module for element in model.elements}

        # Add module nodes
        for module in modules:
            module_elements = [e for e in model.elements if e.module == module]
            G.add_node(module, **{
                'element_count': len(module_elements),
                'complexity': sum(e.complexity for e in module_elements)
            })

        # Add edges based on cross-module relationships
        module_relationships = {}
        for relationship in model.relationships:
            source_element = model.get_element_by_id(relationship.source_id)
            target_element = model.get_element_by_id(relationship.target_id)

            if source_element and target_element:
                source_module = source_element.module
                target_module = target_element.module

                if source_module != target_module:
                    key = (source_module, target_module)
                    if key not in module_relationships:
                        module_relationships[key] = 0
                    module_relationships[key] += 1

        # Add edges with weights
        for (source_module, target_module), weight in module_relationships.items():
            G.add_edge(source_module, target_module, weight=weight)

        return G

    def filter_by_modules(self, graph: nx.DiGraph, included_modules: List[str]) -> nx.DiGraph:
        """Filter graph to only include specified modules."""
        H = graph.copy()
        nodes_to_remove = []

        for node in H.nodes():
            node_data = H.nodes[node]
            module = node_data.get('module', '')
            if not any(module.startswith(m) for m in included_modules):
                nodes_to_remove.append(node)

        H.remove_nodes_from(nodes_to_remove)
        return H

    def filter_by_depth(self, graph: nx.DiGraph, root_node: str, max_depth: int) -> nx.DiGraph:
        """Filter graph to only include nodes within max_depth from root."""
        if root_node not in graph.nodes():
            # Try to find a partial match
            matching_nodes = [n for n in graph.nodes() if root_node in n]
            if matching_nodes:
                root_node = matching_nodes[0]
            else:
                logger.warning(f"Root node {root_node} not found in graph")
                return nx.DiGraph()

        # Use BFS to find nodes within max_depth
        visited = {root_node: 0}
        queue = [(root_node, 0)]

        while queue:
            node, depth = queue.pop(0)
            if depth < max_depth:
                # Add outgoing neighbors
                for neighbor in graph.successors(node):
                    if neighbor not in visited or visited[neighbor] > depth + 1:
                        visited[neighbor] = depth + 1
                        queue.append((neighbor, depth + 1))

        # Create subgraph with visited nodes
        H = graph.subgraph(visited.keys()).copy()
        return H
