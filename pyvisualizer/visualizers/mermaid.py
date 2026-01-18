"""
Mermaid diagram generation for Python code visualization.

This module provides functions to generate Mermaid flowcharts and
interactive HTML viewers for code architecture diagrams.
"""

import os
import logging
from typing import Dict, List, Any

import networkx as nx

logger = logging.getLogger("pyvisualizer.mermaid")

# Color palette for different node types
COLORS = {
    'module': {'primary': '#5D2E8C', 'secondary': '#7B4BAF'},
    'class': {'primary': '#2962FF', 'secondary': '#5C8AFF'},
    'constructor': {'primary': '#E53935', 'secondary': '#EF5350'},
    'method': {'primary': '#00C853', 'secondary': '#4CD964'},
    'async': {'primary': '#AA00FF', 'secondary': '#CE93D8'},
    'property': {'primary': '#FF6D00', 'secondary': '#FFAB40'},
    'static': {'primary': '#00B0FF', 'secondary': '#80D8FF'},
    'private': {'primary': '#757575', 'secondary': '#BDBDBD'}
}


def generate_styled_mermaid(G: nx.DiGraph) -> str:
    """
    Generate a beautifully styled Mermaid flowchart with vibrant colors and icons.
    
    Args:
        G: A directed graph where nodes are functions and edges are calls
        
    Returns:
        A string containing the Mermaid diagram code
    """
    mermaid_code = [
        "flowchart LR",
        "    %% Node definitions with styling"
    ]

    # Track node IDs to ensure uniqueness
    node_ids: Dict[str, str] = {}
    node_count = 0

    # Group nodes by module
    modules: Dict[str, List[str]] = {}
    for node in G.nodes():
        module = G.nodes[node].get('module', 'unknown')
        if module not in modules:
            modules[module] = []
        modules[module].append(node)

    # Create a title node
    mermaid_code.append('    title("fa:fa-project-diagram Python Method Visualization"):::title')

    # Sort modules by name for consistent output
    sorted_modules = sorted(modules.items())

    # Process each module
    for module_idx, (module, nodes) in enumerate(sorted_modules):
        module_short_name = module.split('.')[-1]
        module_id = f"mod{module_idx}"

        # Add module subgraph with icon
        mermaid_code.append(f'    subgraph {module_id}["fa:fa-cube {module_short_name}"]')
        mermaid_code.append("        direction TB")

        # Group nodes by class
        classes: Dict[str, List[str]] = {}
        standalone_nodes: List[str] = []

        for node in nodes:
            class_name = G.nodes[node].get('class')
            if class_name:
                if class_name not in classes:
                    classes[class_name] = []
                classes[class_name].append(node)
            else:
                standalone_nodes.append(node)

        # Process each class
        for class_idx, (class_name, class_nodes) in enumerate(sorted(classes.items())):
            class_short_name = class_name.split('.')[-1]
            class_id = f"cls{module_idx}_{class_idx}"

            # Add class subgraph with icon
            mermaid_code.append(f'        subgraph {class_id}["fa:fa-code {class_short_name}"]')
            mermaid_code.append("            direction TB")

            # Categorize methods by type
            categories = _categorize_methods(G, class_nodes)

            # Process methods in order of importance
            for node_list, icon, style_class in [
                (categories['init'], "fa:fa-play-circle", "constructor"),
                (categories['property'], "fa:fa-lock", "property"),
                (categories['static'], "fa:fa-cog", "static"),
                (categories['async'], "fa:fa-bolt", "async"),
                (categories['regular'], "fa:fa-code-branch", "method"),
                (categories['private'], "fa:fa-key", "private")
            ]:
                for node in node_list:
                    method_name = node.split('.')[-1]
                    # Generate a unique ID for this node
                    if node not in node_ids:
                        node_ids[node] = f"node{node_count}"
                        node_count += 1
                    node_id = node_ids[node]

                    # Add the node with its icon and style
                    mermaid_code.append(f'                {node_id}["{icon} {method_name}"]:::{style_class}')

            mermaid_code.append("        end")

        # Process standalone functions
        if standalone_nodes:
            func_id = f"func{module_idx}"
            mermaid_code.append(f'        subgraph {func_id}["fa:fa-sitemap Module Functions"]')

            for node in standalone_nodes:
                func_name = node.split('.')[-1]
                is_private = func_name.startswith('_') and not func_name.startswith('__') and not func_name.endswith('__')

                # Generate a unique ID for this node
                if node not in node_ids:
                    node_ids[node] = f"node{node_count}"
                    node_count += 1
                node_id = node_ids[node]

                # Determine icon and style based on function type
                if G.nodes[node].get('is_async', False):
                    mermaid_code.append(f'            {node_id}["fa:fa-bolt {func_name}"]:::async')
                elif is_private:
                    mermaid_code.append(f'            {node_id}["fa:fa-key {func_name}"]:::private')
                elif G.nodes[node].get('decorators', []):
                    mermaid_code.append(f'            {node_id}["fa:fa-star {func_name}"]:::decorated')
                else:
                    mermaid_code.append(f'            {node_id}["fa:fa-code-branch {func_name}"]:::method')

            mermaid_code.append("        end")

        mermaid_code.append("    end")

    # Add a legend section
    mermaid_code.extend([
        '    subgraph legend["Legend"]',
        '        l1["fa:fa-play-circle Constructor"]:::constructor',
        '        l2["fa:fa-code-branch Method"]:::method',
        '        l3["fa:fa-bolt Async Method"]:::async',
        '        l4["fa:fa-lock Property"]:::property',
        '        l5["fa:fa-cog Static Method"]:::static',
        '        l6["fa:fa-key Private Method"]:::private',
        '        l7["fa:fa-star Decorated Method"]:::decorated',
        "    end"
    ])

    # Add connections between nodes
    mermaid_code.extend(["", "    %% Connections between methods"])

    # Process edges, using the node IDs we created
    for source, target, data in G.edges(data=True):
        if source in node_ids and target in node_ids:
            source_id = node_ids[source]
            target_id = node_ids[target]

            # Check if this edge is part of a cycle
            if data.get('is_cycle'):
                mermaid_code.append(f"    {source_id} -.-> {target_id}")
            # Check if it's a callback relationship
            elif any(kw in source.lower() for kw in ['callback', 'handler', 'listener']):
                mermaid_code.append(f"    {source_id} ==> {target_id}")
            # Check if it's likely a dependency injection
            elif target.lower().endswith(('factory', 'provider', 'service')):
                mermaid_code.append(f"    {source_id} --o {target_id}")
            else:
                # Regular call
                mermaid_code.append(f"    {source_id} --> {target_id}")

    # Add styling
    mermaid_code.extend(["", "    %% Styling"])
    mermaid_code.append(
        f"    style title color:#ffffff, fill:{COLORS['module']['primary']}, "
        f"stroke:{COLORS['module']['primary']}, stroke-width:0px, font-size:18px"
    )
    
    for style_class, color_key in [
        ('constructor', 'constructor'),
        ('method', 'method'),
        ('async', 'async'),
        ('property', 'property'),
        ('static', 'static'),
        ('private', 'private'),
        ('decorated', 'class'),
    ]:
        mermaid_code.append(
            f"    classDef {style_class} color:#ffffff, "
            f"fill:{COLORS[color_key]['primary']}, "
            f"stroke:{COLORS[color_key]['secondary']}"
        )

    return '\n'.join(mermaid_code)


