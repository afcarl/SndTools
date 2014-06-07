
A collection of Python tools for working with sound.

This is written for me for the fun of it. I've done a lot of image processing
in the past, but never audio processing, so this is a chance for me to learn
something new and build my own toolset.


## Requirements

Linux is targeted and I have no plans to test on other systems. It's written in
Python, so most things probably work cross platform, but some features like
sound conversion will probably only work on Linux. Let me know if you're
testing on another system, or have any interest in fixing cross-platform
problems.

You'll need these external dependencies:

* [OpenCV](http://opencv.org/) - The "cv" python package. Used for image
    processing and display.
* [PyAudio](http://people.csail.mit.edu/hubert/pyaudio/) - Python bindings for PortAudio. Used for playing sound.
* [VLC media player](https://www.videolan.org/vlc/) - Used to convert between
    sound file formats. Required for now, but will be optional in the future.


## Tour

The "sndtools" python package does most of the heavy lifting. It's meant to be
reusable and well documented. The scripts in the top level directory use
sndtools to create various sound tools. Use the "--help" or "-h" option to get
detailed usage for any script.

So far, here are the scripts implemented:

* spectrogram.py - Calculates and displays a sound spectrogram.


## Current Status

Not much is implemented and it needs polishing, but what's there works!
