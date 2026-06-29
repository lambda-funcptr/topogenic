from typing import Iterator

from dill import source
from hashlib import sha3_512
from json import dumps

from topogenic.db import DBBase, Scope, dump_json
from topogenic import Operation

def scope(fn):
    class AutoScope(Scope):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def enumerate(self) -> Iterator[Operation]:
            yield from fn(self)

        def hash(self) -> str:
            hash = super().hash()
            hash.update(source.getsource(fn).encode('utf-8'))

            return hash

    AutoScope.__name__ = fn.__name__

    return AutoScope



def simple_scope(ctx, name: str, kind: str, contents: list[DBBase], *args, **kwargs):
    class SimpleScope(Scope):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def enumerate(self) -> Iterator[Operation]:
            yield from contents

        def hash(self) -> sha3_512:
            hash = super().hash()
            for subobject in contents:
                # TODO: Unhack this shit...
                hash.update(dumps(subobject, default=dump_json).encode('utf-8'))

            return hash

    SimpleScope.__name__ = name

    return SimpleScope(ctx, name, kind, *args, **kwargs)


def device_scope(ctx, name: str, contents: list[DBBase], *args, **kwargs):
    return simple_scope(ctx, name, kind="device", contents=contents, *args, **kwargs)

