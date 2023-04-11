.. image:: https://mybinder.org/badge_logo.svg
 :target: https://mybinder.org/v2/gh/takluyver/bash_kernel/master

=========================
A Jupyter kernel for bash
=========================

Installation
------------
This requires IPython 3.

.. code:: shell

    pip install bash_kernel
    python -m bash_kernel.install

To use it, run one of:

.. code:: shell

    jupyter notebook
    # In the notebook interface, select Bash from the 'New' menu
    jupyter qtconsole --kernel bash
    jupyter console --kernel bash

Displaying Rich Content
-----------------------

To use specialized content (images, html, etc) this file defines (in `build_cmds()`) bash functions
that take the contents as standard input. Currently, `display` (images), `displayHTML` (html)
and `displayJS` (javascript) are supported.

Example:

.. code:: shell

    cat dog.png | display
    echo "<b>Dog</b>, not a cat." | displayHTML
    echo "alert('It is known khaleesi\!');" | displayJS

Updating Rich Content Cells
---------------------------

If one is doing something that requires dynamic updates, one can specify a unique display_id,
should be a string name (downstream documentation is not clear on this), and the contents
will be replaced by the new value. Example:

.. code:: shell

    display_id="id_${RANDOM}"
    ((ii=0))
    while ((ii < 10)) ; do
        echo "<div>${ii}</div>" | displayHTML $display_id
        ((ii = ii+1))
        sleep 1
    done

The same works for images or even javascript content.

**Remember to create always a new id** (random ids works perfect) each time the cell is executed, otherwise
it will try to display on an HTML element that no longer exists (they are erased each time a cell is re-run).

Programmatically Generating Rich Content
----------------------------------------

Alternatively one can simply generate the rich content to a file in /tmp (or $TMPDIR)
and then output the corresponding (to the mimetype) context prefix "_TEXT_SAVED_*"
constant. So one can write programs (C++, Go, Rust, etc.) that generates rich content
appropriately, when within a notebook.

The environment variable "NOTEBOOK_BASH_KERNEL_CAPABILITIES" will be set with a comma
separated list of the supported types (currently "image,html,javascript") that a program
can check for.

To output to a particular "display_id", to allow update of content (e.g: dynamically
updating/generating a plot from a command line program), prefix the filename
with "(<display_id>)". E.g: a line to display the contents of /tmp/myHTML.html to
a display id "id_12345" would look like:

    bash_kernel: saved html data to: (id_12345) /tmp/myHTML.html

More Information
----------------

For details of how this works, see the Jupyter docs on `wrapper kernels
<http://jupyter-client.readthedocs.org/en/latest/wrapperkernels.html>`_, and
Pexpect's docs on the `replwrap module
<http://pexpect.readthedocs.org/en/latest/api/replwrap.html>`_.
