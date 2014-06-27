from IPython.kernel.zmq.kernelbase import Kernel
from pexpect import replwrap
from subprocess import check_output
import re

__version__ = '0.1'

version_pat = re.compile(r'version (\d+(\.\d+)+)')

class BashKernel(Kernel):
    implementation = 'bash_kernel'
    implementation_version = __version__
    language = 'bash'
    @property
    def language_version(self):
        m = version_pat.search(self.banner)
        return m.group(1)

    _banner = None
    @property
    def banner(self):
        if self._banner is None:
            self._banner = check_output(['bash', '--version']).decode('utf-8')
        return self._banner
    
    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self.bashwrapper = replwrap.bash()

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payloads': [], 'user_expressions': {}}
        
        interrupted = False
        try:
            output = self.bashwrapper.run_command(code.rstrip(), timeout=None)
        except KeyboardInterrupt:
            self.bashwrapper.child.sendintr()
            interrupted = True
            self.bashwrapper._expect_prompt()
            output = self.bashwrapper.child.before

        if not silent:
            stream_content = {'name': 'stdout', 'data':output}
            self.send_response(self.iopub_socket, 'stream', stream_content)
        
        if interrupted:
            return {'status': 'abort', 'execution_count': self.execution_count}
        
        try:
            exitcode = int(self.run_command('echo $?').rstrip())
        except Exception:
            exitcode = 1

        if exitcode:
            return {'status': 'error', 'execution_count': self.execution_count,
                    'ename': '', 'evalue': str(exitcode), 'traceback': []}
        else:
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payloads': [], 'user_expressions': {}}

if __name__ == '__main__':
    from IPython.kernel.zmq.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=BashKernel)
