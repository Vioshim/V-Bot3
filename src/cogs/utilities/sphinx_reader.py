# Copyright 2022 Vioshim
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import unicodedata
from io import BytesIO
from zlib import decompressobj

__all__ = ("SphinxObjectFileReader",)


def to_string(c: str) -> str:
    """To String Method

    Parameters
    ----------
    c : str
        Character

    Returns
    -------
    str
        Parameters
    """
    digit = f"{ord(c):x}"
    url = f"http://www.fileformat.info/info/unicode/char/{digit}"
    name = unicodedata.name(c, "Name not found.")
    return f"[`\\U{digit:>08}`](<{url}>): {name} - {c}"


class SphinxObjectFileReader:
    BUFSIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = BytesIO(buffer)

    def readline(self):
        return self.stream.readline().decode("utf-8")

    def skipline(self):
        self.stream.readline()

    def read_compressed_chunks(self):
        decompressor = decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
            if len(chunk) == 0:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self):
        buf = b""
        for chunk in self.read_compressed_chunks():
            buf += chunk
            while (pos := buf.find(b"\n")) != -1:
                yield buf[:pos].decode("utf-8")
                buf = buf[pos + 1 :]
