from distutils.core import setup
from distutils.command.install import install

class install_with_kernelspec(install):
    def run(self):
        install.run(self)
        from IPython.kernel.kernelspec import install_kernel_spec
        install_kernel_spec('kernelspec', 'bash', replace=True)

with open('README.rst') as f:
    readme = f.read()

setup(name='bash_kernel',
      version='0.1',
      description='A bash kernel for IPython',
      long_description=readme,
      author='Thomas Kluyver',
      author_email='thomas@kluyver.me.uk',
      url='https://github.com/takluyver/bash_kernel',
      py_modules=['bash_kernel'],
      cmdclass={'install': install_with_kernelspec},
      install_requires=['ipython>=3.0', 'pexpect>=3.3'],
      classifiers = [
          'Framework :: IPython',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 3',
          'Topic :: System :: Shells',
      ]
)