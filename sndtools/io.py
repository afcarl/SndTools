import subprocess
import tempfile
import os

from scipy.io import wavfile

VLC_COMMAND = "vlc"


def read(filename):
    """Returns (sample_rate, data) tuple for the given sound file.

    Sample width is always 2 bytes, so data is a list of integers between
    -32767 to 32768.

    Internally vlc is used to convert the file to a 16-bit wav file that
    scipy.io.wavfile can read. This function can read any file that vlc can.

    TODO: Skip vlc conversion if file is already 16-bit wav.
    TODO: Alternatively use mencoder.
    TODO: What about stereo sound files?

    """

    # Convert to wav 16 bit
    wav_filename = tempfile.mkstemp()[1]
    command = [VLC_COMMAND,
        '-I', 'dummy',
        '-q', filename,
        '--sout', '#transcode{{acodec=s16l,channels=1}}:standard{{mux=wav,dst="{}",access=file}}'.format(wav_filename),
        "--album-art", "0",  # Don't search for album art, stupid!
        'vlc://quit',
    ]
    subprocess.check_output(command)

    # Read wav
    sample_rate, data = wavfile.read(wav_filename)

    os.remove(wav_filename)
    return sample_rate, data

