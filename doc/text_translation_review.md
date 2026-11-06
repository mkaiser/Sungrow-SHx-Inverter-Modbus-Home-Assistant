# The texts, for review

**248 texts**: everything in `strings.json` that is not an entity name, by its
path -- the setup and options flows, repairs, actions and error messages.
Each is shown in English and with its German, which lives in
`scripts/generate/tables/german_texts.json` and ships in
`translations/de.json`. The entity names are in
[entity_names.md](entity_names.md).

A `{placeholder}` is filled in by the integration and stays as written; backticks
and bold are kept.


## Setup flow (84)

### `config.abort.already_configured`

> **EN** Device is already configured

> **DE** Das Gerät ist bereits konfiguriert

### `config.abort.devices_mode_not_offered`

> **EN** Devices mode is not available in this preview. This build sets the integration up for diagnostics only -- it polls the inverter and can run the capability survey, but creates no sensors. Promotion will be offered in a later release, and the entry does not need to be removed and added again when it is.

> **DE** Der Geräte-Modus ist in dieser Vorschau nicht verfügbar. Diese Version richtet die Integration nur für die Diagnose ein: Sie fragt den Wechselrichter ab und kann die Diagnose ausführen, legt aber keine Sensoren an. Die Freischaltung folgt in einer späteren Version; der Eintrag muss dafür nicht entfernt und neu hinzugefügt werden.

### `config.abort.wrong_device`

> **EN** That address answers as a different inverter ({model}), not the one behind “{title}”. Nothing was changed. Each inverter keeps its own entry; to add that one, use Add integration.

> **DE** Diese Adresse meldet sich als anderer Wechselrichter ({model}), nicht als der hinter „{title}“. Es wurde nichts geändert. Jeder Wechselrichter behält seinen eigenen Eintrag; um jenen hinzuzufügen, wähle „Integration hinzufügen“.

### `config.abort.connection_unchanged`

> **EN** That is the connection this entry already uses. Nothing was changed.

> **DE** Das ist bereits die Verbindung dieses Eintrags. Es wurde nichts geändert.

### `config.abort.connection_moved`

> **EN** “{title}” now uses the new connection. It has been reloaded; its entities, their history and its settings are unchanged.

> **DE** „{title}“ verwendet jetzt die neue Verbindung. Der Eintrag wurde neu geladen; seine Entitäten, deren Verlauf und seine Einstellungen sind unverändert.

### `config.error.cannot_connect`

> **EN** Failed to connect: {error}

> **DE** Verbindung fehlgeschlagen: {error}

### `config.error.no_serial_number`

> **EN** The device answered but reported no serial number.

> **DE** Das Gerät hat geantwortet, aber keine Seriennummer gemeldet.

### `config.error.unrecognized_inverter`

> **EN** The device answered with an unknown model code ({code}). Please open an issue with this code so the model can be added.

> **DE** Das Gerät hat mit einem unbekannten Modellcode ({code}) geantwortet. Bitte eröffne ein Issue mit diesem Code, damit das Modell ergänzt werden kann.

### `config.error.legacy_package_still_loaded`

> **EN** The YAML package is still running, so its entities still hold their IDs. Remove `modbus_sungrow.yaml` from your configuration — or comment out the line that includes it — then restart Home Assistant and try again. Or choose Start fresh.

> **DE** Das YAML-Paket läuft noch, daher belegen seine Entitäten weiterhin ihre IDs. Entferne `modbus_sungrow.yaml` aus deiner Konfiguration – oder kommentiere die Zeile aus, die es einbindet –, starte Home Assistant neu und versuche es erneut. Oder wähle „Neu beginnen“.

### `config.error.network_too_large`

> **EN** That range holds {hosts} addresses, more than the limit of {limit}. Sweeping it would take minutes and flood the network. Narrow it to the subnet the inverter is on, usually a /24.

> **DE** Dieser Bereich umfasst {hosts} Adressen, mehr als die Grenze von {limit}. Ihn zu durchsuchen würde Minuten dauern und das Netzwerk überfluten. Grenze ihn auf das Subnetz ein, in dem der Wechselrichter ist, meist ein /24.

### `config.error.invalid_network`

> **EN** Not a network range: {error}

> **DE** Kein Netzwerkbereich: {error}

### `config.step.entity_ids.title`

> **EN** Existing entities found

> **DE** Bestehende Entitäten gefunden

### `config.step.entity_ids.description`

> **EN** Home Assistant found **{count} entities** from the `modbus_sungrow.yaml` package, such as `{example}`. Your recorder history, your statistics and every dashboard card are stored against those entity IDs.
>
> {status}
>
> **Migrate my existing entities** takes those IDs over. History and statistics carry on uninterrupted and your dashboards keep working unchanged. Nothing is copied and nothing is deleted.
>
> **Start fresh** gives this inverter its own IDs, such as `sensor.sh10rt_total_pv_input_power`. Your old history stays where it is, under the old IDs, and your dashboards keep pointing at it.
>
> Either way the entities are identical in every other respect.

> **DE** Home Assistant hat **{count} Entitäten** aus dem Paket `modbus_sungrow.yaml` gefunden, zum Beispiel `{example}`. Dein Recorder-Verlauf, deine Statistiken und jede Dashboard-Karte sind an diese Entitäts-IDs gebunden.
>
> {status}
>
> **Bestehende Entitäten übernehmen** übernimmt diese IDs. Verlauf und Statistiken laufen ohne Unterbrechung weiter und deine Dashboards funktionieren unverändert. Es wird nichts kopiert und nichts gelöscht.
>
> **Neu beginnen** gibt diesem Wechselrichter eigene IDs, zum Beispiel `sensor.sh10rt_total_pv_input_power`. Dein alter Verlauf bleibt unter den alten IDs, wo er ist, und deine Dashboards zeigen weiterhin darauf.
>
> In jeder anderen Hinsicht sind die Entitäten in beiden Fällen identisch.

### `config.step.entity_ids.data.entity_ids`

> **EN** Entity IDs

> **DE** Entitäts-IDs

### `config.step.entity_ids.data_description.entity_ids`

> **EN** This can be changed later without losing anything.

> **DE** Das lässt sich später ändern, ohne dass etwas verloren geht.

### `config.step.slot_unknown.title`

> **EN** Existing entities found

> **DE** Bestehende Entitäten gefunden

### `config.step.slot_unknown.description`

> **EN** This house ran the YAML package for more than one inverter, and Home Assistant cannot tell which of them this one was. The package's serial sensors are what say so, and neither the running package nor the recorded history has this inverter's serial.
>
> So the YAML package's entity IDs are not offered: taking the wrong set would give this inverter another inverter's history. **Submit** sets it up with its own IDs, such as `sensor.sh10rt_total_pv_input_power`.
>
> To keep its old IDs, put the YAML package back for one restart, so this inverter's serial is recorded, then remove it and restart again. **Configure** can then switch this inverter to its old IDs; the serial stays on record for the recorder's retention, ten days unless you changed it.

> **DE** In diesem Haus lief das YAML-Paket für mehr als einen Wechselrichter, und Home Assistant kann nicht erkennen, welcher davon dieser war. Das sagen die Seriennummer-Sensoren des Pakets, und weder das laufende Paket noch der aufgezeichnete Verlauf kennt die Seriennummer dieses Wechselrichters.
>
> Deshalb werden die Entitäts-IDs des YAML-Pakets nicht angeboten: Mit dem falschen Satz bekäme dieser Wechselrichter den Verlauf eines anderen. **Absenden** richtet ihn mit eigenen IDs ein, zum Beispiel `sensor.sh10rt_total_pv_input_power`.
>
> Um die alten IDs zu behalten, aktiviere das YAML-Paket für einen Neustart wieder, damit die Seriennummer dieses Wechselrichters aufgezeichnet wird, entferne es dann und starte erneut. Mit **Konfigurieren** lässt sich dieser Wechselrichter danach auf seine alten IDs umstellen; die Seriennummer bleibt für die Aufbewahrungsdauer des Recorders gespeichert, zehn Tage, sofern du sie nicht geändert hast.

### `config.step.find.title`

> **EN** Where is the inverter?

> **DE** Wo ist der Wechselrichter?

### `config.step.find.description`

> **EN** Searching is usually easier: many people cannot say what their inverter's IP address is without going to look at the router. The search only probes addresses on the range you confirm.

> **DE** Die Suche ist meist einfacher: Viele können die IP-Adresse ihres Wechselrichters nicht nennen, ohne erst im Router nachzusehen. Die Suche prüft nur Adressen in dem Bereich, den du bestätigst.

### `config.step.find.menu_options.search`

> **EN** Search my network for it

> **DE** Mein Netzwerk danach durchsuchen

### `config.step.find.menu_options.manual`

> **EN** I know the address

> **DE** Ich kenne die Adresse

### `config.step.manual.title`

> **EN** The inverter's address

> **DE** Adresse des Wechselrichters

### `config.step.manual.description`

> **EN** The inverter's IP address, and the Modbus TCP port and device address it answers on. The defaults are right for almost every installation: port 502, device address 1.
>
> If the inverter is behind a WiNet-S dongle, this is the dongle's address rather than the inverter's own. Give the address a reservation in your router first. If it moves anyway, **Reconfigure** on the entry points it at the new one.{error}

> **DE** Die IP-Adresse des Wechselrichters sowie der Modbus-TCP-Port und die Geräteadresse, unter denen er antwortet. Die Standardwerte passen für fast jede Installation: Port 502, Geräteadresse 1.
>
> Befindet sich der Wechselrichter hinter einem WiNet-S-Dongle, ist dies die Adresse des Dongles, nicht die des Wechselrichters selbst. Richte für die Adresse zuerst eine Reservierung im Router ein. Ändert sie sich trotzdem, richtet **Neu konfigurieren** am Eintrag ihn auf die neue aus.{error}

### `config.step.manual.data.host`

> **EN** IP address or hostname

> **DE** IP-Adresse oder Hostname

### `config.step.manual.data.port`

> **EN** Port

> **DE** Port

### `config.step.manual.data.unit_id`

> **EN** Device address

> **DE** Geräteadresse

### `config.step.manual.data_description.host`

> **EN** As your router lists it.

> **DE** So, wie dein Router sie anzeigt.

### `config.step.manual.data_description.port`

> **EN** 502 unless somebody changed it. A Sungrow Logger uses 503.

> **DE** 502, sofern es niemand geändert hat. Ein Sungrow Logger verwendet 503.

### `config.step.manual.data_description.unit_id`

> **EN** 1 for a single inverter. A second inverter in a master/slave cluster answers on 2, and its own address is the one to give here.

> **DE** 1 bei einem einzelnen Wechselrichter. Ein zweiter Wechselrichter in einem Master/Slave-Verbund antwortet auf 2, und seine eigene Adresse ist hier anzugeben.

### `config.step.name.title`

> **EN** What should this inverter be called?

> **DE** Wie soll dieser Wechselrichter heißen?

### `config.step.name.description`

> **EN** You have **{count}** inverters, and both would otherwise be called “{model}” — Home Assistant would add `_2` to whichever you set up second, which records the order you clicked in and nothing else.
>
> This name becomes part of every entity id for this inverter, for example `{example}`. That is what your history and dashboards are keyed to, so it is worth a moment now: renaming later changes the label but leaves the ids already created exactly where they are.
>
> Something about where it is works best — `Roof`, `Garage`, `Barn`. The suggestion is the most the inverter itself can tell us.

