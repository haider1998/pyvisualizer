"""
D3.js interactive visualization generation for Python code architecture.

This module provides functions to generate interactive force-directed
graph visualizations using D3.js.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

import networkx as nx

logger = logging.getLogger("pyvisualizer.d3")


def generate_d3_visualization(
    G: nx.DiGraph,
    output_path: str,
    project_name: str
) -> None:
    """
    Generate an interactive D3.js visualization.
    
    Args:
        G: A directed graph where nodes are functions and edges are calls
        output_path: Path to save the HTML file
        project_name: Name of the project for the title
    """
    # Prepare graph data for D3.js
    graph_data = _prepare_graph_data(G)
    
    # Generate the HTML template with embedded data
    html = create_d3_html_template(graph_data, project_name)
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logger.info(f"D3.js visualization saved to {output_path}")


def _prepare_graph_data(G: nx.DiGraph) -> Dict[str, Any]:
    """Prepare graph data in a format suitable for D3.js."""
    nodes: List[Dict[str, Any]] = []
    links: List[Dict[str, Any]] = []
    
    # Create node ID to index mapping
    node_id_to_idx: Dict[str, int] = {}
    
    for idx, node in enumerate(G.nodes()):
        node_id_to_idx[node] = idx
        node_data = G.nodes[node]
        
        # Determine node type for styling
        node_name = node.split('.')[-1]
        if node_name in ('__init__', '__new__'):
            node_type = 'constructor'
        elif node_data.get('is_property', False):
            node_type = 'property'
        elif node_data.get('is_async', False):
            node_type = 'async'
        elif any(d.get('name') == 'staticmethod' for d in node_data.get('decorators', [])):
            node_type = 'static'
        elif node_name.startswith('_') and not node_name.startswith('__'):
            node_type = 'private'
        elif node_data.get('class'):
            node_type = 'method'
        else:
            node_type = 'function'
        
        nodes.append({
            'id': node,
            'name': node_name,
            'module': node_data.get('module', ''),
            'class': node_data.get('class'),
            'type': node_type,
            'is_async': node_data.get('is_async', False),
            'lineno': node_data.get('lineno', 0),
            'path': node_data.get('path', ''),
        })
    
    # Create links
    for source, target, data in G.edges(data=True):
        if source in node_id_to_idx and target in node_id_to_idx:
            links.append({
                'source': source,
                'target': target,
                'is_cycle': data.get('is_cycle', False),
                'lineno': data.get('lineno', 0),
            })
    
    # Detect cycles for highlighting
    cycles: List[List[str]] = []
    try:
        for cycle in nx.simple_cycles(G):
            if len(cycle) <= 10:  # Only include small cycles
                cycles.append(cycle)
    except Exception:
        pass
    
    # Calculate statistics
    stats = {
        'total_nodes': len(nodes),
        'total_edges': len(links),
        'total_modules': len(set(n['module'] for n in nodes)),
        'total_classes': len(set(n['class'] for n in nodes if n['class'])),
        'total_cycles': len(cycles),
    }
    
    return {
        'nodes': nodes,
        'links': links,
        'cycles': cycles,
        'stats': stats,
    }


def create_d3_html_template(graph_data: Dict[str, Any], project_name: str) -> str:
    """
    Create an HTML template with D3.js visualization.
    
    Args:
        graph_data: Prepared graph data
        project_name: Name of the project
        
    Returns:
        HTML string for the interactive visualization
    """
    graph_json = json.dumps(graph_data)
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - Code Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {{
            --primary-color: #5D2E8C;
            --secondary-color: #2962FF;
            --accent-color: #00C853;
            --danger-color: #F44336;
            --warning-color: #FF9800;
            --text-color: #212121;
            --text-secondary: #757575;
            --background-color: #f8f9fa;
            --card-bg-color: #ffffff;
            --border-color: #e0e0e0;
            --shadow-color: rgba(0,0,0,0.1);
            --node-constructor: #E53935;
            --node-method: #2962FF;
            --node-function: #00C853;
            --node-property: #FF6D00;
            --node-async: #AA00FF;
            --node-private: #757575;
            --link-normal: #616161;
            --link-cycle: #F44336;
        }}
        body.dark-mode {{
            --primary-color: #9C64FE;
            --secondary-color: #448AFF;
            --accent-color: #4CD964;
            --text-color: #EEEEEE;
            --text-secondary: #BDBDBD;
            --background-color: #121212;
            --card-bg-color: #1E1E1E;
            --border-color: #333333;
            --shadow-color: rgba(0,0,0,0.5);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--background-color);
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            transition: background-color 0.3s ease;
        }}
        header {{
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px var(--shadow-color);
        }}
        .project-title {{
            display: flex;
            align-items: center;
            font-size: 1.5rem;
            font-weight: 600;
        }}
        .project-title i {{ margin-right: 0.5rem; }}
        .header-controls {{ display: flex; gap: 0.75rem; }}
        .theme-toggle {{
            background: rgba(255, 255, 255, 0.2);
            border: none;
            border-radius: 50%;
            width: 2.5rem;
            height: 2.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            cursor: pointer;
            transition: background-color 0.3s;
        }}
        .theme-toggle:hover {{ background: rgba(255, 255, 255, 0.3); }}
        .layout-container {{ display: flex; flex: 1; overflow: hidden; }}
        .sidebar {{
            width: 300px;
            background-color: var(--card-bg-color);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            transition: transform 0.3s ease;
        }}
        .controls-section {{
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
        }}
        .controls-section h3 {{
            font-size: 1rem;
            margin-bottom: 0.75rem;
            color: var(--text-color);
            display: flex;
            align-items: center;
        }}
        .controls-section h3 i {{ margin-right: 0.5rem; }}
        .search-box {{ position: relative; margin-bottom: 1rem; }}
        .search-box input {{
            width: 100%;
            padding: 0.75rem 1rem 0.75rem 2.5rem;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 0.9rem;
            color: var(--text-color);
            background-color: var(--card-bg-color);
        }}
        .search-box i {{
            position: absolute;
            left: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-secondary);
        }}
        select {{
            width: 100%;
            padding: 0.75rem;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 0.9rem;
            color: var(--text-color);
            background-color: var(--card-bg-color);
            margin-bottom: 1rem;
        }}
        .btn-group {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
        .btn {{
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            font-size: 0.85rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s;
        }}
        .btn-primary {{ background-color: var(--primary-color); color: white; }}
        .btn-secondary {{ background-color: var(--secondary-color); color: white; }}
        .btn-danger {{ background-color: var(--danger-color); color: white; }}
        .btn:hover {{ opacity: 0.9; transform: translateY(-1px); }}
        .graph-container {{
            flex: 1;
            position: relative;
            overflow: hidden;
            background-color: var(--card-bg-color);
        }}
        #graph-svg {{ width: 100%; height: 100%; }}
        .node {{ cursor: pointer; }}
        .node circle {{ stroke-width: 2px; stroke: white; }}
        .node text {{ font-size: 10px; pointer-events: none; }}
        .link {{ fill: none; stroke-opacity: 0.6; }}
        .link.cycle {{ stroke: var(--link-cycle); stroke-dasharray: 5, 5; }}
        .node.highlighted circle {{ stroke: #FFD700; stroke-width: 4px; }}
        .node.faded {{ opacity: 0.2; }}
        .link.faded {{ opacity: 0.1; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
        }}
        .stat-item {{
            background-color: var(--background-color);
            padding: 0.75rem;
            border-radius: 4px;
            text-align: center;
        }}
        .stat-value {{ font-size: 1.5rem; font-weight: bold; color: var(--primary-color); }}
        .stat-label {{ font-size: 0.75rem; color: var(--text-secondary); }}
        .legend {{ padding: 1rem; }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 0.5rem;
            font-size: 0.85rem;
        }}
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }}
        .tooltip {{
            position: absolute;
            background-color: var(--card-bg-color);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 0.75rem;
            font-size: 0.85rem;
            box-shadow: 0 2px 10px var(--shadow-color);
            pointer-events: none;
            z-index: 1000;
            max-width: 300px;
        }}
        .tooltip h4 {{ margin-bottom: 0.5rem; color: var(--primary-color); }}
        .tooltip p {{ margin: 0.25rem 0; color: var(--text-secondary); }}
    </style>
</head>
<body>
    <header>
        <div class="project-title">
            <i class="fas fa-project-diagram"></i>
            <span>{project_name}</span>
        </div>
        <div class="header-controls">
            <button class="theme-toggle" id="themeToggle" title="Toggle theme">
                <i class="fas fa-moon"></i>
            </button>
        </div>
    </header>
    <div class="layout-container">
        <aside class="sidebar">
            <div class="controls-section">
                <h3><i class="fas fa-search"></i> Search</h3>
                <div class="search-box">
                    <i class="fas fa-search"></i>
                    <input type="text" id="searchInput" placeholder="Search functions...">
                </div>
            </div>
            <div class="controls-section">
                <h3><i class="fas fa-filter"></i> Filters</h3>
                <select id="moduleFilter">
                    <option value="">All Modules</option>
                </select>
                <select id="typeFilter">
                    <option value="">All Types</option>
                    <option value="constructor">Constructors</option>
                    <option value="method">Methods</option>
                    <option value="function">Functions</option>
                    <option value="async">Async</option>
                    <option value="property">Properties</option>
                    <option value="private">Private</option>
                </select>
            </div>
            <div class="controls-section">
                <h3><i class="fas fa-chart-bar"></i> Statistics</h3>
                <div class="stats-grid" id="statsGrid"></div>
            </div>
            <div class="controls-section">
                <h3><i class="fas fa-tools"></i> Controls</h3>
                <div class="btn-group">
                    <button class="btn btn-danger" id="highlightCycles">
                        <i class="fas fa-sync-alt"></i> Cycles
                    </button>
                    <button class="btn btn-secondary" id="resetFilters">
                        <i class="fas fa-undo"></i> Reset
                    </button>
                    <button class="btn btn-primary" id="exportSvg">
                        <i class="fas fa-download"></i> SVG
                    </button>
                </div>
            </div>
            <div class="legend">
                <h3><i class="fas fa-palette"></i> Legend</h3>
                <div class="legend-item">
                    <span class="legend-color" style="background-color: var(--node-constructor);"></span>
                    Constructor
                </div>
                <div class="legend-item">
                    <span class="legend-color" style="background-color: var(--node-method);"></span>
                    Method
                </div>
                <div class="legend-item">
                    <span class="legend-color" style="background-color: var(--node-function);"></span>
                    Function
                </div>
                <div class="legend-item">
                    <span class="legend-color" style="background-color: var(--node-async);"></span>
                    Async
                </div>
                <div class="legend-item">
                    <span class="legend-color" style="background-color: var(--node-property);"></span>
                    Property
                </div>
                <div class="legend-item">
                    <span class="legend-color" style="background-color: var(--node-private);"></span>
                    Private
                </div>
            </div>
        </aside>
        <div class="graph-container" id="graphContainer">
            <svg id="graph-svg"></svg>
        </div>
    </div>
    <div class="tooltip" id="tooltip" style="display: none;"></div>
    
    <script>
        const graphData = {graph_json};
        
        // Color mapping
        const nodeColors = {{
            constructor: '#E53935',
            method: '#2962FF',
            function: '#00C853',
            async: '#AA00FF',
            property: '#FF6D00',
            private: '#757575',
            static: '#00B0FF'
        }};
        
        // Setup SVG
        const container = document.getElementById('graphContainer');
        const svg = d3.select('#graph-svg');
        const width = container.clientWidth;
        const height = container.clientHeight;
        
        svg.attr('width', width).attr('height', height);
        
        // Create zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => g.attr('transform', event.transform));
        
        svg.call(zoom);
        
        const g = svg.append('g');
        
        // Create arrow marker for links
        svg.append('defs').append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '-0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('orient', 'auto')
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .append('path')
            .attr('d', 'M 0,-5 L 10,0 L 0,5')
            .attr('fill', '#616161');
        
        // Create simulation
        const simulation = d3.forceSimulation(graphData.nodes)
            .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(30));
        
        // Create links
        const link = g.append('g')
            .selectAll('line')
            .data(graphData.links)
            .join('line')
            .attr('class', d => d.is_cycle ? 'link cycle' : 'link')
            .attr('stroke', d => d.is_cycle ? '#F44336' : '#616161')
            .attr('stroke-width', 1.5)
            .attr('marker-end', 'url(#arrowhead)');
        
        // Create nodes
        const node = g.append('g')
            .selectAll('g')
            .data(graphData.nodes)
            .join('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));
        
        node.append('circle')
            .attr('r', 12)
            .attr('fill', d => nodeColors[d.type] || nodeColors.function);
        
        node.append('text')
            .attr('dx', 15)
            .attr('dy', 4)
            .text(d => d.name)
            .attr('fill', 'var(--text-color)');
        
        // Tooltip
        const tooltip = document.getElementById('tooltip');
        
        node.on('mouseover', (event, d) => {{
            tooltip.innerHTML = `
                <h4>${{d.name}}</h4>
                <p><strong>Module:</strong> ${{d.module}}</p>
                ${{d.class ? `<p><strong>Class:</strong> ${{d.class.split('.').pop()}}</p>` : ''}}
                <p><strong>Type:</strong> ${{d.type}}</p>
                <p><strong>Line:</strong> ${{d.lineno}}</p>
            `;
            tooltip.style.display = 'block';
            tooltip.style.left = (event.pageX + 10) + 'px';
            tooltip.style.top = (event.pageY - 10) + 'px';
        }})
        .on('mouseout', () => tooltip.style.display = 'none');
        
        // Simulation tick
        simulation.on('tick', () => {{
            link.attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
        }});
        
        // Drag functions
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
        
        // Populate filters
        const modules = [...new Set(graphData.nodes.map(n => n.module))].sort();
        const moduleFilter = document.getElementById('moduleFilter');
        modules.forEach(m => {{
            const option = document.createElement('option');
            option.value = m;
            option.textContent = m;
            moduleFilter.appendChild(option);
        }});
        
        // Populate stats
        const statsGrid = document.getElementById('statsGrid');
        const stats = graphData.stats;
        statsGrid.innerHTML = `
            <div class="stat-item">
                <div class="stat-value">${{stats.total_nodes}}</div>
                <div class="stat-label">Functions</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${{stats.total_edges}}</div>
                <div class="stat-label">Calls</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${{stats.total_modules}}</div>
                <div class="stat-label">Modules</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${{stats.total_cycles}}</div>
                <div class="stat-label">Cycles</div>
            </div>
        `;
        
        // Filter functionality
        function applyFilters() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const moduleValue = moduleFilter.value;
            const typeValue = document.getElementById('typeFilter').value;
            
            node.classed('faded', d => {{
                const matchSearch = !searchTerm || d.name.toLowerCase().includes(searchTerm) || d.id.toLowerCase().includes(searchTerm);
                const matchModule = !moduleValue || d.module === moduleValue;
                const matchType = !typeValue || d.type === typeValue;
                return !(matchSearch && matchModule && matchType);
            }});
            
            link.classed('faded', d => {{
                const sourceNode = graphData.nodes.find(n => n.id === d.source.id || n.id === d.source);
                const targetNode = graphData.nodes.find(n => n.id === d.target.id || n.id === d.target);
                const sourceVisible = sourceNode && !node.filter(n => n.id === sourceNode.id).classed('faded');
                const targetVisible = targetNode && !node.filter(n => n.id === targetNode.id).classed('faded');
                return !(sourceVisible && targetVisible);
            }});
        }}
        
        document.getElementById('searchInput').addEventListener('input', applyFilters);
        moduleFilter.addEventListener('change', applyFilters);
        document.getElementById('typeFilter').addEventListener('change', applyFilters);
        
        document.getElementById('highlightCycles').addEventListener('click', () => {{
            const cycleNodes = new Set(graphData.cycles.flat());
            node.classed('faded', d => !cycleNodes.has(d.id));
            node.classed('highlighted', d => cycleNodes.has(d.id));
            link.classed('faded', d => !(cycleNodes.has(d.source.id || d.source) && cycleNodes.has(d.target.id || d.target)));
        }});
        
        document.getElementById('resetFilters').addEventListener('click', () => {{
            document.getElementById('searchInput').value = '';
            moduleFilter.value = '';
            document.getElementById('typeFilter').value = '';
            node.classed('faded', false).classed('highlighted', false);
            link.classed('faded', false);
        }});
        
        document.getElementById('exportSvg').addEventListener('click', () => {{
            const svgEl = document.getElementById('graph-svg');
            const svgData = new XMLSerializer().serializeToString(svgEl);
            const blob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = '{project_name}_architecture.svg';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }});
        
        document.getElementById('themeToggle').addEventListener('click', () => {{
            document.body.classList.toggle('dark-mode');
            const icon = document.querySelector('#themeToggle i');
            icon.className = document.body.classList.contains('dark-mode') ? 'fas fa-sun' : 'fas fa-moon';
        }});
        
        // Handle window resize
        window.addEventListener('resize', () => {{
            const w = container.clientWidth;
            const h = container.clientHeight;
            svg.attr('width', w).attr('height', h);
            simulation.force('center', d3.forceCenter(w / 2, h / 2));
            simulation.alpha(0.3).restart();
        }});
    </script>
</body>
</html>'''
