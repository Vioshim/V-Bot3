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

from datetime import datetime
from logging import INFO, Formatter, Logger, LogRecord, StreamHandler

from pytz import UTC, timezone

__all__ = ("ColoredLogger",)

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"


def formatter_message(message: str, use_color=True) -> str:
    """Message Formatter

    Parameters
    ----------
    message: str
        Message to format
    use_color: bool = True
        If using colors or not

    Returns
    -------
    str:
        message formatted
    """
    if use_color:
        message = message.replace("$RESET", RESET_SEQ)
        message = message.replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "")
        message = message.replace("$BOLD", "")
    return message


COLORS = dict(
    WARNING=YELLOW,
    INFO=BLUE,
    DEBUG=WHITE,
    CRITICAL=YELLOW,
    ERROR=RED,
)


class ColoredFormatter(Formatter):
    def __init__(self, msg: str, use_color=True):
        """Init Method

        Parameters
        ----------
        msg: str
            Format
        use_color: bool = True
            If using color or not
        """
        super().__init__(fmt=msg, datefmt=r"%Y-%m-%d,%H:%M:%S.%f")
        self.use_color = use_color

    def converter(self, timestamp):
        # Create datetime in UTC
        dt = datetime.fromtimestamp(timestamp, tz=UTC)
        # Change datetime's timezone
        return dt.astimezone(timezone("America/Bogota"))

    def formatTime(self, record: LogRecord, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec="milliseconds")
            except TypeError:
                s = dt.isoformat()
        return s

    def format(self, record: LogRecord) -> str:
        """Formatting Method

        Parameters
        ----------
        record : LogRecord
            Record

        Returns
        -------
        str
            Formatted value
        """
        level_name: str = record.levelname
        if self.use_color and level_name in COLORS:
            level_name_color: str = (
                COLOR_SEQ % (30 + COLORS[level_name]) + level_name + RESET_SEQ
            )
            record.levelname = level_name_color
            pathname = record.pathname.replace("/root/V-Bot3/src/", "")
            pathname = pathname.replace("/root/V-Bot3/", "")
            record.pathname = pathname.replace("/app/", "")
        return super(ColoredFormatter, self).format(record)


class ColoredLogger(Logger):
    FORMAT = "$BOLD[%(levelname)s]$RESET%(pathname)s|%(funcName)s %(message)s"
    COLOR_FORMAT = formatter_message(FORMAT, True)

    def __init__(self, name: str):
        """Init Method

        Parameters
        ----------
        name: str
            Logger's Name
        """
        super().__init__(name, INFO)
        color_formatter = ColoredFormatter(self.COLOR_FORMAT)
        console = StreamHandler()
        console.setFormatter(color_formatter)
        self.addHandler(console)