> **DE** Du hast **{count}** Wechselrichter, und beide hießen sonst „{model}“ – Home Assistant würde beim zuletzt eingerichteten `_2` anhängen, was nur die Reihenfolge deiner Klicks festhält.
>
> Dieser Name wird Teil jeder Entitäts-ID dieses Wechselrichters, zum Beispiel `{example}`. An diese IDs sind dein Verlauf und deine Dashboards gebunden, also lohnt sich jetzt ein Moment: Eine spätere Umbenennung ändert die Bezeichnung, lässt aber die bereits angelegten IDs, wo sie sind.
>
> Am besten eignet sich etwas zum Standort – `Dach`, `Garage`, `Scheune`. Der Vorschlag ist das Meiste, was der Wechselrichter selbst verraten kann.

### `config.step.name.data.name`

> **EN** Name

> **DE** Name

### `config.step.name.data_description.name`

> **EN** Suggested: {suggestion}. Change it to whatever you will recognise.

> **DE** Vorschlag: {suggestion}. Ändere ihn in etwas, das du wiedererkennst.

### `config.step.nothing_found.title`

> **EN** No inverter found

> **DE** Kein Wechselrichter gefunden

### `config.step.nothing_found.description`

> **EN** Nothing on **{scanned}** identified itself as a Sungrow inverter. {candidates} device(s) had the port open but did not answer as one — an open Modbus port on its own is not enough.
>
> Worth checking:
> - the inverter is on **this** network — if Home Assistant is in a container or a VM, it may be on a different one from your inverter;
> - nothing else is holding the inverter's Modbus connection. A Sungrow accepts very few at once, so another integration, a second Home Assistant, or the old YAML package still polling will block it;
> - the port is right — 502 for a direct connection, something else through a Modbus TCP bridge.
>
> You can search a different range, type the address in yourself, or go back to the beginning.

> **DE** Nichts in **{scanned}** hat sich als Sungrow-Wechselrichter zu erkennen gegeben. {candidates} Gerät(e) hatten den Port offen, haben aber nicht als einer geantwortet – ein offener Modbus-Port allein genügt nicht.
>
> Das solltest du prüfen:
> - der Wechselrichter ist in **diesem** Netzwerk – läuft Home Assistant in einem Container oder einer VM, kann es ein anderes sein als das deines Wechselrichters;
> - nichts anderes hält die Modbus-Verbindung des Wechselrichters. Ein Sungrow nimmt nur sehr wenige gleichzeitig an, daher blockieren eine andere Integration, ein zweites Home Assistant oder das alte YAML-Paket, das noch abfragt, ihn;
> - der Port stimmt – 502 bei direkter Verbindung, etwas anderes über eine Modbus-TCP-Bridge.
>
> Du kannst einen anderen Bereich durchsuchen, die Adresse selbst eingeben oder zum Anfang zurückgehen.

### `config.step.nothing_found.menu_options.search`

> **EN** Search a different range

> **DE** Anderen Bereich durchsuchen

### `config.step.nothing_found.menu_options.manual`

> **EN** Enter the address myself

> **DE** Adresse selbst eingeben

### `config.step.nothing_found.menu_options.start_over`

> **EN** Back to the start

> **DE** Zurück zum Anfang

### `config.step.other_inverter.title`

> **EN** What is the other inverter?

> **DE** Welcher ist der andere Wechselrichter?

### `config.step.other_inverter.description`

> **EN** The make, and its size if you know it — *Fronius Symo 8.2*, or *5 kW string inverter on the south roof*. The size is the useful part: it says how large the gap in the load figures is.
>
> This goes into the document, so leave out serial numbers, addresses and names. You can leave it blank.

> **DE** Der Hersteller und, falls bekannt, die Größe – *Fronius Symo 8.2* oder *5-kW-String-Wechselrichter auf dem Süddach*. Die Größe ist der nützliche Teil: Sie sagt, wie groß die Lücke in den Lastwerten ist.
>
> Das gelangt in das Dokument, lass deshalb Seriennummern, Adressen und Namen weg. Du kannst es leer lassen.

### `config.step.other_inverter.data.survey_other_inverter_detail`

> **EN** The other inverter

> **DE** Der andere Wechselrichter

### `config.step.pick.title`

> **EN** Inverters found

> **DE** Wechselrichter gefunden

### `config.step.pick.description`

> **EN** {count} device(s) answered and identified themselves. Names come from your router's DNS where it provides them, otherwise the address is shown.
>
> Where there is more than one inverter, each says its part in the cluster and how that is known: **measured** is read from the inverter itself, **inferred** is worked out from what the others answered. An inferred role is a good guess, not a reading.
>
> If none of these is the inverter you meant, choose the last option and you can enter its address yourself.{note}

> **DE** {count} Gerät(e) haben geantwortet und sich zu erkennen gegeben. Namen stammen aus dem DNS deines Routers, sofern er welche liefert, sonst wird die Adresse angezeigt.
>
> Gibt es mehr als einen Wechselrichter, nennt jeder seine Rolle im Verbund und woher man sie kennt: **gemessen** wurde vom Wechselrichter selbst gelesen, **abgeleitet** wird aus den Antworten der anderen geschlossen. Eine abgeleitete Rolle ist eine gute Vermutung, keine Messung.
>
> Ist keiner davon der gemeinte Wechselrichter, wähle die letzte Option, dann kannst du seine Adresse selbst eingeben.{note}

### `config.step.pick.data.host`

> **EN** Inverter

> **DE** Wechselrichter

### `config.step.search.title`

> **EN** Search my network

> **DE** Mein Netzwerk durchsuchen

### `config.step.search.description`

> **EN** Home Assistant will try every address in this range on the Modbus port, then ask whatever answers what it is — an open port alone is not enough to call something an inverter.
>
> {detected}
>
> A `/24` takes about a second; anything much larger is rejected, because every address probed is real traffic on your network.

> **DE** Home Assistant probiert jede Adresse in diesem Bereich auf dem Modbus-Port aus und fragt dann jedes Gerät, das antwortet, was es ist – ein offener Port allein genügt nicht, um etwas als Wechselrichter zu bezeichnen.
>
> {detected}
>
> Ein `/24` dauert etwa eine Sekunde; deutlich größere Bereiche werden abgelehnt, weil jede geprüfte Adresse echter Datenverkehr in deinem Netzwerk ist.

### `config.step.search.data.network`

> **EN** Network range

> **DE** Netzwerkbereich

### `config.step.search.data_description.network`

> **EN** In CIDR notation, for example 192.168.1.0/24.

> **DE** In CIDR-Notation, zum Beispiel 192.168.1.0/24.

### `config.step.testimony.title`

> **EN** What do you want to tell us?

> **DE** Was möchtest du uns mitteilen?

### `config.step.testimony.description`

> **EN** You chose diagnostics only, which means this entry exists to produce a reading — so these are the questions that reading needs and no register can answer.
>
> {measured}
>
> Everything here is optional, and leaving a field empty is honest: it records that the question was not answered, which is different from answering "I don't know". You can change any of it later under the integration's options.
>
> Afterwards, press **Run read only diagnosis** on the device page.

> **DE** Du hast „nur Diagnose“ gewählt, das heißt, dieser Eintrag existiert, um eine Messung zu erzeugen – dies sind also die Fragen, die diese Messung braucht und die kein Register beantworten kann.
>
> {measured}
>
> Alles hier ist optional, und ein leeres Feld ist ehrlich: Es hält fest, dass die Frage nicht beantwortet wurde, was etwas anderes ist, als mit „Ich weiß es nicht“ zu antworten. Du kannst alles später unter den Optionen der Integration ändern.
>
> Drücke danach auf der Geräteseite **Diagnose ausführen (nur lesend)**.

### `config.step.testimony.data.reporter`

> **EN** Your name or handle

> **DE** Dein Name oder Pseudonym

### `config.step.testimony.data.survey_transport`

> **EN** How this inverter is connected

> **DE** Wie dieser Wechselrichter angebunden ist

### `config.step.testimony.data.survey_proxy`

> **EN** Is a Modbus proxy in the path?

> **DE** Befindet sich ein Modbus-Proxy im Pfad?

### `config.step.testimony.data.survey_pollers`

> **EN** Anything else polling this inverter?

> **DE** Fragt noch etwas anderes diesen Wechselrichter ab?

### `config.step.testimony.data.survey_other_inverter`

> **EN** Is there another inverter here that is not a Sungrow?

> **DE** Gibt es hier einen weiteren Wechselrichter, der kein Sungrow ist?

### `config.step.testimony.data.survey_battery`

> **EN** Battery make and model

> **DE** Hersteller und Modell der Batterie

### `config.step.testimony.data.survey_comment`

> **EN** Anything else worth knowing

> **DE** Sonst noch etwas Wissenswertes

### `config.step.testimony.data.publish_address`

> **EN** May the last two octets of the address be published?

> **DE** Dürfen die letzten zwei Oktette der Adresse veröffentlicht werden?

### `config.step.testimony.data.survey_register_dump`

> **EN** Also sweep the raw register bands (about five minutes)

> **DE** Auch die rohen Registerbereiche durchsuchen (etwa fünf Minuten)

### `config.step.testimony.data_description.reporter`

> **EN** Credited in the published reading, and who gets asked if a row raises a question. Leave empty to contribute anonymously.

> **DE** Wird in der veröffentlichten Messung genannt und gefragt, wenn eine Zeile Fragen aufwirft. Leer lassen, um anonym beizutragen.

### `config.step.testimony.data_description.survey_transport`

> **EN** Cable against dongle is measured already. What only you know is whether a dongle is on its Ethernet socket or its WiFi — a WiNet-S answers identically either way, so "not sure" is a real answer and better than a guess.

> **DE** Kabel gegenüber Dongle ist bereits gemessen. Nur du weißt, ob ein Dongle an seiner Ethernet-Buchse oder per WLAN hängt – ein WiNet-S antwortet in beiden Fällen gleich, daher ist "nicht sicher" eine echte Antwort und besser als eine Vermutung.

### `config.step.testimony.data_description.survey_proxy`

> **EN** modbus-proxy, evcc's proxy, a Home Assistant add-on. A proxy holds one connection and lends it out, so it changes what a dropped register means — and it rebuilds every frame, which can hide or create the frame quirks this project tracks.

> **DE** modbus-proxy, der Proxy von evcc, ein Home-Assistant-Add-on. Ein Proxy hält eine Verbindung und verleiht sie weiter, was die Bedeutung eines ausgefallenen Registers verändert – und er baut jeden Frame neu auf, was die Frame-Eigenheiten, die dieses Projekt verfolgt, verbergen oder erzeugen kann.

### `config.step.testimony.data_description.survey_pollers`

> **EN** This Home Assistant is recorded automatically. What matters here is anything else: another Home Assistant, the YAML package, evcc, a logger. An inverter grants very few connections, and two clients competing for one looks exactly like a broken register.

> **DE** Dieses Home Assistant wird automatisch erfasst. Wichtig ist hier alles andere: ein anderes Home Assistant, das YAML-Paket, evcc, ein Logger. Ein Wechselrichter gewährt sehr wenige Verbindungen, und zwei Clients, die um eine konkurrieren, sehen genau wie ein defektes Register aus.

### `config.step.testimony.data_description.survey_other_inverter`

> **EN** Your Sungrow does not measure how much your house is using — it works it out from its own output plus what the grid meter says is coming in. A second inverter feeding the same meter therefore makes every load figure too low, by exactly what that inverter is producing, while everything else reads normally. No register can tell us: the Sungrow cannot see it. Say yes and we will ask what it is.

