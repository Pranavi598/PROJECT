# setup.py
from setuptools import setup, find_packages

setup(
    name='filemeta',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'SQLAlchemy',
        'Click',
        'psycopg2-binary', # Or remove if only using SQLite
    ],
    entry_points={
        'console_scripts': [
            'filemeta=filemeta.cli:cli',
        ],
    },
    author='Your Name', # Replace with your name
    author_email='your.email@example.com', # Replace with your email
    description='A CLI tool for managing server file metadata.',
    long_description='', # Temporarily set to empty string as README.md doesn't exist yet
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/filemeta_project', # Replace with your project's URL
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License', # Or choose another license
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)