from dataclasses import dataclass
from os import getpid
from pathlib import Path
from subprocess import Popen, PIPE
from sys import stderr
from types import ModuleType
from typing import Annotated, Optional

from . import Debug
from .core import load_script, clean_module, enumerate_module
from .db import Scope

import typer


cli = typer.Typer()


@dataclass
class CliConfig:
    """
    Universal config options.
    """

    verbose: int
    debug: bool


def exec_module(module: ModuleType, config: CliConfig, stdout=True, dry_run=False) -> None:
    # Raw exec module...

    indent = 0
    for obj in enumerate_module(module, verbosity=config.verbose, dry_run=False):
        if stdout:
            if isinstance(obj, Scope.End):
                indent -= 1
                continue

            if isinstance(obj, Debug):
                if obj.level < config.verbose:
                    print(("  "*indent) + f"Debug<{obj.level}>: {obj.message}", file=stderr)
            else:
                for line in str(obj).split('\n'):
                    print(("  "*indent) + line)

            if isinstance(obj, Scope):
                indent += 1


@cli.command()
def sync(ctx: typer.Context, script: str):
    module = load_script(script)
    exec_module(module, ctx.obj)

@cli.command()
def debug(ctx: typer.Context, script: str, dump: Optional[str] = None, sql: bool = False):
    module = load_script(script)

    sqlite_db_location: Optional[Path] = None
    if sql:
        sqlite_db_location = Path(f"/tmp/topogenic.{getpid()}.sqlite")
        module.SQL_CONNECTION = f"sqlite:///{sqlite_db_location}"

    if dump:
        sqlite_db_location = Path(dump)
        module.SQL_CONNECTION = f"sqlite:///{sqlite_db_location}"

    if sqlite_db_location is None:
        print(f"Using in-memory DB connection")
        module.SQL_CONNECTION = f"sqlite:///"
    else:
        print(f"Debugging with SQLite file database: {sqlite_db_location}")

    try:
        exec_module(module, ctx.obj)

    finally:
        if sql:
            sql_shell = Popen(["sqlite3", sqlite_db_location])
            sql_shell.wait()
            sqlite_db_location.unlink()


@cli.command()
def clean(ctx: typer.Context, script: Optional[str]):
    module = load_script(script)
    clean_module(module, verbosity=ctx.obj.verbose)


@cli.callback()
def common(ctx: typer.Context,
           verbose: Annotated[int, typer.Option("--verbose", "-v", count=True, max=5)] = 0):
    ctx.obj = CliConfig(verbose=verbose, debug=False)


def main():
    cli()
