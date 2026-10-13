Sungrow device survey
=====================

Thank you for helping. This reads your inverter and writes one small file
describing what it can do, so the Home Assistant integration can be made to
work with your setup rather than guessed at.


What to run
-----------

On Linux or a Mac, in a terminal in this folder:

    ./read_only_survey.sh

On Windows, double-click read_only_survey.cmd.

That is all of it. It will find the inverter on your network, ask you a
handful of questions, read for a minute or two, and finish by printing which
file to send back.

The survey needs Python and the integration's own Python library, `sungrow-modbus`.
The launcher gets both through uv (https://docs.astral.sh/uv/), which keeps
them in a cache of its own and changes nothing else on your machine. If uv is
not installed, the launcher says so and asks before installing it. Answer no
and it prints how to do it by hand instead.

If you already know the address, save it the search:

    ./read_only_survey.sh 192.168.1.50          (or: read_only_survey.cmd 192.168.1.50)


It only reads
-------------

No file in this directory can write to your inverter. They talk to it
through the library's read functions and nothing else; you are welcome to
check -- search these files for "write" and every hit is a file on your own
disk.

The survey never sends anything anywhere. The launcher goes to the internet
once, to fetch uv and the library the first time; after that the files the
survey writes stay on your machine until you send one.


What gets written, and what to send
-----------------------------------

Three files. The run tells you which is which, and so does this:

  <name>.json                       SEND THIS ONE
                                    Your inverter's capabilities. No serial
                                    number, no address beyond the last two
                                    numbers of it, and the date rather than
                                    the time.

  sungrow-scan-private/<name>.raw.json    KEEP THIS ONE
                                    The same reading with your real serial
                                    number, your address and the exact time.
                                    It is for you, in case a question comes
                                    up. Do not post it anywhere.

  sungrow-scan-<date>.log           KEEP THIS ONE
                                    Everything the run printed, addresses
                                    included. Useful to send *privately* if
                                    something went wrong.

If you would rather not publish even the last two numbers of your address,
answer "no" when it asks -- the file then says xxx.xxx and is still useful.


Before you run it
-----------------

Stop Home Assistant, or anything else polling the inverter, if you can. A
Sungrow inverter accepts very few Modbus connections at once, so a second
program reading at the same time makes registers look broken when they are
not. The scan asks about this and will carry on either way -- a reading from
a busy inverter is still worth having, it is just thinner.


If something goes wrong
-----------------------

The last line of the run says what happened and what it means. Common ones:

  "nothing was collected"   -- it found no inverter. Try giving the address:
                               ./read_only_survey.sh 192.168.1.50
                               Port 502 is usual; a Logger uses 503.

  "this cannot run here"    -- the network you typed could not be read.

  a code of 3 or 4          -- it collected a report, but something about it
                               is uncertain and the run says which. Worth
                               sending anyway, with that line quoted.

Nothing here changes anything on your inverter, so re-running is always safe.


What is in this directory
-------------------------

  read_only_survey.sh    the launcher on Linux and macOS
  read_only_survey.cmd   the launcher on Windows; read_only_survey.ps1 does
                         the work
  sungrow_survey.py      the survey itself, start to finish. Its header names
                         the library version it runs on
  probe.py               the individual steps -- find, identify, read, dump
  blocks.py              the block read test: which grouped read a device
                         refuses
  raw_client.py          a bare-socket Modbus client blocks.py can measure
                         with, because it reports what a stricter client
                         rejects

The control test, which writes to an inverter, is a separate folder,
scripts/sungrow_control_test/, and is never part of this one.

This directory is part of
https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant
and carries the same licence.
