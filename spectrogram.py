#!/usr/bin/python2

from __future__ import division
import sys

import pyaudio
import cv

import sndtools

CONTROLS_HELP = """
Controls:
    Space - Pause
      q   - Quit
      r   - Reverse direction
"""


def main():

    # TODO: Actual argument parsing
    sample_rate, data = sndtools.io.read(sys.argv[1])

    # Window measured in number of samples
    window_width = 20 / 1000 * sample_rate
    window_step = 5 / 1000 * sample_rate

    # If stereo, take left channel
    if len(data.shape) > 1:
        data = data.transpose()[0]

    spectrogram = sndtools.spectrogram.Spectrogram(data, window_width, window_step, 1366)
    cv.NamedWindow("Spectrogram")

    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(2),
                    channels=1,
                    rate=sample_rate,
                    output=True)

    print CONTROLS_HELP

    direction = 1
    paused = False
    samples_read = 0
    while True:

        if not paused:
            next_samples_read = max(min(len(data), samples_read + direction*2048), 0)
            stream.write(data[samples_read:next_samples_read:direction].tostring())
            samples_read = next_samples_read

        img = spectrogram.view(samples_read)
        cv.ShowImage("Spectrogram", img)
        key = chr(cv.WaitKey(5) & 255)

        if key == ' ':
            paused = not paused
        elif key in ['r', 'R']:
            direction = -1*direction
        elif key in ['q', 'Q']:
            break

    stream.stop_stream()
    stream.close()

    p.terminate()

if __name__ == "__main__":
    #import cProfile
    #cProfile.run("main()")
    main()