def _categorize_methods(G: nx.DiGraph, class_nodes: List[str]) -> Dict[str, List[str]]:
    """Categorize methods by their type."""
    categories: Dict[str, List[str]] = {
        'init': [],
        'property': [],
        'static': [],
        'async': [],
        'private': [],
        'regular': []
    }

    for node in class_nodes:
        method_name = node.split('.')[-1]
        is_private = method_name.startswith('_') and not method_name.startswith('__') and not method_name.endswith('__')

        if method_name in ('__init__', '__new__'):
            categories['init'].append(node)
        elif G.nodes[node].get('is_property', False):
            categories['property'].append(node)
        elif any(d.get('name') == 'staticmethod' for d in G.nodes[node].get('decorators', [])):
            categories['static'].append(node)
        elif G.nodes[node].get('is_async', False):
            categories['async'].append(node)
        elif is_private:
            categories['private'].append(node)
        else:
            categories['regular'].append(node)

    return categories


def create_interactive_html(mermaid_code: str, project_name: str) -> str:
    """
    Create a beautiful interactive HTML page for the Mermaid diagram.
    
    Args:
        mermaid_code: The Mermaid diagram code
        project_name: Name of the project for the title
        
    Returns:
        HTML string for the interactive viewer
    """
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - Method Visualization</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        :root {{
            --primary-color: #5D2E8C;
            --secondary-color: #2962FF;
            --accent-color: #00C853;
            --background-color: #f8f9fa;
            --card-bg-color: #ffffff;
            --text-color: #333333;
            --border-radius: 8px;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            margin: 0;
            padding: 0;
            background-color: var(--background-color);
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }}
        header {{
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin: 0;
            font-size: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        h1 i {{ margin-right: 10px; font-size: 24px; }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
            flex: 1;
            display: flex;
            flex-direction: column;
        }}
        .controls-container {{
            background-color: var(--card-bg-color);
            border-radius: var(--border-radius);
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            padding: 20px;
            margin-bottom: 20px;
        }}
        .controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
        }}
        .control-group {{
            display: flex;
            flex-direction: column;
            flex: 1;
            min-width: 200px;
        }}
        .control-group label {{
            font-weight: 600;
            margin-bottom: 5px;
            font-size: 14px;
        }}
        .controls input, .controls select {{
            padding: 10px 15px;
            border: 1px solid #ddd;
            border-radius: var(--border-radius);
            font-size: 14px;
            width: 100%;
        }}
        .button-group {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        button {{
            padding: 10px 15px;
            border: none;
            border-radius: var(--border-radius);
            background-color: var(--primary-color);
            color: white;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            transition: all 0.2s ease;
        }}
        button:hover {{ opacity: 0.9; transform: translateY(-2px); }}
        button i {{ margin-right: 8px; }}
        button.secondary {{ background-color: var(--secondary-color); }}
        button.accent {{ background-color: var(--accent-color); }}
        .diagram-container {{
            background-color: var(--card-bg-color);
            border-radius: var(--border-radius);
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            padding: 20px;
            overflow: auto;
            flex: 1;
            min-height: 600px;
            position: relative;
        }}
        .mermaid {{ display: flex; justify-content: center; }}
        .zoom-controls {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
            flex-direction: column;
        }}
        .zoom-controls button {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }}
        .zoom-controls button i {{ margin: 0; }}
        .theme-switch {{
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: var(--primary-color);
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }}
        footer {{
            background-color: var(--card-bg-color);
            padding: 15px;
            text-align: center;
            font-size: 14px;
            border-top: 1px solid #eee;
            margin-top: 20px;
        }}
        body.dark-mode {{
            --primary-color: #9C64FE;
            --secondary-color: #448AFF;
            --accent-color: #4CD964;
            --background-color: #121212;
            --card-bg-color: #1E1E1E;
            --text-color: #E0E0E0;
        }}
        .loading {{
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 20px;
            z-index: 100;
        }}
        .loading i {{ animation: spin 1s infinite linear; font-size: 48px; }}
        @keyframes spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <div class="theme-switch" id="themeSwitch" title="Toggle dark mode">
        <i class="fas fa-moon"></i>
    </div>
    <header>
        <h1><i class="fas fa-project-diagram"></i> {project_name} Method Visualization</h1>
    </header>
    <div class="container">
        <div class="controls-container">
            <div class="controls">
                <div class="control-group">
                    <label for="searchInput"><i class="fas fa-search"></i> Search Methods</label>
                    <input type="text" id="searchInput" placeholder="Type to search methods...">
                </div>
                <div class="control-group">
                    <label for="moduleFilter"><i class="fas fa-filter"></i> Filter by Module</label>
                    <select id="moduleFilter">
                        <option value="">All Modules</option>
                    </select>
                </div>
                <div class="button-group">
                    <button id="expandAll"><i class="fas fa-expand-arrows-alt"></i> Expand All</button>
                    <button id="collapseAll" class="secondary"><i class="fas fa-compress-arrows-alt"></i> Collapse All</button>
                    <button id="downloadSVG" class="accent"><i class="fas fa-download"></i> Download SVG</button>
                </div>
            </div>
        </div>
        <div class="diagram-container">
            <div class="loading"><i class="fas fa-spinner"></i></div>
            <div class="mermaid" id="mermaidGraph">
{mermaid_code}
            </div>
        </div>
    </div>
    <div class="zoom-controls">
        <button id="zoomIn" title="Zoom In"><i class="fas fa-plus"></i></button>
        <button id="zoomOut" title="Zoom Out"><i class="fas fa-minus"></i></button>
        <button id="resetZoom" title="Reset Zoom"><i class="fas fa-sync-alt"></i></button>
    </div>
    <footer>Generated by PyVisualizer</footer>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            securityLevel: 'loose',
            theme: 'default',
            logLevel: 'error',
            flowchart: {{ useMaxWidth: false, htmlLabels: true, curve: 'basis' }}
        }});
        document.addEventListener('DOMContentLoaded', () => {{
            mermaid.contentLoaded();
            setTimeout(() => {{
                document.querySelector('.loading').style.display = 'none';
                initializeUI();
            }}, 1000);
        }});
        function initializeUI() {{
            const svgDocument = document.querySelector('.mermaid svg');
            if (!svgDocument) return;
            
            // Theme toggle
            document.getElementById('themeSwitch').addEventListener('click', () => {{
                document.body.classList.toggle('dark-mode');
                const icon = document.querySelector('#themeSwitch i');
                icon.className = document.body.classList.contains('dark-mode') ? 'fas fa-sun' : 'fas fa-moon';
            }});
            
            // Zoom controls
            let zoomLevel = 1;
            document.getElementById('zoomIn').addEventListener('click', () => {{
                zoomLevel = Math.min(zoomLevel * 1.2, 5);
                svgDocument.style.transform = `scale(${{zoomLevel}})`;
                svgDocument.style.transformOrigin = 'top left';
            }});
            document.getElementById('zoomOut').addEventListener('click', () => {{
                zoomLevel = Math.max(zoomLevel / 1.2, 0.2);
                svgDocument.style.transform = `scale(${{zoomLevel}})`;
                svgDocument.style.transformOrigin = 'top left';
            }});
            document.getElementById('resetZoom').addEventListener('click', () => {{
                zoomLevel = 1;
                svgDocument.style.transform = 'scale(1)';
            }});
            
            // Download SVG
            document.getElementById('downloadSVG').addEventListener('click', () => {{
                const svgCopy = svgDocument.cloneNode(true);
                svgCopy.setAttribute('width', svgDocument.getBBox().width);
                svgCopy.setAttribute('height', svgDocument.getBBox().height);
                const svgData = new XMLSerializer().serializeToString(svgCopy);
                const svgBlob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
                const svgUrl = URL.createObjectURL(svgBlob);
                const downloadLink = document.createElement('a');
                downloadLink.href = svgUrl;
                downloadLink.download = '{project_name}_methods.svg';
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
                URL.revokeObjectURL(svgUrl);
            }});
        }}
    </script>
