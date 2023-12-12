import setuptools  # type: ignore

setuptools.setup(
    name='glif',
    version='0.1.0',
    description='GLIF core',
    url='https://github.com/jfschaefer/GLIFcore',
    author='Jan Frederik Schaefer',
    packages=setuptools.find_packages(),
    # license='BSD 2-clause',  # TODO: License (also in classifiers)
    install_requires=[
        'setuptools>=46',
        'requests>=2.23',
        'simplejson',
    ],
    classifiers=[  # https://pypi.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
    ],
    include_package_data=True,
)
