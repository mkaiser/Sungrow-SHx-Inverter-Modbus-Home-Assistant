"""Connection parameters this integration builds for a device of its own."""

from __future__ import annotations

from modbus_connection import ModbusTcpParams, ModbusTlsParams

from .const import WALLBOX_TLS_PORT


def unit_247_params(
    host: str, port: int, *, tls: bool
) -> ModbusTcpParams | ModbusTlsParams:
    """Return the link to an iHomeManager or a Logger: plain, or inside TLS.

    Unverified inside TLS, as for a wallbox: the certificate is Sungrow's own,
    and what answers is checked by its type code, not by the certificate.
    """
    if tls:
        return ModbusTlsParams(host=host, port=port, verify=False, check_hostname=False)
    return ModbusTcpParams(host=host, port=port)


def wallbox_tls_params(host: str) -> ModbusTlsParams:
    """Return the link to a wallbox's own address: Modbus inside TLS, unverified.

    Not verified because there is nothing to verify against: the certificate
    is Sungrow's own, signed by `OT.SUNGROW`, and byte-identical on a WiNet-S
    and a wallbox at the same house.
    """
    return ModbusTlsParams(
        host=host, port=WALLBOX_TLS_PORT, verify=False, check_hostname=False
    )
