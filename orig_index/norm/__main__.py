import ast
import hashlib
import sys
from pathlib import Path

from . import normalize

if __name__ == "__main__":
    for f in sys.argv[1:]:
        try:
            # TODO read_text is not correct
            mod = normalize(ast.parse(Path(f).read_text()))
            result = ast.unparse(mod)
            sha = hashlib.sha256(result.encode("utf-8")).hexdigest()
            print(f"# normalize({f!r}) sha256={sha}")
            print(result)
        except Exception as e:
            print(f"{f}: {e}")
