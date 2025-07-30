"""Setup configuration for py-code-visualizer."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="py-code-visualizer",
    version="1.0.0",
    author="Syed Mohd Haider Rizvi",
    author_email="smhrizvi281@gmail.com",
    description="Transform complex Python codebases into beautiful interactive diagrams",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/haider1998/PyVisualizer",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "networkx>=3.0",
        "click>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
            "coverage>=7.0.0",
        ],
        "rich": [
            "rich>=13.0.0",
            "pydantic>=2.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "py-code-visualizer=pyvizualizer.cli.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
