from setuptools import setup  # type: ignore

setup(
    name='glif',
    version='0.0.1',    
    description='GLIF core',
    url='https://github.com/jfschaefer/GLIFcore',
    author='Jan Frederik Schaefer',
    packages=['glif'],
    # license='BSD 2-clause',  # TODO: License (also in classifiers)
    install_requires=[
        'setuptools>=46',
        'requests>=2.23',
        'simplejson',
    ],
    classifiers=[       # https://pypi.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 1 - Planning',
        'Programming Language :: Python :: 3',
    ],
    include_package_data = True,
)
