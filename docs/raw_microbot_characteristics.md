# Raw Microbot characteristics

This document contains a library of microbot states collected from various devices.

Having this in a single place is useful for reverse engineering.


## Updated device imported from the USA

### Notes
this device appears to be in inversed mode. Its arm is extended by default and touching the panel causes the arm to retract.

```python
{
    '000015301212EFDE1523785FEABCD123': {
        '000015311212EFDE1523785FEABCD123': None,
        '000015321212EFDE1523785FEABCD123': None,
        '000015341212EFDE1523785FEABCD123': '\x01\x00'
    },
    '1800': {
        '2A00': 'mibp',
        '2A01': '\x00\x00',
        '2A04': '@\x01\x08\x02\x00\x00\x90\x01'
    },
    '1801': {
        '2A05': None
    },
    '180A': {
        '2A29': 'Naran'
    },
    '1821': {
        '2A11': '\x01',
        '2A12': '<',
        '2A15': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A18': '\x01',
        '2A35': '<',
        '2A53': '\x01',
        '2A77': '\x01'
    },
    '1831': {
        '2A13': '\x1e',
        '2A14': '\x01\x05\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A19': 'b',
        '2A20': '\x00\x01',
        '2A21': '\x00\x01\x05',
        '2A87': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A90': '\x01[\xd6\xc3\x9f\n\xb1\xa5\x94_*\x7f{\xa4&P\x17\x00\x00\x00',
        '2A97': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A98': '\x01\xcao\x06\xc3I\xe2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A99': '\x01'
        }
    }
```

## Brand new device (from Amazon.co.uk)