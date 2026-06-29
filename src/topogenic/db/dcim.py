from enum import Enum
from json import dumps
from typing import Optional

from . import Entity
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import ForeignKey, String, Integer, JSON, UniqueConstraint
# TODO: Port to netaddr
from netaddr import EUI, mac_unix


class Interface(Entity):
    __tablename__ = "interfaces"

    device: Mapped[str] = mapped_column(ForeignKey("devices.name", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String, primary_key=True)
    mac: Mapped[Optional[mac_unix]] = mapped_column(String, unique=True, nullable=True)
    port: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phy: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    data: Mapped[object] = mapped_column(JSON, nullable=True)

    def __init__(
        self,
        name: str,
        mac: Optional[str | EUI],
        port: Optional[str] = None,
        phy: Optional[str] = None,
        data: Optional[dict] = None
    ):
        if type(mac) == str:
            mac = EUI(mac, dialect=mac_unix)

        # Try to JSON dump the data, if not successful, this should error
        if data:
            _ = dumps(data)

        self.name = name
        if mac is not None:
            self.mac = str(mac)
        self.port = port
        self.phy = phy
        self.data = data

    def __repr__(self):
        return f"{self.name} [{self.mac}]"


class Device(Entity):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("vendor", "serial"),
    )

    name: Mapped[str] = mapped_column(String, primary_key=True)
    vendor: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    serial: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    intfs: Mapped[list[Interface]] = relationship(Interface, cascade="all, delete")
    data: Mapped[Optional[JSON]] = mapped_column(JSON, nullable=True)

    def __repr__(self):
        string = f"Device"

        model_string = []
        if self.vendor:
            model_string.append(self.vendor)
        if self.model:
            model_string.append(self.model)
        if model_string:
            string += f"[{' '.join(model_string)}]"

        string += f"({self.name})"

        if self.intfs:
            string += ":"
            # Only print the first 2 and last 2 intf if > 2 ports
            if len(self.intfs) > 4:
                for id in [0, 1]:
                    string += "\n  + " + str(self.intfs[id])
                string += "\n    ..."
                for id in [-2, -1]:
                    string += "\n  + " + str(self.intfs[id])
            else:
                string += f" {set(self.intfs)}"

        return string


    def set_scope(self, scope):
        super().set_scope(scope)
        for intf in self.intfs:
            intf.scope = scope 
