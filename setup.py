from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='DeliciousBackup',
      version=version,
      description="Backup your del.icio.us bookmarks",
      long_description=""" This script will backup all of your
del.icio.us bookmarks and tags into an sqlite database. It will even
preserve the tag/bookmark associations.

Currently this script only supports the v1 API and will blindly fetch
all of your bookmarks every time you run it. Future versions will be
smarter about about this and support the v2 API as well.
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='J Kenneth King',
      author_email='james@agentultra.com',
      url='',
      license='GPLv2',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
        'DeliciousAPI',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [console-scripts]
      dbackup = deliciousbackup:main
      """,
      )
