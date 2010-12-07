#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
  name = 'flight-scraper',
  version = '0.1',
  packages = find_packages(),
  install_requires =
    '''
    argparse>=1.1
    ludibrio>=2.0
    selenium>=2.0a5
    '''.split(),
  entry_points = {
    'console_scripts': 'flightscraper = flightscraper:main'
  },
  # extra metadata for pypi
  author = 'Yang Zhang',
  author_email = 'yaaang NOSPAM at REMOVECAPS gmail',
  url = 'http://github.com/yang/flight-scraper',
  description =
    'Drives a browser to search for tickets across multiple airline sites, '
    'scraping/emailing/plotting fare information.',
  license = 'GPL',
  keywords =
    '''
    air airfare airline flight flights search scraper scraping ticket tickets
    travel
    '''.strip(),
  classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Internet :: WWW/HTTP',
  ],
)
