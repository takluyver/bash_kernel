... image:: https://mybinder.org/badge_logo.svg
 :target: https://mybinder.org/v2/gh/takluyver/bash_kernel/master

A Jupyter kernel for bash

This requires IPython 3.

To install::

    pip install bash_kernel
    python -m bash_kernel.install

To use it, run one of:

.. code:: shell

    jupyter notebook
    # In the notebook interface, select Bash from the 'New' menu
    jupyter qtconsole --kernel bash
    jupyter console --kernel bash

The kernel exports two handy bash functions: `display` to display images; `displayHTML` to display HTML content.

Example:

.. code:: shell

    cat dog.png | display
    echo "<b>Dog</b>, not a cat." | displayHTML

Alternatively one can simply generate the rich content to a file in /tmp (or $TMPDIR)
and then output the corresponding (to the mimetype) context prefix _TEXT_SAVED_*
constant (see `display.py`).

The environment variable "NOTEBOOK_BASH_KERNEL_CAPABILITIES" will be set with a comma
separated list of the supported types (currently "image,html"). This way programs
(in C++, Go, Rust, etc.) can adjust their output to display rich content appropriately.

For details of how this works, see the Jupyter docs on `wrapper kernels
<http://jupyter-client.readthedocs.org/en/latest/wrapperkernels.html>`_, and
Pexpect's docs on the `replwrap module
<http://pexpect.readthedocs.org/en/latest/api/replwrap.html>`_
