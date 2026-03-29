from setuptools import setup, find_packages

setup(
    name="ravn",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "customtkinter>=5.0.0",
        "Pillow>=9.0.0",
        "yt-dlp",
        "requests>=2.31.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "ravn=ravn_app.cli:cli",
        ],
    },
    python_requires=">=3.9",
)
