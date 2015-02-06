#!/usr/bin/python2
"""Generate and output a spectrogram.

The spectrogram is a representation of frequency over time. It shows a fourier
transform of sound samples as a window is moved through the data. The
spectrogram image shows time on the x axis and frequency on the y axis, with
the intensity of the pixel showing the intensity of that frequency sound.
"""

from __future__ import division

import pyaudio
import cv

import sndtools

CONTROLS_HELP = """
Controls:
    Space  : Pause
      q    : Quit
      r    : Reverse direction
    + / -  : Speed increase / decrease
"""
MIN_SPEED = 0.05
MAX_SPEED = 4


def run_interface(data, sample_rate, spectrogram, view_width, speed=1):
    spec_view = sndtools.spectrogram.SpectrogramView(spectrogram, view_width)
    cv.NamedWindow("Spectrogram")

    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(2),
                    channels=1,
                    rate=int(sample_rate * speed),
                    output=True)

    print CONTROLS_HELP

    direction = 1
    current_sample = 0
    while True:

        if stream.is_active():
            slice_end = current_sample + direction*2048
            slice_end = max(min(slice_end, len(data)), 0)
            data_slice = data[current_sample:slice_end:direction]
            stream.write(data_slice.tostring())
            current_sample = slice_end

        img = spec_view.view(current_sample)
        cv.ShowImage("Spectrogram", img)
        key = chr(cv.WaitKey(5) & 255)

        if key == ' ':
            if stream.is_active():
                stream.stop_stream()
            else:
                stream.start_stream()
        elif key in ('r', 'R'):
            direction = -1*direction
        elif key in ('q', 'Q'):
            break
        elif key in ('+', '=', '-', '_'):
            if key in ('+', '='):
                speed += 0.1
            else:
                speed -= 0.1
            speed = min(MAX_SPEED, max(0.1, speed))
            print "Speed:", speed
            stream.close()
            stream = p.open(format=p.get_format_from_width(2),
                            channels=1,
                            rate=int(sample_rate * speed),
                            output=True)

    stream.stop_stream()
    stream.close()

    p.terminate()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sound_file",
        help="Sound file of which to generate the spectrogram")
    parser.add_argument("-w --window-width", dest="window_width", type=int,
        default=20,
        help="Size of the moving window in milliseconds")
    parser.add_argument("-s --window-step", dest="window_step", type=int,
        default=5,
        help="""Step between windows in milliseconds. If this is less than
        window_size, the windows will overlap. If it is more, the windows will
        have gaps between them.""")
    parser.add_argument("-d --display-width", dest="display_width", type=int,
        default=1024, help="Width in pixels of the live display.")
    parser.add_argument("-o --output", dest="out_filename", default=None,
        action="store", help="Do not display interface, but output image file.")
    parser.add_argument("--speed", type=float, default=1,
        help="""Playback speed multiplier, default 1.""")
    args = parser.parse_args()

    if args.speed < MIN_SPEED or args.speed > MAX_SPEED:
        parser.error("Speed must be in range {} - {}".format(MIN_SPEED, MAX_SPEED))

    sample_rate, data = sndtools.io.read(args.sound_file)

    # Window measured in number of samples
    window_width = args.window_width / 1000 * sample_rate
    window_step = args.window_step / 1000 * sample_rate

    # If stereo, take left channel
    if len(data.shape) > 1:
        data = data.transpose()[0]

    spectrogram = sndtools.spectrogram.Spectrogram(
        data, window_width, window_step, "blackman"
    )

    if args.out_filename is None:
        run_interface(data, sample_rate, spectrogram,
                      args.display_width, speed=args.speed)
    else:
        cv.SaveImage(args.out_filename, spectrogram.get_image())
