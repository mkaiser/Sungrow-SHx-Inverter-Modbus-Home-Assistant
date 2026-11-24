"""What each check is called in front of a person, in English and German.

The ledger's names ("forced-charging window 2 encoding", "total_pv_generation
against daily_pv_generation") are identifiers: kept runs, revisions and the
published documents are keyed by them, so they cannot be reworded. This is
what the dashboard's results card shows beside them.
`tests/test_capability_labels.py` holds the table to every check there is.
"""

from __future__ import annotations

import re

from .procedure import (
    CLAMPED,
    CONFIRMED,
    DROPPED,
    EFFECT_SCALED,
    INCONCLUSIVE,
    MATCH,
    NO_BOUNDS,
    NO_EFFECT,
    NO_SNAPSHOT,
    NO_WINDOW,
    NOT_CAPABLE,
    OFF_BY,
    OUT_OF_TIME,
    REFUSED,
    SCALED,
    SIGN_INVERTED,
    SKIPPED,
    SLOPE_WRONG,
    STOPPED,
    UNCHANGED,
    UNSAFE_STATE,
    USER_DECLINED,
)

type Label = dict[str, str]


def _label(en: str, de: str) -> Label:
    return {"en": en, "de": de}


#: A setting or counter, by the field the checks name it by.
FIELDS: dict[str, Label] = {
    "battery_min_soc": _label("Min SoC", "Min. SoC"),
    "battery_max_soc": _label("Max SoC", "Max. SoC"),
    "battery_reserved_soc_for_backup": _label("Backup reserve", "Notstromreserve"),
    "battery_max_charge_power": _label("Charge power limit", "Ladeleistungsgrenze"),
    "battery_max_discharge_power": _label(
        "Discharge power limit", "Entladeleistungsgrenze"
    ),
    "export_power_limit": _label("Export limit", "Einspeisegrenze"),
    "battery_forced_charge_discharge_power": _label("Forced power", "Zwangsleistung"),
    "battery_charging_start_power": _label(
        "Charge battery over", "Batterie laden über"
    ),
    "battery_discharging_start_power": _label(
        "Discharge battery over", "Batterie entladen über"
    ),
    "pv_generation": _label("PV energy", "PV-Energie"),
    "imported_energy": _label("Imported energy", "Netzbezug"),
    "exported_energy": _label("Exported energy", "Einspeisung"),
    "battery_charge": _label("Battery charge", "Batterieladung"),
    "battery_discharge": _label("Battery discharge", "Batterieentladung"),
    "exported_energy_from_pv": _label("Export from PV", "Einspeisung aus PV"),
    "battery_charge_from_pv": _label("Battery charge from PV", "Batterieladung aus PV"),
    "direct_energy_consumption": _label("Direct consumption", "Direktverbrauch"),
}

