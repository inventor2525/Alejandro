from setuptools import setup, find_packages

setup(
    name="alejandro",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ]
    },
    python_requires=">=3.8",
    author="Charlie",
    description="A voice-controlled interface framework",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    license="MIT",
)
