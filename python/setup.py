#!/usr/bin/env python3
"""Setup script for MCP Descope SDK."""

from setuptools import setup, find_packages

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements from pyproject.toml
with open("pyproject.toml", "r", encoding="utf-8") as fh:
    content = fh.read()
    # Simple parsing for dependencies
    start = content.find('dependencies = [')
    if start != -1:
        end = content.find(']', start)
        deps_section = content[start:end]
        dependencies = []
        for line in deps_section.split('\n'):
            line = line.strip()
            if line.startswith('"') and line.endswith('",'):
                dep = line[1:-2]  # Remove quotes and comma
                dependencies.append(dep)
    else:
        dependencies = [
            "mcp>=1.0.0",
            "descope>=1.0.0",
            "pydantic>=2.0.0",
            "typing-extensions>=4.0.0",
        ]

setup(
    name="descope-mcp",
    version="0.1.0",
    author="Descope",
    author_email="support@descope.com",
    description="Descope Python MCP SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/descope/descope-ai",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.10",
    install_requires=dependencies,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=26.10.1",
            "isort>=5.12.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "descope-mcp-server=descope_mcp.server:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 