# hpxqt

`hpxqt` is GUI interface for [hpxclient](https://github.com/chainprox/hpxclient) application.


## What do I need?

### Python3.9+
A compatible version comes preinstalled with most current Linux systems.
If that is not the case consult your distribution for instructions
on how to install Python 3.9+.

### virtualenv or virtualenvwrapper
See detailed installation instructions for [virtualenv](https://virtualenv.pypa.io/en/latest/installation/) or
[virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/install.html).


## Usage

1. Create a top level directory to hold all project files under the same parent directory. For example:
    ```
    $ mkdir ~/chainprox
    ```

1. Create isolated Python environment. Make sure to use python 3.9+:

    * **virtualenv**

    `$ virtualenv -p python3.9 ~/chainprox/env`

    * **virtualenvwrapper**

    `$ mkvirtualenv -p python3.9 chainproxenv`

1. Activate virtual environment created in previous step.

1. Download [hpxqt](https://github.com/chainprox/hpxqt) and [hpxclient](https://github.com/chainprox/hpxclient)
projects and place them under the parent directory created in step 1.

   ```
   $ git clone https://github.com/chainprox/hpxqt ~/chainprox
   $ git clone https://github.com/chainprox/hpxclient ~/chainprox
   ```
1. Each project contains `requirements.txt` file with dependencies. You can install them using `pip`

1. Add parent directory created in the very first step to your `$PYTHONPATH` environment variable.

   For virtualenv you can append the following line to the end of your
   [activate shell script](https://virtualenv.pypa.io/en/latest/userguide/#activate-script). For virtualenvwrapper
   you could use [add2virtualenv](https://virtualenvwrapper.readthedocs.io/en/latest/command_ref.html#add2virtualenv) command.
   For example:

   ```
   export PYTHONPATH="/home/username/chainprox/:$PYTHONPATH"
   ```
1. Run `hpxqt/chainproxy.py` script using `python` to start up an instance of desktop application.
