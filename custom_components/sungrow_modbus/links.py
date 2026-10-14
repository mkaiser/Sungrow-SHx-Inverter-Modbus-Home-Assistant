"""Connection parameters this integration builds for a device of its own."""

from __future__ import annotations

from modbus_connection import ModbusTlsParams

from .const import WALLBOX_TLS_PORT


def wallbox_tls_params(host: str) -> ModbusTlsParams:
    """Return the link to a wallbox's own address: Modbus inside TLS, unverified.

    Not verified because there is nothing to verify against: the certificate
    is Sungrow's own, signed by `OT.SUNGROW`, and byte-identical on a WiNet-S
    and a wallbox at the same house.
    """
    return ModbusTlsParams(
        host=host, port=WALLBOX_TLS_PORT, verify=False, check_hostname=False
    )
