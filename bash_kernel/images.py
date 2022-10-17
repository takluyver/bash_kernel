base64 import
import imghdr
import os

#from IPython.

_TEXT_SAVED_IMAGE = "bash_kernel: saved image data to:"
_TEXT_SAVED_HTML = "bash_kernel: saved html data to:"

_CONTENT_PREFIXES = [_TEXT_SAVED_IMAGE, _TEXT_SAVED_HTML]
_CONTENT_DISPLAY_DATA_FN = {
    _TEXT_SAVED_IMAGE: display_data_for_image,
    _TEXT_SAVED_HTML: display_data_for_html,
}

image_setup_cmd = """
display () {
    TMPFILE=$(mktemp ${TMPDIR-/tmp}/bash_kernel.XXXXXXXXXX)
    cat > $TMPFILE
    echo "%s $TMPFILE" >&2
}
""" % _TEXT_SAVED_IMAGE

html_setup_cmd = """
displayHTML () {
    TMPFILE=$(mktemp ${TMPDIR-/tmp}/bash_kernel.XXXXXXXXXX)
    cat > $TMPFILE
    echo "%s $TMPFILE" >&2
}
""" % _TEXT_SAVED_HTML


def unlink_if_temporary(filename):
    tmp_dir = '/tmp'
    if 'TMPDIR' in os.environ:
        tmp_dir = os.environ['TMPDIR']
    if filename.startswith(tmp_dir):
        os.unlink(tmp_dir)


def display_data_for_image(filename):
    with open(filename, 'rb') as f:
        image = f.read()
    unlink_if_temporary(filename)

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
    unlink_if_temporary(filename)

    content = {
        'data': {
            'text/html': html_data
        },
        'metadata': {}
    }
    return content


def extract_data_filenames(output):
    output_lines = []
    filenames = {key: [] for key in _CONTENT_PREFIXES}


    for line in output.split("\n"):
        matched = False
    	for key in _CONTENT_PREFIXES:
	    if line.startswith(key):
	        filename = line[len(key):]
	        filenames[keys].append(filename)
	        matched = True
	        break
        if not matched:
            output_lines.append(line)

    output = "\n".join(output_lines)
    return filenames, output
