from IPython.kernel.zmq.kernelbase import Kernel
from pexpect import replwrap, EOF

from subprocess import check_output
from os import unlink

import base64
import imghdr
import re
import signal
import urllib

__version__ = '0.2'

version_pat = re.compile(r'version (\d+(\.\d+)+)')

_TEXT_SAVED_IMAGE = "bash_kernel: saved image data to:"


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

    language_info = {'codemirror_mode': 'shell',
                     'mimetype': 'text/x-sh',
                     'file_extension': 'sh'}

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self._start_bash()

    def _start_bash(self):
        # Signal handlers are inherited by forked processes, and we can't easily
        # reset it from the subprocess. Since kernelapp ignores SIGINT except in
        # message handlers, we need to temporarily reset the SIGINT handler here
        # so that bash and its children are interruptible.
        sig = signal.signal(signal.SIGINT, signal.SIG_DFL)
        try:
            self.bashwrapper = replwrap.bash()
        finally:
            signal.signal(signal.SIGINT, sig)

        # Register Bash function to write image data to temporary file
        bash_rc = """
        display () {
            TMPFILE=$(mktemp ${TMPDIR-/tmp}/bash_kernel.XXXXXXXXXX)
            cat > $TMPFILE
            echo "%s $TMPFILE" >&2
        }
        """ % _TEXT_SAVED_IMAGE
        self.bashwrapper.run_command(bash_rc)

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        interrupted = False
        try:
            output = self.bashwrapper.run_command(code.rstrip(), timeout=None)
        except KeyboardInterrupt:
            self.bashwrapper.child.sendintr()
            interrupted = True
            self.bashwrapper._expect_prompt()
            output = self.bashwrapper.child.before
        except EOF:
            output = self.bashwrapper.child.before + 'Restarting Bash'
            self._start_bash()

        if not silent:
            image_filenames, output = extract_image_filenames(output)

            # Send standard output
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)

            # Send images, if any
            for filename in image_filenames:
                try:
                    data = display_data(filename)
                except ValueError as e:
                    message = {'name': 'stdout', 'text': str(e)}
                    self.send_response(self.iopub_socket, 'stream', message)
                else:
                    self.send_response(self.iopub_socket, 'display_data', data)

        if interrupted:
            return {'status': 'abort', 'execution_count': self.execution_count}

        try:
            exitcode = int(self.bashwrapper.run_command('echo $?').rstrip())
        except Exception:
            exitcode = 1

        if exitcode:
            return {'status': 'error', 'execution_count': self.execution_count,
                    'ename': '', 'evalue': str(exitcode), 'traceback': []}
        else:
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

    def do_complete(self, code, cursor_pos):
        code = code[:cursor_pos]
        default = {'matches': [], 'cursor_start': 0,
                   'cursor_end': cursor_pos, 'metadata': dict(),
                   'status': 'ok'}

        if not code or code[-1] == ' ':
            return default

        tokens = code.replace(';', ' ').split()
        if not tokens:
            return default

        token = tokens[-1]
        start = cursor_pos - len(token)
        cmd = 'compgen -cdfa %s' % token
        output = self.bashwrapper.run_command(cmd).rstrip()

        matches = output.split()
        if not matches:
            return default
        matches = [m for m in matches if m.startswith(token)]

        return {'matches': matches, 'cursor_start': start,
                'cursor_end': cursor_pos, 'metadata': dict(),
                'status': 'ok'}


def display_data(filename):
    with open(filename, 'rb') as f:
        image = f.read()
    unlink(filename)

    image_type = imghdr.what(None, image)
    if image_type is None:
        raise ValueError("Not a valid image: %s" % image)

    image_data = urllib.parse.quote(base64.b64encode(image))
    content = {
        'source': 'kernel',
        'data': {
            'image/' + image_type: image_data
        }
    }
    return content


def extract_image_filenames(output):
    output_lines = []
    image_filenames = []

    for line in output.split("\n"):
        if line.startswith(_TEXT_SAVED_IMAGE):
            filename = line.rstrip().split(": ")[-1]
            image_filenames.append(filename)
        else:
            output_lines.append(line)

    output = "\n".join(output_lines)
    return image_filenames, output

if __name__ == '__main__':
    from IPython.kernel.zmq.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=BashKernel)
