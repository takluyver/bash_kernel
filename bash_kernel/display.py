"""display.py holds the functions needed to display different types of content.

To use specialized content (images, html, etc) this file defines (in `build_cmds()`) bash functions
that take the contents as standard input. Currently, `display` (images), `displayHTML` (html)
and `displayJS` (javascript) are supported.

Example:

$ cat dog.png | display
$ echo "<b>Dog</b>, not a cat." | displayHTML
$ echo "alert('It is known khaleesi\!');" | displayJS

### Updating rich content cells

If one is doing something that requires dynamic updates, one can specify a display_id,
should be a string name (downstream documentation is not clear on this), and the contents
will be replaced by the new value. Example:


display_id="id_${RANDOM}"
((ii=0))
while ((ii < 10)) ; do
    echo "<div>${ii}<script></div>" | displayHTML $display_id
    ((ii = ii+1))
    sleep 1
done
echo

Remember to create a new id each time the cell is executed.javascript. The same
will work for images or even javascript content (execute javascript snippet
without creating new output cells for each execution).

## Programmatically generating rich content

Alternatively one can simply generate the rich content to a file in /tmp (or $TMPDIR)
and then output the corresponding (to the mimetype) context prefix _TEXT_SAVED_*
constant. So one can write programs (C++, Go, Rust, etc.) that generates rich content
appropriately.

The environment variable "NOTEBOOK_BASH_KERNEL_CAPABILITIES" will be set with a comma
separated list of the supported types (currently "image,html,javascript") that a program can check
for.

To output to a particular "display_id", to allow update of content, prefix the filename
with "(<display_id>)". E.g: a line to display the contents of /tmp/myHTML.html to
a display id "id_12345" would look like:

bash_kernel: saved html data to: (id_12345) /tmp/myHTML.html

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
_TEXT_SAVED_JAVASCRIPT = "bash_kernel: saved javascript data to: "

def _build_cmd_for_type(display_cmd, line_prefix):
    return """
%s () {
    display_id="$1"; shift;
    TMPFILE=$(mktemp ${TMPDIR-/tmp}/bash_kernel.XXXXXXXXXX)
    cat > $TMPFILE
    prefix="%s"
    if [[ "${display_id}" != "" ]]; then
        echo "${prefix}(${display_id}) $TMPFILE" >&2
    else
        echo "${prefix}$TMPFILE" >&2
    fi
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

def display_data_for_js(filename):
    """JavaScript data will all be displayed within the same display_id, to avoid creating different ones for each javascript command."""
    with open(filename, 'rb') as f:
        html_data = f.read()
    _unlink_if_temporary(filename)
    content = {
        'data': {
            'text/javascript': html_data.decode('utf-8'),
        },
        'metadata': {}
    }
    return content

def split_lines(text):
    """Split lines on '\n' or '\r', preserving the ending (end-of-line/line-feed or carriage-return)."""
    # lines_and_endings will alternate between the line content and a line separator (end-of-line or carriage-return),
    # We loop over these putting together again the line contents and one lines+ending, special
    # casing when we have '\r\n' (may still be used in DOS/Windows).
    lines_and_endings = re.split('([\r\n])', text)
    if lines_and_endings[-1] == '':
        # re.split will add a spurious empty part in the end, if the text ends in '\r' or '\n'.
        lines_and_endings = lines_and_endings[:-1]
    num_parts = len(lines_and_endings)
    lines = []
    ii = 0
    while ii < num_parts:
        content = lines_and_endings[ii]
        ending = '\n'
        if ii+1 < num_parts:
            ending = lines_and_endings[ii+1]
            # Special case old DOS end of line sequence '\r\n':
            if ii+3 < num_parts and ending == '\r' and lines_and_endings[ii+2] == '' and lines_and_endings[ii+3] == '\n':
                ending = '\n'  # Replace by a single end-of-line/line-feed.
                ii += 2   # Skip the empty line content between the '\r' and '\n'
        lines.append(content+ending)
        ii += 2  # Skip to next content+ending parts.
    return lines

def extract_contents(output):
    """Returns plain_output string and a list of rich content data."""
    output_lines = []
    rich_contents = []
    for line in split_lines(output):
        matched = False
        for key, info in CONTENT_DATA_PREFIXES.items():
            if line.startswith(key):
                filename, display_id = _filename_and_display_id(line[len(key):-1])
                content = info['display_data_fn'](filename)
                if display_id is not None:
                    if 'transient' not in content:
                        content['transient'] = {}
                    content['transient']['display_id'] = display_id
                rich_contents.append(content)
                matched = True
                break
        if not matched:
            output_lines.append(line)

    plain_output = ''.join(output_lines)
    return plain_output, rich_contents


def _filename_and_display_id(line):
    """line will be either "filename" or "(display_id) filename"."""
    if line[0] != '(':
        return line, None
    pos = line.find(')')
    if pos == -1:
        raise ValueError('Invalid filename/display_id for rich content "{}"'.format(line))
    if line[pos+1] == ' ':
        filename = line[pos+2:]
    else:
        filename = line[pos+1:]
    return filename, line[1:pos]


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
    },
    _TEXT_SAVED_JAVASCRIPT: {
        'display_cmd': 'displayJS',
        'display_data_fn': display_data_for_js,
        'capability': 'javascript',
    }
}
