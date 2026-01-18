"""
PyVisualizer CLI - Command-line interface for Python code visualization.

Usage:
    py-code-visualizer /path/to/project [options]
"""

import argparse
import logging
import os
import sys
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pyvisualizer")


def main(args: Optional[list] = None) -> int:
    """
    Main entry point for the PyVisualizer CLI.
    
    Args:
        args: Command-line arguments (defaults to sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description='Generate code architecture diagrams for Python projects',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='py-code-visualizer'
    )
    
    parser.add_argument(
        'path',
        help='Path to Python project or file'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path (default: <project>_visualization.<format>)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['html', 'mermaid', 'svg', 'png'],
        default='html',
        help='Output format: html (interactive D3.js), mermaid (diagram), svg/png (static image)'
    )
    parser.add_argument(
        '--modules', '-m',
        nargs='+',
        help='Filter by module names (include only these modules)'
    )
    parser.add_argument(
        '--exclude', '-x',
        nargs='+',
        help='Exclude modules matching these patterns'
    )
    parser.add_argument(
        '--depth', '-d',
        type=int,
        help='Maximum call depth from entry point'
    )
    parser.add_argument(
        '--entry', '-e',
        help='Entry point function (format: module.function)'
    )
    parser.add_argument(
        '--max-nodes',
        type=int,
        default=150,
        help='Maximum number of nodes to include in the diagram'
    )
    parser.add_argument(
        '--project-name', '-p',
        help='Project name to use in diagram title'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    parsed_args = parser.parse_args(args)
    
    # Set log level
    if parsed_args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("pyvisualizer").setLevel(logging.DEBUG)
    
    # Import here to avoid circular imports and improve startup time
    try:
        import networkx as nx
    except ImportError:
        logger.error("networkx is required. Install it with: pip install networkx")
        return 1
    
    from pyvisualizer.utils.file_discovery import find_project_python_files, analyze_project
    from pyvisualizer.core.graph import build_call_graph
    from pyvisualizer.core.resolver import filter_by_modules, filter_by_depth
    from pyvisualizer.visualizers.mermaid import generate_styled_mermaid, create_interactive_html
    from pyvisualizer.visualizers.d3 import generate_d3_visualization
    
    # Normalize project path to absolute path
    project_path = os.path.abspath(parsed_args.path)
    
    if not os.path.exists(project_path):
        logger.error(f"Path does not exist: {project_path}")
        return 1
    
    # Get project name from path or argument
    project_name = parsed_args.project_name or os.path.basename(project_path)
    
    # Find Python files
    py_files = find_project_python_files(project_path)
    if not py_files:
        logger.error(f"No Python files found in {parsed_args.path}")
        return 1
    
    # Get project root
    project_root = project_path if os.path.isdir(project_path) else os.path.dirname(project_path)
    
    # Analyze the project
    logger.info("Analyzing project structure and dependencies...")
    module_analyzers, all_calls = analyze_project(py_files, project_root)
    
    # Build the call graph
    logger.info("Building function call graph...")
    G = build_call_graph(module_analyzers, all_calls)
    logger.info(f"Built graph with {len(G.nodes())} functions and {len(G.edges())} calls")
    
    # Apply filters
    if parsed_args.modules:
        logger.info(f"Filtering to include only modules: {', '.join(parsed_args.modules)}")
        G = filter_by_modules(G, parsed_args.modules)
        logger.info(f"After module filtering: {len(G.nodes())} functions and {len(G.edges())} calls")
    
    if parsed_args.exclude:
        logger.info(f"Excluding modules: {', '.join(parsed_args.exclude)}")
        nodes_to_remove = []
        for node in G.nodes():
            module = G.nodes[node].get('module', '')
            if any(module.startswith(excluded) for excluded in parsed_args.exclude):
                nodes_to_remove.append(node)
        G.remove_nodes_from(nodes_to_remove)
        logger.info(f"After exclusion: {len(G.nodes())} functions and {len(G.edges())} calls")
    
    if parsed_args.entry and parsed_args.depth:
        logger.info(f"Filtering to depth {parsed_args.depth} from entry point {parsed_args.entry}")
        G = filter_by_depth(G, parsed_args.entry, parsed_args.depth)
        logger.info(f"After depth filtering: {len(G.nodes())} functions and {len(G.edges())} calls")
    
    # Limit nodes if needed
    if len(G.nodes()) > parsed_args.max_nodes:
        logger.warning(f"Graph has {len(G.nodes())} nodes, exceeding limit of {parsed_args.max_nodes}")
        logger.warning("Removing least connected nodes to reduce graph size")
        
        # Sort nodes by degree (number of connections)
        node_degrees = sorted(G.degree(), key=lambda x: x[1])
        nodes_to_remove = [node for node, degree in node_degrees[:len(G.nodes()) - parsed_args.max_nodes]]
        G.remove_nodes_from(nodes_to_remove)
        logger.info(f"After limiting nodes: {len(G.nodes())} functions and {len(G.edges())} calls")
    
    # Check if we have anything to visualize
    if len(G.nodes()) == 0:
        logger.warning("No functions to visualize after applying filters")
        return 0
    
    # Set default output path
    if not parsed_args.output:
        parsed_args.output = f"{project_name}_visualization.{parsed_args.format}"
    
    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(parsed_args.output))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Generate visualization
    if parsed_args.format == 'html':
        logger.info("Generating interactive D3.js visualization...")
        generate_d3_visualization(G, parsed_args.output, project_name)
        
    elif parsed_args.format == 'mermaid':
        logger.info("Generating Mermaid diagram...")
        mermaid_code = generate_styled_mermaid(G)
        
        with open(parsed_args.output, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        
        # Also generate HTML version
        html_path = f"{os.path.splitext(parsed_args.output)[0]}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(create_interactive_html(mermaid_code, project_name))
        
        logger.info(f"Mermaid diagram saved to {parsed_args.output}")
        logger.info(f"Interactive HTML version saved to {html_path}")
        
    elif parsed_args.format in ['svg', 'png']:
        try:
            import graphviz
            logger.info(f"Generating {parsed_args.format.upper()} using Graphviz...")
            
            dot = graphviz.Digraph(
                comment=f'{project_name} Code Structure',
                engine='dot',
                format=parsed_args.format,
                graph_attr={
                    'rankdir': 'LR',
                    'bgcolor': 'transparent',
                    'fontname': 'Arial',
                    'nodesep': '0.8',
                    'ranksep': '1.0'
                }
            )
            
            # Color mapping
            colors = {
                '__init__': '#E53935',
                '__new__': '#E53935',
                'property': '#FF6D00',
                'async': '#AA00FF',
                'private': '#757575',
                'method': '#2962FF',
                'function': '#00C853',
            }
            
            for node in G.nodes():
                node_name = node.split('.')[-1]
                node_data = G.nodes[node]
                
                # Determine color
                if node_name in ('__init__', '__new__'):
                    fillcolor = colors['__init__']
                elif node_data.get('is_property', False):
                    fillcolor = colors['property']
                elif node_data.get('is_async', False):
                    fillcolor = colors['async']
                elif node_name.startswith('_') and not node_name.startswith('__'):
                    fillcolor = colors['private']
                elif node_data.get('class'):
                    fillcolor = colors['method']
                else:
                    fillcolor = colors['function']
                
                dot.node(
                    node,
                    label=node_name,
                    shape='box' if node_data.get('class') else 'ellipse',
                    style='filled',
                    fillcolor=fillcolor,
                    fontcolor='white',
                    fontname='Arial',
                    fontsize='12'
                )
            
            for source, target, data in G.edges(data=True):
                is_cycle = data.get('is_cycle', False)
                if is_cycle:
                    dot.edge(source, target, color='#F44336', style='dashed', penwidth='1.5')
                else:
                    dot.edge(source, target, color='#616161', penwidth='1.0')
            
            dot.render(parsed_args.output, cleanup=True)
            logger.info(f"{parsed_args.format.upper()} saved to {parsed_args.output}.{parsed_args.format}")
            
        except ImportError:
            logger.error("graphviz is required for SVG/PNG output. Install it with: pip install graphviz")
            logger.warning("Falling back to D3.js HTML visualization")
            generate_d3_visualization(G, f"{os.path.splitext(parsed_args.output)[0]}.html", project_name)
        except Exception as e:
            logger.error(f"Failed to generate {parsed_args.format}: {e}")
            logger.warning("Falling back to D3.js HTML visualization")
            generate_d3_visualization(G, f"{os.path.splitext(parsed_args.output)[0]}.html", project_name)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
