import json
import os
import sys

from IPython.kernel.kernelspec import install_kernel_spec
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

def main(argv=None):
    user = True
    if len(argv) > 1 and argv[1].find("=") != -1:
        key,val = argv[1].split('=')
        if key == "user":
            if val == "false" or val == "False":
	        user = False
        else:
            raise ValueError(usage())
                
    install_my_kernel_spec(user=user)

def usage():
    usage = """
    Install bash_kernel as user or system user.
    python bash_kernel.install user=False will install system wide
    python bash_kernel.install will install to current user directory
    """
    return usage

if __name__ == '__main__':
    main(argv=sys.argv)
