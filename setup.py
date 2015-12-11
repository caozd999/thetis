#!/usr/bin/env python

from distutils.core import setup
from glob import glob

setup(name='COFS',
      version='0.1',
      description='Coastal Ocean Flow Solver',
      author='Tuomas Karna',
      author_email='tuomas.karna@gmail.com',
      url='https://bitbucket.org/tkarna/cofs',
      packages=['cofs', 'test', 'examples'],
      scripts=glob('scripts/*'),
     )
