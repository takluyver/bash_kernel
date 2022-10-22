"""display.py holds the functions needed to display different types of content.

To use specialized content (images, html, etc) this file defines (in `build_cmds()`) bash functions
that take the contents as standard input. Currently, `display` (images) and `displayHTML` (html)
are supported.

Example:

$ cat dog.png | display
$ echo "<b>Dog</b>, not a cat." | displayHTML

Alternatively one can simply generate the rich content to a file in /tmp (or $TMPDIR)
and then output the corresponding (to the mimetype) context prefix _TEXT_SAVED_*
constant. So one can write programs (C++, Go, Rust, etc.) that generates rich content
appropriately.

The environment variable "NOTEBOOK_BASH_KERNEL_CAPABILITIES" will be set with a comma
separated list of the supported types (currently "image,html") that a program can check
for.

To add support to new content types: (1) create a constant _TEXT_SAVED_<new_type>; (2) create a function
display_data_for_<new_type>; (3) Create an entry in CONTENT_DATA_PREFIXES. Btw, `$ jupyter-lab --Session.debug=True`
is your friend to debug the format of the content message.
"""
import base64
import imghdr
import json
import os
import re


_TEXT_SAVED_IMAGE = "bash_kernel: saved image data to: "
_TEXT_SAVED_HTML = "bash_kernel: saved html data to: "

def _build_cmd_for_type(display_cmd, line_prefix):
    return """
%s () {
    TMPFILE=$(mktemp ${TMPDIR-/tmp}/bash_kernel.XXXXXXXXXX)
    cat > $TMPFILE
    echo "%s$TMPFILE" >&2
}
""" % (display_cmd, line_prefix)


def build_cmds():
    commands = []
    capabilities = []
    for line_prefix, info in CONTENT_DATA_PREFIXES.items():
        commands.append(_build_cmd_for_type(info['display_cmd'], line_prefix))
        capabilities.append(info['capability'])
    capabilities_cmd = 'export NOTEBOOK_BASH_KERNEL_CAPABILITIES="{}"'.format(','.join(capabilities))
    commands.append(capabilities_cmd)
    return "\n".join(commands)


def _unlink_if_temporary(filename):
    tmp_dir = '/tmp'
    if 'TMPDIR' in os.environ:
        tmp_dir = os.environ['TMPDIR']
    if filename.startswith(tmp_dir):
        os.unlink(filename)


def display_data_for_image(filename):
    with open(filename, 'rb') as f:
        image = f.read()
    _unlink_if_temporary(filename)

    image_type = imghdr.what(None, image)
    if image_type is None:
        raise ValueError("Not a valid image: %s" % image)

    image_data = base64.b64encode(image).decode('ascii')
    content = {
        'data': {
            'image/' + image_type: image_data
        },
        'metadata': {}
    }
    return content


def display_data_for_html(filename):
    with open(filename, 'rb') as f:
        html_data = f.read()
    _unlink_if_temporary(filename)
    content = {
        'data': {
            'text/html': html_data.decode('utf-8'),
        },
        'metadata': {}
    }
    return content

def split_lines(text):
    """Split lines on '\n' or '\r', preserving the ending."""
    # This allows programs that display things like progress bars, using \r for
    # carriage return (updating the same line) to work.
    lines_and_endings = re.split('([\r\n])', text)
    lines = []
    num_parts = len(lines_and_endings)
    for ii in range(int((num_parts+1)/2)):
      if ii*2+1 < num_parts:
        lines.append(lines_and_endings[ii*2]+lines_and_endings[ii*2+1])
      elif lines_and_endings[ii*2] != '':
        lines.append(lines_and_endings[ii*2]+'\n')
    return lines


def extract_data_filenames(output):
    output_lines = []
    filenames = {key: [] for key in CONTENT_DATA_PREFIXES.keys()}
    for line in split_lines(output):
        matched = False
        for key in CONTENT_DATA_PREFIXES.keys():
            if line.startswith(key):
                filename = line[len(key):-1]
                filenames[key].append(filename)
                matched = True
                break
        if not matched:
            output_lines.append(line)

    output = ''.join(output_lines)
    return filenames, output


# Maps content prefixes to function that display its contents.
CONTENT_DATA_PREFIXES = {
    _TEXT_SAVED_IMAGE: {
        'display_cmd': 'display',
        'display_data_fn': display_data_for_image,
        'capability': 'image',
    },
    _TEXT_SAVED_HTML: {
        'display_cmd': 'displayHTML',
        'display_data_fn': display_data_for_html,
        'capability': 'html',
    }
}
