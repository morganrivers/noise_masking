"""
A Python script to generate noise using SOX based on audio statistics.
The generated noise will adjust its volume based on the system's volume setting.
"""

import numpy as np
import os
import platform
import signal
import shutil
import subprocess
import sys
import time


if sys.platform.startswith("linux"):
    import pulsectl

    t = time.localtime()
    time_str = f"{t.tm_year}_{t.tm_mon}_{t.tm_mday}_{t.tm_hour}_{t.tm_min}"


# This function handles graceful exit when Ctrl+C is pressed.
def signal_handler(sig, frame):
    print("Exiting gracefully...")
    subprocess.run("killall play", shell=True)
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def get_system_volume():
    result = subprocess.run(["amixer", "sget", "Master"], stdout=subprocess.PIPE)
    output = result.stdout.decode()
    volume = int(output.split("[")[1].split("%")[0])
    is_muted = "off" in output
    return volume, is_muted


def set_system_volume(volume):
    """Set the system volume. Volume should be an integer between 0 and 100."""
    result = subprocess.run(["amixer", "sget", "Master"], stdout=subprocess.PIPE)
    output = result.stdout.decode()
    volume = int(output.split("[")[1].split("%")[0])
    is_muted = "off" in output
    return volume, is_muted


def record_audio(duration=10):
    subprocess.run(f"arecord -d {duration} -f cd data/input.wav", shell=True)
    # copy as a record for the future
    shutil.copy("data/input.wav", f"data/input_{time_str}.wav")


# Function to record audio using 'arecord'
def record_audio_osx(duration=10):
    print(f"Recording {duration} seconds of audio...")
    filename = f"data/input.wav"
    subprocess.run(f"sox -d {filename} trim 0 {duration}", shell=True)
    print(f"Audio recorded and saved as {filename}")


# Function to generate a spectrogram from an audio file using SOX
def generate_spectrogram():
    print("Generating spectrogram...")
    subprocess.run(
        f"sox data/input.wav -n spectrogram -o data/spectrum.png", shell=True
    )


# Function to fetch audio statistics using SOX
def fetch_audio_stats():
    print("Fetching audio statistics...")
    subprocess.run(
        "sox data/input.wav -n stat -freq 2>&1 | sed -n -e :a -e '1,15!{P;N;D;};N;ba' > data/data.txt",
        shell=True,
    )


def db_to_linear(dB):
    """Convert dB value to linear scale factor"""
    return 10 ** (dB / 20)


def get_new_volume(volume_percentage, is_muted):
    volume_adjustment = 0
    return 0 if is_muted else (volume_percentage / 100.0)


def set_volume(volume_percentage, is_muted, pulse, sox_sink_input):
    new_volume = get_new_volume(volume_percentage, is_muted)

    new_volume_info = pulsectl.PulseVolumeInfo(
        new_volume, channels=len(sox_sink_input.volume.values)
    )

    pulse.volume_set(sox_sink_input, new_volume_info)


def play_noise_osx(mean, standard_deviation, volume_dB):
    """Play noise using sox with specified parameters and return the subprocess."""
    volume_adjustment = volume_dB  # Use the calculated volume or set a preferred level
    command = f"play -n synth noise band {mean} {standard_deviation} vol {volume_adjustment}dB"
    print("Playing noise. Press Ctrl+C to stop.")
    process = subprocess.Popen(command, shell=True)
    print("process.pid: ", process.pid)
    return process


# Function to play noise and adjust its volume based on system volume
def play_and_adjust_volume(mean, standard_deviation, initial_volume_dB):
    with pulsectl.Pulse("volume-adjuster") as pulse:
        volume_percentage, is_muted = get_system_volume()  # Get initial system volume

        # Give some time in case a previous play command is still lingering
        time.sleep(0.2)

        # Check if the SOX process exists in the pulse audio list
        sox_sink_input = next(
            (
                si
                for si in pulse.sink_input_list()
                if si.proplist.get("application.name") == "ALSA plug-in [sox]"
            ),
            None,
        )

        # If the SOX process isn't already playing, start it
        if not sox_sink_input:
            # reduce by 10db... it's a bit too loud generally without doing this
            reduced_volume = initial_volume_dB - 20

            # This actually renders the noise using the sox package.
            # Eliminating loud noise at beginning from previous command:
            #     play -n synth noise band {mean} {standard_deviation} vol {initial_volume_dB}dB > /dev/null 2>&1
            command = f"play -n trim 0.0 2.0 : synth noise band {mean} {standard_deviation} \
                        vol {reduced_volume}dB \
                        > /dev/null 2>&1"  # don't show errors or stdout

            subprocess.Popen(command, shell=True)

            time.sleep(0.2)  # Give time for the new play process to show up

            sox_sink_input = next(
                (
                    si
                    for si in pulse.sink_input_list()
                    if si.proplist.get("application.name") == "ALSA plug-in [sox]"
                ),
                None,
            )

            if not sox_sink_input:
                print("Couldn't find sox stream in PulseAudio.")
                return

        # Get the initial volume of the SOX process
        initial_sink_volume = sox_sink_input.volume.value_flat

        # Set the playback volume based on the system volume
        set_volume(volume_percentage, is_muted, pulse, sox_sink_input)

        # Continuously adjust the playback volume based on system volume
        while True:
            volume_percentage, is_muted = get_system_volume()
            set_volume(volume_percentage, is_muted, pulse, sox_sink_input)
            time.sleep(0.5)


def identify_os():
    if sys.platform.startswith("darwin"):
        return "OS X (macOS)"
    elif sys.platform.startswith("linux"):
        return "Linux"
    else:
        return "Unsupported OS, feel free to open an issue here https://github.com/morganrivers/noise_masking"


def main():
    # Check OS validity
    identify_os()

    # Create data directory if it doesn't exist
    if not os.path.exists("data"):
        os.makedirs("data")
    if os.path.isfile("data/data.txt"):
        while True:
            user_input = input("Record new audio or use the old one? [r/o]\n")
            if user_input == "r":
                if sys.platform.startswith("darwin"):
                    record_audio_osx()
                    break
                elif sys.platform.startswith("linux"):
                    record_audio()
                    break
            elif user_input == "o":
                print("Using old audio...")
                break
            else:
                print(
                    'You didn\'t type "r" for record or "o" for old. Please try again.'
                )
    else:
        record_audio()

    # Generate spectrogram and fetch audio statistics
    generate_spectrogram()
    fetch_audio_stats()

    # Calculate statistics for noise generation
    frequency, amplitude = np.loadtxt("data/data.txt", unpack=True)
    mean_amplitude = np.mean(amplitude)
    volume_dB = 10 * np.log10(mean_amplitude)

    # Check if the sum of amplitude is zero
    if np.sum(amplitude) == 0:
        raise ValueError(
            "Error: The microphone was not turned on or there's no audio input signal."
        )
    else:
        mean = np.average(frequency, weights=amplitude)

    standard_deviation = np.sqrt(np.average((frequency - mean) ** 2, weights=amplitude))

    # Print the calculated values
    print("\nMean Frequency:", mean)
    print("Standard Deviation:", standard_deviation)
    print("Volume (dB):", volume_dB)
    print("")
    print("Please use Control + c or other SIGINT to exit gracefully.")

    # Play the noise and adjust volume
    if sys.platform.startswith("darwin"):
        play_noise_osx(mean, standard_deviation, volume_dB)
    elif sys.platform.startswith("linux"):
        play_and_adjust_volume(mean, standard_deviation, volume_dB)


if __name__ == "__main__":
    main()
