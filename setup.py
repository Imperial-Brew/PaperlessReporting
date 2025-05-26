from setuptools import setup, find_packages

setup(
    name="paperless-reporting",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Flask==2.3.2",
        "gunicorn==21.2.0",
        "requests>=2.28.0",
        "pandas>=1.3.0",
    ],
    python_requires=">=3.8",
) 