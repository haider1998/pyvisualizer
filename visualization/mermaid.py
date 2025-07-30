"""
Mermaid diagram visualization generator.
"""

from typing import Dict, List

from ..core.models import CodeModel, VisualizationRequest, ElementType
from .base import BaseVisualizer
from .templates.mermaid_template import MERMAID_HTML_TEMPLATE


class MermaidVisualizer(BaseVisualizer):
    """Generates Mermaid diagrams."""

    def __init__(self):
        super().__init__("Mermaid", ["mermaid", "mmd"])

        # Color scheme for different element types
        self.colors = {
            ElementType.MODULE: {"primary": "#5D2E8C", "secondary": "#7B4BAF"},
            ElementType.CLASS: {"primary": "#2962FF", "secondary": "#5C8AFF"},
            ElementType.CONSTRUCTOR: {"primary": "#E53935", "secondary": "#EF5350"},
            ElementType.METHOD: {"primary": "#00C853", "secondary": "#4CD964"},
            ElementType.FUNCTION: {"primary": "#00C853", "secondary": "#4CD964"},
            ElementType.ASYNC_METHOD: {"primary": "#AA00FF", "secondary": "#CE93D8"},
            ElementType.PROPERTY: {"primary": "#FF6D00", "secondary": "#FFAB40"},
            ElementType.STATIC_METHOD: {"primary": "#00B0FF", "secondary": "#80D8FF"},
            ElementType.PRIVATE_METHOD: {"primary": "#757575", "secondary": "#BDBDBD"},
        }

    def _generate_content(self, model: CodeModel, request: VisualizationRequest) -> str:
        """Generate Mermaid diagram content."""
        if request.format == "mermaid" or request.format == "mmd":
            return self._generate_mermaid_code(model)
        else:
            # Generate HTML with embedded Mermaid
            mermaid_code = self._generate_mermaid_code(model)
            return MERMAID_HTML_TEMPLATE.format(
                project_name=model.project_name,
                mermaid_code=mermaid_code
            )

    def _generate_mermaid_code(self, model: CodeModel) -> str:
        """Generate the Mermaid diagram code."""
        lines = [
            "flowchart TD",
            "    %% Nodes"
        ]

        # Group elements by module
        modules = {}
        for element in model.elements:
            if element.module not in modules:
                modules[element.module] = []
            modules[element.module].append(element)

        node_counter = 0
        node_map = {}  # element_id -> node_id

        # Generate nodes grouped by module
        for module_name, elements in sorted(modules.items()):
            module_id = f"mod{len(node_map)}"
            lines.append(f"    subgraph {module_id}[\"{module_name}\"]")

            # Group by class within module
            classes = {}
            standalone_functions = []

            for element in elements:
                if element.class_name:
                    if element.class_name not in classes:
                        classes[element.class_name] = []
                    classes[element.class_name].append(element)
                else:
                    standalone_functions.append(element)

            # Generate class subgraphs
            for class_name, methods in classes.items():
                class_short_name = class_name.split('.')[-1]
                class_id = f"cls{node_counter}"
                node_counter += 1

                lines.append(f"        subgraph {class_id}[\"{class_short_name}\"]")

                for method in methods:
                    node_id = f"n{node_counter}"
                    node_counter += 1
                    node_map[method.id] = node_id

                    icon = self._get_element_icon(method)
                    style_class = self._get_style_class(method.element_type)

                    lines.append(f"            {node_id}[\"{icon} {method.name}\"]:::{style_class}")

                lines.append("        end")

            # Generate standalone functions
            for function in standalone_functions:
                node_id = f"n{node_counter}"
                node_counter += 1
                node_map[function.id] = node_id

                icon = self._get_element_icon(function)
                style_class = self._get_style_class(function.element_type)

                lines.append(f"        {node_id}[\"{icon} {function.name}\"]:::{style_class}")

            lines.append("    end")

        # Generate relationships
        lines.append("")
        lines.append("    %% Relationships")

        for relationship in model.relationships:
            source_node = node_map.get(relationship.source_id)
            target_node = node_map.get(relationship.target_id)

            if source_node and target_node:
                lines.append(f"    {source_node} --> {target_node}")

        # Generate styles
        lines.extend(self._generate_styles())

        return "\n".join(lines)

    def _get_element_icon(self, element) -> str:
        """Get Font Awesome icon for element type."""
        icon_map = {
            ElementType.CLASS: "fa:fa-cube",
            ElementType.CONSTRUCTOR: "fa:fa-play-circle",
            ElementType.METHOD: "fa:fa-code-branch",
            ElementType.FUNCTION: "fa:fa-code-branch",
            ElementType.ASYNC_METHOD: "fa:fa-bolt",
            ElementType.PROPERTY: "fa:fa-lock",
            ElementType.STATIC_METHOD: "fa:fa-cog",
            ElementType.PRIVATE_METHOD: "fa:fa-key",
        }
        return icon_map.get(element.element_type, "fa:fa-code")

    def _get_style_class(self, element_type: ElementType) -> str:
        """Get CSS style class for element type."""
        return element_type.value.replace('_', '-')

    def _generate_styles(self) -> List[str]:
        """Generate CSS styles for the diagram."""
        styles = [
            "",
            "    %% Styles",
        ]

        for element_type, colors in self.colors.items():
            class_name = self._get_style_class(element_type)
            styles.append(
                f"    classDef {class_name} "
                f"color:#ffffff, fill:{colors['primary']}, stroke:{colors['secondary']}"
            )

        return styles
