from setuptools import setup, find_packages

import bash_kernel

DESCRIPTION = bash_kernel.__doc__
VERSION = bash_kernel.__version__

setup(
    name='bash_kernel',
    version=VERSION,
    packages=find_packages(),

    author='Thomas Kluyver',
    author_email='thomas@kluyver.me.uk',
    description=DESCRIPTION,
    license='BSD',
    url='https://github.com/takluyver/bash_kernel',
    long_description=open("README.rst").read(),
    install_requires=["pexpect>=3.3"],
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Shells"
    ]
)
