import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="EMS",
    version="0.0.1",
    author="PET Computação UFRGS",
    author_email="pet@inf.ufrgs.br",
    description="The Expressive MIDI Serializer is a tool to turn MIDI files into a model-friendly representation for ML projects.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/petcomputacaoufrgs/EMS",
    project_urls={
        "LSTM model using EMS": "https://github.com/petcomputacaoufrgs/papagaio",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
