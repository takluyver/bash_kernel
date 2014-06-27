A simple IPython kernel for bash

This requires IPython 3, which is not yet released.

To test it, install with ``setup.py``, then::

    ipython qtconsole --kernel bash

For details of how this works, see IPython's docs on `wrapper kernels
<http://ipython.org/ipython-doc/dev/development/wrapperkernels.html>`_, and
Pexpect's docs on the `replwrap module
<http://pexpect.readthedocs.org/en/latest/api/replwrap.html>`_
