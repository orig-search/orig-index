import ast
import sys
from pathlib import Path

from ..norm import normalize
from . import segment

if __name__ == "__main__":
    for f in sys.argv[1:]:
        try:
            # TODO read_text is not correct
            mod = normalize(ast.parse(Path(f).read_text()))
            for item in list(segment(mod)):
                print("  ", item)
        except Exception as e:
            print(f"{f}: {e}")
