import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "PyTTP",
    version = "0.1.1",
    author = "Paul Seidel",
    author_email = "puseidel@gmail.com",
    description = ("Small and dirty WSGI-compliant server written entirely in Python"),
    license = "GPL",
    keywords = "http wsgi ORM",
    url = "",
    packages=['pyttp'],
    long_description=read('README'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
        "License :: OSI Approved :: GNU General Public License (GPL)",
    ],
)
