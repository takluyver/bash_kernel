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


`pipx` and "externally managed" environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A recent-ish `PEP 668 <https://peps.python.org/pep-0668/#guide-users-towards-virtual-environments>`_ recommends that users install Python applications with `pipx` rather than global installs with `pip`. This is strongly suggested/enforced in current Linux distros. Because `bash_kernel` needs an extra step to actually work after installing with `pip` or `pipx`, this causes some inconvenience.

First, one must install the Jupyter ecosystem with pipx, and then inject bash_kernel (and any other bits of the jupyter ecosystem you use, like papermill) into the same pipx venv.

.. code:: shell

    pipx install --include-deps jupyter
    pipx inject --include-apps --include-deps jupyter bash_kernel

One then must manually find the corresponding venv, activate it, and run `python -m bash_kernel.install` *within* that virtual env. If done outside it, this won't work as bash_kernel is not installed in the global environment.

.. code:: shell

    cd ~/.local/pipx/venvs/jupyter/
    source bin/activate
    python -m bash_kernel.install
    deactivate

Of course, one can also install bash_kernel to the global environement thusly:

.. code:: shell

    pip install --break-system-packages juptyer bash_kernel
    python -m bash_kernel.install

Requirements of Bash
~~~~~~~~~~~~~~~~~~~~

Bash kernel directly interacts with bash, and therefore requires a functioning interactive build of bash. In nearly all cases this will be the default, however some distributions remove GNU readline or other interactivity features of bash. Almost always, these features are provided in a separate, more complete bash package, which should be installed. See for example https://github.com/takluyver/bash_kernel/issues/142.

Using a custom bash command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default the kernel launches the ``bash`` found on your ``PATH``. You can
override this by setting the ``BASH_KERNEL_CMD`` environment variable before
starting Jupyter. You can put in whatever you like here, as long as it starts an
interactive ``bash``.

This is useful for running the kernel inside a container, or via any other
wrapper that eventually launches ``bash``. For example, to run the kernel's
bash inside an `Apptainer <https://apptainer.org/>`_ (formerly Singularity)
container:

.. code:: shell

    export BASH_KERNEL_CMD="apptainer exec --nv container.sif bash"
    jupyter notebook

To make the override available as its own entry in the Jupyter kernel menu
(instead of exporting the variable globally), install a dedicated kernelspec
whose ``kernel.json`` sets the variable in its ``env`` block. This also lets a
plain-bash kernel and a wrapped kernel coexist:

.. code:: json

    {
      "argv": ["python", "-m", "bash_kernel", "-f", "{connection_file}"],
      "display_name": "Bash (container)",
      "language": "bash",
      "env": { "BASH_KERNEL_CMD": "apptainer exec --nv container.sif bash" }
    }

**Note:** the bash startup file must be readable from inside the wrapper. The
kernel places it in ``$TMPDIR`` (or ``/tmp``), so this works automatically as
long as that directory is shared with the wrapper at the same path -- Apptainer
does this for ``/tmp`` by default. Other runtimes may need an explicit mount
(e.g. Docker's ``-v /tmp:/tmp``), and pointing ``$TMPDIR`` at a directory the
wrapper can't see will prevent startup.

Displaying Rich Content
-----------------------

To use specialized content (images, html, etc) this file defines (in `build_cmds()`) bash functions
that take the contents as standard input. Currently, `display` (images), `displayHTML` (html)
and `displayJS` (javascript) are supported.

Example:

.. code:: shell

    cat dog.png | display
    echo "<b>Dog</b>, not a cat." | displayHTML
    echo "alert('Hello from bash_kernel\!');" | displayJS

Updating Rich Content Cells
---------------------------

If one is doing something that requires dynamic updates, one can specify a unique display_id,
which should be a string name. On each update, the contents will be replaced by the new value. Example:

.. code:: shell

    display_id="id_${RANDOM}"
    ((ii=0))
    while ((ii < 10)) ; do
        echo "<div>${ii}</div>" | displayHTML $display_id
        ((ii = ii+1))
        sleep 1
    done

The same works for images and javascript content.

**Remember to create always a new id** each time the cell is executed, otherwise it will try to display
on an HTML element that no longer exists (they are erased each time a cell is re-run).

Programmatically Generating Rich Content
----------------------------------------

Alternatively one can simply generate the rich content to a file in /tmp (or $TMPDIR)
and then output the corresponding (to the mimetype) context prefix ``"_TEXT_SAVED_*"``
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