</body>
</html>'''


def export_diagram(
    mermaid_code: str,
    output_path: str,
    output_format: str = 'mermaid',
    project_name: str = "Project"
) -> None:
    """
    Export the Mermaid diagram to the specified format.
    
    Args:
        mermaid_code: The Mermaid diagram code
        output_path: Path to save the output
        output_format: 'mermaid', 'svg', or 'png'
        project_name: Name of the project for titles
    """
    if output_format == 'mermaid':
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        logger.info(f"Mermaid diagram saved to {output_path}")

        # Create an enhanced HTML version
        html_path = f"{os.path.splitext(output_path)[0]}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(create_interactive_html(mermaid_code, project_name))
        logger.info(f"Interactive HTML diagram saved to {html_path}")
    else:
        try:
            import subprocess

            # Save the mermaid code to a temporary file
            temp_file = f"{output_path}.tmp.mmd"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(mermaid_code)

            # Run mmdc with enhanced configuration
            result = subprocess.run(
                [
                    'mmdc',
                    '-i', temp_file,
                    '-o', output_path,
                    '-b', 'transparent',
                    '-w', '2000',
                    '-H', '1500',
                ],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                logger.error(f"Error generating {output_format}: {result.stderr}")
                logger.info("Falling back to mermaid format")
                with open(f"{output_path}.mmd", 'w', encoding='utf-8') as f:
                    f.write(mermaid_code)
            else:
                logger.info(f"{output_format.upper()} diagram saved to {output_path}")

            # Always create an HTML version
            html_path = f"{os.path.splitext(output_path)[0]}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(create_interactive_html(mermaid_code, project_name))

            # Clean up the temporary file
            try:
                os.remove(temp_file)
            except Exception:
                pass

        except (ImportError, FileNotFoundError):
            logger.error(f"Could not generate {output_format}. Make sure mermaid-cli is installed.")
            logger.info("Saving as mermaid format instead")
            with open(f"{output_path}.mmd", 'w', encoding='utf-8') as f:
                f.write(mermaid_code)

            html_path = f"{os.path.splitext(output_path)[0]}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(create_interactive_html(mermaid_code, project_name))