> **DE** Dein Sungrow misst nicht, wie viel dein Haus verbraucht – er errechnet es aus seiner eigenen Leistung plus dem, was der Netzzähler als Bezug meldet. Ein zweiter Wechselrichter am selben Zähler macht daher jeden Lastwert um genau dessen Erzeugung zu niedrig, während alles andere normal aussieht. Kein Register kann uns das sagen: Der Sungrow sieht ihn nicht. Antworte mit Ja, dann fragen wir, was es ist.

### `config.step.testimony.data_description.survey_battery`

> **EN** No register reports it. "SBR096" or "Pylontech Force H1, 14.4 kWh" is more useful than a capacity the inverter already reports.

> **DE** Kein Register meldet das. "SBR096" oder "Pylontech Force H1, 14,4 kWh" ist nützlicher als eine Kapazität, die der Wechselrichter ohnehin meldet.

### `config.step.testimony.data_description.survey_comment`

> **EN** Anything unusual about the installation — a cluster, a second inverter, a wallbox, a firmware update you remember.

> **DE** Alles Ungewöhnliche an der Anlage – ein Verbund, ein zweiter Wechselrichter, eine Wallbox, ein Firmware-Update, an das du dich erinnerst.

### `config.step.testimony.data_description.publish_address`

> **EN** On, and yours to turn off before you submit. Only the last two octets ever reach the document — never the third, which is what would identify your network — and clear this and it reads xxx.xxx instead. What it buys is telling several readings from one house apart: a master, a slave and two dongles otherwise produce four files that look alike.

> **DE** An, und du kannst es vor dem Absenden ausschalten. Nur die letzten zwei Oktette gelangen je in das Dokument – nie das dritte, das dein Netzwerk identifizieren würde –, und wenn du das deaktivierst, steht stattdessen xxx.xxx. Der Nutzen: Mehrere Messungen aus einem Haus lassen sich unterscheiden – ein Master, ein Slave und zwei Dongles ergeben sonst vier gleich aussehende Dateien.

### `config.step.testimony.data_description.survey_register_dump`

> **EN** On, and worth turning off if you are in a hurry. Without it a survey reads the registers this integration already knows about and takes a couple of seconds. With it, it also sweeps 2181 addresses across sixteen bands, including the ones no specification documents — which is how every undocumented register this project knows was found. That is slow because an address with nothing behind it goes quiet rather than refusing, so each empty one costs a full timeout: about five minutes on a direct cable, and considerably longer through a WiNet-S or a VPN. Your inverter keeps being polled throughout, and the survey button on the device page shows how far along it is.

> **DE** An, und besser auszuschalten, wenn du es eilig hast. Ohne sie liest die Diagnose die Register, die diese Integration bereits kennt, und braucht ein paar Sekunden. Mit ihr durchsucht sie zusätzlich 2181 Adressen in sechzehn Bereichen, auch die, die keine Spezifikation dokumentiert – so wurde jedes undokumentierte Register gefunden, das dieses Projekt kennt. Das ist langsam, weil eine Adresse ohne Inhalt verstummt statt abzulehnen, sodass jede leere ein volles Timeout kostet: etwa fünf Minuten am direkten Kabel und deutlich länger über ein WiNet-S oder ein VPN. Dein Wechselrichter wird die ganze Zeit weiter abgefragt, und die Diagnose-Schaltfläche auf der Geräteseite zeigt den Fortschritt.

### `config.step.user.title`

> **EN** What is this for?

> **DE** Wofür ist das?

### `config.step.user.description`

> **EN** {mode_intro}**The device survey** connects to the inverter, works out what it is and what it answers, and creates **no entities at all**. It exists because this project has to *measure* which registers each model and firmware supports — Sungrow's own specification has been wrong in both directions — and today that evidence comes from the few houses that have sent a reading.{mode_choice}

> **DE** {mode_intro}**Die Geräte-Diagnose** verbindet sich mit dem Wechselrichter, ermittelt, was er ist und was er beantwortet, und legt **überhaupt keine Entitäten an**. Es gibt sie, weil dieses Projekt *messen* muss, welche Register jedes Modell und jede Firmware unterstützt – Sungrows eigene Spezifikation lag in beide Richtungen falsch – und dieser Nachweis stammt heute von den wenigen Haushalten, die eine Messung eingesandt haben.{mode_choice}

### `config.step.user.menu_options.setup_devices`

> **EN** Set up my inverter — sensors, controls, the lot

> **DE** Meinen Wechselrichter einrichten – Sensoren, Steuerungen, alles

### `config.step.user.menu_options.setup_diagnostics`

> **EN** Perform the device survey — help this project, create no entities

> **DE** Geräte-Diagnose durchführen – dem Projekt helfen, keine Entitäten anlegen

### `config.step.reconfigure.title`

> **EN** Change the connection

> **DE** Verbindung ändern

### `config.step.reconfigure.description`

> **EN** This entry reaches its inverter at **{current}**. Give the other way to reach the **same** inverter -- its own LAN port after a cable is laid, the WiNet-S dongle, or a new address.
>
> The new connection is checked first: it has to answer with this inverter's serial number. Entity IDs, history and settings stay as they are.{error}

> **DE** Dieser Eintrag erreicht seinen Wechselrichter unter **{current}**. Gib den anderen Weg zum **selben** Wechselrichter an – seinen eigenen LAN-Port nach dem Verlegen eines Kabels, den WiNet-S-Dongle oder eine neue Adresse.
>
> Die neue Verbindung wird zuerst geprüft: Sie muss mit der Seriennummer dieses Wechselrichters antworten. Entitäts-IDs, Verlauf und Einstellungen bleiben, wie sie sind.{error}

### `config.step.reconfigure.data.host`

> **EN** IP address or hostname

> **DE** IP-Adresse oder Hostname

### `config.step.reconfigure.data.port`

> **EN** Port

> **DE** Port

### `config.step.reconfigure.data.unit_id`

> **EN** Device address

> **DE** Geräteadresse

### `config.step.reconfigure.data_description.host`

> **EN** As your router lists it.

> **DE** So, wie dein Router sie anzeigt.

### `config.step.reconfigure.data_description.port`

> **EN** 502 unless somebody changed it. A Sungrow Logger uses 503.

> **DE** 502, sofern es niemand geändert hat. Ein Sungrow Logger verwendet 503.

### `config.step.reconfigure.data_description.unit_id`

> **EN** 1 for a single inverter. A second inverter in a master/slave cluster answers on 2, and its own address is the one to give here.

> **DE** 1 bei einem einzelnen Wechselrichter. Ein zweiter Wechselrichter in einem Master/Slave-Verbund antwortet auf 2, und seine eigene Adresse ist hier anzugeben.

### `config.step.move.title`

> **EN** Use the new connection?

> **DE** Neue Verbindung verwenden?

### `config.step.move.description`

> **EN** This inverter is already set up as **{title}**, reached at **{old}**. It also answers at **{new}**.
>
> **Submit** switches the entry to **{new}** and reloads it. Its entity IDs, their history and its settings stay as they are; the battery and wallbox are looked for again on the new connection. Your answer about how the survey reaches the inverter is cleared, because it described the old connection.{wallbox}
>
> To keep the current connection, close this dialog.

> **DE** Dieser Wechselrichter ist bereits als **{title}** eingerichtet und wird unter **{old}** erreicht. Er antwortet auch unter **{new}**.
>
> **Absenden** stellt den Eintrag auf **{new}** um und lädt ihn neu. Seine Entitäts-IDs, deren Verlauf und seine Einstellungen bleiben, wie sie sind; Batterie und Wallbox werden an der neuen Verbindung erneut gesucht. Deine Antwort darauf, wie die Diagnose den Wechselrichter erreicht, wird gelöscht, weil sie die alte Verbindung beschrieb.{wallbox}
>
> Um die aktuelle Verbindung zu behalten, schließe diesen Dialog.

### `config.progress.searching`

> **EN** Searching {network}.
>
> {stage}
>
> Ports 502 and 503 are both tried, so you do not have to know which one your equipment uses.

> **DE** {network} wird durchsucht.
>
> {stage}
>
> Die Ports 502 und 503 werden beide probiert, du musst also nicht wissen, welchen deine Geräte verwenden.

### `config.create_entry.diagnostics`

> **EN** **You are set up, and nothing has been read yet.** Two more steps, both on the device page this dialog is about to show you:
>
> 1. Press **Run read only diagnosis**, under *Diagnostic*. It reads and never writes. On a cable it is over in a couple of minutes with the register sweep on; over a VPN it can take considerably longer, and the three sensors beside the button say how far along it is and what it is reading.
> 2. When it finishes, open **Notifications** in the sidebar — the badge at the bottom left. The notification there carries a summary and a **Download the document** link. That link is the JSON file to send us, and it stops working after an hour.
>
> Missed it, or came back the next day? **Download diagnostics** on the same device page carries the same document and never expires. Send either to [the survey issue]({survey_issue_url}).
>
> The file names your inverter by a stand-in rather than its serial number, and carries the last two octets of its address only while that box is ticked.

> **DE** **Die Einrichtung ist abgeschlossen, und es wurde noch nichts gelesen.** Zwei weitere Schritte, beide auf der Geräteseite, die dieser Dialog gleich anzeigt:
>
> 1. Drücke **Diagnose ausführen (nur lesend)** unter *Diagnose*. Sie liest und schreibt nie. Am Kabel ist sie mit dem Registerdurchlauf in ein paar Minuten fertig; über ein VPN kann es deutlich länger dauern, und die drei Sensoren neben der Schaltfläche zeigen, wie weit sie ist und was sie liest.
> 2. Öffne danach **Benachrichtigungen** in der Seitenleiste – das Abzeichen unten links. Die Benachrichtigung dort enthält eine Zusammenfassung und einen Link **Dokument herunterladen**. Dieser Link ist die JSON-Datei, die du uns schicken sollst, und er funktioniert nach einer Stunde nicht mehr.
>
> Verpasst, oder erst am nächsten Tag zurück? **Diagnose herunterladen** auf derselben Geräteseite enthält dasselbe Dokument und läuft nie ab. Schicke eines davon an [das Diagnose-Issue]({survey_issue_url}).
>
> Die Datei benennt deinen Wechselrichter mit einem Platzhalter statt der Seriennummer und enthält die letzten zwei Oktette seiner Adresse nur, solange dieses Feld angehakt ist.


## Select states (13)

### `entity.select.battery_forced_charge_discharge.state.stop`

> **EN** Stop

> **DE** Stopp

### `entity.select.battery_forced_charge_discharge.state.charge`

> **EN** Forced charge

> **DE** Zwangsladung

### `entity.select.battery_forced_charge_discharge.state.discharge`

> **EN** Forced discharge

> **DE** Zwangsentladung

### `entity.select.ems_mode.state.self_consumption`

> **EN** Self-consumption

> **DE** Eigenverbrauch

### `entity.select.ems_mode.state.forced`

> **EN** Forced (compulsory)

> **DE** Zwangsbetrieb

### `entity.select.ems_mode.state.external_ems`

> **EN** External EMS

> **DE** Externes EMS

### `entity.select.ems_mode.state.vpp`

> **EN** VPP

> **DE** VPP

### `entity.select.forced_charging_days.state.weekdays`

> **EN** Weekdays

> **DE** Werktage

### `entity.select.forced_charging_days.state.every_day`

> **EN** Every day

> **DE** Jeden Tag

### `entity.select.load_adjustment_mode.state.timing`

> **EN** Timing

> **DE** Zeitsteuerung

### `entity.select.load_adjustment_mode.state.on_off`

> **EN** On/off

> **DE** Ein/Aus

### `entity.select.load_adjustment_mode.state.power_optimised`

> **EN** Power optimised

> **DE** Leistungsoptimiert

### `entity.select.load_adjustment_mode.state.disabled`

