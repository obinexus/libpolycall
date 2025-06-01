from setuptools import setup, find_packages

setup(
    name="pypolycall",
    version="1.0.0", 
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    zip_safe=False
)
