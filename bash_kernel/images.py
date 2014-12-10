import base64
import imghdr
import os

#from IPython.

_TEXT_SAVED_IMAGE = "bash_kernel: saved image data to:"

image_setup_cmd = """
display () {
    TMPFILE=$(mktemp ${TMPDIR-/tmp}/bash_kernel.XXXXXXXXXX)
    cat > $TMPFILE
    echo "%s $TMPFILE" >&2
}
""" % _TEXT_SAVED_IMAGE

def display_data_for_image(filename):
    with open(filename, 'rb') as f:
        image = f.read()
    os.unlink(filename)

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
