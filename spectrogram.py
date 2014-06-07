#!/usr/bin/python2

from __future__ import division
import sys

import pyaudio
import cv

import sndtools


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

    direction = 1
    samples_read = 0
    while samples_read < len(data):
        next_samples_read = max(min(len(data), samples_read + direction*2048), 0)
        stream.write(data[samples_read:next_samples_read:direction].tostring())
        samples_read = next_samples_read

        img = spectrogram.view(samples_read)
        cv.ShowImage("Spectrogram", img)
        key = cv.WaitKey(5)

        # Hack: Press ' ' to pause
        #       Press 'r' to reverse direction
        if key == 1048608:  # ' '
            while cv.WaitKey(-1) != 1048608:
                pass
        if key == 1048690:  # 'r'
            direction = -1*direction

    cv.WaitKey(-1)

    stream.stop_stream()
    stream.close()

    p.terminate()

if __name__ == "__main__":
    #import cProfile
    #cProfile.run("main()")
    main()
