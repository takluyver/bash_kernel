import json
import os
import sys

from jupyter_client.kernelspec import install_kernel_spec
from IPython.utils.tempdir import TemporaryDirectory

kernel_json = {"argv":[sys.executable,"-m","bash_kernel", "-f", "{connection_file}"],
 "display_name":"Bash",
 "language":"bash",
 "codemirror_mode":"shell",
 "env":{"PS1": "$"}
}

def install_my_kernel_spec(user=True):
    with TemporaryDirectory() as td:
        os.chmod(td, 0o755) # Starts off as 700, not user readable
        with open(os.path.join(td, 'kernel.json'), 'w') as f:
            json.dump(kernel_json, f, sort_keys=True)
        # TODO: Copy resources once they're specified

        print('Installing IPython kernel spec')
        install_kernel_spec(td, 'bash', user=user, replace=True)

def _is_root():
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False # assume not an admin on non-Unix platforms

def main(argv=[]):
    user = '--user' in argv or not _is_root()
    install_my_kernel_spec(user=user)

if __name__ == '__main__':
    main(argv=sys.argv)