#: A check, by its own name.
CHECKS: dict[str, Label] = {
    "forced charge": _label("Forced charge", "Zwangsladung"),
    "forced discharge": _label("Forced discharge", "Zwangsentladung"),
    "charge ceiling": _label("Charging stops at max SoC", "Laden endet bei max. SoC"),
    "export power limit": _label(
        "The export limit holds", "Die Einspeisegrenze wird eingehalten"
    ),
    "PV generation cut": _label("PV can be stopped", "PV lässt sich abschalten"),
    "forced-charging window": _label(
        "The charging schedule starts a charge", "Der Ladeplan startet eine Ladung"
    ),
    "discharge windows away from now": _label(
        "The discharge schedule holds", "Der Entladeplan wird eingehalten"
    ),
    "site import limit": _label(
        "The import limit holds", "Die Bezugsgrenze wird eingehalten"
    ),
    "forced startup under low SoC": _label(
        "Wakes from low-SoC standby", "Wacht aus dem Standby bei leerer Batterie auf"
    ),
    "charging start threshold": _label(
        "Charges only over its threshold", "Lädt erst über der Schwelle"
    ),
    "discharging start threshold": _label(
        "Discharges only over its threshold", "Entlädt erst über der Schwelle"
    ),
    "backup mode write path": _label(
        "Backup mode can be set", "Notstrom lässt sich einstellen"
    ),
    "load control write path": _label(
        "Load control can be set", "Lastregelung lässt sich einstellen"
    ),
    "weekend discharge enable write path": _label(
        "Weekend schedule can be set", "Wochenendplan lässt sich einstellen"
    ),
    "forced-charging window 2 encoding": _label(
        "Second charging window is stored right",
        "Zweites Ladefenster wird richtig gespeichert",
    ),
    "EMS mode options": _label(
        "Operating modes can be set", "Betriebsarten lassen sich einstellen"
    ),
    "power balance": _label("The powers add up", "Die Leistungen gehen auf"),
    "battery voltage times current": _label(
        "Battery power fits voltage and current",
        "Batterieleistung passt zu Spannung und Strom",
    ),
    "tracker voltage times current": _label(
        "PV power fits voltage and current", "PV-Leistung passt zu Spannung und Strom"
    ),
    "phase voltage times current": _label(
        "Output power fits voltage and current",
        "Ausgangsleistung passt zu Spannung und Strom",
    ),
    "meter phases add up": _label(
        "The meter's phases add up", "Die Zählerphasen ergeben die Summe"
    ),
    "meter against export power": _label(
        "Meter and export power agree", "Zähler und Einspeiseleistung stimmen überein"
    ),
    "lifetime counters never fall": _label(
        "Lifetime counters never fall", "Gesamtzähler fallen nie"
    ),
    "lifetime battery counters contain each other": _label(
        "Lifetime battery counters fit together",
        "Gesamtzähler der Batterie passen zusammen",
    ),
    "daily counters reset at midnight": _label(
        "Daily counters reset at midnight",
        "Tageszähler beginnen um Mitternacht neu",
    ),
    "daily counters keep up with the totals": _label(
        "Daily counters keep up with the totals",
        "Tageszähler halten mit den Gesamtzählern mit",
    ),
    "battery level follows its power": _label(
        "Battery level follows its power", "Ladestand folgt der Batterieleistung"
    ),
    "pv_generation this month against daily_pv_generation": _label(
        "PV generation: month and day agree", "PV-Erzeugung: Monat und Tag passen"
    ),
    "direct_consumption this month against daily_direct_energy_consumption": _label(
        "Direct consumption: month and day agree",
        "Direktverbrauch: Monat und Tag passen",
    ),
    "export_from_pv this month against daily_exported_energy_from_pv": _label(
        "Export from PV: month and day agree",
        "Einspeisung aus PV: Monat und Tag passen",
    ),
    "history year contains its month": _label(
        "The year's total contains the month's",
        "Die Jahressumme enthält die des Monats",
    ),
    "running states": _label(
        "Running states are known", "Betriebszustände sind bekannt"
    ),
    "mppt3 carries a string": _label("MPPT 3 is in use", "MPPT 3 ist belegt"),
    "mppt4 carries a string": _label("MPPT 4 is in use", "MPPT 4 ist belegt"),
    "wallbox power times voltage and current": _label(
        "Wallbox power fits voltage and current",
        "Wallbox-Leistung passt zu Spannung und Strom",
    ),
    "wallbox session energy against power": _label(
        "Session energy fits the power", "Energie des Ladevorgangs passt zur Leistung"
    ),
    "wallbox lifetime energy against session": _label(
        "Wallbox total follows the session",
        "Wallbox-Gesamtzähler folgt dem Ladevorgang",
    ),
    "wallbox energy counters never fall": _label(
        "Wallbox counters never fall", "Wallbox-Zähler fallen nie"
    ),
    "wallbox control pilot against status": _label(
        "Control pilot fits the status", "Control Pilot passt zum Status"
    ),
    "inverter load includes the wallbox": _label(
        "The house load includes the wallbox", "Die Hauslast enthält die Wallbox"
    ),
    "wallbox output current": _label(
        "Wallbox current can be set", "Wallbox-Strom lässt sich einstellen"
    ),
    "wallbox current follow": _label(
        "The car follows the set current", "Das Auto folgt dem eingestellten Strom"
    ),
    "wallbox available current": _label(
        "The offered current follows the setting",
        "Der angebotene Strom folgt der Einstellung",
    ),
    "wallbox below minimum": _label(
        "Current below the minimum", "Strom unter dem Minimum"
    ),
    "wallbox above rating": _label(
        "Current above the rating", "Strom über dem Nennwert"
    ),
    "wallbox start/stop": _label(
        "Charging can be started and stopped",
        "Laden lässt sich starten und stoppen",
    ),
    "wallbox enable": _label(
        "The wallbox can be disabled", "Die Wallbox lässt sich abschalten"
    ),
    "wallbox phase": _label("Phases can be switched", "Phasen lassen sich umschalten"),
    "wallbox phase while charging": _label(
        "Phases can be switched while charging",
        "Phasen lassen sich beim Laden umschalten",
    ),
    "wallbox fallback": _label(
        "Falls back when contact is lost", "Fällt ohne Verbindung zurück"
    ),
    "wallbox user current": _label(
        "The inverter's charging current is followed",
        "Dem Ladestrom vom Wechselrichter wird gefolgt",
    ),
    "wallbox floor": _label(
        "The inverter's lowest current", "Kleinster Strom vom Wechselrichter"
    ),
}

