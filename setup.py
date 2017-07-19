from distutils.core import setup

setup(
    name='friends',
    version='0.1.0',
    author='Mikael Frykholm',
    author_email='mikael@frykholm.com',
    packages=['friends'],
    
    url='https://github.com/mikaelfrykholm/friends/',
    license='LICENSE.txt',
    description='Ostatus app.',
    long_description=open('README.md').read(),
    install_requires=[
        "tornado >= 3.1",
    ],
)
