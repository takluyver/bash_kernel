from distutils.core import setup
from distutils.command.install import install

class install_with_kernelspec(install):
    def run(self):
        install.run(self)
        from IPython.kernel.kernelspec import install_kernel_spec
        install_kernel_spec('kernelspec', 'bash', replace=True)

setup(name='bash_kernel',
      version='0.1',
      description='A bash kernel for IPython',
      author='Thomas Kluyver',
      author_email='thomas@kluyver.me.uk',
      py_modules=['bash_kernel'],
      cmdclass={'install': install_with_kernelspec}
      )