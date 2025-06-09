from setuptools import setup, find_packages

# Read the content of README.md
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="pypolycall",
    version="0.1.0",
    description="Python bindings for LibPolyCall",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="OBINexusComputing",
    author_email="nnamdi@obinexuscomputing.com",
    url="https://github.com/obinexuscomputing/pypolycall",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
    install_requires=[
        "aiohttp>=3.7.4",
        "cryptography>=3.4.7",
        "msgpack>=1.0.2",
        "pydantic>=1.8.2",
    ],
    extras_require={
        "dev": [
            "pytest>=6.2.5",
            "pytest-asyncio>=0.15.1",
            "pytest-cov>=2.12.1",
            "black>=21.5b2",
            "isort>=5.9.1",
            "mypy>=0.812",
            "sphinx>=4.0.2",
            "sphinx-rtd-theme>=0.5.2",
        ],
    },
    keywords="polycall, rpc, ipc, network, protocol",
)