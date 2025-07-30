"""
Main code analyzer that orchestrates the analysis process.
"""

from pathlib import Path
from typing import List, Optional

from ..core.interfaces import ICodeAnalyzer
from ..core.models import CodeModel, Module, CodeElement, Relationship
from ..core.exceptions import AnalysisError
from ..parsing.ast_parser import ASTParser, ElementExtractor
from ..parsing.call_extractor import CallExtractor
from ..utils.file_utils import FileUtils
from ..utils.logging import logger
from ..config.settings import settings


class CodeAnalyzer(ICodeAnalyzer):
    """Main code analyzer that orchestrates the analysis process."""

    def __init__(self,
                 parser: Optional[ASTParser] = None,
                 file_utils: Optional[FileUtils] = None):
        self.parser = parser or ASTParser()
        self.file_utils = file_utils or FileUtils()
        self.config = settings.analysis

    def analyze_project(self, project_path: Path) -> CodeModel:
        """Analyze a complete project and return a code model."""
        try:
            logger.info(f"Starting analysis of project: {project_path}")

            # Parse all files
            parse_results = self.parser.parse_project(project_path)
            successful_results = [r for r in parse_results if r.success]

            if not successful_results:
                raise AnalysisError("No files could be parsed successfully")

            logger.info(f"Analyzing {len(successful_results)} parsed files")

            # Extract code elements from each file
            all_elements = []
            all_relationships = []
            modules = []

            for result in successful_results:
                module_name = self.file_utils.get_module_name(result.file_path, project_path)

                # Extract elements
                extractor = ElementExtractor(module_name, result.file_path)
                extractor.visit(result.tree)

                # Create module
                module = Module(
                    name=module_name,
                    file_path=result.file_path,
                    elements=extractor.elements,
                    docstring=self._extract_module_docstring(result.tree)
                )
                modules.append(module)
                all_elements.extend(extractor.elements)

                # Extract relationships
                call_extractor = CallExtractor(module_name, result.file_path, extractor.elements)
                # Note: This would need the AST passed to it in a real implementation
                relationships = call_extractor.extract_relationships()
                all_relationships.extend(relationships)

            # Apply filters if configured
            filtered_elements, filtered_relationships = self._apply_filters(
                all_elements, all_relationships
            )

            # Create the code model
            model = CodeModel(
                project_name=project_path.name,
                project_path=project_path,
                modules=modules,
                elements=filtered_elements,
                relationships=filtered_relationships,
                metadata={
                    'total_files_found': len(parse_results),
                    'total_files_parsed': len(successful_results),
                    'total_elements': len(filtered_elements),
                    'total_relationships': len(filtered_relationships)
                }
            )

            logger.info(f"Analysis complete: {len(model.elements)} elements, "
                        f"{len(model.relationships)} relationships")

            return model

        except Exception as e:
            raise AnalysisError(f"Failed to analyze project: {e}") from e

    def _extract_module_docstring(self, tree) -> Optional[str]:
        """Extract the module-level docstring."""
        try:
            import ast
            return ast.get_docstring(tree)
        except:
            return None

    def _apply_filters(self, elements: List[CodeElement],
                       relationships: List[Relationship]) -> tuple[List[CodeElement], List[Relationship]]:
        """Apply configured filters to elements and relationships."""
        filtered_elements = elements

        # Filter private elements if configured
        if not self.config.include_private:
            filtered_elements = [e for e in filtered_elements if not e.is_private]

        # Limit number of elements if configured
        if self.config.max_nodes and len(filtered_elements) > self.config.max_nodes:
            logger.warning(f"Limiting to {self.config.max_nodes} elements (found {len(filtered_elements)})")

            # Sort by complexity and importance, keep the most important ones
            filtered_elements = sorted(
                filtered_elements,
                key=lambda e: (e.complexity, len(e.name)),
                reverse=True
            )[:self.config.max_nodes]

        # Filter relationships to only include those between remaining elements
        element_ids = {e.id for e in filtered_elements}
        filtered_relationships = [
            r for r in relationships
            if r.source_id in element_ids and r.target_id in element_ids
        ]

        return filtered_elements, filtered_relationships
