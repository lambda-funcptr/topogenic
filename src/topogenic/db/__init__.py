from base64 import b64encode
from dill import source
from hashlib import sha3_512
from itertools import chain
from json import dumps
from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship
from typing import Any, Iterator, Optional, Tuple

from ..resources import Resource

from topogenic.util.generators import Counter


# TODO: Port to SQLModel


class DBBase(DeclarativeBase):
    pass


class BaseScope():
    def __init__(self):
        self.name = ""

    @property
    def counters(self) -> dict[str, Counter]:
        return {}

    def counter(self, name):
        raise KeyError(f"Unable to find counter: {name}")

    @property
    def resources(self) -> dict[str, Resource]:
        return {}

    def resource(self, name):
        raise KeyError(f"Unable to find resource: {name}")


class Scope(BaseScope):
    class Meta(DBBase):
        name: Mapped[str] = mapped_column(String, primary_key=True)
        kind: Mapped[str] = mapped_column(String)
        data: Mapped[Any] = mapped_column(JSON)
        dill_hash: Mapped[str] = mapped_column(String)

        __tablename__ = "scopes"

        def __init__(self, name: str, kind: str, data: Any, dill_hash: str):
            self.name = name
            self.kind = kind
            self.data = data
            self.dill_hash = dill_hash

        def __repr__(self) -> str:
            return f"Meta: {self.dill_hash}"


    class End():
        """
        This is a simple signal class to notify that we're done with a scope...
        """
        def __repr__(self):
            return ""

    def __init__(self, parent: Optional["Scope"],
                 name_part: str, kind=None, data=None,
                 counters={}, resources={}, *args, **kwargs):
        BaseScope.__init__(self)
        if parent.name != "":
            self.name = f"{ parent.name }::{ name_part }"
        else:
            self.name = name_part

        self._counters = counters
        self._resources = resources

        self.kind = kind
        self.data = data

        # Stash the parent so we can walk up...
        self.parent = parent

    @property
    def counters(self) -> dict[str, Counter]:
        return {
            k: v for k, v in chain(self._counters.items(), self.parent.counters.items())
        }

    def counter(self, counter: str) -> Iterator[int]:
        # micro-op: check local first
        if counter in self._counters:
            return self._counters.get(counter)

        return self.counters.get(counter)

    @property
    def resources(self) -> dict[str, Counter]:
        return {
            k: v for k, v in chain(self._resources.items(), self.parent.resources.items())
        }

    def resource(self, resource: str) -> Resource:
        if resource in self._resources:
            return self._resources.get(resource)

        return self.resources.get(resource)

    def hash(self) -> sha3_512:
        bound = [
            member
            for member in dir(self)
            if not member.startswith("_") # and callable(getattr(self, member))
        ]
        dill_hash = sha3_512()

        for member in bound:
            if callable(getattr(self, member)):
                dill_hash.update(source.getsource(getattr(self, member)).encode('utf-8'))

        dill_hash.update(dumps({
            name: counter.state()
            for name, counter in self.counters.items()
        }, ).encode('utf-8'))


        dill_hash.update(dumps({
            name: resource.hash()
            for name, resource in self.resources.items()
        }).encode('utf-8'))

        return dill_hash


    def subelements(self) -> Tuple[Iterator["Operation"], Meta]:
        meta = Scope.Meta(self.name, self.kind, self.data, str(self.hash().digest()))
        # We've been concretized here, we can query the DB here
        # If our dill hashes are unchanged we can skip
        def subobj_iter() -> Iterator["Operation"]:
            subobjects = iter(self.enumerate())
            while item := next(subobjects, None):
                if isinstance(item, Entity):
                    item.set_scope(meta)
                yield item
                if isinstance(type(item), BaseScope):
                    yield from item

            yield Scope.End()

        return subobj_iter(), meta

    def __repr__(self) -> str:
        return f"Scope[{self.kind}]({self.name}):"

    def enumerate(self) -> Iterator["Operation"]:
        raise NotImplementedError()


class Entity(DBBase):
    __abstract__ = True

    @declared_attr
    def scope_name(cls):
        return mapped_column(ForeignKey("scopes.name", ondelete="CASCADE"))

    @declared_attr
    def scope(cls):
        return relationship(Scope.Meta, cascade="all, delete")

    # Propegates scope into child objects if we're using ORM mapping
    def set_scope(self, scope) -> None:
        self.scope = scope


def dump_json(ent: Entity):
    if isinstance(ent, DBBase):
        return {
            col.name: getattr(ent, col.name)
            for col in ent.__mapper__.columns
        }

    else:
        raise TypeError
