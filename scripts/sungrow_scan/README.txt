Sungrow device scan
===================

Thank you for helping. This reads your inverter and writes one small file
describing what it can do, so the Home Assistant integration can be made to
work with your setup rather than guessed at.


What to run
-----------

    python collect.py

That is all of it. Python 3.11 or newer, nothing to install. It will find
the inverter on your network, ask you a handful of questions, read for a
minute or two, and finish by printing which file to send back.

If `python` is not found, try `python3`. If it says the version is too old,
say so in the issue -- the floor is 3.11 today and is not there for a good
reason, so it can be lowered.

If you already know the address, save it the search:

    python collect.py 192.168.1.50


It only reads
-------------

No file in this directory can write to your inverter. The Modbus function
codes for writing -- 6 and 16 -- are not implemented anywhere in it; the two
that are, 3 and 4, are both reads. You are welcome to check: the reading
happens in portable.py, and every place it talks to the network is in the
first 250 lines.

It also never sends anything anywhere. Nothing here opens an internet
connection; the files it writes stay on your machine until you send one.


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
                               python collect.py 192.168.1.50
                               Port 502 is usual; a Logger uses 503.

  "this cannot run here"    -- the network you typed could not be read.

  a code of 3 or 4          -- it collected a report, but something about it
                               is uncertain and the run says which. Worth
                               sending anyway, with that line quoted.

Nothing here changes anything on your inverter, so re-running is always safe.


What is in this directory
-------------------------

  collect.py       the one thing to run: the whole survey, start to finish
  probe.py         the individual steps -- find, identify, read, dump
  blocks.py        the block read test: which grouped read a device refuses
  portable.py      the Modbus client and register decoder, standard library
                   only, which is why none of this needs installing
  scan_plan.json   which registers to read and how to decode them, generated
                   from the integration's own definitions

This directory is part of
https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant
and carries the same licence.
