"""
File helpers shared by the writers.
"""

import time
from pathlib import Path

REPLACE_ATTEMPTS = 6
REPLACE_DELAY_SECONDS = 0.5


def replace_file(temporary, destination):
    """
    Move a finished temporary file onto its destination.

    On Windows the destination can be held open for a moment by a viewer, an
    indexer or a virus scanner, and the move then raises PermissionError. The
    move is tried a few times. If the file is still held, the error is raised
    and the temporary file is left in place.
    """
    temporary = Path(temporary)
    for attempt in range(1, REPLACE_ATTEMPTS + 1):
        try:
            return temporary.replace(destination)
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS:
                raise
            time.sleep(REPLACE_DELAY_SECONDS)
