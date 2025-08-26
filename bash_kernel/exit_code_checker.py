import re

exit_code_format = "BASHKERNEL_RETCODE<<<{}>>>"
exit_code_re = re.compile(exit_code_format.format("([0-9]+)"))
exit_code_printf_format = exit_code_format.format("%d")
exit_code_command_checker = f'{{ printf "{exit_code_printf_format}" $?; }} 2>/dev/null'


def get_last_exit_code(bashwrapper):
    output = bashwrapper.run_command(exit_code_command_checker)
    matches = exit_code_re.findall(output)
    return int(matches[0])
