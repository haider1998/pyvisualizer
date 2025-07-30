# setup.py

from setuptools import setup, find_packages

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name="py-code-visualizer",
    version="0.1.0",
    author="Syed Mohd Haider Rizvi",
    author_email="smhrizvi281@gmail.com",
    description="Architectural intelligence for Python codebases. Transform complex systems into stunning interactive diagrams.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/haider1998/PyVisualizer",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
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
    python_requires='>=3.8',
    install_requires=[
        "click>=8.0.0",
        "networkx>=3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black",
            "flake8",
            "mypy",
        ],
        "build": [
            "build",
            "twine",
            "setuptools>=68.0.0",
        ]
    },
    entry_points={
        'console_scripts': [
            'py-code-visualizer=pyvizualizer.pyvizualizer.cli:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
