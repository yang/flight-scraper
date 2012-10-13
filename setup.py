#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
  name = 'flight-scraper',
  version = '0.2',
  packages = find_packages(),
  install_requires =
    '''
    ludibrio>=3.1.0
    selenium>=2.25.0
    parsedatetime>=0.8.7
    path.py>=2.4.1
    ipdb>=0.7
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
