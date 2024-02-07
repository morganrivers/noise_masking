# noise_masking

This script records audio, generates a spectrogram, fetches audio statistics, and plays back audio with adjusted volume in real-time based on the system volume. It's great for blocking voices at coffee shops and communal spaces, but it doesn't have to be very loud as it focuses the audio only on the frequency range that is the loudest in the environment. It works great in combination with noise-cancelling headphones.

WATCH OUT FOR YOUR EARS RUNNING THE SCRIPT THE FIRST TIME! IT MIGHT BE LOUD

## Requirements

This script requires Python3 and the following external libraries and software:

- `numpy`: For numerical calculations.
- `matplotlib`: For plotting audio data.
- `pulsectl`: For adjusting played audio volume in real-time.
- `sox`: For audio recording, spectrogram generation, and playback.
- `amixer`: For fetching the system volume.

## Installation

### Ubuntu/Debian

You can install the required Python libraries using pip and external software using apt:

```bash
# Install pip if not already installed
sudo apt-get install python3-pip

# Install required Python libraries
pip3 install numpy matplotlib pulsectl

# Install sox and amixer
sudo apt-get install sox alsa-utils
```

### Other Operating Systems

Please refer to the official websites for installation instructions on other operating systems:

- [NumPy](https://numpy.org/install/)
- [Matplotlib](https://matplotlib.org/stable/users/installing.html)
- [PulseCtl](https://pypi.org/project/pulsectl/)
- [SoX](https://linux.die.net/man/1/sox)

## Running the Script

To run the script, navigate to the directory containing the script in the terminal and execute the following command:

```bash
python3 make_adjustable_noise_mask.py
```

## Usage

Run the script, and it will automatically record audio, generate a spectrogram, fetch audio statistics, and play back audio with volume adjusted in real-time based on your system volume. The script is intended to be used as is, and further modification might be required for more specific use cases.

It adjusts to alterations of system volume every half second.

## Note

Ensure the `amixer` and `sox` utilities are correctly set up and configured for your audio hardware for the script to function as expected.

It's only been tested on my machine... you might need to fine-tune the script a bit for your system and audio devices.
