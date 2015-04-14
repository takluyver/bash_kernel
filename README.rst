A simple IPython kernel for bash

This requires IPython 3.

To use it, install with ``pip install bash_kernel``, and then run one of:

.. code:: shell

    ipython notebook
    # In the notebook interface, select Bash from the 'New' menu
    ipython qtconsole --kernel bash
    ipython console --kernel bash

For details of how this works, see IPython's docs on `wrapper kernels
<http://ipython.org/ipython-doc/dev/development/wrapperkernels.html>`_, and
Pexpect's docs on the `replwrap module
<http://pexpect.readthedocs.org/en/latest/api/replwrap.html>`_
