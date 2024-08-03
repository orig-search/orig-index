import functools
import re
from io import StringIO
from random import Random
from tokenize import generate_tokens
from typing import Sequence, Union

import click

# from cityhash import CityHash64
from numpy import array, array_equal, zeros
from numpy.linalg import norm
from xxhash import xxh64_intdigest

from .importer import get_model

SILLY_TOKENIZER = re.compile(
    r"(0x[0-9a-f]+)|(0[0-7]+)|([0-9]+)|([()\[\].*/+-]=?)|(\w+)|(\s+)|(.)",
)


def generate_tokens_re(readline):
    while line := readline():
        for m in SILLY_TOKENIZER.finditer(line):
            groups = tuple(m.groups())
            for i, g in enumerate(groups):
                if g is not None:
                    yield (i, g)
                    break
                else:
                    yield (-1, "")


class SimpleModel:
    def __init__(self, num_vectors: int) -> None:
        self.num_vectors = num_vectors

    def encode(self, texts_or_text: Union[Sequence[str], str]):
        if isinstance(texts_or_text, str):
            return self._encode(texts_or_text)
        else:
            return [self._encode(t) for t in texts_or_text]

    def _encode(self, text: str) -> Sequence[float]:
        """
        Extremely simple encoder intended for tests where low recall is ok.

        Based on bigrams of python-level tokens, and randomly distributed
        vectors because then my model takes up no space to store :)
        """
        tokens = [t[:2] for t in generate_tokens(StringIO(text).readline)]

        @functools.lru_cache(maxsize=None)
        def get_vector(a, b):
            t = zeros(self.num_vectors)
            for i in (f"\x00{a[0]}", f"\x01{b[0]}", f"\x02{a[1]}", f"\x03{b[1]}"):
                # r = Random(CityHash64(i))
                r = Random(xxh64_intdigest(i))
                t += array([r.random() for _ in range(self.num_vectors)])
            return t

        v = array([get_vector(a, b) for (a, b) in zip(tokens, tokens[1:])]).sum(axis=0)

        # Scale to unit vector
        return v / norm(v)


def l2_distance(a, b):
    return norm(a - b)


TEST_SNIPPETS = (
    "def f(x): pass",
    "def g(x): pass",
    "1",
    "2",
    "x = 1 + 1",
    "x = 2 + 2",
    "x = 1 + 1 + 1",
    "x = f(x)",
    "'localhost'",
    "'foobar'",
    str(list(range(1000))),
)

if __name__ == "__main__":
    import ast
    import sys
    import time

    from .importer import normalize, segment

    if len(sys.argv) > 1:
        for filename in sys.argv[1:]:
            with open(filename) as f:
                data = f.read()
            mod = normalize(ast.parse(data))
            segments = [x[2] for x in segment(mod)]

            t0 = time.monotonic()
            get_model().encode("z")  # prime anything that's going to load...
            time_to_load_model = time.monotonic() - t0
            print(filename, "is", len(segments), "segments")

            for model in (SimpleModel(512), get_model()):
                t0 = time.monotonic()
                print(model.__class__.__name__)
                print("=" * len(model.__class__.__name__))
                list(model.encode(segments))
                print("took %.2fs" % (time.monotonic() - t0,))
                if model.__class__.__name__ == "SentenceTransformer":
                    print("load %.2fs" % (time_to_load_model,))
                print()
    else:
        get_model().encode("z")  # prime anything that's going to load...

        for model in (SimpleModel(512), get_model()):
            t0 = time.monotonic()
            print(model.__class__.__name__)
            print("=" * len(model.__class__.__name__))

            e = model.encode(TEST_SNIPPETS)
            for a, t in zip(e, TEST_SNIPPETS):
                d = [l2_distance(a, b) for b in e]
                s = sorted(d)
                for b, c in zip(e, d):
                    if array_equal(a, b):
                        # probably diagonal
                        print("x\t", end="")
                    elif c == s[1]:
                        # closest -- with itself is always zero
                        click.secho("%.2f\t" % c, fg="green", nl=False)
                    elif c == s[2]:
                        # second closest
                        click.secho("%.2f\t" % c, fg="yellow", nl=False)
                    else:
                        # others
                        click.echo("%.2f\t" % c, nl=False)
                print(t[:40])
            print("took %.2fs" % (time.monotonic() - t0,))
            print()
