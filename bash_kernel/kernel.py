from ipykernel.kernelbase import Kernel
from pexpect import replwrap, EOF
import pexpect

from subprocess import check_output
import os.path
import uuid
import random
import string

import re
import signal

__version__ = '0.9.3'

version_pat = re.compile(r'version (\d+(\.\d+)+)')

from .display import (extract_contents, build_cmds)

# Special command patterns
su = re.compile("(sudo )? *((\/usr)?\/bin\/)?su( +|$).*")
env = re.compile("(sudo )? *((\/usr)?\/bin\/)?(chroot |env )(.* )?((\/usr)?\/bin\/)?bash( +|$).*")
bash = re.compile("(sudo )? *((\/usr)?\/bin\/)?bash( +|$).*")
passwd = re.compile("(sudo )? *((\/usr)?\/bin\/)?passwd( +|$).*")
sudo = re.compile("sudo .+")
special_commands = [su, env, bash, passwd, sudo] if os.getenv("BASH_KERNEL_SPECIAL_COMMANDS") is not None else []

class IREPLWrapper(replwrap.REPLWrapper):
    """A subclass of REPLWrapper that gives incremental output
    specifically for bash_kernel.

    The parameters are the same as for REPLWrapper, except for one
    extra parameter:

    :param line_output_callback: a callback method to receive each batch
      of incremental output. It takes one string parameter.
    """
    def __init__(self, cmd_or_spawn, orig_prompt, prompt_change, unique_prompt,
                 extra_init_cmd=None, line_output_callback=None, getpass=None):
        self.prompt_change = prompt_change
        self.extra_init_cmd = extra_init_cmd
        self.unique_prompt = unique_prompt
        self.line_output_callback = line_output_callback
        self.getpass = getpass
        # The extra regex at the start of PS1 below is designed to catch the
        # `(envname) ` which conda/mamba add to the start of PS1 by default.
        # Obviously anything else that looks like this, including user output,
        # will be eaten.
        # FIXME: work out if there is a way to update these by reading PS1
        # after each command and checking that it has changed. The answer is
        # probably no, as we never see individual commands but rather cells
        # with possibly many commands, and would need to update this half-way
        # through a cell.
        self.ps1_re = r"(\(\w+\) )?" + re.escape(self.unique_prompt + ">")
        self.ps2_re = re.escape(self.unique_prompt + "+")
        replwrap.REPLWrapper.__init__(self, cmd_or_spawn, orig_prompt,
                prompt_change, new_prompt=self.ps1_re,
                continuation_prompt=self.ps2_re, extra_init_cmd=extra_init_cmd)

    def _expect_prompt(self, timeout=-1):
        prompts = [self.ps1_re, self.ps2_re]

        if timeout == None:
            # "None" means we are executing code from a Jupyter cell by way of the run_command
            # in the do_execute() code below, so do incremental output, i.e.
            # also look for end of line or carridge return
            prompts.extend(['\r?\n', '\r'])
            while True:
                pos = self.child.expect_list([re.compile(x) for x in prompts], timeout=None)
                if pos == 2:
                    # End of line received.
                    self.line_output_callback(self.child.before + '\n')
                elif pos == 3:
                    # Carriage return ('\r') received.
                    self.line_output_callback(self.child.before + '\r')
                else:
                    if len(self.child.before) != 0:
                        # Prompt received, but partial line precedes it.
                        self.line_output_callback(self.child.before)
                    break
        else:
            # Otherwise, wait (with timeout) until the next prompt
            pos = self.child.expect_list([re.compile(x) for x in prompts], timeout=timeout)

        # Prompt received, so return normally
        return pos

    def special_command(self, code):

        # Some supported cases for su, env and chroot commands
        if su.match(code):
            code += " -s /bin/bash"

        # Send code
        self.child.sendline(code)

        # If there is not need to wait for the password prompt
        if bash.match(code) and not sudo.match(code):
            self.child.sendline(self.prompt_change)

        prompts = [self.ps1_re, self.ps2_re,
                   u"Password", u"\[sudo\] password for ",
                   u"New password",
                   u"Retype new password",
                   u"Authentication failure",
                   u"incorrect password attempts",
                   " all the required fields",
                   "chroot: cannot change root directory to",
                   "passwd: password updated successfully",
                   "passwd: password unchanged"]
        timeout = 1
        while True:
            try:
                pos = self.child.expect_list([re.compile(x) for x in prompts], timeout=timeout)
                if pos in [2, 3, 4, 5]:
                    if self.child.before:   # To print Sorry, try again. when sudo password is wrong
                        self.line_output_callback(self.child.before)
                    self.child.expect_exact(':')
                    self.line_output_callback(prompts[pos].replace("\\", "") + self.child.before + self.child.after + '\n')
                    password = self.getpass()
                    self.child.sendline(password)
                    timeout = None  # Ensure we wait long enough to catch wrong password cases
                elif pos in [6, 7, 8, 9, 10, 11]:
                    if pos == 9:
                        self.child.expect_exact(':')
                        self.line_output_callback(prompts[pos] + self.child.before + self.child.after + '\n')
                    else:
                        self.line_output_callback(self.child.before + self.child.after + '\n')
                    self._expect_prompt(1)
                    self._expect_prompt(1)
                    return
                else:
                    if not su.match(code) and not bash.match(code) and not env.match(code)\
                            and len(self.child.before) != 0:
                        # Prompt received, but partial line precedes it.
                        self.line_output_callback(self.child.before)
                    break

                if su.match(code) or bash.match(code) or env.match(code):
                    self.child.sendline(self.prompt_change)
            except:
                # Required for sudo su if not prompted for password
                self.child.sendline(self.prompt_change)

        # Initialization
        if su.match(code) or bash.match(code) or env.match(code):
            self.run_command(self.extra_init_cmd)
            self.run_command("bind 'set enable-bracketed-paste off' >/dev/null 2>&1 || true")
            # self.run_command(build_cmds())

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
        # Make a random prompt, further reducing chances of accidental matches.
        rand = ''.join(random.choices(string.ascii_uppercase, k=12))
        self.unique_prompt = "PROMPT_" + rand
        Kernel.__init__(self, **kwargs)
        self._start_bash()
        self._known_display_ids = set()
        # Enable this to allow calling Kernel.getpass() for passwords.
        self._allow_stdin = True

    def _start_bash(self):
        # Signal handlers are inherited by forked processes, and we can't easily
        # reset it from the subprocess. Since kernelapp ignores SIGINT except in
        # message handlers, we need to temporarily reset the SIGINT handler here
        # so that bash and its children are interruptible.
        old_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_DFL)
        # We need to temporarily reset the default signal handler for SIGPIPE so
        # that commands like `head` used in a pipe chain can signal to the data
        # producers. 
        old_sigpipe_handler = signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        try:
            # Note: the next few lines mirror functionality in the
            # bash() function of pexpect/replwrap.py.  Look at the
            # source code there for comments and context for
            # understanding the code here.
            bashrc = os.path.join(os.path.dirname(pexpect.__file__), 'bashrc.sh')
            child = pexpect.spawn("bash", ['--rcfile', bashrc], echo=False,
                                  encoding='utf-8', codec_errors='replace')
            # Following comment stolen from upstream's REPLWrap:
            # If the user runs 'env', the value of PS1 will be in the output. To avoid
            # replwrap seeing that as the next prompt, we'll embed the marker characters
            # for invisible characters in the prompt; these show up when inspecting the
            # environment variable, but not when bash displays the prompt.
            ps1 = self.unique_prompt + u'\[\]' + ">"
            ps2 = self.unique_prompt + u'\[\]' + "+"
            prompt_change = u"PS1='{0}' PS2='{1}' PROMPT_COMMAND=''".format(ps1, ps2)
            # Using IREPLWrapper to get incremental output
            self.bashwrapper = IREPLWrapper(child, u'\$', prompt_change, self.unique_prompt,
                                            extra_init_cmd="export PAGER=cat",
                                            line_output_callback=self.process_output,
                                            getpass=self.getpass)
        finally:
            signal.signal(signal.SIGINT, old_sigint_handler)
            signal.signal(signal.SIGPIPE, old_sigpipe_handler)

        # Disable bracketed paste (see <https://github.com/takluyver/bash_kernel/issues/117>)
        self.bashwrapper.run_command("bind 'set enable-bracketed-paste off' >/dev/null 2>&1 || true")
        # Register Bash function to write image data to temporary file
        self.bashwrapper.run_command(build_cmds())


    def process_output(self, output):
        if hasattr(self, "silent") and not self.silent:
            plain_output, rich_contents = extract_contents(output)

            # Send standard output
            if plain_output:
                stream_content = {'name': 'stdout', 'text': plain_output}
                self.send_response(self.iopub_socket, 'stream', stream_content)

            # Send rich contents, if any:
            for content in rich_contents:
                if isinstance(content, Exception):
                    message = {'name': 'stderr', 'text': str(content)}
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


        if code.strip().endswith("\\"):
            error_content = {
                'ename': '',
                'evalue': "Cell has trailing backslash",
                'traceback': []
            }
            self.send_response(self.iopub_socket, 'error', error_content)
            error_content['execution_count'] = self.execution_count
            error_content['status'] = 'error'
            return error_content

        interrupted = False
        try:
            if True in [cmd.match(code.rstrip()) is not None for cmd in special_commands]:
                self.bashwrapper.special_command(code.rstrip())
            else:
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
            exitcode = int(self.bashwrapper.run_command('{ echo $?; } 2>/dev/null').rstrip().split("\r\n")[0])
        except Exception as exc:
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


        matches = []
        # The regex below might cause issues, but is designed to allow
        # completion on the rhs of a variable assignment and within strings,
        # like var="/etc/<tab>", which should complete from /etc/.
        # Let's just hope no one makes a habit of puting =/"/' into file names
        # </naievity>  (blame @kdm9 if it breaks)
        tokens = re.split("[\t \n;=\"'><]+", code)
        token = tokens[-1]
        start = cursor_pos - len(token)
        if token and token[0] == '$':
            # complete variables
            cmd = 'compgen -A arrayvar -A export -A variable %s' % token[1:] # strip leading $
            output = self.bashwrapper.run_command(cmd).rstrip()
            completions = set(output.split())
            # append matches including leading $
            matches.extend(['$'+c for c in completions])
        else:
            # complete path 
            cmd = 'compgen -d -S / %s' % token
            output = self.bashwrapper.run_command(cmd).rstrip()
            dirs = list(set(output.split()))
            cmd = 'compgen -f %s' % token
            output = self.bashwrapper.run_command(cmd).rstrip()
            filesanddirs = list(set(output.split()))
            files = [x for x in filesanddirs if x + "/" not in dirs]
            if '/' not in token:
                # Add an explict ./ for relative paths
                matches.extend(["./" + x for x in files + dirs])
            else:
                matches.extend(files)
                matches.extend(dirs)
        if '/' not in token and code[-1] != '"':
            # complete anything command-like (avoid annoying errors where command names get completed after a directory)
            cmd = 'compgen -abc -A function %s' % token
            output = self.bashwrapper.run_command(cmd).rstrip()
            matches.extend(list(set(output.split())))
        if code[-1] == '"':
            # complete variables
            cmd = 'compgen -A arrayvar -A export -A variable %s' % token[1:] # strip leading $
            output = self.bashwrapper.run_command(cmd).rstrip()
            completions = set(output.split())
            # append matches including leading $
            matches.extend(['$'+c for c in completions])

        if not matches:
            return default
        matches = [m for m in matches if m.startswith(token)]

        return {'matches': sorted(matches), 'cursor_start': start,
                'cursor_end': cursor_pos, 'metadata': dict(),
                'status': 'ok'}
