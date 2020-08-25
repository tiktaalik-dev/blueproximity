---
BlueProximity
---
>This software helps you add a little more security to your
desktop. It does so by detecting one of your bluetooth devices, 
most likely your mobile phone, and keeping track of its distance. 

[![Python Version][python-image]][python-url]
[![Download from][github-downloads-image]][github-downloads-url]

>## Note from the maintainer of this fork ##
>This current version (1.3.1) only upgraded the original code to make it run in Python 3 / GTK+ 3.
I have respected the original work from Lars Friedrichs as much as possible.
In the future, if there's interest on this software I might continue developing it under a new name. Just let me know :-)
> - Rodrigo Gambra-Middleton (rodrigo@tiktaalik.dev)
## Description from the original author
>If you move away from your computer and the distance is above
a certain level for a 
given time, it automatically locks your desktop 
(or starts any other shell command you want).

>Once away your computer awaits its master back - if you are 
nearer than a given level for a set time your computer unlocks 
magically without any interaction 
(or starts any other shell command you want).

>See the doc/ directory or the website which both contain
a manual with screenshots.

>Please note that there might still some bugs, use the sourceforge 
site to keep track of them or tell me about new ones not mentioned 
there. 
>Please read the whole manual - it's short enough, hopefully easy 
understandable and hey - it even got some pretty pictures in there
too :-)

## Installation
Note from the maintainer of this fork (RGM):
>For the moment, this application hasn't been packaged for installation as a .deb or .rpm.
If you know how to do it, please reach out and I'll include such packages!

## Development setup

Create a virtual environment for Python 3.8 and install the 
required libraries using the requirements.txt file.

```sh
cd my-blueproximity-project/
virtualenv --python=python3.8 venvs/venv3.8
source venvs/venv-3.8/bin/activate
pip3 install -r requirements.txt
```

## Configuration
Note from the 'maintainer' of this fork (RGM):
>The only important configuration for this version is to set the correct path where the software will be installed.
If you download this software and you run it as a local user from a folder in your home directory,
then you don't have to change anything. But if you're creating an installation package for a distribution,
please take care of setting the right path in the variable dist_path that you will find at the beginning of the 
proximity.py script.

## Release History

* 1.3.2 Fixed README.md (this file) mistake
* 1.3.1 Bug fix
* 1.3.0 Updated application so it now runs in Python 3 and GTK+ 3

## About the maintainer of this fork

Rodrigo Gambra – [@TiktaalikDev](https://twitter.com/TiktaalikDev) – rodrigo@tiktaalik.dev

## License
Distributed under the GPL v.2 license. See ``COPYING`` for more information.

     Blueproximity - Desktop application to lock/unlock your screen automatically based on detecting
                     how close it's another Bluetooth device (e.g. your mobile phone).
    
     Copyright (C) 2007 Lars Friedrichs <larsfriedrichs@gmx.de>

     This program is free software: you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation, either version 3 of the License, or
     (at your option) any later version.

     This program is distributed in the hope that it will be useful,
     but WITHOUT ANY WARRANTY; without even the implied warranty of
     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
     GNU General Public License for more details.

     You should have received a copy of the GNU General Public License
     along with this program.  If not, see <https://www.gnu.org/licenses/>.


[https://github.com/tiktaalik-dev/blueproximity/](https://github.com/tiktaalik-dev/blueproximity/)

## Contributing

1. Fork it (<https://github.com/tiktaalik-dev/blueproximity/>)
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Commit your changes (`git commit -am 'Add some fooBar'`)
4. Push to the branch (`git push origin feature/fooBar`)
5. Create a new Pull Request

## Acknowledgements

Here's a list on contributors to the source:
1. Lars Friedrichs (Author)
2. Tobias Jakobs (GUI optimizations)
3. Zsolt Mazolt (GUI and KDE stuff)
4. Rodrigo Gambra-Middleton (Upgrade to run in Python3 and GTK+ 3. Maintainer of this fork)
5. Dan Bader for providing a free README.md template for this documentation. 
See [https://dbader.org/blog/write-a-great-readme-for-your-github-project](https://dbader.org/blog/write-a-great-readme-for-your-github-project)

<!-- Markdown link & img dfn's -->
[python-image]: https://img.shields.io/badge/python-3.8-blue
[python-url]: https://www.python.org/downloads/release/python-370/
[github-downloads-image]: https://img.shields.io/badge/Download%20from-GitHub-orange
[github-downloads-url]: https://github.com/doctortoffu/Event-Info-Bot