#: What a run came to, by its outcome code (`procedure.CODES`).
OUTCOMES: dict[int, Label] = {
    0: _label("Every planned check ran", "Alle geplanten Prüfungen liefen"),
    1: _label("Nothing ran", "Nichts lief"),
    2: _label("Could not run at that moment", "Konnte in dem Moment nicht laufen"),
    3: _label("Some checks were left open", "Einige Prüfungen blieben offen"),
    4: _label("A value was off by a factor", "Ein Wert war um einen Faktor daneben"),
    5: _label(
        "A setting was not put back", "Eine Einstellung wurde nicht zurückgesetzt"
    ),
}

_BOUND = "upper bound of "
_REFUSED_PAST = (
    "values past the maximum are refused",
    "Werte über dem Maximum werden abgelehnt",
)
_BOUND_FOUND: dict[str, tuple[str, str]] = {
    CONFIRMED: _REFUSED_PAST,
    REFUSED: _REFUSED_PAST,
    CLAMPED: (
        "values past the maximum are cut to it",
        "Werte über dem Maximum werden darauf begrenzt",
    ),
    NO_EFFECT: (
        "values past the maximum are accepted",
        "Werte über dem Maximum werden angenommen",
    ),
}

#: How a step's label starts (`_step`, after the part's name) and the check it
#: belongs to, so that a page can mark the check being measured. The first
#: that fits; a step of none of these (the restore, the setup) marks nothing.
#: A check whose step is its own name needs no row.
STEPS: tuple[tuple[str, str], ...] = (
    ("export limit at", "export power limit"),
    ("discharging ", "export power limit"),
    ("discharge windows", "discharge windows away from now"),
    ("offer under the pilot minimum", "wallbox below minimum"),
    ("offer above the rating", "wallbox above rating"),
    ("offer under the floor", "wallbox floor"),
    ("offer ", "wallbox output current"),
    ("follow the offer", "wallbox current follow"),
    ("stop and start the charge", "wallbox start/stop"),
    ("stop the charge", "wallbox start/stop"),
    ("start the charge", "wallbox start/stop"),
    ("disable and enable", "wallbox enable"),
    ("switch the phase setting", "wallbox phase"),
    ("switch the phase with a car", "wallbox phase while charging"),
    ("fall silent", "wallbox fallback"),
    ("user current", "wallbox user current"),
)
_AGAINST_POWER = " against power"


#: A verdict's German; the ledger's English is the verdict itself.
VERDICTS_DE: dict[str, str] = {
    MATCH: "stimmt überein",
    SCALED: "um genau eine Zehnerpotenz daneben",
    SLOPE_WRONG: "zwei Punkte, falsche Steigung",
    OFF_BY: "um etwas anderes daneben",
    CLAMPED: "das Gerät hat den Wert begrenzt",
    REFUSED: "mit einer Fehlermeldung abgelehnt",
    UNCHANGED: "das Gerät hat seinen alten Wert behalten",
    DROPPED: "die Verbindung brach ab",
    SKIPPED: "nicht gelaufen",
    CONFIRMED: "der Wechselrichter hat getan, was verlangt war",
    EFFECT_SCALED: (
        "der Wechselrichter hat auf einen um eine Zehnerpotenz falschen Wert reagiert"
    ),
    SIGN_INVERTED: "richtige Größe, falsche Richtung",
    NO_EFFECT: "nichts Messbares ist passiert",
    INCONCLUSIVE: "nicht zu entscheiden",
    OUT_OF_TIME: "die Zeit reichte nicht",
    STOPPED: "vom Besitzer gestoppt",
    NOT_CAPABLE: "das Gerät hat es nicht",
    UNSAFE_STATE: "das Haus war nicht im passenden Zustand",
    USER_DECLINED: "nicht verlangt",
    NO_BOUNDS: "die Grenzen ließen sich nicht bestimmen",
    NO_SNAPSHOT: "der aktuelle Wert ließ sich nicht lesen",
    NO_WINDOW: "kein Prüfwert kann hier einen Zehnerfehler zeigen",
}

