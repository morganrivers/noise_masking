import pulsectl

# NOTE: this needs to have another terminal running something like
# $ play -n synth noise band 294.64755584600573 889.2414365714045 vol -20dB
# running.
# Then it will reset volume to normal.


def reset_sox_volume():
    # Define the name of the application we're looking for
    app_name = "ALSA plug-in [sox]"

    # Connect to PulseAudio
    with pulsectl.Pulse("volume-resetter") as pulse:
        # Find the SOX process in the PulseAudio list
        sox_sink_input = next(
            (
                si
                for si in pulse.sink_input_list()
                if si.proplist.get("application.name") == app_name
            ),
            None,
        )

        # If found, set its volume to 100%
        if sox_sink_input:
            volume_info = pulsectl.PulseVolumeInfo(
                1, channels=len(sox_sink_input.volume.values)
            )
            pulse.volume_set(sox_sink_input, volume_info)
            print(f"Volume for '{app_name}' reset to 100%.")
        else:
            print(f"No active stream found for '{app_name}'.")


if __name__ == "__main__":
    reset_sox_volume()
