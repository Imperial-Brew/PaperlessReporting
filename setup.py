from setuptools import setup, find_packages

setup(
    name="paperless-reporting",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Flask==3.1.2",
        "gunicorn==25.0",
        "requests>=2.28.0",
        "pandas>=1.3.0",
        "tqdm>=4.64.0",
        "python-dotenv>=0.19.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "aiohttp-test-utils>=0.1.0",
        "aiohttp~=3.12.2",
        "setuptools~=78.1.1",
        "boto3>=1.28.0",
    ],
    python_requires=">=3.8",
) 
