from distutils.core import setup, Extension

crackthresh_module = Extension(
    name = 'crackthresh',
    sources = ['src/crackthresh_module.cpp', 'src/point_set.cpp', 'src/filter.cpp'],
    include_dirs = ['include']
)

setup (
    name = 'crackthresh',
    version = '1.0',
    description = 'temp',
    ext_modules = [crackthresh_module]
)
