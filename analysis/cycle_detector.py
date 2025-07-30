"""
Detect cycles in code relationships.
"""

import networkx as nx
from typing import List

from ..core.interfaces import ICycleDetector
from ..core.models import CodeModel
from ..utils.logging import logger
from .graph_builder import GraphBuilder


class CycleDetector(ICycleDetector):
    """Detects cycles in code relationships."""

    def __init__(self, graph_builder: GraphBuilder = None):
        self.graph_builder = graph_builder or GraphBuilder()

    def detect_cycles(self, model: CodeModel) -> List[List[str]]:
        """Detect cycles in the code model."""
        # Build call graph
        call_graph = self.graph_builder.build_call_graph(model)

        # Find strongly connected components with more than one node
        cycles = []
        try:
            strongly_connected = list(nx.strongly_connected_components(call_graph))

            for component in strongly_connected:
                if len(component) > 1:
                    # This is a cycle - convert to list and add to results
                    cycle_nodes = list(component)
                    cycles.append(cycle_nodes)
                    logger.info(f"Found cycle with {len(cycle_nodes)} nodes: {cycle_nodes}")

        except Exception as e:
            logger.error(f"Error detecting cycles: {e}")

        # Also detect simple cycles
        try:
            simple_cycles = list(nx.simple_cycles(call_graph))
            for cycle in simple_cycles:
                if cycle not in cycles:
                    cycles.append(cycle)
                    logger.info(f"Found simple cycle: {cycle}")

        except Exception as e:
            logger.error(f"Error detecting simple cycles: {e}")

        logger.info(f"Detected {len(cycles)} cycles total")
        return cycles

    def mark_cycle_edges(self, model: CodeModel, graph: nx.DiGraph) -> nx.DiGraph:
        """Mark edges that are part of cycles."""
        cycles = self.detect_cycles(model)

        # Create a copy of the graph
        G = graph.copy()

        # Mark cycle edges
        for cycle in cycles:
            for i in range(len(cycle)):
                source = cycle[i]
                target = cycle[(i + 1) % len(cycle)]

                if G.has_edge(source, target):
                    G.edges[source, target]['is_cycle'] = True

        return G

    def get_cycle_statistics(self, cycles: List[List[str]]) -> dict:
        """Get statistics about detected cycles."""
        if not cycles:
            return {
                'total_cycles': 0,
                'max_cycle_length': 0,
                'min_cycle_length': 0,
                'avg_cycle_length': 0,
                'total_nodes_in_cycles': 0
            }

        cycle_lengths = [len(cycle) for cycle in cycles]
        all_cycle_nodes = set()
        for cycle in cycles:
            all_cycle_nodes.update(cycle)

        return {
            'total_cycles': len(cycles),
            'max_cycle_length': max(cycle_lengths),
            'min_cycle_length': min(cycle_lengths),
            'avg_cycle_length': sum(cycle_lengths) / len(cycle_lengths),
            'total_nodes_in_cycles': len(all_cycle_nodes)
        }
