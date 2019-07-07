from setuptools import setup, find_packages
from os.path import join, dirname


setup(
    name = "botovod",
    version = "0.1",
    
    author = "Oleg Yurchik",
    author_email = "oleg.yurchik@protonmail.com",
    url = "https://github.com/OlegYurchik/botovod",
    
    description = "",
    long_description = open(join(dirname(__file__), "README.md")).read(),
    
    packages = find_packages(),
    install_requires = ["requests"],
)
