# setup.py

from setuptools import setup, find_packages

setup(
    name='udecimal',
    version='0.1.0',
    author='Arthem Harutiunyan',
    author_email='arthemharutiunyan@gmail.com',
    description='Пакет для работы с десятичными числами с учётом неопределённостей и ковариаций',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/skyfet/udecimal',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=[
        'mpmath>=1.2.1',
    ],
    extras_require={
        'dev': [
            'pytest>=6.0'
        ],
    },
)
