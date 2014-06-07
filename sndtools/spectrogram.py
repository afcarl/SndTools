import numpy

from scipy import signal
from scipy.fftpack import rfft

import cv

class Spectrogram(object):
    '''Calculate a fourier transform over time.

    The data is split into windows (possibly overlapping). The fourier
    transform is calculated in each window.

    TODO: Split this into two classes: Spectrogram and another class to view a
           slice of the spectrogram. Once this is done, more options can be
           cleanly added to both classes.
    TODO: What about the maximum frequency (height) of the spectrogram?
    '''

    def __init__(self, data, window_width, window_step, display_width=1024):
        '''
        Args:
            data: The samples to calculate the spectrogram of.
            window_width: Width of the moving fourier transform window.
            window_step: Window step size. If this is less than window_width,
                the windows will overlap.
            display_width: The number of windows to show in images returned by
                the ``view`` method. Each window is one pixel wide.

        TODO: Add options for taper function and smoothing.
        '''
        self.data = data
        self.window_width = window_width
        self.window_step = window_step

        self.n_windows = int((len(data) - window_width) // window_step) + 1
        self.display_width = min(display_width, self.n_windows)
        self.fft_height = int(window_width // 2)

        self.img = cv.CreateImage((self.n_windows, self.fft_height), 8, 3)
        cv.Zero(self.img)
        self.display_img = cv.CreateImage((self.display_width, self.fft_height), 8, 3)

        self.taper = None
        #self.taper = numpy.blackman(window_width)

        self.smooth_kernel = None
        #self.smooth_kernel = signal.gaussian(5, 1)

        for x in xrange(self.display_width):
            self._write_fft(self.img, x)
        self.next_window = self.display_width

    def window_idx_from_sample(self, sample_idx):
        '''Return the window index of the given index into data.

        Note that this method can't be exact, since there may be more than one
        windows overlapping any point. A window is always returned, even though
        there may be no windows at the exact point given.
        '''
        clamp = lambda lower, upper, x: max(lower, min(upper, x))
        return clamp(
            0, self.n_windows-1,
            (sample_idx - self.window_width) // self.window_step
        )

    def _write_fft(self, spectrogram_img, window_idx):
        '''Write a single column of the spectrogram.'''
        if window_idx >= self.n_windows:
            return

        start = self.window_step * window_idx
        end = start + self.window_width

        window = self.data[start:end]
        if self.taper is not None:
            window = window * self.taper

        fft_data = rfft(window)
        fft_data = fft_data[:len(fft_data)//2][::-1]

        if self.smooth_kernel is not None:
            fft_data = signal.convolve(fft_data, self.smooth_kernel, mode="same")

        for i, x in enumerate(fft_data):
            # TODO: Better scaling
            v = min(255, 32*x // 65535)
            cv.Set2D(spectrogram_img, i, window_idx, (v, v, v))

    def view(self, sample_idx):
        '''Generate a spectrogram centered around the sample index.

        Arguments:
            sample_idx: The offset into data which to center and highlight.

        Returns:
            An spectrogram in the form of an OpenCV IplImage with the
            sample_idx at the center. The image is always ``display_width``
            pixels wide. The current sample window is highlighted.
        '''
        window_idx = self.window_idx_from_sample(sample_idx)

        # Center view on current window, but stop snap view to edges if we're
        # at the beginning or end.
        if self.display_width == self.n_windows:
            view_start = 0  # Display has shrunk to number of windows
        elif window_idx < self.display_width / 2:
            view_start = 0
        elif window_idx > self.n_windows - self.display_width/2:
            view_start = self.n_windows - self.display_width - 1
        else:
            view_start = window_idx - self.display_width//2

        # Write fft on demand
        windows_to_write = int(view_start + self.display_width - self.next_window)
        for i in xrange(self.next_window, self.next_window + windows_to_write):
            self._write_fft(self.img, i)
        self.next_window = self.next_window + windows_to_write

        # Copy full spectogram, self.img, to self.display_img
        roi = (
            int(view_start), 0,
            self.display_width, self.fft_height
        )
        cv.SetImageROI(self.img, roi)
        cv.Copy(self.img, self.display_img)
        cv.ResetImageROI(self.img)

        # Draw line for current window
        for y in xrange(self.display_img.height):
            x = min(int(window_idx - view_start), self.display_img.width-1)
            v = 255 - cv.Get2D(self.display_img, y, x)[0]
            cv.Set2D(self.display_img, y, x, (v, v, v))

        return self.display_img
