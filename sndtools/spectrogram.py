from __future__ import division
import numpy

from scipy import signal
from scipy import fftpack

import cv


class Spectrogram(object):
    """Calculate a fourier transform over time.

    The data is split into windows (possibly overlapping). The fourier
    transform is calculated in each window.

    This class is lazy. It doesn't calculate the spectrogram until the actual
    data is requested. If you want the whole spectrogram image, you can call
    ``get_image()``. Otherwise, you can call ``calculate``, then access the
    ``spec`` element directly.

    TODO: What about the maximum frequency (height) of the spectrogram?

    """

    # Maps names of taper windows to a function generating the taper window
    # given the window width.
    _taper_funcs = {
        "blackman": lambda w: numpy.blackman(w),
        "bartlett": lambda w: numpy.bartlett(w),
        "hamming": lambda w: numpy.hamming(w),
        "hanning": lambda w: numpy.hanning(w),
        "none": lambda w: None,
    }

    def __init__(self, data, window_width, window_step, taper=None):
        """
        Args:
            data: The samples to calculate the spectrogram of. Should be a list
                of numbers.
            window_width: Width of the moving fourier transform window.
            window_step: Window step size. If this is less than window_width,
                the windows will overlap.
            taper: Taper to apply to the window before performing fourier
                transform. Must be an array of floats of length
                ``window_width``. Alternatively, the following strings can be
                passed in to use some well known taper functions: "blackman",
                "bartlett", "hamming", "hanning", "none". If "none" or None
                (default) is given, no taper will be used.

        TODO: Add options for taper function and smoothing.
        """
        self.data = numpy.array(data)
        self.window_width = int(window_width)
        self.window_step = window_step

        self.n_windows = int((len(data) - window_width) // window_step) + 1
        self.height = int(window_width // 2)

        # The spectrogram image itself
        self.spec = numpy.ndarray((self.n_windows, self.height), dtype=numpy.uint8)

        if isinstance(taper, basestring):
            taper = taper.lower()
            if taper not in self._taper_funcs:
                raise ValueError('"taper" argument is a string ("{}"), but '
                                 'not one of the possible predefined taper '
                                 'windows: {}'.format(taper, self._taper_funcs.keys()))
            self.taper = self._taper_funcs[taper](window_width)
        elif taper is None:
            self.taper = None
        else:
            self.taper = numpy.array(taper)

        self.smooth_kernel = None
        #self.smooth_kernel = signal.gaussian(5, 1)

        self._next_window = 0

    def get_image(self):
        """Returns the whole spectrogram as an image.

        Returns:
            A spectrogram in the form of an OpenCV IplImage. Each vertical line
            shows the fourier transform of a window, with time going from left
            to right.
        """
        return self.get_slice(0, self.n_windows)

    def window_from_sample(self, sample_idx):
        """Return the window index of the given index into data.

        Note that this method can't be exact, since there may be more than one
        windows overlapping any point. A window is always returned, even though
        there may be no windows at the exact point given.
        """
        clamp = lambda lower, upper, x: max(lower, min(upper, x))
        return clamp(
            0, self.n_windows-1,
            (sample_idx - self.window_width) // self.window_step
        )

    def calculate(self, start, end):
        """
        Calculates the fft in the range [start, end), store result in
        ``spec``.

        This is useful if you're using the ``spec`` attribute directly and
        need to ensure that the spectrogram is calculated up to a certain
        point. If you just want the whole image, call ``get_image()``.
        """
        #TODO: Don't ignore start, implement a smarter lazy system.
        end = int(end)
        for x in xrange(self._next_window, end):
            self.write_fft(x)
        self._next_window = end

    def get_slice(self, start, end):
        """
        Calculates and returns the spectrogram in the range [start, end).
        """
        start, end = int(start), int(end)
        width = end - start
        if width < 0:
            raise ValueError("start cannot be greater than end.")
        if end > self.n_windows:
            raise ValueError("end cannot be greater than n_windows.")
        if start < 0:
            raise ValueError("start cannot be less than zero.")

        self.calculate(start, end)

        # Convert to OpenCV Image
        # Partially based on:
        # http://www.socouldanyone.com/2013/03/converting-grayscale-to-rgb-with-numpy.html
        #TODO: This is a bit messy, but it will be removed when OpenCV is no
        #      longer a dependancy.
        gray = self.spec[start:end].transpose()
        rgb = numpy.empty(gray.shape + (3,), dtype=numpy.uint8)
        rgb[:, :, 2] = rgb[:, :, 1] = rgb[:, :, 0] = gray
        mat = cv.fromarray(rgb)
        img = cv.CreateImage((mat.width, mat.height), 8, 3)
        cv.Copy(mat, img)
        return img

        #return self.spec[start:end]

    def write_fft(self, window_idx):
        """Write a single column of the spectrogram."""
        if window_idx >= self.n_windows:
            return

        start = self.window_step * window_idx
        end = start + self.window_width

        window = self.data[start:end]
        if self.taper is not None:
            window = window * self.taper

        fft_data = fftpack.fft(window)
        fft_data = fft_data[:len(fft_data)//2][::-1]

        # Take magnitude of imaginary fft output
        # Faster version of:
        #   >>> map(lambda x: sqrt(x.real**2 + x.imag**2), fft_data)
        fft_data = numpy.absolute(fft_data)

        if self.smooth_kernel is not None:
            fft_data = signal.convolve(fft_data, self.smooth_kernel, mode="same")

        fft_data = map(lambda x: min(255, 32*x // 65535), fft_data)
        self.spec[window_idx] = fft_data

    def get_freq_at_pos(self, y, sample_rate=1):
        freqs = numpy.fft.fftfreq(self.window_width, 1/sample_rate)
        return freqs[y]


class SpectrogramView(object):
    """
    Produce images showing slices of the spectrogram.
    """

    def __init__(self, spectrogram, display_width=1024, precalc_first_view=True):
        """
        Args:
            spectrogram: A Spectrogram instance to display.
            display_width: The number of windows to show in images returned by
                the ``view`` method. Each window is one pixel wide.
            precalc_first_view: If True, the spectrogram is precalculated for
                the first ``display_width`` windows durring initialization.
        """
        self.spectrogram = spectrogram
        self.display_width = min(display_width, spectrogram.n_windows)
        self.height = None

        if precalc_first_view:
            self.spectrogram.calculate(0, display_width)
        #self.spectrogram.calculate(0, spectrogram.n_windows)

    def view(self, sample_idx):
        """
        Return an image of the spectrogram centered around the sample at
        sample_idx.

        Arguments:
            sample_idx: The offset into data which to center and highlight.

        Returns:
            A spectrogram in the form of an OpenCV IplImage with the sample_idx
            at the center. The image is always ``display_width`` pixels wide.
            The current sample window is highlighted.
        """
        window_idx = self.spectrogram.window_from_sample(sample_idx)

        # Center view on current window, but stop snap view to edges if we're
        # at the beginning or end.
        if self.display_width == self.spectrogram.n_windows:
            view_start = 0  # Display has shrunk to number of windows
        elif window_idx < self.display_width / 2:
            view_start = 0
        elif window_idx > self.spectrogram.n_windows - self.display_width/2:
            view_start = self.spectrogram.n_windows - self.display_width - 1
        else:
            view_start = window_idx - self.display_width//2

        img = self.spectrogram.get_slice(view_start, view_start + self.display_width)
        self.height = img.height

        # Draw line for current window
        for y in xrange(img.height):
            x = min(int(window_idx - view_start), img.width-1)
            v = 255 - cv.Get2D(img, y, x)[0]
            cv.Set2D(img, y, x, (v, v, v))

        return img
