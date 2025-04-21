from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="instagram_data_pipeline",
    version="0.1.0",
    author="Ayush Mishra",
    author_email="f20201993@pilani.bits-pilani.ac.in",
    description="A data pipeline for Instagram user analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Dante134/instagram_data_pipeline",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "instagram-pipeline=instagram_pipeline.main:main",
        ],
    },
)