from setuptools import setup, Extension
from Cython.Build import cythonize

setup(
    name="chronosmatch",
    version="0.1.0",
    packages=["chronosmatch"],
    ext_modules=cythonize(
        [Extension("chronosmatch.matching_engine", ["chronosmatch/matching_engine.pyx"])],
        compiler_directives={"language_level": 3},
    ),
    zip_safe=False,
)
