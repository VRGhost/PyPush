# Raw Microbot characteristics

This document contains a library of microbot states collected from various devices.

Having this in a single place is useful for reverse engineering.


## Updated device imported from the USA

### BLE scan announce

#### Unpaired
```python
AdvancedSegment(type_code=255, type_name='BLE_GAP_AD_TYPE_MANUFACTURER_SPECIFIC_DATA', data='\x00\x00Push (e249)')
AdvancedSegment(type_code=9, type_name='BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME', data='mibp')
```

#### Paired
```python
AdvancedSegment(type_code=244, type_name=None, data="<last 4 digits of host's MAC>")
```


### State

#### Extended
Note: this device appears to be in inversed mode. Its arm is extended by default and touching the panel causes the arm to retract.
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

#### Retracted
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
        '2A11': '<',
        '2A12': '<',
        '2A15': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A18': '\x01',
        '2A35': '<',
        '2A53': '\x01',
        '2A77': '\x01'
    },
    '1831': {
        '2A13': '\x01',
        '2A14': '\x01\x06\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A19': 'b',
        '2A20': '\x00\x01',
        '2A21': '\x00\x01\x05',
        '2A87': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A90': '\x01\xfcI"\xa2\xff\x8b\xf8\xe2\xd5y\x1b\xfc\xdc\x9c\x1fT\x00\x00\x00',
        '2A97': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A98': '\x01\xcao\x06\xc3I\xe2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A99': '\x01'
    }
}
```

## Brand new device (from Amazon.co.uk), factory firmware

### BLE scan announce

#### Unpaired
```python
AdvancedSegment(type_code=1, type_name='BLE_GAP_AD_TYPE_FLAGS', data='\x06')
AdvancedSegment(type_code=3, type_name='BLE_GAP_AD_TYPE_16BIT_SERVICE_UUID_COMPLETE', data='\x0f\x18\n\x18')
AdvancedSegment(type_code=9, type_name='BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME', data='mib-push')
```

#### Paired
```python
AdvancedSegment(type_code=244, type_name=None, data="<last 4 digits of host's MAC>")
```

### State

#### Retracted pusher
```python
{
    '000015301212EFDE1523785FEABCD123': {
        '000015311212EFDE1523785FEABCD123': None,
        '000015321212EFDE1523785FEABCD123': None,
        '000015341212EFDE1523785FEABCD123': '\x01\x00'
    },
    '1800': {
        '2A00': 'mib-push',
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
        '2A12': '\x01',
        '2A16': '\x01',
        '2A35': 'd',
        '2A53': '\x00'
    },
    '1831': {
        '2A13': '\x01',
        '2A14': '\x01\x05\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A19': 'b',
        '2A20': '\x00\x01',
        '2A21': '\x00\x01\x00',
        '2A22': '\x00\x01',
        '2A87': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A90': '\x01\xe3\x12\xfc\xea\xe58\xbb\x1b{>EM\x1fzav\x00\x00\x00',
        '2A91': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A98': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A99': '\x01'
    }
}
```

#### Extended pusher
```python
{
    '000015301212EFDE1523785FEABCD123': {
        '000015311212EFDE1523785FEABCD123': None,
        '000015321212EFDE1523785FEABCD123': None,
        '000015341212EFDE1523785FEABCD123': '\x01\x00'
    },
    '1800': {
        '2A00': 'mib-push',
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
        '2A11': 'd',
        '2A12': 'd',
        '2A16': '\x01',
        '2A35': 'd',
        '2A53': '\x00'
    },
    '1831': {
        '2A13': '\x01',
        '2A14': '\x01\x05\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A19': 'b',
        '2A20': '\x00\x01',
        '2A21': '\x00\x01\x00',
        '2A22': '\x00\x01',
        '2A87': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A90': '\x01\xe3\x12\xfc\xea\xe58\xbb\x1b{>EM\x1fzav\x00\x00\x00',
        '2A91': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A98': '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        '2A99': '\x01'
    }
}

```