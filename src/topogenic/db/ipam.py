from . import Entity
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String, Integer
# TODO: Port from ipaddress to netaddr
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network
from typing import Iterable, Union, Optional, TypeAlias


IPNetwork : TypeAlias = Union[IPv4Network, IPv6Network]


class Network(Entity):
    """
    Networks are IPv4/IPv6 networks that are given names (although the names may be non-unique)
    """

    __tablename__ = "networks"

    prefix = mapped_column(String, primary_key=True)
    name = mapped_column(String)

    def __init__(self, name, prefix, **kwargs):
        super().__init__(prefix=str(prefix), name=name, **kwargs)

    @property
    def addresses(self) -> Union[IPv4Network, IPv6Network]:
        return ip_network(self.prefix)

    def subnets(self, prefix_size) -> list[IPNetwork]:
        # Addresses is actually a IPv*Network object, so we access here
        return self.addresses.subnets(new_prefix=prefix_size)

    def __repr__(self):
        return f"Network({self.name}): {str(self.prefix)}"


class Host(Entity):
    __tablename__ = "hosts"
    host: Mapped[str] = mapped_column(String, primary_key=True)
    domain: Mapped[Optional[str]] = mapped_column(String)
    ipv4: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    ipv6: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)

    def __init__(self, hostname : str, domain : Optional[str] = None,
                 ipv4 : Optional[IPv4Address] = None, ipv6 : Optional[IPv6Address] = None,
                 **kwargs):
        if ipv4 and ipv4.version != 4:
            raise ValueError("Invalid IPv4 address!")
        if ipv6 and ipv6.version != 6:
            raise ValueError("Invalid IPv6 address!")

        if not ipv4 and not ipv6:
            raise ValueError("Must specify at least one address family: ipv4 or ipv6!")

        super().__init__(host=hostname,
                         domain=domain,
                         ipv4=str(ipv4) if ipv4 else None,
                         ipv6=str(ipv6) if ipv6 else None,
                         **kwargs)

    def __repr__(self):
        return (
            f"Host({str(self.host) if not self.domain else '.'.join([self.host, self.domain])}):"
            + ( f" {self.ipv4}" if self.ipv4 else "" )
            + ( f" [{self.ipv6}]" if self.ipv6 else "" )
        )


class DNSRecord(Entity):
    """
    DNSRecords provides a way to define DNS records that are beyond the scope of unique forward A/AAAA records with PTR reverse records.
    These do not have to be unique - therefore ID is just to track insertion ordering.
    """

    __tablename__ = "dnsrecords"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record: Mapped[str] = mapped_column(String)
    recordclass: Mapped[str] = mapped_column(String)
    ttl: Mapped[int] = mapped_column(String)
    recordtype: Mapped[str] = mapped_column(String)
    data: Mapped[str] = mapped_column(String)