#: What a check waits for, in German, by the words its need is written in
#: (`ledger.NEEDS`, the readings' `Check.needs`, the wallbox's `CHECKS`).
NEEDS_DE: dict[str, str] = {
    "1 kWh into or out of the battery": "1 kWh in die oder aus der Batterie",
    "10 kWh on the daily counter": "10 kWh auf dem Tageszähler",
    "10 kWh through the counters": "10 kWh über die Zähler",
    "100 kWh through the battery": "100 kWh durch die Batterie",
    "2 kWh on the daily counter": "2 kWh auf dem Tageszähler",
    "300 W through the meter": "300 W über den Zähler",
    "PV above 1000 W": "PV über 1000 W",
    "PV above 300 W": "PV über 300 W",
    "PV above 700 W": "PV über 700 W",
    "a car charging (status 3, drawing 5 A or more)": (
        "ein ladendes Auto (Status 3, mindestens 5 A)"
    ),
    "a car drawing 500 W": "ein Auto, das 500 W zieht",
    "a car plugged in, and one charging": "ein angestecktes und ein ladendes Auto",
    "a charging session": "ein Ladevorgang",
    "a day of polls": "ein Tag Messwerte",
    "a house load of 500 W": "500 W Hausverbrauch",
    "a midnight": "eine Mitternacht",
    "a run": "ein Lauf",
    "a session that delivers 0.5 kWh": "ein Ladevorgang mit 0,5 kWh",
    "any state": "jeder Zustand",
    "dark (PV under 200 W), the battery under 85 %": (
        "Dunkelheit (PV unter 200 W), Batterie unter 85 %"
    ),
    "export, or a battery to discharge into the grid": (
        "Einspeisung oder eine Batterie, die ins Netz entladen kann"
    ),
    "low-SoC standby, the battery at its minimum and no PV": (
        "Standby bei niedrigem Ladestand, Batterie am Minimum und keine PV"
    ),
    "nothing flowing": "kein Ladestrom",
    "the battery above 15 %": "Batterie über 15 %",
    "the battery above 30 %": "Batterie über 30 %",
    "the battery above 57 %": "Batterie über 57 %",
    "the battery charging 200 to 800 W, nothing exported": (
        "Batterie lädt mit 200 bis 800 W, keine Einspeisung"
    ),
    "the battery charging, above 55 %": "Batterie lädt, über 55 %",
    "the battery discharging": "Batterie entlädt",
    "the battery discharging 200 to 800 W, nothing imported": (
        "Batterie entlädt mit 200 bis 800 W, kein Netzbezug"
    ),
    "the battery moving 300 W": "300 W in die oder aus der Batterie",
    "the battery under 85 %": "Batterie unter 85 %",
    "the battery under 85 % and not charging": "Batterie unter 85 % und lädt nicht",
    "the inverter delivering 1000 W": "1000 W vom Wechselrichter",
    "the inverter's energy history": "der Energieverlauf des Wechselrichters",
    "the wallbox's power stepping by 1 kW": "ein Leistungssprung der Wallbox um 1 kW",
    "three kilowatt-hours of flow": "drei Kilowattstunden",
}

_COUNT = re.compile(r"(\d+) of (\d+) [a-z ]+")


def need(words: str, detail: str | None = None) -> Label:
    """Return what a check waits for; a need without German stays English."""
    en, de = words, NEEDS_DE.get(words, words)
    if detail:
        en = f"{en} ({detail})"
        counted = _COUNT.fullmatch(detail)
        de = f"{de} ({f'{counted[1]} von {counted[2]}' if counted else detail})"
    return _label(en, de)


def verdict_label(verdict: str | None) -> Label | None:
    """Return a verdict as it is shown."""
    if verdict is None:
        return None
    return _label(verdict, VERDICTS_DE.get(verdict, verdict))


def _counter(name: str) -> Label | None:
    """Return the label of a daily or total counter, without which it is."""
    return FIELDS.get(name.removeprefix("daily_").removeprefix("total_"))


def label(name: str, verdict: str | None = None) -> Label | None:
    """Return a check's label, or None for one this table does not know.

    What is past a setting's maximum is named by what was found: a check that
    asks whether it is refused, beside a mark that says no, has to be read
    twice.
    """
    if name in CHECKS:
        return CHECKS[name]
    if name in FIELDS:
        return _label(
            f"{FIELDS[name]['en']} can be set",
            f"{FIELDS[name]['de']} lässt sich einstellen",
        )
    if name.startswith(_BOUND) and (field := FIELDS.get(name.removeprefix(_BOUND))):
        en, de = _BOUND_FOUND.get(
            verdict or "", ("is the maximum enforced?", "gilt das Maximum?")
        )
        return _label(f"{field['en']}: {en}", f"{field['de']}: {de}")
    if name.endswith(_AGAINST_POWER) and (
        field := _counter(name.removesuffix(_AGAINST_POWER))
    ):
        return _label(
            f"{field['en']} today fits the power",
            f"{field['de']} heute passt zur Leistung",
        )
    total, _, daily = name.partition(" against ")
    if daily and (field := _counter(total)) and _counter(daily) == field:
        return _label(
            f"{field['en']}: total and daily agree",
            f"{field['de']}: Gesamt und Tag stimmen überein",
        )
    return None
