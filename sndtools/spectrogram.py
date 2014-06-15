import numpy

from scipy import signal
from scipy import fftpack

import cv


class Spectrogram(object):
    """Calculate a fourier transform over time.

    The data is split into windows (possibly overlapping). The fourier
    transform is calculated in each window.

    TODO: What about the maximum frequency (height) of the spectrogram?
    """

    def __init__(self, data, window_width, window_step):
        """
        Args:
            data: The samples to calculate the spectrogram of. Should be a list
                of numbers.
            window_width: Width of the moving fourier transform window.
            window_step: Window step size. If this is less than window_width,
                the windows will overlap.

        TODO: Add options for taper function and smoothing.
        """
        self.data = numpy.array(data)
        self.window_width = window_width
        self.window_step = window_step

        self.n_windows = int((len(data) - window_width) // window_step) + 1
        self.height = int(window_width // 2)

        # The spectrogram image itself
        self.img = cv.CreateImage((self.n_windows, self.height), 8, 3)

        self.taper = None
        #self.taper = numpy.blackman(window_width)

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
        self.calculate_up_to(self.n_windows)
        return cv.CloneImage(self.img)

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

    def calculate_up_to(self, window_idx):
        """
        Calculates the fft up to the given ``window_idx``.

        Users don't normally need to use this. It's useful if you're using the
        ``img`` attribute directly and need to ensure that the spectrogram is
        calculated up to a certain point.
        """
        window_idx = int(window_idx)
        for x in xrange(self._next_window, window_idx):
            self.write_fft(x)
        self._next_window = window_idx

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

        for i, x in enumerate(fft_data):
            # TODO: Better scaling
            v = min(255, 32*x // 65535)
            cv.Set2D(self.img, i, window_idx, (v, v, v))


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
        self.display_width = display_width
        self.display_img = cv.CreateImage((self.display_width, self.spectrogram.height), 8, 3)

        if precalc_first_view:
            self.spectrogram.calculate_up_to(display_width)

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

        # Calculate fft on demand
        self.spectrogram.calculate_up_to(view_start + self.display_width)

        # Copy full spectogram, self.spectrogram.img, to self.display_img
        roi = (
            int(view_start), 0,
            self.display_width, self.spectrogram.height
        )
        original_roi = cv.GetImageROI(self.spectrogram.img)
        cv.SetImageROI(self.spectrogram.img, roi)
        cv.Copy(self.spectrogram.img, self.display_img)
        cv.SetImageROI(self.spectrogram.img, original_roi)

        # Draw line for current window
        for y in xrange(self.display_img.height):
            x = min(int(window_idx - view_start), self.display_img.width-1)
            v = 255 - cv.Get2D(self.display_img, y, x)[0]
            cv.Set2D(self.display_img, y, x, (v, v, v))

        return cv.CloneImage(self.display_img)
