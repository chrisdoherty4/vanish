from setuptools import setup
from codecs import open
from os import path, makedirs
from vanish.__version__ import VERSION
from vanish.config import config

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'requirements.txt'), encoding="utf-8") as f:
    requirements = f.read().split("\n")

with open(path.join(here, 'README.md'), encoding="utf-8") as f:
    long_description = f.read()

if not path.exists(config["ovpn.configs.path"]):
    makedirs(config["ovpn.configs.path"])

setup(
    name='vanish',
    version=VERSION,
    description='A command line tool for interacting with IPVanish servers',
    lond_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/chrisdoherty4/vanish',

    author='Chris Doherty',
    author_email='chris.doherty4@gmail.com',

    maintainer='Chris Doherty',
    maintainer_email='chris.doherty4@gmail.com',

    license='GPL-3.0',

    packages=['vanish'],

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Topic :: System :: Networking',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only'
    ],

    keywords='ipvanish vanish vpn openvpn',

    install_requires=requirements,

    scripts=['bin/vanish']
)
