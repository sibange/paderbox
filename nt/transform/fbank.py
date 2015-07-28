"""
Provides fbank features and the fbank filterbank.
"""

import numpy
from nt.transform import filter
from nt.transform import mod_stft
import scipy.signal

def fbank(time_signal, sample_rate=16000, window_length=400, stft_shift=160,
          number_of_filters=26, stft_size=512, lowest_frequency=0,
          highest_frequency=None, preemphasis=0.97,
          window=scipy.signal.hamming):
    """
    Compute Mel-filterbank energy features from an audio signal.

    Source: https://github.com/jameslyons/python_speech_features
    Tutorial: http://www.practicalcryptography.com/miscellaneous/machine-learning/guide-mel-frequency-cepstral-coefficients-mfccs/ # noqa

    :param time_signal: the audio signal from which to compute features.
        Should be an N*1 array
    :param sample_rate: the samplerate of the signal we are working with.
    :param window_length: the length of the analysis window in samples.
        Default is 400 (25 milliseconds @ 16kHz)
    :param stft_shift: the step between successive windows in seconds.
        Default is 0.01s (10 milliseconds)
    :param number_of_filters: the number of filters in the filterbank,
        default 26.
    :param stft_size: the FFT size. Default is 512.
    :param lowest_frequency: lowest band edge of mel filters.
        In Hz, default is 0.
    :param highest_frequency: highest band edge of mel filters.
        In Hz, default is samplerate/2
    :param preemphasis: apply preemphasis filter with preemph as coefficient.
        0 is no filter. Default is 0.97.
    :returns: Mel filterbank features.
    """
    highest_frequency = highest_frequency or sample_rate/2
    time_signal = filter.offcomp(time_signal)
    time_signal = filter.preemphasis(time_signal, preemphasis)

    stft_signal = mod_stft.stft(time_signal, size=stft_size, shift=stft_shift,
                      window=window, window_length=window_length, fading=False)

    spectrogram = mod_stft.stft_to_spectrogram(stft_signal)/stft_size

    filterbanks = get_filterbanks(number_of_filters, stft_size, sample_rate,
                                  lowest_frequency, highest_frequency)

    # compute the filterbank energies
    feature = numpy.dot(spectrogram, filterbanks.T)

    # if feat is zero, we get problems with log
    feature = numpy.where(feature == 0, numpy.finfo(float).eps, feature)

    return feature


def get_filterbanks(number_of_filters=20, nfft=1024, sample_rate=16000,
                    lowfreq=0, highfreq=None):
    """Compute a Mel-filterbank. The filters are stored in the rows, the columns
    correspond to fft bins. The filters are returned as an array of size
    nfilt * (nfft/2 + 1)

    Source: https://github.com/jameslyons/python_speech_features

    :param nfilt: the number of filters in the filterbank, default 20.
    :param nfft: the FFT size. Default is 1024.
    :param sample_rate: the samplerate of the signal we are working with.
        Affects mel spacing.
    :param lowfreq: lowest band edge of mel filters, default 0 Hz
    :param highfreq: highest band edge of mel filters, default samplerate/2
    :returns: A numpy array of size nfilt * (nfft/2 + 1) containing filterbank.
        Each row holds 1 filter.
    """
    highfreq = highfreq or sample_rate/2
    assert highfreq <= sample_rate/2, "highfreq is greater than samplerate/2"

    # compute points evenly spaced in mels
    lowmel = hz2mel(lowfreq)
    highmel = hz2mel(highfreq)
    melpoints = numpy.linspace(lowmel, highmel, number_of_filters+2)
    # our points are in Hz, but we use fft bins, so we have to convert
    #  from Hz to fft bin number
    bin = numpy.floor((nfft+1)*mel2hz(melpoints)/sample_rate)

    fbank = numpy.zeros([number_of_filters, nfft/2+1])
    for j in range(0, number_of_filters):
        for i in range(int(bin[j]),int(bin[j+1])):
            fbank[j,i] = (i - bin[j])/(bin[j+1]-bin[j])
        for i in range(int(bin[j+1]),int(bin[j+2])):
            fbank[j,i] = (bin[j+2]-i)/(bin[j+2]-bin[j+1])
    return fbank

def hz2mel(hz):
    """Convert a value in Hertz to Mels

    :param hz: a value in Hz. This can also be a numpy array, conversion
        proceeds element-wise.
    :returns: a value in Mels. If an array was passed in, an identical sized
        array is returned.
    """
    return 2595 * numpy.log10(1+hz/700.0)

def mel2hz(mel):
    """Convert a value in Mels to Hertz

    :param mel: a value in Mels. This can also be a numpy array, conversion
        proceeds element-wise.
    :returns: a value in Hertz. If an array was passed in, an identical sized
        array is returned.
    """
    return 700*(10**(mel/2595.0)-1)