> **EN** Disabled

> **DE** Deaktiviert


## Selector options (19)

### `selector.entity_ids.options.migrate`

> **EN** Migrate my existing entities — keep their history

> **DE** Bestehende Entitäten übernehmen — Verlauf behalten

### `selector.entity_ids.options.new`

> **EN** Start fresh / create new entities

> **DE** Neu beginnen / neue Entitäten anlegen

### `selector.audience.options.admins`

> **EN** Administrators only

> **DE** Nur Administratoren

### `selector.audience.options.users`

> **EN** Any user who can control this device

> **DE** Jeder Benutzer, der dieses Gerät steuern darf

### `selector.external_placement.options.behind_meter`

> **EN** Behind the same grid meter — it reduces what the house imports

> **DE** Hinter demselben Netzzähler – er verringert, was das Haus bezieht

### `selector.external_placement.options.separately_metered`

> **EN** On its own supply — none of it passes this inverter's meter

> **DE** An einem eigenen Anschluss – nichts davon passiert den Zähler dieses Wechselrichters

### `selector.survey_transport.options.direct_lan`

> **EN** A cable straight into the inverter's own LAN port

> **DE** Ein Kabel direkt am eigenen LAN-Port des Wechselrichters

### `selector.survey_transport.options.winet_lan`

> **EN** A WiNet-S dongle, on its Ethernet socket

> **DE** Ein WiNet-S-Dongle an seiner Ethernet-Buchse

### `selector.survey_transport.options.winet_wlan`

> **EN** A WiNet-S dongle, over WiFi

> **DE** Ein WiNet-S-Dongle über WLAN

### `selector.survey_transport.options.winet`

> **EN** A WiNet-S dongle, but I am not sure which medium

> **DE** Ein WiNet-S-Dongle, aber ich bin nicht sicher, über welches Medium

### `selector.survey_transport.options.logger`

> **EN** A Logger1000 or Logger3000

> **DE** Ein Logger1000 oder Logger3000

### `selector.survey_transport.options.unsure`

> **EN** Not sure

> **DE** Nicht sicher

### `selector.survey_proxy.options.yes`

> **EN** Yes — modbus-proxy, evcc's proxy, or a Home Assistant add-on

> **DE** Ja – modbus-proxy, der Proxy von evcc oder ein Home-Assistant-Add-on

### `selector.survey_proxy.options.no`

> **EN** No, this talks straight to the inverter

> **DE** Nein, er spricht direkt mit dem Wechselrichter

### `selector.survey_proxy.options.unknown`

> **EN** I do not know what that is

> **DE** Ich weiß nicht, was das ist

### `selector.survey_other_inverter.options.yes`

> **EN** Yes — there is another inverter that is not a Sungrow

> **DE** Ja – es gibt einen weiteren Wechselrichter, der kein Sungrow ist

### `selector.survey_other_inverter.options.no`

> **EN** No — the Sungrow is the only inverter here

> **DE** Nein – der Sungrow ist hier der einzige Wechselrichter

### `selector.entity_id_style.options.migrate`

> **EN** The YAML package's IDs, such as sensor.total_dc_power

> **DE** Die IDs des YAML-Pakets, etwa sensor.total_dc_power

### `selector.entity_id_style.options.new`

> **EN** Device-scoped IDs, such as sensor.sh10rt_total_pv_input_power

> **DE** Gerätebezogene IDs, etwa sensor.sh10rt_total_pv_input_power


## Repairs (10)

### `issues.preview_release.title`

> **EN** Sungrow Modbus is a preview

> **DE** Sungrow Modbus ist eine Vorschau

### `issues.preview_release.description`

> **EN** This integration is a preview release, for testers rather than for a system you depend on.
>
> **Entity names may still change.** A name supplies an entity id when the entity is first created, so a change does not move the ids you already have -- your history and dashboards are safe. What it does mean is that your ids can end up differing from somebody who installs later. Where that matters, a rename will ship with a migration that moves yours across and carries the history with it.
>
> **What is not in flux:** readings, units, and the migration from the YAML package. If you chose to keep the YAML package's entity ids, those are reproduced exactly and none of this touches them.
>
> Please report anything that looks wrong -- that is what a preview is for.

> **DE** Diese Integration ist eine Vorschauversion, für Tester und nicht für ein System, auf das du dich verlässt.
>
> **Entitätsnamen können sich noch ändern.** Ein Name liefert eine Entitäts-ID, wenn die Entität erstmals angelegt wird, eine Änderung verschiebt also die vorhandenen IDs nicht – dein Verlauf und deine Dashboards sind sicher. Es bedeutet aber, dass deine IDs von denen eines später Installierenden abweichen können. Wo das eine Rolle spielt, kommt eine Umbenennung mit einer Migration, die deine IDs mitzieht und den Verlauf mitnimmt.
>
> **Was nicht im Fluss ist:** Messwerte, Einheiten und die Migration vom YAML-Paket. Wenn du dich für die Entitäts-IDs des YAML-Pakets entschieden hast, werden diese genau reproduziert, und nichts davon berührt sie.
>
> Bitte melde alles, was falsch aussieht – dafür ist eine Vorschau da.

### `issues.control_test_unfinished.title`

> **EN** A control write test on {name} did not finish

> **DE** Ein Steuerungs-Schreibtest an {name} wurde nicht abgeschlossen

### `issues.control_test_unfinished.fix_flow.step.confirm.title`

> **EN** Put these settings back

> **DE** Diese Einstellungen zurücksetzen

### `issues.control_test_unfinished.fix_flow.step.confirm.description`

> **EN** The control write test changes a setting, checks it, and changes it back. This one did not get to the changing-back part — Home Assistant was restarted, the entry was reloaded, or the inverter stopped answering partway through.
>
> These settings may still be holding the test's values rather than yours:
>
> {registers}
>
> Fixing this writes each of them back and reads it again to check it took.
>
> The following will be written back to your inverter and then read again to confirm:
>
> {registers}
>
> If anything refuses the write, nothing is hidden — you will be told which and this will stay here. The usual cause is something else polling the inverter at the same time.

> **DE** Der Steuerungs-Schreibtest ändert eine Einstellung, prüft sie und ändert sie zurück. Dieser kam nicht bis zum Zurückändern – Home Assistant wurde neu gestartet, der Eintrag neu geladen oder der Wechselrichter hörte mittendrin auf zu antworten.
>
> Diese Einstellungen enthalten womöglich noch die Werte des Tests statt deiner:
>
> {registers}
>
> Die Behebung schreibt jede davon zurück und liest sie erneut, um zu prüfen, dass es geklappt hat.
>
> Folgendes wird an deinen Wechselrichter zurückgeschrieben und zur Bestätigung erneut gelesen:
>
> {registers}
>
> Verweigert etwas das Schreiben, wird nichts verschwiegen – du erfährst, was, und die Reparatur bleibt bestehen. Die übliche Ursache ist, dass gleichzeitig etwas anderes den Wechselrichter abfragt.

### `issues.control_test_unfinished.fix_flow.abort.restore_failed`

> **EN** Could not put everything back: {error}
>
> This repair stays open so you can try again.

> **DE** Es konnte nicht alles zurückgesetzt werden: {error}
>
> Diese Reparatur bleibt offen, damit du es erneut versuchen kannst.

### `issues.control_test_left_stopped.title`

> **EN** {name} may still be stopped after a control write test

> **DE** {name} ist nach einem Steuerungs-Schreibtest womöglich noch gestoppt

### `issues.control_test_left_stopped.fix_flow.step.confirm.title`

> **EN** Start the inverter and put these settings back

> **DE** Den Wechselrichter starten und diese Einstellungen zurücksetzen

### `issues.control_test_left_stopped.fix_flow.step.confirm.description`

> **EN** **Check whether your inverter is generating.** A control write test was given permission to stop and restart it, and did not get to the restart — Home Assistant was restarted, the entry was reloaded, or the inverter stopped answering partway through.
>
> Fixing this starts the inverter, then puts these settings back and reads each one again to check it took:
>
> {registers}
>
> The inverter will be started first, then the following written back and read again to confirm:
>
> {registers}
>
> If anything refuses, you will be told which and this will stay here.

> **DE** **Prüfe, ob dein Wechselrichter erzeugt.** Ein Steuerungs-Schreibtest durfte ihn stoppen und neu starten und kam nicht bis zum Neustart – Home Assistant wurde neu gestartet, der Eintrag neu geladen oder der Wechselrichter hörte mittendrin auf zu antworten.
>
> Die Behebung startet den Wechselrichter, setzt dann diese Einstellungen zurück und liest jede erneut, um zu prüfen, dass es geklappt hat:
>
> {registers}
>
> Der Wechselrichter wird zuerst gestartet, dann wird Folgendes zurückgeschrieben und zur Bestätigung erneut gelesen:
>
> {registers}
>
> Verweigert etwas, erfährst du, was, und die Reparatur bleibt bestehen.

### `issues.control_test_left_stopped.fix_flow.abort.restore_failed`

> **EN** Could not finish: {error}
>
> **Check whether your inverter is running.** This repair stays open so you can try again.

> **DE** Es konnte nicht abgeschlossen werden: {error}
>
> **Prüfe, ob dein Wechselrichter läuft.** Diese Reparatur bleibt offen, damit du es erneut versuchen kannst.


## Options flow (87)

### `options.step.init.title`

> **EN** Sungrow Modbus options

> **DE** Sungrow-Modbus-Optionen

### `options.step.init.description`

> **EN** Everything this integration lets you change, in one place. Open a section to see it; what you do not open stays as it is.
>
> Connection details are not here — changing the host or the unit id means talking to a different device, which is **Reconfigure** rather than an option.

> **DE** Alles, was diese Integration dich ändern lässt, an einem Ort. Öffne einen Abschnitt, um ihn zu sehen; was du nicht öffnest, bleibt, wie es ist.
>
> Verbindungsdaten sind nicht hier – Host oder Geräteadresse zu ändern heißt, mit einem anderen Gerät zu sprechen, das ist **Neu konfigurieren** und keine Option.

### `options.step.init.data.add_devices`

> **EN** Add this endpoint's devices now

> **DE** Die Geräte dieses Endpunkts jetzt hinzufügen

### `options.step.init.data.entity_ids`

> **EN** Entity IDs

> **DE** Entitäts-IDs

### `options.step.init.data_description.add_devices`

> **EN** This entry was set up for diagnostics only, so it has no entities. Ticking this asks the one question that was skipped — whether to take over the YAML package's entity ids — and then creates them.{devices_mode}

> **DE** Dieser Eintrag wurde nur für die Diagnose eingerichtet und hat deshalb keine Entitäten. Das Anhaken stellt die eine übersprungene Frage – ob die Entitäts-IDs des YAML-Pakets übernommen werden sollen – und legt sie dann an.{devices_mode}

### `options.step.init.data_description.entity_ids`

> **EN** Which IDs this inverter's entities have. Changing it moves them, with their history and statistics; the next page says exactly what moves before anything does.

> **DE** Welche IDs die Entitäten dieses Wechselrichters haben. Eine Änderung verschiebt sie samt Verlauf und Statistiken; die nächste Seite sagt genau, was sich verschiebt, bevor etwas passiert.

### `options.step.init.sections.polling.name`

> **EN** Polling

> **DE** Abfrage

### `options.step.init.sections.polling.description`

> **EN** Registers are read in four groups, each fetched as one cycle at the interval you set. {tiers} A Sungrow accepts very few Modbus connections, so if something else polls it (the YAML package, another Home Assistant, EVCC, a logger), slowing a group down or setting it to 0 (never read, its entities not created) is the cheapest fix for dropouts. The minimum is 5 seconds. Changing anything here reloads the integration.

