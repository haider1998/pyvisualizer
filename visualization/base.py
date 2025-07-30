"""
Base classes for visualization generation.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from ..core.interfaces import IVisualizer
from ..core.models import CodeModel, VisualizationRequest, VisualizationResult
from ..utils.logging import logger


class BaseVisualizer(IVisualizer):
    """Base class for all visualizers."""

    def __init__(self, name: str, supported_formats: list):
        self.name = name
        self.supported_formats = supported_formats

    def supports_format(self, format: str) -> bool:
        """Check if this visualizer supports the given format."""
        return format.lower() in self.supported_formats

    def create_visualization(self, model: CodeModel, request: VisualizationRequest) -> VisualizationResult:
        """Create a visualization from a code model."""
        try:
            logger.info(f"Creating {request.format} visualization with {self.name}")

            # Apply filters if specified
            filtered_model = self._apply_request_filters(model, request)

            # Generate the visualization content
            content = self._generate_content(filtered_model, request)

            # Write to output file
            self._write_output(content, request.output_path)

            return VisualizationResult(
                success=True,
                output_path=request.output_path,
                metrics={
                    'elements_count': len(filtered_model.elements),
                    'relationships_count': len(filtered_model.relationships),
                    'output_size_bytes': request.output_path.stat().st_size if request.output_path.exists() else 0
                }
            )

        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            return VisualizationResult(
                success=False,
                error_message=str(e)
            )

    @abstractmethod
    def _generate_content(self, model: CodeModel, request: VisualizationRequest) -> str:
        """Generate the visualization content."""
        pass

    def _apply_request_filters(self, model: CodeModel, request: VisualizationRequest) -> CodeModel:
        """Apply filters specified in the visualization request."""
        filtered_elements = model.elements

        # Module filters
        if request.include_modules:
            filtered_elements = [
                e for e in filtered_elements
                if any(e.module.startswith(m) for m in request.include_modules)
            ]

        if request.exclude_modules:
            filtered_elements = [
                e for e in filtered_elements
                if not any(e.module.startswith(m) for m in request.exclude_modules)
            ]

        # Private element filter
        if not request.show_private:
            filtered_elements = [e for e in filtered_elements if not e.is_private]

        # Node limit
        if len(filtered_elements) > request.max_nodes:
            logger.warning(f"Limiting to {request.max_nodes} elements")
            # Sort by complexity and keep the most complex/important ones
            filtered_elements = sorted(
                filtered_elements,
                key=lambda e: (e.complexity, len(e.name)),
                reverse=True
            )[:request.max_nodes]

        # Filter relationships
        element_ids = {e.id for e in filtered_elements}
        filtered_relationships = [
            r for r in model.relationships
            if r.source_id in element_ids and r.target_id in element_ids
        ]

        # Create filtered model
        filtered_model = CodeModel(
            project_name=model.project_name,
            project_path=model.project_path,
            modules=model.modules,
            elements=filtered_elements,
            relationships=filtered_relationships,
            cycles=model.cycles,
            metadata=model.metadata
        )

        return filtered_model

    def _write_output(self, content: str, output_path: Path) -> None:
        """Write content to output file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding='utf-8')
        logger.info(f"Visualization saved to {output_path}")
