import os
import pexpect
from bash_kernel.kernel import IREPLWrapper
from bash_kernel.exit_code_checker import get_last_exit_code
import pytest


def test_get_last_exit_code_command_not_found(bashwrapper):
    bashwrapper.run_command("this-command-does-not-exist")
    assert get_last_exit_code(bashwrapper) == 127


def test_get_last_exit_code_success(bashwrapper):
    bashwrapper.run_command("echo")
    assert get_last_exit_code(bashwrapper) == 0


def test_get_last_exit_code_command_not_found_conda(mock_conda_bashwrapper):
    mock_conda_bashwrapper.run_command("this-command-does-not-exist")
    assert get_last_exit_code(mock_conda_bashwrapper) == 127


def test_get_last_exit_code_success_conda(mock_conda_bashwrapper):
    mock_conda_bashwrapper.run_command("echo")
    assert get_last_exit_code(mock_conda_bashwrapper) == 0


@pytest.fixture(scope="session")
def mock_conda_bashwrapper(bashwrapper):
    class FakeCondaWrapper:
        def __init__(self):
            self.child = bashwrapper

        def run_command(self, cmd):
            out = self.child.run_command(cmd)
            # Simulating the effect of a conda env
            # on the output of a wrapper
            return out + "(condaenv)"

    return FakeCondaWrapper()


# From BashKernel._start_bash
@pytest.fixture(scope="session")
def bashwrapper():
    unique_prompt = "PROMPT_ASDFASFAS"
    bashrc = os.path.join(os.path.dirname(pexpect.__file__), "bashrc.sh")
    child = pexpect.spawn(
        "bash",
        ["--rcfile", bashrc],
        echo=False,
        encoding="utf-8",
        codec_errors="replace",
    )

    ps1 = unique_prompt + "\[\]" + ">"
    ps2 = unique_prompt + "\[\]" + "+"
    prompt_change = "PS1='{0}' PS2='{1}' PROMPT_COMMAND=''".format(ps1, ps2)
    # Using IREPLWrapper to get incremental output
    bashwrapper = IREPLWrapper(
        child, "\$", prompt_change, unique_prompt, extra_init_cmd="export PAGER=cat"
    )
    return bashwrapper
