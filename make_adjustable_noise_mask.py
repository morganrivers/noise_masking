"""
A Python script to generate noise using SOX based on audio statistics.
The generated noise will adjust its volume based on the system's volume setting.
"""

import os
import numpy as np
import subprocess
import pulsectl
import time
import signal
import sys


# This function handles graceful exit when Ctrl+C is pressed.
def signal_handler(sig, frame):
    print("Exiting gracefully...")
    subprocess.run("killall play", shell=True)
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


# Function to fetch the system's volume and mute status
def get_system_volume():
    result = subprocess.run(["amixer", "sget", "Master"], stdout=subprocess.PIPE)
    output = result.stdout.decode()
    volume = int(output.split("[")[1].split("%")[0])
    is_muted = "off" in output
    return volume, is_muted


# Function to record audio using 'arecord'
def record_audio(duration=10):
    print(f"Recording {duration} seconds of audio...")
    subprocess.run(f"arecord -d {duration} -f cd data/input.wav", shell=True)


# Function to generate a spectrogram from an audio file using SOX
def generate_spectrogram():
    print("Generating spectrogram...")
    subprocess.run("sox data/input.wav -n spectrogram -o data/spectrum.png", shell=True)


# Function to fetch audio statistics using SOX
def fetch_audio_stats():
    print("Fetching audio statistics...")
    subprocess.run(
        "sox data/input.wav -n stat -freq 2>&1 | sed -n -e :a -e '1,15!{P;N;D;};N;ba' > data/data.txt",
        shell=True,
    )


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
            command = f"play -n synth noise band {mean} {standard_deviation} vol {initial_volume_dB}dB > /dev/null 2>&1"
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
        new_volume = 0 if is_muted else (volume_percentage / 100.0)
        new_volume_info = pulsectl.PulseVolumeInfo(
            new_volume, channels=len(sox_sink_input.volume.values)
        )
        pulse.volume_set(sox_sink_input, new_volume_info)

        # Continuously adjust the playback volume based on system volume
        while True:
            volume_percentage, is_muted = get_system_volume()
            new_volume = 0 if is_muted else (volume_percentage / 100.0)
            new_volume_info = pulsectl.PulseVolumeInfo(
                new_volume, channels=len(sox_sink_input.volume.values)
            )
            pulse.volume_set(sox_sink_input, new_volume_info)
            time.sleep(0.5)


def main():
    # Create data directory if it doesn't exist
    if not os.path.exists("data"):
        os.makedirs("data")

    # Uncomment the below line if you wish to record audio
    # record_audio()

    # Generate spectrogram and fetch audio statistics
    generate_spectrogram()
    fetch_audio_stats()

    # Calculate statistics for noise generation
    frequency, amplitude = np.loadtxt("data/data.txt", unpack=True)
    mean_amplitude = np.mean(amplitude)
    volume_dB = 10 * np.log10(mean_amplitude)
    mean = np.average(frequency, weights=amplitude)
    standard_deviation = np.sqrt(np.average((frequency - mean) ** 2, weights=amplitude))

    # Print the calculated values
    print("\nMean Frequency:", mean)
    print("Standard Deviation:", standard_deviation)
    print("Volume (dB):", volume_dB)

    # Play the noise and adjust volume
    play_and_adjust_volume(mean, standard_deviation, volume_dB)


if __name__ == "__main__":
    main()