> **DE** Die Register werden in vier Gruppen gelesen, jede als ein Zyklus im von dir eingestellten Intervall. {tiers} Ein Sungrow nimmt nur sehr wenige Modbus-Verbindungen an. Wenn also etwas anderes ihn abfragt (das YAML-Paket, ein anderes Home Assistant, EVCC, ein Logger), ist das Verlangsamen einer Gruppe oder das Setzen auf 0 (nie lesen, ihre Entitäten werden nicht angelegt) die günstigste Abhilfe gegen Aussetzer. Das Minimum sind 5 Sekunden. Jede Änderung hier lädt die Integration neu.

### `options.step.init.sections.polling.data.realtime`

> **EN** Realtime group

> **DE** Echtzeit-Gruppe

### `options.step.init.sections.polling.data.fast`

> **EN** Fast group

> **DE** Schnelle Gruppe

### `options.step.init.sections.polling.data.medium`

> **EN** Medium group

> **DE** Mittlere Gruppe

### `options.step.init.sections.polling.data.slowest`

> **EN** Slowest group

> **DE** Langsamste Gruppe

### `options.step.init.sections.polling.data_description.realtime`

> **EN** Seconds between reads, or 0 for never.

> **DE** Sekunden zwischen den Lesevorgängen, oder 0 für nie.

### `options.step.init.sections.polling.data_description.fast`

> **EN** Seconds between reads, or 0 for never.

> **DE** Sekunden zwischen den Lesevorgängen, oder 0 für nie.

### `options.step.init.sections.polling.data_description.medium`

> **EN** Seconds between reads, or 0 for never.

> **DE** Sekunden zwischen den Lesevorgängen, oder 0 für nie.

### `options.step.init.sections.polling.data_description.slowest`

> **EN** Seconds between reads, or 0 for never.

> **DE** Sekunden zwischen den Lesevorgängen, oder 0 für nie.

### `options.step.init.sections.permissions.name`

> **EN** Permissions

> **DE** Berechtigungen

### `options.step.init.sections.permissions.description`

> **EN** Who may call the start and stop actions, and who may press the control write test's button. Administrators only is the default: a stopped inverter stays stopped until somebody starts it. Users means users who can already change this device; read-only logins never can, and automations and scripts are not affected. Every other setting is an entity, and Home Assistant decides who may change it: make an account read-only under Settings → People to keep a person from changing any of them.

> **DE** Wer die Aktionen Start und Stopp aufrufen darf und wer die Schaltfläche des Steuerungs-Schreibtests drücken darf. Standard ist nur Administratoren: Ein gestoppter Wechselrichter bleibt gestoppt, bis ihn jemand startet. Benutzer bedeutet Benutzer, die dieses Gerät bereits ändern dürfen; Konten mit reinem Lesezugriff können das nie, und Automationen und Skripte sind nicht betroffen. Jede andere Einstellung ist eine Entität, und Home Assistant entscheidet, wer sie ändern darf: Mache ein Konto unter Einstellungen → Personen schreibgeschützt, um einer Person jede Änderung zu verwehren.

### `options.step.init.sections.permissions.data.start_stop`

> **EN** Start and stop the inverter

> **DE** Den Wechselrichter starten und stoppen

### `options.step.init.sections.permissions.data.control_test`

> **EN** Run the control write test

> **DE** Den Steuerungs-Schreibtest ausführen

### `options.step.init.sections.permissions.data_description.start_stop`

> **EN** Who may call the start and stop actions on this inverter.

> **DE** Wer die Aktionen Start und Stopp für diesen Wechselrichter aufrufen darf.

### `options.step.init.sections.permissions.data_description.control_test`

> **EN** Administrators only by default. The control write test changes settings on the inverter and puts them back, and — where you have allowed it above — stops and restarts it. Opening it to users means users who can already change this device; a read-only login still cannot.

> **DE** Standardmäßig nur Administratoren. Der Steuerungs-Schreibtest ändert Einstellungen am Wechselrichter und setzt sie zurück und – wo du es oben erlaubt hast – stoppt und startet ihn neu. Ihn für Benutzer zu öffnen bedeutet Benutzer, die dieses Gerät bereits ändern dürfen; ein Konto mit reinem Lesezugriff kann es weiterhin nicht.

### `options.step.init.sections.external.name`

> **EN** Another inverter on the same supply

> **DE** Ein weiterer Wechselrichter an derselben Einspeisung

### `options.step.init.sections.external.description`

> **EN** This inverter works out your house load from its own production and its grid meter, so a second, non-Sungrow inverter makes the load read low by exactly what it makes. {reported_load} Pick the entities that report the other inverter's power, and two corrected sensors are added. For energy in kWh, add it as a solar source on the Energy dashboard instead. A source that reports unavailable overnight makes the corrected sensors unknown overnight too, rather than assuming zero.

> **DE** Dieser Wechselrichter ermittelt deine Hauslast aus seiner eigenen Erzeugung und seinem Netzzähler, ein zweiter Wechselrichter, der kein Sungrow ist, lässt die Last daher um genau dessen Erzeugung zu niedrig erscheinen. {reported_load} Wähle die Entitäten, die die Leistung des anderen Wechselrichters melden, dann werden zwei korrigierte Sensoren hinzugefügt. Für Energie in kWh füge ihn stattdessen als Solarquelle im Energie-Dashboard hinzu. Eine Quelle, die über Nacht „nicht verfügbar“ meldet, macht die korrigierten Sensoren über Nacht ebenfalls unbekannt, statt Null anzunehmen.

### `options.step.init.sections.external.data.external_sources`

> **EN** Power sensors for the other generation

> **DE** Leistungssensoren für die andere Erzeugung

### `options.step.init.sections.external.data.external_placement`

> **EN** Where it is connected

> **DE** Wo er angeschlossen ist

### `options.step.init.sections.external.data_description.external_sources`

> **EN** Only power sensors are listed. Pick every one that reports generation this Sungrow cannot see; leave empty to switch the correction off.

> **DE** Nur Leistungssensoren werden aufgelistet. Wähle jeden, der Erzeugung meldet, die dieser Sungrow nicht sehen kann; leer lassen, um die Korrektur auszuschalten.

### `options.step.init.sections.external.data_description.external_placement`

> **EN** This changes the arithmetic, so it is asked rather than guessed.

> **DE** Das ändert die Rechnung, daher wird gefragt statt geraten.

### `options.step.init.sections.advanced.name`

> **EN** Battery, wallbox and diagnostics

> **DE** Batterie, Wallbox und Diagnose

### `options.step.init.sections.advanced.description`

> **EN** Battery charge power: {battery_status} Leave it at 0 to let the integration work it out. Otherwise take your datasheet's recommended charge current times the low end of the voltage range, not the nominal voltage (25 A at 355 V is about 8875 W), and round down. Download diagnostics on the device page describes this setup, with the serial number and address removed.

> **DE** Batterie-Ladeleistung: {battery_status} Auf 0 lassen, damit die Integration sie selbst ermittelt. Andernfalls nimm den vom Datenblatt empfohlenen Ladestrom mal das untere Ende des Spannungsbereichs, nicht die Nennspannung (25 A bei 355 V sind etwa 8875 W), und runde ab. Diagnose herunterladen auf der Geräteseite beschreibt diese Einrichtung, ohne Seriennummer und Adresse.

### `options.step.init.sections.advanced.data.battery_max_power`

> **EN** Maximum battery charge power (W)

> **DE** Maximale Batterie-Ladeleistung (W)

### `options.step.init.sections.advanced.data.register_dump`

> **EN** Include a raw register dump in diagnostics

> **DE** Rohen Registerauszug in die Diagnose aufnehmen

### `options.step.init.sections.advanced.data.wallbox_host`

> **EN** Wallbox address, when it is on the network itself

> **DE** Wallbox-Adresse, wenn sie selbst im Netzwerk ist

### `options.step.init.sections.advanced.data_description.battery_max_power`

> **EN** 0 means work it out: a Sungrow pack is identified from the capacity it reports and looked up against its datasheet, and any other pack that reports a BMS charge current gets that instead. Set a value to override either.

> **DE** 0 heißt selbst ermitteln: Ein Sungrow-Pack wird anhand der gemeldeten Kapazität erkannt und im Datenblatt nachgeschlagen, und jeder andere Pack, der einen BMS-Ladestrom meldet, bekommt stattdessen diesen. Setze einen Wert, um beides zu überschreiben.

### `options.step.init.sections.advanced.data_description.register_dump`

> **EN** Adds every mapped register's raw value. Only useful when a value looks wrong and the decoding itself is in question. Producing it is a second full read of the register map on top of normal polling, which is slow over a WiNet-S dongle, so leave it off unless you have been asked for it.

> **DE** Fügt den Rohwert jedes abgebildeten Registers hinzu. Nur nützlich, wenn ein Wert falsch aussieht und die Dekodierung selbst in Frage steht. Ihn zu erzeugen ist ein zweiter vollständiger Lesedurchlauf der Registerkarte zusätzlich zur normalen Abfrage, was über einen WiNet-S-Dongle langsam ist, lass es also aus, außer jemand hat danach gefragt.

### `options.step.init.sections.advanced.data_description.wallbox_host`

> **EN** Only for a Sungrow wallbox with a network cable or WiFi of its own. Without this, the integration finds a wallbox behind a WiNet-S by itself, and that is all most installations need. With it, the wallbox is read at its own address instead -- encrypted, on port 516 -- which also works when this entry is on the inverter's own LAN port, where a wallbox cannot otherwise be seen. Its entities and their history stay as they are. Leave empty to go back to the WiNet-S.

> **DE** Nur für eine Sungrow-Wallbox mit eigenem Netzwerkkabel oder WLAN. Ohne dies findet die Integration eine Wallbox hinter einem WiNet-S selbst, und das ist alles, was die meisten Installationen brauchen. Mit dieser Angabe wird die Wallbox stattdessen an ihrer eigenen Adresse gelesen – verschlüsselt, auf Port 516 –, was auch funktioniert, wenn dieser Eintrag am eigenen LAN-Port des Wechselrichters hängt, wo eine Wallbox sonst nicht zu sehen ist. Ihre Entitäten und deren Verlauf bleiben, wie sie sind. Leer lassen, um zum WiNet-S zurückzukehren.

### `options.step.init.sections.survey.name`

> **EN** Contribute a capability survey

> **DE** Eine Funktionsdiagnose beisteuern

### `options.step.init.sections.survey.description`

> **EN** Which registers an inverter answers is measured, not looked up, and a reading from yours is what improves support for it. {measured} Everything below is optional and answers what no register can; an empty field records that the question was not answered. Saving keeps your answers. To run the survey, press Run read only diagnosis on the device page: it reads and never writes, and replaces the serial number with a stand-in.

> **DE** Welche Register ein Wechselrichter beantwortet, wird gemessen, nicht nachgeschlagen, und eine Messung von deinem verbessert die Unterstützung dafür. {measured} Alles unten ist optional und beantwortet, was kein Register kann; ein leeres Feld hält fest, dass die Frage nicht beantwortet wurde. Speichern behält deine Antworten. Um die Diagnose auszuführen, drücke auf der Geräteseite Diagnose ausführen (nur lesend): Sie liest und schreibt nie und ersetzt die Seriennummer durch einen Platzhalter.

### `options.step.init.sections.survey.data.reporter`

> **EN** Your name or handle

> **DE** Dein Name oder Pseudonym

### `options.step.init.sections.survey.data.survey_transport`

> **EN** How this inverter is connected

