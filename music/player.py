import os
import shlex
import subprocess
import tempfile
import time
from typing import List, Optional, Union

from discord.oggparse import OggStream
from discord.player import FFmpegAudio


class FFmpegTmpFileAudio(FFmpegAudio):
    """
    Audio source from FFMpeg.

    The decoded audio is stored inside a temporary file,
    to avoid buffer and disconnect issues.
    """

    def __init__(
        self,
        source: str,
        *,
        bitrate: int = 128,
        codec: Optional[str] = None,
        executable: str = "ffmpeg",
        before_options: Optional[Union[str, List[str]]] = None,
        options: Optional[Union[str, List[str]]] = None,
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
        elif isinstance(options, list):
            args.extend(options)

        args.append(self._tempfile.name)
        args = shlex.split(" ".join(args))

        super().__init__(source, executable=executable, args=args, **subprocess_kwargs)

        # Wait for file to be nonempty to stream (avoids premature stopping)
        # Loses up to 1s on very slow connections...
        while not os.stat(self._tempfile.name).st_size:
            time.sleep(0.01)

        self._packet_iter = OggStream(self._tempfile).iter_packets()

    def read(self):
        return next(self._packet_iter, b"")

    def is_opus(self):
        return True

    def cleanup(self):
        self._tempfile.close()
