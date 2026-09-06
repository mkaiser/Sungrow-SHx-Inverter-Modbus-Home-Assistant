"""Constants for the Sungrow Modbus integration."""

DOMAIN = "sungrow_modbus"

DEFAULT_NAME = "Sungrow SHx"
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1

CONF_UNIT_ID = "unit_id"

#: The subnet a discovery sweep covers. Asked for, never assumed: every
#: address probed is an ARP entry and a SYN on somebody's network.
CONF_NETWORK = "network"

#: Which entity ids the integration's entities claim. The entities themselves
#: are identical either way — device-scoped naming, translation keys, device
#: and state classes — so this is only about which id, and therefore whose
#: recorder history and which dashboard cards, they attach to.
CONF_ENTITY_IDS = "entity_ids"

ENTITY_IDS_MIGRATE = "migrate"
"""Take over the ids modbus_sungrow.yaml used, so history carries on."""

ENTITY_IDS_NEW = "new"
"""Create device-scoped ids, leaving the YAML package's history where it is."""

# The poll intervals come from the register map, which takes them from the
# YAML package's own tiers — see sungrow_modbus.registers.TIERS.

#: An option, not entry data: whether diagnostics include a raw register dump.
#: Off by default because producing it is a second full read of the register
#: map on top of the ordinary polling, which through a WiNet-S is slow enough
#: to disturb it.
CONF_REGISTER_DUMP = "register_dump"