> **DE** Wie dieser Wechselrichter angebunden ist

### `options.step.init.sections.survey.data.survey_proxy`

> **EN** Is a Modbus proxy in the path?

> **DE** Befindet sich ein Modbus-Proxy im Pfad?

### `options.step.init.sections.survey.data.survey_pollers`

> **EN** Anything else polling this inverter?

> **DE** Fragt noch etwas anderes diesen Wechselrichter ab?

### `options.step.init.sections.survey.data.survey_other_inverter`

> **EN** Is there another inverter here that is not a Sungrow?

> **DE** Gibt es hier einen weiteren Wechselrichter, der kein Sungrow ist?

### `options.step.init.sections.survey.data.survey_battery`

> **EN** Battery make and model

> **DE** Hersteller und Modell der Batterie

### `options.step.init.sections.survey.data.survey_comment`

> **EN** Anything else worth knowing

> **DE** Sonst noch etwas Wissenswertes

### `options.step.init.sections.survey.data.publish_address`

> **EN** May the last two octets of the address be published?

> **DE** Dürfen die letzten zwei Oktette der Adresse veröffentlicht werden?

### `options.step.init.sections.survey.data.survey_register_dump`

> **EN** Also sweep the raw register bands (about five minutes)

> **DE** Auch die rohen Registerbereiche durchsuchen (etwa fünf Minuten)

### `options.step.init.sections.survey.data_description.reporter`

> **EN** Credited in the published reading, and who gets asked if a row raises a question. Leave empty to contribute anonymously.

> **DE** Wird in der veröffentlichten Messung genannt und gefragt, wenn eine Zeile Fragen aufwirft. Leer lassen, um anonym beizutragen.

### `options.step.init.sections.survey.data_description.survey_transport`

> **EN** Cable against dongle is measured already. What only you know is whether a dongle is on its Ethernet socket or its WiFi — a WiNet-S answers identically either way, so "not sure" is a real answer and better than a guess.

> **DE** Kabel gegenüber Dongle ist bereits gemessen. Nur du weißt, ob ein Dongle an seiner Ethernet-Buchse oder per WLAN hängt – ein WiNet-S antwortet in beiden Fällen gleich, daher ist "nicht sicher" eine echte Antwort und besser als eine Vermutung.

### `options.step.init.sections.survey.data_description.survey_proxy`

> **EN** modbus-proxy, evcc's proxy, a Home Assistant add-on. A proxy holds one connection and lends it out, so it changes what a dropped register means — and it rebuilds every frame, which can hide or create the frame quirks this project tracks.

> **DE** modbus-proxy, der Proxy von evcc, ein Home-Assistant-Add-on. Ein Proxy hält eine Verbindung und verleiht sie weiter, was die Bedeutung eines ausgefallenen Registers verändert – und er baut jeden Frame neu auf, was die Frame-Eigenheiten, die dieses Projekt verfolgt, verbergen oder erzeugen kann.

### `options.step.init.sections.survey.data_description.survey_pollers`

> **EN** This Home Assistant is recorded automatically. What matters here is anything else: another Home Assistant, the YAML package, evcc, a logger. An inverter grants very few connections, and two clients competing for one looks exactly like a broken register.

> **DE** Dieses Home Assistant wird automatisch erfasst. Wichtig ist hier alles andere: ein anderes Home Assistant, das YAML-Paket, evcc, ein Logger. Ein Wechselrichter gewährt sehr wenige Verbindungen, und zwei Clients, die um eine konkurrieren, sehen genau wie ein defektes Register aus.

### `options.step.init.sections.survey.data_description.survey_other_inverter`

> **EN** Your Sungrow does not measure how much your house is using — it works it out from its own output plus what the grid meter says is coming in. A second inverter feeding the same meter therefore makes every load figure too low, by exactly what that inverter is producing, while everything else reads normally. No register can tell us: the Sungrow cannot see it. Say yes and we will ask what it is.

> **DE** Dein Sungrow misst nicht, wie viel dein Haus verbraucht – er errechnet es aus seiner eigenen Leistung plus dem, was der Netzzähler als Bezug meldet. Ein zweiter Wechselrichter am selben Zähler macht daher jeden Lastwert um genau dessen Erzeugung zu niedrig, während alles andere normal aussieht. Kein Register kann uns das sagen: Der Sungrow sieht ihn nicht. Antworte mit Ja, dann fragen wir, was es ist.

### `options.step.init.sections.survey.data_description.survey_battery`

> **EN** No register reports it. "SBR096" or "Pylontech Force H1, 14.4 kWh" is more useful than a capacity the inverter already reports.

> **DE** Kein Register meldet das. "SBR096" oder "Pylontech Force H1, 14,4 kWh" ist nützlicher als eine Kapazität, die der Wechselrichter ohnehin meldet.

### `options.step.init.sections.survey.data_description.survey_comment`

> **EN** Anything unusual about the installation — a cluster, a second inverter, a wallbox, a firmware update you remember.

> **DE** Alles Ungewöhnliche an der Anlage – ein Verbund, ein zweiter Wechselrichter, eine Wallbox, ein Firmware-Update, an das du dich erinnerst.

### `options.step.init.sections.survey.data_description.publish_address`

> **EN** On, and yours to turn off before you submit. Only the last two octets ever reach the document — never the third, which is what would identify your network — and clear this and it reads xxx.xxx instead. What it buys is telling several readings from one house apart: a master, a slave and two dongles otherwise produce four files that look alike.

> **DE** An, und du kannst es vor dem Absenden ausschalten. Nur die letzten zwei Oktette gelangen je in das Dokument – nie das dritte, das dein Netzwerk identifizieren würde –, und wenn du das deaktivierst, steht stattdessen xxx.xxx. Der Nutzen: Mehrere Messungen aus einem Haus lassen sich unterscheiden – ein Master, ein Slave und zwei Dongles ergeben sonst vier gleich aussehende Dateien.

### `options.step.init.sections.survey.data_description.survey_register_dump`

> **EN** On, and worth turning off if you are in a hurry. Without it a survey reads the registers this integration already knows about and takes a couple of seconds. With it, it also sweeps 2181 addresses across sixteen bands, including the ones no specification documents — which is how every undocumented register this project knows was found. That is slow because an address with nothing behind it goes quiet rather than refusing, so each empty one costs a full timeout: about five minutes on a direct cable, and considerably longer through a WiNet-S or a VPN. Your inverter keeps being polled throughout, and the survey button on the device page shows how far along it is.

> **DE** An, und besser auszuschalten, wenn du es eilig hast. Ohne sie liest die Diagnose die Register, die diese Integration bereits kennt, und braucht ein paar Sekunden. Mit ihr durchsucht sie zusätzlich 2181 Adressen in sechzehn Bereichen, auch die, die keine Spezifikation dokumentiert – so wurde jedes undokumentierte Register gefunden, das dieses Projekt kennt. Das ist langsam, weil eine Adresse ohne Inhalt verstummt statt abzulehnen, sodass jede leere ein volles Timeout kostet: etwa fünf Minuten am direkten Kabel und deutlich länger über ein WiNet-S oder ein VPN. Dein Wechselrichter wird die ganze Zeit weiter abgefragt, und die Diagnose-Schaltfläche auf der Geräteseite zeigt den Fortschritt.

### `options.step.init.sections.control_test.name`

> **EN** What the control write test may do

> **DE** Was der Steuerungs-Schreibtest darf

### `options.step.init.sections.control_test.description`

> **EN** Run complete diagnosis and tests on the device page writes each setting, reads it straight back against Sungrow's specification and puts your value back: the only way to catch a value written at ten times what you asked. Anything that could not be put back becomes a repair that restores it. The five switches below go further, and each is on until you switch it off: pressing the button is your consent. What you switch off stays off.

> **DE** Vollständige Diagnose und Tests ausführen auf der Geräteseite schreibt jede Einstellung, liest sie sofort gegen Sungrows Spezifikation zurück und setzt deinen Wert wieder ein: die einzige Möglichkeit, einen Wert zu finden, der mit dem Zehnfachen des Gewünschten geschrieben wurde. Alles, was nicht zurückgesetzt werden konnte, wird zu einer Reparatur, die es wiederherstellt. Die fünf Schalter unten gehen weiter, und jeder ist an, bis du ihn ausschaltest: Das Drücken der Schaltfläche ist deine Zustimmung. Was du ausschaltest, bleibt aus.

### `options.step.init.sections.control_test.data.control_test_restart`

> **EN** May it stop and restart the inverter?

> **DE** Darf er den Wechselrichter stoppen und neu starten?

### `options.step.init.sections.control_test.data.control_test_export_limit`

> **EN** May it switch feed-in limitation on?

> **DE** Darf er die Einspeisebegrenzung einschalten?

### `options.step.init.sections.control_test.data.control_test_pv_cut`

> **EN** May it cut PV generation for about a minute?

> **DE** Darf er die PV-Erzeugung für etwa eine Minute abschalten?

### `options.step.init.sections.control_test.data.control_test_charge_window`

> **EN** May it set a forced-charging window around now?

> **DE** Darf er ein Zwangslade-Fenster um jetzt herum setzen?

### `options.step.init.sections.control_test.data.control_test_discharge_window`

> **EN** May it move the discharge windows away from now?

> **DE** Darf er die Entladefenster von jetzt weg verschieben?

### `options.step.init.sections.control_test.data_description.control_test_restart`

> **EN** On unless you switch it off. With this on, the test writes the stop register, waits for the inverter to report itself stopped, starts it again and times all three transitions, so each model's figures are on record.
>
> While it is stopped you generate nothing, the battery neither charges nor discharges, and anything on a backup circuit loses power. Measured so far: stopped within about 2 seconds, running again after 3 to 4 minutes in daylight and over 6 at night, generating up to 20 seconds later. The inverter is never left stopped: the start is retried on fresh connections, it is started again if Home Assistant shuts down mid-test, and if all of that fails you get a repair that starts it.

> **DE** An, sofern du es nicht ausschaltest. Mit dieser Einstellung schreibt der Test das Stoppregister, wartet, bis sich der Wechselrichter als gestoppt meldet, startet ihn wieder und misst alle drei Übergänge, damit die Zahlen jedes Modells festgehalten sind.
>
> Während er gestoppt ist, erzeugst du nichts, die Batterie lädt und entlädt nicht, und alles am Backup-Ausgang verliert die Versorgung. Bisher gemessen: gestoppt nach etwa 2 Sekunden, wieder in Betrieb nach 3 bis 4 Minuten bei Tageslicht und über 6 nachts, Erzeugung bis zu 20 Sekunden später. Der Wechselrichter bleibt nie gestoppt: Der Start wird über frische Verbindungen wiederholt, er wird erneut gestartet, wenn Home Assistant mitten im Test herunterfährt, und schlägt all das fehl, bekommst du eine Reparatur, die ihn startet.

### `options.step.init.sections.control_test.data_description.control_test_export_limit`

> **EN** On unless you switch it off. Where you already limit feed-in, the test uses that and this changes nothing. With this on it may also switch the limit on for about a minute where you do not.
>
> It is the one setting whose failed restore costs you something ongoing rather than just accuracy: an export limit that did not get switched back means you feed in less than you could. If that happens you get a repair here that switches it back.

> **DE** An, sofern du es nicht ausschaltest. Wo du die Einspeisung bereits begrenzt, nutzt der Test diese Begrenzung und das ändert nichts. Mit dieser Einstellung darf er die Begrenzung dort, wo du keine hast, für etwa eine Minute einschalten.
>
> Es ist die eine Einstellung, deren fehlgeschlagene Wiederherstellung dich etwas Dauerhaftes kostet statt nur Genauigkeit: Eine nicht zurückgeschaltete Einspeisebegrenzung heißt, du speist weniger ein, als du könntest. Passiert das, bekommst du hier eine Reparatur, die sie zurückschaltet.

