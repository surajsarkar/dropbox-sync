from setuptools import setup, find_packages

setup(
    name="sdb-sync",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "dropbox>=11.36.0",
        "python-dotenv>=1.0.0"
    ],
    entry_points={
        "console_scripts": [
            "sdb=sdb.cli:main",
        ],
    },
)
