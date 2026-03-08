#!/usr/bin/env python3

import argparse
import sys

from pymodbus.client import ModbusTcpClient

HOST = "192.168.178.35"
PORT = 502
UNIT_ID = 1


def _read_registers(client: ModbusTcpClient, reg_type: str, addr: int, cnt: int, unit_id: int):
    read_func = client.read_holding_registers if reg_type == "HOLDING" else client.read_input_registers
    return read_func(address=addr, count=cnt)


def _write_registers(client: ModbusTcpClient, addr: int, values: list[int]):
    if len(values) == 1:
        return client.write_register(address=addr, value=values[0])
    else:
        return client.write_registers(address=addr, values=values)


def _parse_int(value: str, name: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got: {value}")


def parse_args() -> argparse.Namespace:
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        sys.argv.append('-h')
    
    parser = argparse.ArgumentParser(
        description="""
Read or write Sungrow Modbus registers via TCP.

Register Types:
  INPUT    - Read-only input registers (sensors, status values)
  HOLDING  - Read/write holding registers (configuration, settings)

Note: Register addresses in Modbus start at 0, but documentation often shows them starting at 1.
      For example, register 13022 in docs = address 13021 in Modbus (subtract 1).
""",
        epilog="""
Examples:
  Read single INPUT register (e.g., Battery Power at reg 5215):
    ./modbus_regAccess.py INPUT 5214
    ./modbus_regAccess.py 5214              (defaults to INPUT if type omitted)
  
  Read multiple HOLDING registers (e.g., 2 registers starting at 13051):
    ./modbus_regAccess.py HOLDING 13050 2
  
  Write single value to HOLDING register (e.g., set Export Power Limit):
    ./modbus_regAccess.py --write HOLDING 13050 5000
  
  Write multiple values to consecutive HOLDING registers:
    ./modbus_regAccess.py --write HOLDING 13050 100 200 300
  
  Connect to custom host/port:
    ./modbus_regAccess.py --host 192.168.1.100 --port 502 INPUT 5214

Tip: Use -h or --help to show this help message.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "args",
        nargs="+",
        metavar="ARG",
        help="Read: [HOLDING|INPUT] addr [count]  |  Write: HOLDING addr value [value...]",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Enable write mode (only for HOLDING registers)",
    )
    parser.add_argument(
        "--host",
        default=HOST,
        metavar="IP",
        help=f"Inverter IP address (default: {HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=PORT,
        metavar="PORT",
        help=f"Modbus TCP port (default: {PORT})",
    )
    parser.add_argument(
        "--unit-id",
        type=int,
        default=UNIT_ID,
        metavar="ID",
        help=f"Modbus unit/slave ID (default: {UNIT_ID})",
    )
    parsed = parser.parse_args()

    reg_type = "INPUT"
    addr = None
    cnt = 1
    values = None
    raw_args = parsed.args

    if parsed.write:
        # Write mode: HOLDING addr value [value...]
        if len(raw_args) < 3:
            parser.error("Write mode requires: HOLDING addr value [value...]")
        
        reg_type = raw_args[0].upper()
        if reg_type != "HOLDING":
            parser.error("Write mode only supports HOLDING registers")
        
        try:
            addr = _parse_int(raw_args[1], "addr")
            values = [_parse_int(v, f"value[{i}]") for i, v in enumerate(raw_args[2:])]
        except ValueError as exc:
            parser.error(str(exc))
    else:
        # Read mode: [HOLDING|INPUT] addr [cnt]
        if raw_args[0].upper() in {"INPUT", "HOLDING"}:
            reg_type = raw_args[0].upper()
            if len(raw_args) < 2 or len(raw_args) > 3:
                parser.error("Read mode: [HOLDING|INPUT] addr [cnt]")
            try:
                addr = _parse_int(raw_args[1], "addr")
                if len(raw_args) == 3:
                    cnt = _parse_int(raw_args[2], "cnt")
            except ValueError as exc:
                parser.error(str(exc))
        else:
            if len(raw_args) > 2:
                parser.error("Read mode: [HOLDING|INPUT] addr [cnt]")
            try:
                addr = _parse_int(raw_args[0], "addr")
                if len(raw_args) == 2:
                    cnt = _parse_int(raw_args[1], "cnt")
            except ValueError as exc:
                parser.error(str(exc))

    parsed.write_mode = parsed.write
    parsed.reg_type = reg_type
    parsed.addr = addr
    parsed.cnt = cnt
    parsed.values = values
    return parsed


def main() -> int:
    args = parse_args()
    reg_type = args.reg_type.upper()

    if args.addr < 0:
        print("Error: addr must be >= 0", file=sys.stderr)
        return 2

    if not args.write_mode and args.cnt <= 0:
        print("Error: cnt must be > 0", file=sys.stderr)
        return 2

    client = ModbusTcpClient(args.host, port=args.port)

    if not client.connect():
        print(f"Connection failed: {args.host}:{args.port}", file=sys.stderr)
        return 1

    try:
        if args.write_mode:
            # Write mode
            rr = _write_registers(
                client=client,
                addr=args.addr,
                values=args.values,
            )

            if rr.isError():
                print(f"Modbus write error: {rr}", file=sys.stderr)
                return 1

            print(f"Write successful: type=HOLDING addr={args.addr} values={args.values}")
            return 0
        else:
            # Read mode
            rr = _read_registers(
                client=client,
                reg_type=reg_type,
                addr=args.addr,
                cnt=args.cnt,
                unit_id=args.unit_id,
            )

            if rr.isError():
                print(f"Modbus read error: {rr}", file=sys.stderr)
                return 1

            print(f"type={reg_type} addr={args.addr} cnt={args.cnt} values={rr.registers}")
            return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())