### `options.step.init.sections.control_test.data_description.control_test_pv_cut`

> **EN** On unless you switch it off. With this on, and where your inverter answers register 31211, the test writes the code that stops PV generation, checks that DC power falls to zero, and allows PV again. Generation stops for about half a minute and takes up to a minute more to come back while the inverter searches for its operating point again; the battery and the grid cover the house meanwhile.
>
> This register is not in Sungrow's documentation, which is why the **Cut PV generation** switch is offered only on firmware where this check has passed. A run on yours is how your firmware gets on that list.

> **DE** An, sofern du es nicht ausschaltest. Mit dieser Einstellung und wo dein Wechselrichter Register 31211 beantwortet, schreibt der Test den Code, der die PV-Erzeugung stoppt, prüft, dass die DC-Leistung auf null fällt, und erlaubt PV wieder. Die Erzeugung stoppt für etwa eine halbe Minute und braucht bis zu eine Minute mehr, um zurückzukommen, während der Wechselrichter seinen Arbeitspunkt neu sucht; Batterie und Netz versorgen das Haus in der Zwischenzeit.
>
> Dieses Register steht nicht in Sungrows Dokumentation, weshalb der Schalter **PV-Erzeugung abschalten** nur für Firmware angeboten wird, auf der diese Prüfung bestanden wurde. Ein Lauf auf deiner ist der Weg, wie deine Firmware auf diese Liste kommt.

### `options.step.init.sections.control_test.data_description.control_test_charge_window`

> **EN** On unless you switch it off. With this on, and where your inverter has the forced-charging schedule and it is off, the test writes a window around the inverter's own clock with a target a few percent above the battery, switches the schedule on, checks that the battery starts charging, and switches it off again. The battery charges for a minute or two, from the grid if there is no sun. Every word of the schedule is put back afterwards. Skipped where your own schedule is on.

> **DE** An, sofern du es nicht ausschaltest. Mit dieser Einstellung und wo dein Wechselrichter den Zwangslade-Zeitplan hat und dieser aus ist, schreibt der Test ein Fenster um die eigene Uhr des Wechselrichters mit einem Ziel einige Prozent über der Batterie, schaltet den Zeitplan ein, prüft, dass die Batterie zu laden beginnt, und schaltet ihn wieder aus. Die Batterie lädt ein bis zwei Minuten, aus dem Netz, wenn keine Sonne scheint. Jedes Wort des Zeitplans wird danach zurückgesetzt. Übersprungen, wo dein eigener Zeitplan an ist.

### `options.step.init.sections.control_test.data_description.control_test_discharge_window`

> **EN** On unless you switch it off. With this on, and where your inverter answers the discharge schedules (registers 33151-33187), the test moves every weekday and weekend discharge window away from now, checks that the battery stops discharging, and puts every window back. For a minute or two the house imports instead of using the battery.
>
> These registers are not in Sungrow's documentation, which is why they are offered only as readings. A run on yours is the evidence that writing them does what it should.

> **DE** An, sofern du es nicht ausschaltest. Mit dieser Einstellung und wo dein Wechselrichter die Entladezeitpläne beantwortet (Register 33151–33187), verschiebt der Test jedes Entladefenster an Werktagen und am Wochenende von jetzt weg, prüft, dass die Batterie nicht mehr entlädt, und setzt jedes Fenster zurück. Ein bis zwei Minuten bezieht das Haus Strom, statt die Batterie zu nutzen.
>
> Diese Register stehen nicht in Sungrows Dokumentation, weshalb sie nur als Messwerte angeboten werden. Ein Lauf auf deiner ist der Beleg, dass Schreiben darauf tut, was es soll.

### `options.step.promote.title`

> **EN** Set up the devices

> **DE** Die Geräte einrichten

### `options.step.promote.description`

> **EN** Home Assistant found **{count} entities** from the `modbus_sungrow.yaml` package, such as `{example}`. Your recorder history, your statistics and every dashboard card are stored against those entity IDs.
>
> {status}
>
> **Migrate my existing entities** takes those IDs over. History and statistics carry on uninterrupted and your dashboards keep working unchanged. Nothing is copied and nothing is deleted.
>
> **Start fresh** gives this inverter its own IDs, such as `sensor.sh10rt_total_pv_input_power`. Your old history stays where it is, under the old IDs, and your dashboards keep pointing at it.
>
> Either way the entities are identical in every other respect.

> **DE** Home Assistant hat **{count} Entitäten** aus dem Paket `modbus_sungrow.yaml` gefunden, zum Beispiel `{example}`. Dein Recorder-Verlauf, deine Statistiken und jede Dashboard-Karte sind an diese Entitäts-IDs gebunden.
>
> {status}
>
> **Bestehende Entitäten übernehmen** übernimmt diese IDs. Verlauf und Statistiken laufen ohne Unterbrechung weiter und deine Dashboards funktionieren unverändert. Es wird nichts kopiert und nichts gelöscht.
>
> **Neu beginnen** gibt diesem Wechselrichter eigene IDs, zum Beispiel `sensor.sh10rt_total_pv_input_power`. Dein alter Verlauf bleibt unter den alten IDs, wo er ist, und deine Dashboards zeigen weiterhin darauf.
>
> In jeder anderen Hinsicht sind die Entitäten in beiden Fällen identisch.

### `options.step.promote.data.entity_ids`

> **EN** Entity IDs

> **DE** Entitäts-IDs

### `options.step.promote.data_description.entity_ids`

> **EN** This can be changed later without losing anything.

> **DE** Das lässt sich später ändern, ohne dass etwas verloren geht.

### `options.step.slot_unknown.title`

> **EN** Set up the devices

> **DE** Die Geräte einrichten

### `options.step.slot_unknown.description`

> **EN** This house ran the YAML package for more than one inverter, and Home Assistant cannot tell which of them this one was. The package's serial sensors are what say so, and neither the running package nor the recorded history has this inverter's serial.
>
> So the YAML package's entity IDs are not offered: taking the wrong set would give this inverter another inverter's history. **Submit** sets it up with its own IDs, such as `sensor.sh10rt_total_pv_input_power`.
>
> To keep its old IDs, put the YAML package back for one restart, so this inverter's serial is recorded, then remove it and restart again. **Configure** can then switch this inverter to its old IDs; the serial stays on record for the recorder's retention, ten days unless you changed it.

> **DE** In diesem Haus lief das YAML-Paket für mehr als einen Wechselrichter, und Home Assistant kann nicht erkennen, welcher davon dieser war. Das sagen die Seriennummer-Sensoren des Pakets, und weder das laufende Paket noch der aufgezeichnete Verlauf kennt die Seriennummer dieses Wechselrichters.
>
> Deshalb werden die Entitäts-IDs des YAML-Pakets nicht angeboten: Mit dem falschen Satz bekäme dieser Wechselrichter den Verlauf eines anderen. **Absenden** richtet ihn mit eigenen IDs ein, zum Beispiel `sensor.sh10rt_total_pv_input_power`.
>
> Um die alten IDs zu behalten, aktiviere das YAML-Paket für einen Neustart wieder, damit die Seriennummer dieses Wechselrichters aufgezeichnet wird, entferne es dann und starte erneut. Mit **Konfigurieren** lässt sich dieser Wechselrichter danach auf seine alten IDs umstellen; die Seriennummer bleibt für die Aufbewahrungsdauer des Recorders gespeichert, zehn Tage, sofern du sie nicht geändert hast.

### `options.step.other_inverter.title`

> **EN** What is the other inverter?

> **DE** Welcher ist der andere Wechselrichter?

### `options.step.other_inverter.description`

> **EN** The make, and its size if you know it — *Fronius Symo 8.2*, or *5 kW string inverter on the south roof*. The size is the useful part: it says how large the gap in the load figures is.
>
> This goes into the document, so leave out serial numbers, addresses and names. You can leave it blank.

> **DE** Der Hersteller und, falls bekannt, die Größe – *Fronius Symo 8.2* oder *5-kW-String-Wechselrichter auf dem Süddach*. Die Größe ist der nützliche Teil: Sie sagt, wie groß die Lücke in den Lastwerten ist.
>
> Das gelangt in das Dokument, lass deshalb Seriennummern, Adressen und Namen weg. Du kannst es leer lassen.

### `options.step.other_inverter.data.survey_other_inverter_detail`

> **EN** The other inverter

> **DE** Der andere Wechselrichter

### `options.step.entity_ids_legacy.title`

> **EN** Move to the YAML package's entity IDs

> **DE** Zu den Entitäts-IDs des YAML-Pakets wechseln

### `options.step.entity_ids_legacy.description`

> **EN** The entities take the IDs `modbus_sungrow.yaml` gave them, such as `sensor.total_dc_power` — the IDs existing dashboards and years of history are stored against.
>
> {changes}{status}
>
> Nothing is copied and nothing is deleted. Names, areas and other settings you gave the entities stay with them. Dashboards, automations and scripts that use the old IDs are not rewritten, so check them afterwards.

> **DE** Die Entitäten erhalten die IDs, die `modbus_sungrow.yaml` ihnen gab, etwa `sensor.total_dc_power` – die IDs, an die bestehende Dashboards und jahrelanger Verlauf gebunden sind.
>
> {changes}{status}
>
> Es wird nichts kopiert und nichts gelöscht. Namen, Bereiche und andere Einstellungen, die du den Entitäten gegeben hast, bleiben bei ihnen. Dashboards, Automationen und Skripte, die die alten IDs verwenden, werden nicht umgeschrieben, prüfe sie also danach.

### `options.step.entity_ids_modern.title`

> **EN** Move to device-scoped entity IDs

> **DE** Zu gerätebezogenen Entitäts-IDs wechseln

### `options.step.entity_ids_modern.description`

> **EN** The entities take IDs named after this device, such as `sensor.sh10rt_total_pv_input_power`. Their history and statistics move with them.
>
> {changes}{status}
>
> Nothing is copied and nothing is deleted. Names, areas and other settings you gave the entities stay with them. Dashboards, automations and scripts that use the old IDs are not rewritten, so check them afterwards.
>
> You can move back here at any time.

> **DE** Die Entitäten erhalten IDs, die nach diesem Gerät benannt sind, etwa `sensor.sh10rt_total_pv_input_power`. Ihr Verlauf und ihre Statistiken ziehen mit.
>
> {changes}{status}
>
> Es wird nichts kopiert und nichts gelöscht. Namen, Bereiche und andere Einstellungen, die du den Entitäten gegeben hast, bleiben bei ihnen. Dashboards, Automationen und Skripte, die die alten IDs verwenden, werden nicht umgeschrieben, prüfe sie also danach.
>
> Du kannst jederzeit hierher zurückwechseln.

### `options.error.nothing_left_to_poll`

> **EN** Every group is set to never, which would leave the integration with nothing to read and no entities at all. Leave at least one group with an interval.

> **DE** Jede Gruppe steht auf „nie“, was der Integration nichts zu lesen und überhaupt keine Entitäten ließe. Lass mindestens eine Gruppe mit einem Intervall.

### `options.error.wallbox_not_found`

> **EN** No Sungrow wallbox answered at that address. It has to be the wallbox's own address (not the inverter's or the WiNet-S's), reachable from Home Assistant, and not busy with another client.

> **DE** Unter dieser Adresse hat keine Sungrow-Wallbox geantwortet. Es muss die eigene Adresse der Wallbox sein (nicht die des Wechselrichters oder des WiNet-S), von Home Assistant erreichbar und nicht von einem anderen Client belegt.

