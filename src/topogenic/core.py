from collections.abc import Iterator
from dataclasses import dataclass
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
# Oof, massive hack
from sys import path as python_search_path
from types import ModuleType
from typing import Callable, Optional, Tuple

from sqlalchemy import create_engine, delete, event, select, text
from sqlalchemy import Engine
from sqlalchemy.orm import Session, relationship

from . import Debug, Operation
from .db import BaseScope, DBBase, Entity, Scope


ScopeFn = Callable[Scope, Iterator[Operation]]


ROOT_SCOPES: list[ScopeFn] = []


@dataclass
class ScopeCtx:
    name: str


def load_script(name: str) -> ModuleType:
    script_path = Path(name)

    if not script_path.exists():
        raise FileNotFoundError(f'Script "{name}" not found in current directory!')

    python_search_path.append(str(script_path.absolute().parents[0]))

    spec = spec_from_file_location(script_path.stem, script_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def root(fn: Callable[Scope, Iterator[Operation]]) -> None:
    ROOT_SCOPES.append(fn)
    return None


def _clean_scope(scope: str, session: Session) -> dict[str, int]:
    deleted = session.execute(delete(Scope.Meta).where(
        Scope.Meta.name == scope
    ))

    return deleted



def _recurse(objects: Iterator[Operation], session: Session, ctx: ScopeCtx, suppressed=False) -> Iterator[Entity]:
    # Roll a series of operations into section cache
    cache = []

    while result := next(objects, None):
        # Check if we're a tuple or not...
        obj: Operation
        callback: Callable[Operation, None]

        if isinstance(result, tuple):
            obj, callback = result
        else:
            obj = result
            callback = None

        if isinstance(obj, DBBase):
            if not suppressed:
                cache.append(obj)
                yield obj

        elif isinstance(obj, Scope):
            # We need to track if the subscope is suppressed or not based on hash
            subscope_suppressed = False

            scope_elements, metadata = obj.subelements()

            # Emit the object first
            yield obj
            # Grab the row where this happens:
            if row := session.execute(
                    select(Scope.Meta.dill_hash).where(Scope.Meta.name == metadata.name)
            ).first():
                db_hash = row[0]

                if db_hash != metadata.dill_hash:
                    # We need to unsuppress the scope on subscope changes as the iterators may change
                    suppressed = False
                    subscope_suppressed = False
                else:
                    # Even though we won't actually do any tx from this branch, we still need to walk to get counters to state
                    subscope_suppressed = True

            yield from _recurse(scope_elements, session, ScopeCtx(metadata.name), subscope_suppressed)

        elif isinstance(obj, Scope.End):
            if not suppressed:
                deleted = _clean_scope(ctx.name, session)
                # TODO: Reimplement +n/-n semantics by storing metadata on push
                yield Debug(1, f"{ctx.name} changed (+{len(cache)})")
                session.add_all(cache)
                session.commit()
                cache.clear()
            else:
                yield Debug(3, f"{ctx.name} suppressed")

            yield obj

        else:
            yield obj


def clean_module(module: ModuleType, verbosity: int = 0) -> None:
    engine = create_engine(module.SQL_CONNECTION, echo=(verbosity >= 5))
    # Hope this doesn't oops you...
    DBBase.metadata.drop_all(bind=engine)


def enumerate_module(module: ModuleType, verbosity: int = 0, dry_run: bool = False) -> Iterator[Operation]:
    engine = create_engine(module.SQL_CONNECTION, echo=(verbosity >= 5))

    DBBase.metadata.create_all(engine)

    base_scope = BaseScope()

    with Session(engine, expire_on_commit=False) as session:
        root_scopes_iterators = map(lambda fn: fn(base_scope, fn.__name__, kind="root"), ROOT_SCOPES)
        # for fn in ROOT_SCOPES:
        yield from _recurse(root_scopes_iterators, session, ScopeCtx(""))

        session.expunge_all()

    return


# Stolen shamelessly from docs to enable foreign keys...
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # the sqlite3 driver will not set PRAGMA foreign_keys
    # if autocommit=False; set to True temporarily
    ac = dbapi_connection.autocommit
    dbapi_connection.autocommit = True

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

    # restore previous autocommit setting
    dbapi_connection.autocommit = ac
