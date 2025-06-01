#!/usr/bin/env python3
"""
PyPolyCall Package Setup - Modern Packaging Standards
Python binding for LibPolyCall with strict port mapping
Uses wheel format, not egg - Python 3.8+ compatible
"""

from setuptools import setup, find_packages
import os
import sys

# Ensure Python 3.8+
if sys.version_info < (3, 8):
    sys.exit("PyPolyCall requires Python 3.8 or higher")

# Read README
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "PyPolyCall - Python binding for LibPolyCall"

# Read requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="pypolycall",
    version="1.0.0",
    description="Python binding for LibPolyCall - Modern packaging with wheel format",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    
    author="OBINexusComputing",
    author_email="nnamdi@obinexuscomputing.com",
    url="https://gitlab.com/obinexuscomputing/libpolycall",
    
    # Modern package discovery
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    # Include package data
    include_package_data=True,
    package_data={
        "": [
            "*.polycallrc",
            "*.md", 
            "*.txt",
            "*.html"
        ]
    },
    
    # Python version requirement - STRICT 3.8+
    python_requires=">=3.8",
    
    # No external dependencies (zero-trust principle)
    install_requires=[],
    
    # Development dependencies (optional)
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=22.0",
            "flake8>=4.0",
        ],
        "test": [
            "pytest>=6.0",
            "requests>=2.25.0",
        ],
    },
    
    # Modern classifiers
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Operating System :: OS Independent",
    ],
    
    # Keywords for PyPI
    keywords=[
        "libpolycall",
        "polycall", 
        "python-binding",
        "zero-trust",
        "port-mapping",
        "wheel-format"
    ],
    
    # Console scripts
    entry_points={
        "console_scripts": [
            "pypolycall-server=examples.server:main",
        ],
    },
    
    # Project URLs
    project_urls={
        "Bug Reports": "https://gitlab.com/obinexuscomputing/libpolycall/-/issues",
        "Source": "https://gitlab.com/obinexuscomputing/libpolycall",
        "Documentation": "https://gitlab.com/obinexuscomputing/libpolycall/-/blob/main/README.md",
    },
    
    # License
    license="MIT",
    
    # Modern packaging options - WHEEL FORMAT, NOT EGG
    options={
        "bdist_wheel": {
            "universal": False,  # Python 3.8+ only
        },
        "egg_info": {
            "tag_build": "",
            "tag_date": False,
        }
    },
    
    # Ensure wheel format, disable egg
    zip_safe=False,
    
    # Setup requires modern setuptools
    setup_requires=[
        "setuptools>=45",
        "wheel>=0.36",
    ],
)

# Post-install verification
def verify_installation():
    """Verify installation completed successfully"""
    try:
        import pypolycall
        print(f"\n✅ PyPolyCall v{pypolycall.__version__} installed successfully!")
        print("📡 Port mapping: 3001:8084 (RESERVED FOR PYTHON)")
        print("🛡️  Zero-trust configuration required")
        return True
    except ImportError as e:
        print(f"\n❌ Installation verification failed: {e}")
        return False

if __name__ == "__main__": print("🐍 Installing PyPolyCall with modern 
    packaging...") print("📦 Format: wheel (.whl), not egg") print("🐍 Python: 
    3.8+ required") print("🛡️ Zero-trust: Manual configuration required")
