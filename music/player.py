import os
import shlex
import subprocess
import tempfile
import time
from discord.oggparse import OggStream
from discord.player import FFmpegAudio

before_options = [
    "-y",
    "-vn",  # discard everything but the audio
    "-multiple_requests 1",  # not sure what this is doing
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",  # reconnect on failure
    "-fflags +discardcorrupt",  # don't crash on corrupt frames
]


class FFmpegTmpFileAudio(FFmpegAudio):
    """
    Audio source from FFMpeg.

    The decoded audio is stored inside a temporary file,
    to avoid buffer and disconnect issues.
    """

    def __init__(
        self,
        source,
        *,
        bitrate=128,
        codec=None,
        executable="ffmpeg",
        before_options=before_options,
        options=None,
    ):
        args = []
        subprocess_kwargs = {
            "stdin": subprocess.DEVNULL,
            "stderr": None,
            "stdout": None,
        }

        self._tempfile = tempfile.NamedTemporaryFile()

        if isinstance(before_options, str):
            args.append(before_options)
        elif isinstance(before_options, list):
            args.extend(before_options)

        codec = "copy" if codec in ("opus", "libopus") else "libopus"

        args.extend(
            (
                f"-i {source}",
                "-map_metadata -1",
                "-f opus",
                f"-c:a {codec}",
                "-ar 48000",
                "-ac 2",
                f"-b:a {bitrate}k",
                "-loglevel warning",
            )
        )

        if isinstance(options, str):
            args.append(options)

        args.append(self._tempfile.name)
        args = shlex.split(" ".join(args))

        super().__init__(source, executable=executable, args=args, **subprocess_kwargs)

        # Wait for file to be nonempty to stream (avoids premature stopping)
        t = time.time()
        while not os.stat(self._tempfile.name).st_size:
            time.sleep(0.01)
        print(time.time() - t)

        self._packet_iter = OggStream(self._tempfile).iter_packets()

    def read(self):
        return next(self._packet_iter, b"")

    def is_opus(self):
        return True

    def cleanup(self):
        self._tempfile.close()
