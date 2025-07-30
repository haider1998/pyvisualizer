"""
Command line interface for PyVisualizer.
"""

import argparse
import sys
from pathlib import Path

from ..core.models import VisualizationRequest
from ..analysis.code_analyzer import CodeAnalyzer
from ..visualization.mermaid import MermaidVisualizer
from ..visualization.d3js import D3JSVisualizer
from ..utils.logging import logger, setup_logging
from ..config.settings import settings


def create_parser() -> argparse.ArgumentParser:
    """Create the command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Generate beautiful visualizations of Python code architecture',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        'path',
        type=Path,
        help='Path to Python project or file to analyze'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file path'
    )

    parser.add_argument(
        '--format', '-f',
        choices=['html', 'mermaid', 'svg', 'png'],
        default='html',
        help='Output format'
    )

    parser.add_argument(
        '--modules', '-m',
        nargs='+',
        help='Include only specified modules'
    )

    parser.add_argument(
        '--exclude', '-x',
        nargs='+',
        help='Exclude specified modules'
    )

    parser.add_argument(
        '--entry', '-e',
        help='Entry point function for depth-limited analysis'
    )

    parser.add_argument(
        '--depth', '-d',
        type=int,
        help='Maximum depth from entry point'
    )

    parser.add_argument(
        '--max-nodes',
        type=int,
        default=150,
        help='Maximum number of nodes to include'
    )

    parser.add_argument(
        '--project-name', '-p',
        help='Project name for visualization title'
    )

    parser.add_argument(
        '--no-private',
        action='store_true',
        help='Exclude private methods and functions'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser


def get_visualizer(format: str):
    """Get the appropriate visualizer for the format."""
    if format == 'html':
        return D3JSVisualizer()
    elif format in ['mermaid', 'mmd']:
        return MermaidVisualizer()
    else:
        # For other formats, we'll use Mermaid as a fallback
        # In a full implementation, you'd add SVG/PNG visualizers
        logger.warning(f"Format {format} not fully implemented, using Mermaid")
        return MermaidVisualizer()


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        settings.logging.level = "DEBUG"
    setup_logging(settings.logging)

    try:
        # Validate input path
        if not args.path.exists():
            logger.error(f"Path does not exist: {args.path}")
            sys.exit(1)

        # Determine output path
        output_path = args.output
        if not output_path:
            project_name = args.project_name or args.path.name
            extension = 'html' if args.format == 'html' else 'mmd'
            output_path = Path(f"{project_name}_visualization.{extension}")

        # Determine project name
        project_name = args.project_name or args.path.name

        # Create visualization request
        request = VisualizationRequest(
            project_path=args.path,
            output_path=output_path,
            format=args.format,
            include_modules=args.modules,
            exclude_modules=args.exclude,
            max_depth=args.depth,
            entry_point=args.entry,
            max_nodes=args.max_nodes,
            show_private=not args.no_private
        )

        # Analyze the project
        logger.info(f"Analyzing project: {args.path}")
        analyzer = CodeAnalyzer()
        model = analyzer.analyze_project(args.path)

        if not model.elements:
            logger.warning("No code elements found to visualize")
            sys.exit(0)

        # Generate visualization
        visualizer = get_visualizer(args.format)
        result = visualizer.create_visualization(model, request)

        if result.success:
            logger.info(f"Visualization created successfully: {result.output_path}")
            if result.metrics:
                logger.info(f"Elements: {result.metrics.get('elements_count', 0)}, "
                            f"Relationships: {result.metrics.get('relationships_count', 0)}")
        else:
            logger.error(f"Failed to create visualization: {result.error_message}")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
