# commands.py
# Parses and validates raw terminal input.
# No state logic. No output formatting. No side effects.

from dataclasses import dataclass, field
from typing import Tuple, Union
import time

from config import PERMITTED_COMMANDS


@dataclass
class CommandRecord:
    name:      str
    argument:  str
    timestamp: float = field(default_factory=time.time)


@dataclass
class RejectionRecord:
    raw:    str
    reason: str


class CommandParser:

    def parse(self, raw: str) -> Tuple[bool, Union[CommandRecord, RejectionRecord]]:
        """
        Returns (True, CommandRecord) for valid input.
        Returns (False, RejectionRecord) for anything else.
        """
        stripped = raw.strip()

        if not stripped:
            return False, RejectionRecord(raw=raw, reason="EMPTY_INPUT")

        tokens  = stripped.split(None, 1)
        keyword = tokens[0].upper()
        arg     = tokens[1].strip() if len(tokens) > 1 else ""

        if keyword not in PERMITTED_COMMANDS:
            return False, RejectionRecord(raw=raw, reason=f"UNKNOWN_COMMAND:{keyword}")

        return True, CommandRecord(name=keyword, argument=arg)

    def format_rejection(self, record: RejectionRecord) -> str:
        return (
            f"\n[BOUNDARY]\n"
            f"  STATUS   : INPUT_REJECTED\n"
            f"  REASON   : {record.reason}\n"
            f"  INPUT    : {repr(record.raw[:60])}\n"
            f"  PERMITTED: {', '.join(sorted(PERMITTED_COMMANDS))}"
        )