### `options.error.legacy_package_still_loaded`

> **EN** The YAML package is still running, so its entities still hold their IDs. Remove `modbus_sungrow.yaml` from your configuration, restart Home Assistant and try again.

> **DE** Das YAML-Paket läuft noch, daher belegen seine Entitäten weiterhin ihre IDs. Entferne `modbus_sungrow.yaml` aus deiner Konfiguration, starte Home Assistant neu und versuche es erneut.

### `options.error.legacy_slot_unknown`

> **EN** This house ran the YAML package for more than one inverter, and Home Assistant cannot tell which of them this one was, so the old IDs could be another inverter's. Put the YAML package back for one restart, so this inverter's serial is recorded, then remove it, restart again and come back here.

> **DE** In diesem Haus lief das YAML-Paket für mehr als einen Wechselrichter, und Home Assistant kann nicht erkennen, welcher davon dieser war, die alten IDs könnten also die eines anderen Wechselrichters sein. Aktiviere das YAML-Paket für einen Neustart wieder, damit die Seriennummer dieses Wechselrichters aufgezeichnet wird, entferne es dann, starte erneut und komm hierher zurück.

### `options.progress.running_survey`

> **EN** Reading your inverter: 19 capability probes. Through a WiNet-S this can take a minute.

> **DE** Dein Wechselrichter wird gelesen: 19 Funktionsprüfungen. Über ein WiNet-S kann das eine Minute dauern.

### `options.abort.devices_mode_not_offered`

> **EN** Setting up sensors and controls is not in this release. This alpha creates diagnostics-only entries; start again and choose **Perform the device survey**.

> **DE** Sensoren und Steuerungen einzurichten ist in dieser Version nicht enthalten. Diese Alpha legt nur Einträge für die Diagnose an; beginne erneut und wähle **Geräte-Diagnose durchführen**.


## Actions (16)

### `services.run_control_test.name`

> **EN** Run complete diagnosis and tests

> **DE** Vollständige Diagnose und Tests ausführen

### `services.run_control_test.description`

> **EN** Writes to every control this integration can write to, checks each one three ways and puts it back. Unlike the capability survey, this CHANGES SETTINGS on the inverter: it limits the battery and the export, and it briefly forces a charge and a discharge. Everything is recorded before the first write and restored afterwards, and the run reports anything it could not put back. It exists because a wrong scale is invisible to a readback -- write 700 W, get 700 W back -- and only writing can find it. The restart and export-limit permissions are set in the integration's options and are off by default.

> **DE** Schreibt in jede Steuerung, in die diese Integration schreiben kann, prüft jede auf drei Arten und setzt sie zurück. Anders als die Diagnose ÄNDERT dies EINSTELLUNGEN am Wechselrichter: Es begrenzt die Batterie und die Einspeisung und erzwingt kurz ein Laden und ein Entladen. Alles wird vor dem ersten Schreiben festgehalten und danach wiederhergestellt, und der Lauf meldet alles, was er nicht zurücksetzen konnte. Es gibt sie, weil ein falscher Skalierungsfaktor für ein Zurücklesen unsichtbar ist – 700 W schreiben, 700 W zurückbekommen – und nur Schreiben ihn finden kann. Die Berechtigungen für Neustart und Einspeisebegrenzung werden in den Optionen der Integration gesetzt und sind standardmäßig aus.

### `services.run_control_test.fields.device_id.name`

> **EN** Device

> **DE** Gerät

### `services.run_control_test.fields.device_id.description`

> **EN** The Sungrow device to write to, and put back.

> **DE** Das Sungrow-Gerät, in das geschrieben wird und das zurückgesetzt wird.

### `services.run_survey.name`

> **EN** Run read only diagnosis

> **DE** Diagnose ausführen (nur lesend)

### `services.run_survey.description`

> **EN** Reads this installation's registers and produces a document describing what answered, so support for it can be measured rather than guessed. Reads only; nothing is written to the inverter, and the serial number is replaced by a stand-in. The finished document arrives as a notification with a download link.

> **DE** Liest die Register dieser Installation und erzeugt ein Dokument, das beschreibt, was geantwortet hat, damit die Unterstützung dafür gemessen statt geraten werden kann. Nur Lesen; es wird nichts in den Wechselrichter geschrieben, und die Seriennummer wird durch einen Platzhalter ersetzt. Das fertige Dokument kommt als Benachrichtigung mit Download-Link.

### `services.run_survey.fields.device_id.name`

> **EN** Device

> **DE** Gerät

### `services.run_survey.fields.device_id.description`

> **EN** The Sungrow device to survey.

> **DE** Das Sungrow-Gerät, das diagnostiziert wird.

### `services.start_inverter.name`

> **EN** Start inverter

> **DE** Wechselrichter starten

### `services.start_inverter.description`

> **EN** Boots an inverter that has been shut down. Deliberately an action rather than a button: Home Assistant has no confirmation dialog for a button press, and admin rights are required to call this.

> **DE** Fährt einen heruntergefahrenen Wechselrichter hoch. Bewusst eine Aktion statt einer Schaltfläche: Home Assistant hat keinen Bestätigungsdialog für einen Tastendruck, und zum Aufruf sind Administratorrechte nötig.

### `services.start_inverter.fields.device_id.name`

> **EN** Inverter

> **DE** Wechselrichter

### `services.start_inverter.fields.device_id.description`

> **EN** Which inverter to start.

> **DE** Welcher Wechselrichter gestartet werden soll.

### `services.stop_inverter.name`

> **EN** Stop inverter

> **DE** Wechselrichter stoppen

### `services.stop_inverter.description`

> **EN** Shuts the inverter down. It stops generating, stops charging and stops discharging until it is started again. Deliberately an action rather than a button, and admin rights are required to call it — a dashboard card cannot do this by accident.

> **DE** Fährt den Wechselrichter herunter. Er hört auf zu erzeugen, zu laden und zu entladen, bis er wieder gestartet wird. Bewusst eine Aktion statt einer Schaltfläche, und zum Aufruf sind Administratorrechte nötig – eine Dashboard-Karte kann das nicht versehentlich tun.

### `services.stop_inverter.fields.device_id.name`

> **EN** Inverter

> **DE** Wechselrichter

### `services.stop_inverter.fields.device_id.description`

> **EN** Which inverter to stop.

> **DE** Welcher Wechselrichter gestoppt werden soll.


## Error messages (19)

### `exceptions.device_not_found.message`

> **EN** No device with ID {device_id} exists. If this call came from a script, the device may have been removed and re-added since it was written.

> **DE** Es gibt kein Gerät mit der ID {device_id}. Stammt dieser Aufruf aus einem Skript, wurde das Gerät möglicherweise seit dessen Erstellung entfernt und neu hinzugefügt.

### `exceptions.entry_not_loaded.message`

> **EN** {title} is not loaded, so it cannot be started or stopped. Check the integration page for a setup error.

> **DE** {title} ist nicht geladen und kann daher nicht gestartet oder gestoppt werden. Prüfe die Integrationsseite auf einen Einrichtungsfehler.

### `exceptions.not_a_sungrow_device.message`

> **EN** {name} is not a Sungrow Modbus device.

> **DE** {name} ist kein Sungrow-Modbus-Gerät.

### `exceptions.survey_already_running.message`

> **EN** A survey is already running on this inverter. Two at once would compete for one of its very few Modbus connections.

> **DE** Auf diesem Wechselrichter läuft bereits eine Diagnose. Zwei gleichzeitig würden um eine seiner sehr wenigen Modbus-Verbindungen konkurrieren.

### `exceptions.not_on_string_inverter.message`

> **EN** {title} is a string inverter. This action writes to a hybrid inverter's registers, and nothing in this integration writes to a string inverter.

> **DE** {title} ist ein String-Wechselrichter. Diese Aktion schreibt in die Register eines Hybrid-Wechselrichters, und nichts in dieser Integration schreibt in einen String-Wechselrichter.

### `exceptions.write_failed.message`

> **EN** Could not write {entity_id}: {error}

> **DE** {entity_id} konnte nicht geschrieben werden: {error}

### `exceptions.write_scale_unread.message`

> **EN** Could not write {entity_id}: could not read the export limit's bounds to work out this inverter's write scale: {error}

> **DE** {entity_id} konnte nicht geschrieben werden: Die Grenzen der Einspeisebegrenzung konnten nicht gelesen werden, um den Schreibfaktor dieses Wechselrichters zu ermitteln: {error}

### `exceptions.start_failed.message`

> **EN** Could not start {device}: {error}

> **DE** {device} konnte nicht gestartet werden: {error}

### `exceptions.stop_failed.message`

> **EN** Could not stop {device}: {error}

> **DE** {device} konnte nicht gestoppt werden: {error}

### `exceptions.setup_unreachable.message`

> **EN** Could not reach {title}: {error}. A Sungrow inverter accepts very few Modbus connections at once, so check whether something else is polling it -- the modbus_sungrow.yaml package, another Home Assistant, or another tool.

> **DE** {title} konnte nicht erreicht werden: {error}. Ein Sungrow-Wechselrichter nimmt nur sehr wenige Modbus-Verbindungen gleichzeitig an, prüfe daher, ob etwas anderes ihn abfragt – das Paket modbus_sungrow.yaml, ein anderes Home Assistant oder ein anderes Werkzeug.

### `exceptions.identity_unread.message`

> **EN** Could not read the identity of {title}: {error}

> **DE** Die Identität von {title} konnte nicht gelesen werden: {error}

### `exceptions.no_serial.message`

> **EN** {title} answered but reported no serial number, so its entities cannot be identified. Please open an issue with the model and firmware version.

> **DE** {title} hat geantwortet, aber keine Seriennummer gemeldet, daher können seine Entitäten nicht identifiziert werden. Bitte eröffne ein Issue mit Modell und Firmware-Version.

### `exceptions.firmware_unread.message`

> **EN** Could not read the firmware of {title}: {error}

> **DE** Die Firmware von {title} konnte nicht gelesen werden: {error}

### `exceptions.nothing_to_poll.message`

> **EN** Every poll tier of {title} is set to never, so there is nothing to read. Set at least one interval in the integration's options.

> **DE** Jede Abfragestufe von {title} steht auf „nie“, es gibt also nichts zu lesen. Setze in den Optionen der Integration mindestens ein Intervall.

### `exceptions.connection_lost.message`

> **EN** Lost the connection to the inverter: {error}. A Sungrow inverter accepts very few Modbus connections at once, so check whether something else is polling it -- the modbus_sungrow.yaml package, another Home Assistant, or another tool.

> **DE** Die Verbindung zum Wechselrichter ging verloren: {error}. Ein Sungrow-Wechselrichter nimmt nur sehr wenige Modbus-Verbindungen gleichzeitig an, prüfe daher, ob etwas anderes ihn abfragt – das Paket modbus_sungrow.yaml, ein anderes Home Assistant oder ein anderes Werkzeug.

### `exceptions.communication_error.message`

> **EN** Error communicating with the inverter: {error}

> **DE** Fehler bei der Kommunikation mit dem Wechselrichter: {error}

### `exceptions.no_block_answered.message`

> **EN** No register block answered

> **DE** Kein Registerblock hat geantwortet

### `exceptions.device_connection_lost.message`

> **EN** Lost the connection while reading the {device}: {error}

> **DE** Die Verbindung ging beim Lesen von {device} verloren: {error}

### `exceptions.device_read_error.message`

> **EN** Error reading the {device}: {error}

> **DE** Fehler beim Lesen von {device}: {error}
