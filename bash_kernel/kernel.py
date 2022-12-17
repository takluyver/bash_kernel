from ipykernel.kernelbase import Kernel
from pexpect import replwrap, EOF
import pexpect

from subprocess import check_output
import os.path
import uuid

import re
import signal

__version__ = '0.9.0'

version_pat = re.compile(r'version (\d+(\.\d+)+)')

from .display import (extract_contents, build_cmds)

class IREPLWrapper(replwrap.REPLWrapper):
    """A subclass of REPLWrapper that gives incremental output
    specifically for bash_kernel.

    The parameters are the same as for REPLWrapper, except for one
    extra parameter:

    :param line_output_callback: a callback method to receive each batch
      of incremental output. It takes one string parameter.
    """
    def __init__(self, cmd_or_spawn, orig_prompt, prompt_change,
                 extra_init_cmd=None, line_output_callback=None):
        self.line_output_callback = line_output_callback
        replwrap.REPLWrapper.__init__(self, cmd_or_spawn, orig_prompt,
                                      prompt_change, extra_init_cmd=extra_init_cmd)

    def _expect_prompt(self, timeout=-1):
        if timeout == None:
            # "None" means we are executing code from a Jupyter cell by way of the run_command
            # in the do_execute() code below, so do incremental output.
            while True:
                pos = self.child.expect_exact([self.prompt, self.continuation_prompt, u'\r\n', u'\n', u'\r'],
                                              timeout=None)
                if pos == 2 or pos == 3:
                    # End of line received.
                    self.line_output_callback(self.child.before + '\n')
                elif pos == 4:
                    # Carriage return ('\r') received.
                    self.line_output_callback(self.child.before + '\r')
                else:
                    if len(self.child.before) != 0:
                        # Prompt received, but partial line precedes it.
                        self.line_output_callback(self.child.before)
                    break
        else:
            # Otherwise, use existing non-incremental code
            pos = replwrap.REPLWrapper._expect_prompt(self, timeout=timeout)

        # Prompt received, so return normally
        return pos

class BashKernel(Kernel):
    implementation = 'bash_kernel'
    implementation_version = __version__

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

    language_info = {'name': 'bash',
                     'codemirror_mode': 'shell',
                     'mimetype': 'text/x-sh',
                     'file_extension': '.sh'}

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self._start_bash()
        self._known_display_ids = set()

    def _start_bash(self):
        # Signal handlers are inherited by forked processes, and we can't easily
        # reset it from the subprocess. Since kernelapp ignores SIGINT except in
        # message handlers, we need to temporarily reset the SIGINT handler here
        # so that bash and its children are interruptible.
        sig = signal.signal(signal.SIGINT, signal.SIG_DFL)
        try:
            # Note: the next few lines mirror functionality in the
            # bash() function of pexpect/replwrap.py.  Look at the
            # source code there for comments and context for
            # understanding the code here.
            bashrc = os.path.join(os.path.dirname(pexpect.__file__), 'bashrc.sh')
            child = pexpect.spawn("bash", ['--rcfile', bashrc], echo=False,
                                  encoding='utf-8', codec_errors='replace')
            ps1 = replwrap.PEXPECT_PROMPT[:5] + u'\[\]' + replwrap.PEXPECT_PROMPT[5:]
            ps2 = replwrap.PEXPECT_CONTINUATION_PROMPT[:5] + u'\[\]' + replwrap.PEXPECT_CONTINUATION_PROMPT[5:]
            prompt_change = u"PS1='{0}' PS2='{1}' PROMPT_COMMAND=''".format(ps1, ps2)

            # Using IREPLWrapper to get incremental output
            self.bashwrapper = IREPLWrapper(child, u'\$', prompt_change,
                                            extra_init_cmd="export PAGER=cat",
                                            line_output_callback=self.process_output)
        finally:
            signal.signal(signal.SIGINT, sig)

        # Disable bracketed paste (see <https://github.com/takluyver/bash_kernel/issues/117>)
        self.bashwrapper.run_command("bind 'set enable-bracketed-paste off' >/dev/null 2>&1 || true")
        # Register Bash function to write image data to temporary file
        self.bashwrapper.run_command(build_cmds())


    def process_output(self, output):
        if not self.silent:
            plain_output, rich_contents = extract_contents(output)

            # Send standard output
            if plain_output:
                stream_content = {'name': 'stdout', 'text': plain_output}
                self.send_response(self.iopub_socket, 'stream', stream_content)

            # Send rich contents, if any:
            for content in rich_contents:
                if isinstance(content, Exception):
                    message = {'name': 'stderr', 'text': str(e)}
                    self.send_response(self.iopub_socket, 'stream', message)
                else:
                    if 'transient' in content and 'display_id' in content['transient']:
                        self._send_content_to_display_id(content)
                    else:
                        self.send_response(self.iopub_socket, 'display_data', content)

    def _send_content_to_display_id(self, content):
        """If display_id is not known, use "display_data", otherwise "update_display_data"."""
        # Notice this is imperfect, because when re-running the same cell, the output cell
        # is destroyed and the div element (the html tag) with the display_id no longer exists. But the
        # `update_display_data` function has no way of knowing this, and thinks that the
        # display_id still exists and will try, and fail to update it (as opposed to re-create
        # the div with the display_id).
        #
        # The solution is to have the user always to generate a new display_id for a cell: this
        # way `update_display_data` will not have seen the display_id when the cell is re-run and
        # correctly creates the new div element.
        display_id = content['transient']['display_id']
        if display_id in self._known_display_ids:
            msg_type = 'update_display_data'
        else:
            msg_type = 'display_data'
            self._known_display_ids.add(display_id)
        self.send_response(self.iopub_socket, msg_type, content)

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        self.silent = silent
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        interrupted = False
        try:
            # Note: timeout=None tells IREPLWrapper to do incremental
            # output.  Also note that the return value from
            # run_command is not needed, because the output was
            # already sent by IREPLWrapper.
            self.bashwrapper.run_command(code.rstrip(), timeout=None)
        except KeyboardInterrupt:
            self.bashwrapper.child.sendintr()
            interrupted = True
            self.bashwrapper._expect_prompt()
            output = self.bashwrapper.child.before
            self.process_output(output)
        except EOF:
            output = self.bashwrapper.child.before + 'Restarting Bash'
            self._start_bash()
            self.process_output(output)

        if interrupted:
            return {'status': 'abort', 'execution_count': self.execution_count}

        try:
            exitcode = int(self.bashwrapper.run_command('echo $?').rstrip())
        except Exception:
            exitcode = 1

        if exitcode:
            error_content = {
                'ename': '',
                'evalue': str(exitcode),
                'traceback': []
            }
            self.send_response(self.iopub_socket, 'error', error_content)

            error_content['execution_count'] = self.execution_count
            error_content['status'] = 'error'
            return error_content
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

        matches = []
        token = tokens[-1]
        start = cursor_pos - len(token)

        if token[0] == '$':
            # complete variables
            cmd = 'compgen -A arrayvar -A export -A variable %s' % token[1:] # strip leading $
            output = self.bashwrapper.run_command(cmd).rstrip()
            completions = set(output.split())
            # append matches including leading $
            matches.extend(['$'+c for c in completions])
        else:
            # complete functions and builtins
            cmd = 'compgen -cdfa %s' % token
            output = self.bashwrapper.run_command(cmd).rstrip()
            matches.extend(output.split())

        if not matches:
            return default
        matches = [m for m in matches if m.startswith(token)]

        return {'matches': sorted(matches), 'cursor_start': start,
                'cursor_end': cursor_pos, 'metadata': dict(),
                'status': 'ok'}
