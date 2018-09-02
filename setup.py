from setuptools import setup
from os.path import join, dirname

setup(
    name = "botovod",
    version = "1.0",
    
    author = "Oleg Yurchik",
    author_email = "oleg.yurchik@protonmail.com",
    url = "https://github.com/OlegYurchik/botovod",
    
    description = "",
    long_description = open(join(dirname(__file__), "README.md")).read(),
    
    packages = ["botovod", "botovod.agents"],
    package_dir = {"botovod": "src"},
    install_requires = ["requests"],
)
