#!/usr/bin/env python

from setuptools import setup, find_packages
import warnings

isrelease = True

version = '0.7.0'

if not isrelease:
    import subprocess
    try:
        pipe = subprocess.Popen(
            ["git", "describe", "--always", "--match", "v[0-9]*"],
            stdout=subprocess.PIPE)
        (version, stderr) = pipe.communicate()
    except:
        warnings.warn("WARNING: Couldn't get git revision, using generic "
                      "version string")

setup(name='mpas_analysis',
      version=version,
      description='Analysis for Model for Prediction Across Scales (MPAS) '
                  'simulations.',
      url='https://github.com/MPAS-Dev/MPAS-Analysis',
      author='MPAS-Analysis Developers',
      author_email='mpas-developers@googlegroups.com',
      license='BSD',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Intended Audience :: Science/Research',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Topic :: Scientific/Engineering',
      ],
      packages=find_packages(),
      package_data={'mpas_analysis': ['config.default'],
                    'mpas_analysis.shared.html': ['templates/*'],
                    'mpas_analysis.test': ['test*/*', 'test*/*/*']},
      install_requires=['numpy', 'scipy', 'matplotlib', 'netCDF4', 'xarray',
                        'dask', 'bottleneck', 'basemap', 'lxml', 'nco',
                        ' pyproj', 'pillow'],
      scripts=['run_mpas_analysis'])
