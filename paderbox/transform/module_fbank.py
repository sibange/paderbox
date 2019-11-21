"""
Provides fbank features and the fbank filterbank.
"""

from typing import Optional

import numpy
import numpy as np
import scipy.signal
from cached_property import cached_property
from paderbox.transform.module_filter import \
    preemphasis_with_offset_compensation
from paderbox.transform.module_stft import stft
from paderbox.transform.module_stft import stft_to_spectrogram


class MelTransform:
    def __init__(
            self,
            sample_rate: int,
            fft_length: int,
            n_mels: Optional[int] = 40,
            fmin: Optional[int] = 50,
            fmax: Optional[int] = None,
            log: bool = True
    ):
        """
        Transforms linear spectrogram to (log) mel spectrogram.

        Args:
            sample_rate: sample rate of audio signal
            fft_length: fft_length used in stft
            n_mels: number of filters to be applied
            fmin: lowest frequency (onset of first filter)
            fmax: highest frequency (offset of last filter)
            log: apply log to mel spectrogram

        >>> mel_transform = MelTransform(16000, 512)
        >>> spec = np.zeros((100, 257))
        >>> logmelspec = mel_transform(spec)
        >>> logmelspec.shape
        (100, 40)
        >>> rec = mel_transform.inverse(logmelspec)
        >>> rec.shape
        (100, 257)
        """
        self.sample_rate = sample_rate
        self.fft_length = fft_length
        self.n_mels = n_mels
        self.fmin = fmin
        self.fmax = fmax
        self.log = log

    @cached_property
    def fbanks(self):
        import librosa
        fbanks = librosa.filters.mel(
            n_mels=self.n_mels,
            n_fft=self.fft_length,
            sr=self.sample_rate,
            fmin=self.fmin,
            fmax=self.fmax,
            htk=True,
            norm=None
        )
        fbanks = fbanks / fbanks.sum(axis=-1, keepdims=True)
        return fbanks.T

    @cached_property
    def ifbanks(self):
        return np.linalg.pinv(self.fbanks.T).T

    def __call__(self, x):
        x = np.dot(x, self.fbanks)
        if self.log:
            x = np.log(x + 1e-18)
        return x

    def inverse(self, x):
        if self.log:
            x = np.exp(x)
        return np.maximum(np.dot(x, self.ifbanks), 0.)


def fbank(time_signal, sample_rate=16000, window_length=400, stft_shift=160,
          number_of_filters=23, stft_size=512, lowest_frequency=0,
          highest_frequency=None, preemphasis_factor=0.97,
          window=scipy.signal.hamming, denoise=False):
    """
    Compute Mel-filterbank energy features from an audio signal.

    Source: https://github.com/jameslyons/python_speech_features
    Tutorial: http://www.practicalcryptography.com/miscellaneous/machine-learning/guide-mel-frequency-cepstral-coefficients-mfccs/ # noqa

    Illustrations: http://ntjenkins.upb.de/view/PythonToolbox/job/python_toolbox_notebooks/HTML_Report/toolbox_examples/transform/06%20-%20Additional%20features.html


    :param time_signal: the audio signal from which to compute features.
        Should be an N*1 array
    :param sample_rate: the sample rate of the signal we are working with.
    :param window_length: the length of the analysis window in samples.
        Default is 400 (25 milliseconds @ 16kHz)
    :param stft_shift: the step between successive windows in samples.
        Default is 160 (10 milliseconds @ 16kHz)
    :param number_of_filters: the number of filters in the filterbank,
        default 23.
    :param stft_size: the FFT size. Default is 512.
    :param lowest_frequency: lowest band edge of mel filters.
        In Hz, default is 0.
    :param highest_frequency: highest band edge of mel filters.
        In Hz, default is samplerate/2
    :param preemphasis_factor: apply preemphasis filter with preemph as coefficient.
        0 is no filter. Default is 0.97.
    :param window: window function used for stft
    :param denoise: ???.
    :returns: A numpy array of size (frames by number_of_filters) containing the
        Mel filterbank features.
    """
    highest_frequency = highest_frequency or sample_rate / 2
    time_signal = preemphasis_with_offset_compensation(
        time_signal, preemphasis_factor)

    stft_signal = stft(
        time_signal,
        size=stft_size, shift=stft_shift,
        window=window, window_length=window_length,
        fading=None
    )

    spectrogram = stft_to_spectrogram(stft_signal) / stft_size

    mel_transform = MelTransform(
        sample_rate=sample_rate,
        fft_length=stft_size,
        n_mels=number_of_filters,
        fmin=lowest_frequency,
        fmax=highest_frequency,
        log=False
    )
    feature = mel_transform(spectrogram)

    if denoise:
        feature -= numpy.min(feature, axis=0)

    # if feat is zero, we get problems with log
    feature = numpy.where(feature == 0, numpy.finfo(float).eps, feature)

    return feature


