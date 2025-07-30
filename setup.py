# setup.py

from setuptools import setup, find_packages

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name="pyvizualizer",
    version="0.1.0",
    author="Syed Mohd Haider Rizvi",
    author_email="smhrizvi281@gmail.com",
    description="Visualize Python project workflows using Mermaid diagrams",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/haider1998/PyVisualizer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
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
    entry_points={
        'console_scripts': [
            'pyvizualizer=pyvizualizer.cli:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
