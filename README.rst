A simple IPython kernel for bash

This requires IPython 3.

To install::

    pip install bash_kernel
    python -m bash_kernel.install

To use it, run one of:

.. code:: shell

    ipython notebook
    # In the notebook interface, select Bash from the 'New' menu
    ipython qtconsole --kernel bash
    ipython console --kernel bash

For details of how this works, see the Jupyter docs on `wrapper kernels
<http://jupyter-client.readthedocs.org/en/latest/wrapperkernels.html>`_, and
Pexpect's docs on the `replwrap module
<http://pexpect.readthedocs.org/en/latest/api/replwrap.html>`_
