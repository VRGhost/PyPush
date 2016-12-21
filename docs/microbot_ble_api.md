# Microbot Bluetooth api

This document contains registry/analisys of microbot services inferred from the [Raw Characteristics dumps](./raw_microbot_characteristics.md).
Everything in this document are my best current guesses for the low-level microbot APIs. I do not give any guarantees or claims of correctness of the content found below.

## Service `1800`

Suspected device metainformation service. Contains three known characteristics:
 *  `2A00` : device name
 *  `2A01` : unknown
 *  `2A04` : unknown

## Service `1801`

Known to contain only one characteristic (`2A05`). Role unknown as it is not readable.

## Service `180A`

Only one known characteristic: `2A29`. The characteristic contains name of the manufacturer `Naran` (either hardware or firmware or both).

## Service `1821`

Pusher status & control.

Known services:
 *  `2A11`: write `\x01` here to extend the pusher, meaning of read value unknown
 *  `2A12`: write `\x01` here to retract the pusher, meaning of the read value unknown
 *  `2A15`: pusher extension status, found in the firmware `0x0105`, not available in the fw `0x0100`
 *  `2A16`: role unknown, only known to exist in the firmware `0x0100`
 *  `2A18`: role unknown, only known to exist in the firmware `0x0105`
 *  `2A35`: suspected pusher mode. `d` for default, `<` for "extended by default"
 *  `2A53`: another suspect for the pusher mode (`\x01` for extended, `\x00` for default)
 *  `2A77`: only found in the `0x0105` firmware. Role unknown. Maybe toggle mode?

## Service `1831`

Misc utility functions.

Services:
 *  `2A13`: blinker control. Any value written into this causes the LED to blink for the number of seconds equal to the value written.
 *  `2A14`: low-level LED control. Write `0x01CxxxT` here (`x` = `0x00`, T=_seconds_, C= bitwise or for R/G/B [R=0x1, G=0x2, b=0x4]) to set colour of the LED to `C` for `T` seconds
 *  `2A19`: battery level, 0-100 scale
 *  `2A20`: unknown
 *  `2A21`: suspected firmware version
 *  `2A22`: present in the `0x01000` fw, removed in the `0x0105`. Role unknown
 *  `2A87`: unknown
 *  `2A90`: unknown, looks like a mirror of devices' internal state
 *  `2A91`: found in `0x0100`, removed in `0x0105`. unknown
 *  `2A97`: introduced in `0x0105`. unknown.
 *  `2A98`: unknown.
 *  `2A99`: unknown.


## Service `000015301212EFDE1523785FEABCD123`

This service contains three characteristics: `000015311212EFDE1523785FEABCD123` (from now on `11212`), `000015321212EFDE1523785FEABCD123` (from now on `21212`) and `000015341212EFDE1523785FEABCD123`( from now on `41212`). With only one (`41212`) being readable. 

Considering length of the service IDs this is suspected firmware upgrade hole (with `41212` probably telling the upgrade process state, ergo `'\x01\x00'` value representing "idle" state).