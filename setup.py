from setuptools import setup, find_packages

setup(
    name="alejandro",
    version="0.1.0",
    author="Charlie Mehlenbeck",
    author_email="charlie_inventor2003@yahoo.com",
    description="A voice-controlled interface framework focused on ease of automated self expansion using LLMs.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/inventor2525/Alejandro",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10.12",
    install_requires=[
        "flask",
        "python-socketio",
        "groq",
        "dataclasses-json",
        "nltk",
        "git+https://github.com/inventor2525/RequiredAI.git@main#egg=RequiredAI",
        "git+https://github.com/inventor2525/assistant_merger.git@main#egg=assistant_merger",
        "git+https://github.com/inventor2525/assistant_interaction.git@main#egg=assistant_interaction",
    ],
    extras_require={
        "dev": ["unittest"],
    },
)