def get_filterbanks(number_of_filters=20, nfft=1024, sample_rate=16000,
                    lowfreq=0, highfreq=None):
    """Compute a Mel-filterbank. The filters are stored in the rows, the columns
    correspond to fft bins. The filters are returned as an array of size
    nfilt * (nfft/2 + 1)

    Source: https://github.com/jameslyons/python_speech_features

    :param number_of_filters: the number of filters in the filterbank.
        Default is 20.
    :param nfft: the FFT size. Default is 1024.
    :param sample_rate: the samplerate of the signal we are working with.
        Affects mel spacing.
    :param lowfreq: lowest band edge of mel filters, Default 0 Hz.
    :param highfreq: highest band edge of mel filters, Default is samplerate/2.
    :returns: A numpy array of size nfilt by (nfft/2 + 1) containing filterbank.
        Each row holds 1 filter.

    ToDo: Can this function be removed?
    """
    raise AssertionError('This function is wrong. Use e.g. librosa. '
                         'See http://ntjenkins.upb.de:8082/'
                         'python_toolbox_notebooks/build/toolbox_examples/'
                         'transform/06%20-%20Additional%20features.html')
    highfreq = highfreq or sample_rate / 2
    assert highfreq <= sample_rate / 2, "highfreq is greater than samplerate/2"

    # compute points evenly spaced in mels
    lowmel = hz2mel(lowfreq)
    highmel = hz2mel(highfreq)
    melpoints = numpy.linspace(lowmel, highmel, number_of_filters + 2)
    # our points are in Hz, but we use fft bins, so we have to convert
    #  from Hz to fft bin number
    bin = numpy.floor((nfft + 1) * mel2hz(melpoints) / sample_rate)

    assert numpy.mod(nfft, 2) == 0
    fbank = numpy.zeros([number_of_filters, nfft // 2 + 1])
    for j in range(0, number_of_filters):
        for i in range(int(bin[j]), int(bin[j + 1])):
            fbank[j, i] = (i - bin[j]) / (bin[j + 1] - bin[j])
        for i in range(int(bin[j + 1]), int(bin[j + 2])):
            fbank[j, i] = (bin[j + 2] - i) / (bin[j + 2] - bin[j + 1])
    return fbank


def hz2mel(hz):
    """Convert a value in Hertz to Mels

    :param hz: a value in Hz. This can also be a numpy array, conversion
        proceeds element-wise.
    :returns: a value in Mels. If an array was passed in, an identical sized
        array is returned.
    """
    return 2595 * numpy.log10(1 + hz / 700.0)


def mel2hz(mel):
    """Convert a value in Mels to Hertz

    :param mel: a value in Mels. This can also be a numpy array, conversion
        proceeds element-wise.
    :returns: a value in Hertz. If an array was passed in, an identical sized
        array is returned.
    """
    return 700 * (10 ** (mel / 2595.0) - 1)


def logfbank(time_signal, sample_rate=16000, window_length=400, stft_shift=160,
             number_of_filters=23, stft_size=512, lowest_frequency=0,
             highest_frequency=None, preemphasis_factor=0.97,
             window=scipy.signal.hamming, denoise=False):
    """Generates log fbank features from time signal.

    Simply wraps fbank function. See parameters there.
    """
    return numpy.log(fbank(
        time_signal,
        sample_rate=sample_rate,
        window_length=window_length,
        stft_shift=stft_shift,
        number_of_filters=number_of_filters,
        stft_size=stft_size,
        lowest_frequency=lowest_frequency,
        highest_frequency=highest_frequency,
        preemphasis_factor=preemphasis_factor,
        window=window,
        denoise=denoise
    ))
