GLIF Core
=========

*This is an on-going effort to re-implement [https://github.com/kwarc/glif](GLIF) independently of Jupyter and add new features.*

This repository contains the `glif` package.
It enables the user to access GLIF's functionality using Python.
In the future, command line tools for using GLIF may be added.
For beginners it is recommended to use the [https://github.com/jfschaefer/GLIFKernel](Jupyter interface for GLIF)


#### Installation
**Note:** If you only want to use the Jupyter interface, you may follow the instructions for the [https://github.com/jfschaefer/GLIFKernel](GLIFkernel repository).

Requirements:
* A recent Python version (at least 3.7)
* `pip` (you can use `python3 -m pip` to ensure pip corresponds to the right python installation)
* `setuptools` (probably preinstalled, otherwise do `pip install setuptools`)
* `git` for the installation from github

Other dependencies:
* [https://www.grammaticalframework.org/](GF), [https://uniformal.github.io/](MMT) and [https://github.com/lpcic/elpi](ELPI), which GLIF is based on.
    Note that you only need to install the frameworks you actually want to use (i.e. you can e.g. not install ELPI if you don't plan to use it).
    To help GLIF find MMT, you should set the `MMT_JAR` environment variable to the installation destination (`export MMT_JAR=/path/to/mmt.jar`).
* [https://www.graphviz.org/](Graphviz), specifically `dot`, if you want to  visualize ASTs.

```
pip install git+https://github.com/jfschaefer/GLIFcore.git#egg=glif
```
or
```
git clone https://github.com/jfschaefer/GLIFcore.git
cd GLIFcore
pip install .
```


#### Development
To run all unittest, execute the following command in the root folder of the repository:
```
python -m unittest discover -v
```
The type annotations can be checked with `mypy` (`pip install mypy`):
```
mypy .
```

