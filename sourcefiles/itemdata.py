'''Module to Read and Write Items'''
from __future__ import annotations
import functools
import typing
from typing import Optional

import byteops
import ctenums
import ctrom
import ctstrings


WritableBytes = typing.Union[bytearray, memoryview]


class DataSizeException(Exception):
    '''Exception to raise when a data record's size is incorrect'''


class InvalidItemID(Exception):
    '''Exception to raise when an item's id does not match the desired type.'''


class ArmorEffects(ctenums.StrIntEnum):
    '''Enum of possible effects that can go on armor/helms.'''
    NONE = 0x00
    SHIELD = 0x17
    ABSORB_LIT_25 = 0x1A
    ABSORB_SHD_25 = 0x1B
    ABSORB_WAT_25 = 0x1C
    ABSORB_FIR_25 = 0x1D
    ABSORB_LIT_100 = 0x1F
    ABSORB_SHD_100 = 0x20
    ABSORB_WAT_100 = 0x21
    ABSORB_FIR_100 = 0x22
    IMMUNE_CHAOS = 0x2A
    IMMUNE_LOCK = 0x2B
    IMMUNE_SLOW_STOP = 0x2C
    IMMUNE_ALL = 0x2D
    BARRIER = 0x31
    CHAOS_HP_DOWN = 0x32
    HASTE = 0x33


_armor_status_abbrev_dict: dict[ArmorEffects, str] = {
    ArmorEffects.NONE: '',
    ArmorEffects.SHIELD: 'Shd',
    ArmorEffects.ABSORB_LIT_25: 'Ab:Li 25%',
    ArmorEffects.ABSORB_SHD_25: 'Ab:Sh 25%',
    ArmorEffects.ABSORB_WAT_25: 'Ab:Wa 25%',
    ArmorEffects.ABSORB_FIR_25: 'Ab:Fi 25%',
    ArmorEffects.ABSORB_LIT_100: 'Ab:Li 100%',
    ArmorEffects.ABSORB_SHD_100: 'Ab:Sh 100%',
    ArmorEffects.ABSORB_WAT_100: 'Ab:Wa 100%',
    ArmorEffects.ABSORB_FIR_100: 'Ab:Fi 100%',
    ArmorEffects.IMMUNE_CHAOS: 'P:Chaos',
    ArmorEffects.IMMUNE_LOCK: 'P:Lock',
    ArmorEffects.IMMUNE_SLOW_STOP: 'P:Sl/St',
    ArmorEffects.IMMUNE_ALL: 'P:All',
    ArmorEffects.BARRIER: 'Bar',
    ArmorEffects.CHAOS_HP_DOWN: 'Chaos/HP Dn',
    ArmorEffects.HASTE: 'Haste'
}


class WeaponEffects(ctenums.StrIntEnum):
    '''Enum of possible effects that can go on weapons.'''
    NONE = 0x00
    CRIT_X2 = 0x01
    WONDERSHOT = 0x02
    DMG_125 = 0x03
    DMG_150 = 0x04
    DMG_175 = 0x05
    DMG_200 = 0x06
    MAGIC = 0x07
    DMG_MAG_125 = 0x08
    DMG_MAG_150 = 0x09
    DMG_MAG_175 = 0x0A
    DMG_MAG_200 = 0x0B
    DMG_TO_MAG_150 = 0x0C
    DMG_TO_MAG_200 = 0x0D
    HP_TO_1 = 0x0E
    CHARM_80 = 0x0F
    CHARM_100 = 0x10
    CLEAR_STATUS = 0x11
    DMG_33 = 0x13
    DMG_25 = 0x14
    SLEEP_80_AQUA = 0x15
    DOOMSICKLE = 0x16
    HP_50_50 = 0x18
    CRISIS = 0x19
    HP_50_100 = 0x1E
    ATTACKER_DIES = 0x23
    DEATH_40 = 0x24
    DEATH_100 = 0x25
    STOP_60 = 0x26
    SLOW_60 = 0x27
    STOP_80_MACHINES = 0x28
    CHAOS_60 = 0x29
    CHAOS_80 = 0x2E
    CRIT_4X = 0x2F
    CLEAR_SHIELD_BARRIER = 0x30
    DMG_400 = 0x34
    CLEAR_IMMUNITY = 0x35
    RANDOM_STATUS = 0x36
    SLEEP = 0x37
    CRIT_9999 = 0x38


_weapon_effect_abbrev_dict: dict[WeaponEffects, str] = {
    WeaponEffects.NONE: '',
    WeaponEffects.CRIT_X2: '',
    WeaponEffects.WONDERSHOT: 'Rnd. Dmg',
    WeaponEffects.DMG_125: '125% Atk',
    WeaponEffects.DMG_150: '150% Atk',
    WeaponEffects.DMG_175: '175% Atk',
    WeaponEffects.DMG_200: '200% Atk',
    WeaponEffects.MAGIC: 'Mag Dmg',
    WeaponEffects.DMG_MAG_125: '125% Mag Dmg',
    WeaponEffects.DMG_MAG_150: '150% Mag Dmg',
    WeaponEffects.DMG_MAG_175: '175% Mag Dmg',
    WeaponEffects.DMG_MAG_200: '200% Mag Dmg',
    WeaponEffects.DMG_TO_MAG_150: '1.5x v. Mag',
    WeaponEffects.DMG_TO_MAG_200: '2x v. Mag',
    WeaponEffects.HP_TO_1: 'HP to 1',
    WeaponEffects.CHARM_80: '80% Steal',
    WeaponEffects.CHARM_100: '100% Steal',
    WeaponEffects.CLEAR_STATUS: 'Heal Stat.',
    WeaponEffects.DMG_33: '33% Dmg',
    WeaponEffects.DMG_25: '25% Dmg',
    WeaponEffects.SLEEP_80_AQUA: '80% Slp to Aqua',
    WeaponEffects.DOOMSICKLE: '+Doom',
    WeaponEffects.HP_50_50: '1/2 HP (50%)',
    WeaponEffects.CRISIS: 'Crisis',
    WeaponEffects.HP_50_100: '1/2 HP',
    WeaponEffects.ATTACKER_DIES: 'Attacker dies',
    WeaponEffects.DEATH_40: '40% Death',
    WeaponEffects.DEATH_100: '100% Death',
    WeaponEffects.STOP_60: '60% Stop',
    WeaponEffects.SLOW_60: '60% Slow',
    WeaponEffects.STOP_80_MACHINES: '80% Stop Mach.',
    WeaponEffects.CHAOS_60: '60% Chaos',
    WeaponEffects.CHAOS_80: '80% Chaos',
    WeaponEffects.CRIT_4X: '4x Crit Dmg',
    WeaponEffects.CLEAR_SHIELD_BARRIER: 'Clear Shld/Bar',
    WeaponEffects.DMG_400: '400% Dmg',
    WeaponEffects.CLEAR_IMMUNITY: 'Prot. Seal',
    WeaponEffects.RANDOM_STATUS: 'Random Status',
    WeaponEffects.SLEEP: 'Sleep',
    WeaponEffects.CRIT_9999: '9,999 Crit'
}


class StatBit(ctenums.StrIntEnum):
    '''Associate Stat to bit for StatBoost.'''
    POWER = 0x80
    SPEED = 0x40
    STAMINA = 0x20
    HIT = 0x10
    EVADE = 0x08
    MAGIC = 0x04
    MDEF = 0x02


# TODO: Use BinaryData from cttypes
class BinaryData:
    '''Class for manipulating rom data.'''
    SIZE = 0
    ROM_START = 0

    def __init__(self, data: typing.Optional[bytes] = None):
        default_data = bytes([0 for i in range(self.SIZE)])

        if data is None:
            data = default_data

        if len(data) != self.SIZE:
            raise DataSizeException(
                f'{self.__class__.__name__} requires data of size '
                f'{self.SIZE} (given {len(data)}).'
            )

        self._data = bytearray(data)

    def __eq__(self, other: object):
        if not hasattr(other, '_data'):
            return False
        return self._data == other._data

    def get_copy(self):
        '''Return a copy of this object.'''
        return self.__class__(self._data)

    def __len__(self) -> int:
        return self.SIZE

    def __str__(self) -> str:
        name_str = self.__class__.__name__
        data_str = ' '.join(f'{x:02X}' for x in self._data)
        return name_str + ': ' + data_str


class StatBoost(BinaryData):
    '''Two byte gear stat boost data.'''
    SIZE = 2
    ROM_START = 0x0C29D7

    @classmethod
    def from_rom(cls, rom: bytes, index: int):
        '''Read StatBoost from a rom.'''
        start = cls.ROM_START + cls.SIZE*index
        end = start + cls.SIZE

        return cls(bytes(rom[start:end]))

    def write_to_rom(self, rom: WritableBytes, index: int):
        '''Write StatBoost to a rom.'''
        start = self.ROM_START + self.SIZE*index
        end = start + self.SIZE

        rom[start:end] = self._data[:]

    def __le__(self, other):
        return (
            self._data[0] & other._data[0] == self._data[0] and
            self.magnitude <= other.magnitude
        )

    def __eq__(self, other):
        return self._data == other._data

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return self <= other and self != other

    def __gt__(self, other):
        return self >= other and self != other

    def __ge__(self, other):
        return (
            self._data[0] & other._data[0] == other._data[0] and
            self.magnitude >= other.magnitude
        )

    @property
    def magnitude(self):
        '''The magnitude of the stat boost.'''
        return self._data[1]

    @magnitude.setter
    def magnitude(self, val: int):
        if val > 0xFF:
            print('Warning: magnitude must be in [0, 0xFF]. Setting to 0xFF.')
            val = 0xFF
        elif val < 0:
            print('Warning: magnitude must be in [0, 0xFF]. Setting to 0.')
            val = 0

        self._data[1] = val

    @property
    def stats_boosted(self) -> list[StatBit]:
        '''Which stats are included in the boost.'''
        stat_list = [
            x for x in list(StatBit)
            if int(x) & self._data[0]
        ]

        return stat_list

    def stat_string(self) -> str:
        '''Get an abbreviated string representing the StatBoost.'''
        abbrev_dict = {
            StatBit.POWER: 'Pw',
            StatBit.SPEED: 'Sp',
            StatBit.STAMINA: 'St',
            StatBit.HIT: 'Hi',
            StatBit.EVADE: 'Ev',
            StatBit.MAGIC: 'Mg',
            StatBit.MDEF: 'Md'
        }

        if self.magnitude == 0 or not self.stats_boosted:
            return ''

        stat_str = '/'.join(abbrev_dict[x] for x in self.stats_boosted)

        return stat_str+'+'+str(self.magnitude)


class ItemData(BinaryData):
    '''
    BinaryData with controls on which ItemIDs are valid for the data.

    Assumes the data exists as fixed-size (SIZE) records with a given start
    at ROM_START.
    '''
    SIZE = 0
    ROM_START = 0
    MIN_ID = 0
    MAX_ID = 0

    @classmethod
    def _validate_item_id(cls, item_id: int) -> ctenums.ItemID:
        '''Check that item_id matches the class bounds'''
        if item_id > cls.MAX_ID:
            raise InvalidItemID(
                f'{cls.__name__}: item_id 0x{item_id:02X} exceeds '
                f'MAX=0x{cls.MAX_ID:02X}.'
            )
        if item_id < cls.MIN_ID:
            raise InvalidItemID(
                f'{cls.__name__}: item_id 0x{item_id:02X} is less than '
                f'MIN=0x{cls.MIN_ID:02X}.'
            )

        return ctenums.ItemID(item_id)

    @classmethod
    def from_rom(cls, rom: bytes, item_id: ctenums.ItemID):
        '''Read ItemData from rom'''
        item_id = cls._validate_item_id(item_id)

        shifted_id = item_id - cls.MIN_ID
        start = cls.ROM_START+shifted_id*cls.SIZE
        end = start + cls.SIZE

        return cls(bytes(rom[start:end]))

    def write_to_rom(self, rom: WritableBytes, item_id: ctenums.ItemID):
        '''Write ItemData to a rom in the given item_id slot.'''
        item_id = self._validate_item_id(item_id)
        shifted_id = item_id - self.MIN_ID

        start = self.ROM_START+shifted_id*self.SIZE
        end = start + self.SIZE

        rom[start:end] = self._data


class ItemSecondaryData(ItemData):
    '''
    Class for storing properties shared by many item types such as price,
    ability to sell, and ability to equip.
    '''
    @property
    def price(self) -> int:
        return int.from_bytes(self._data[1:3], 'little')

    @price.setter
    def price(self, val: int):
        self._data[1:3] = val.to_bytes(2, 'little')

    @property
    def is_unsellable(self) -> bool:
        return bool(self._data[0] & 0x04)

    @is_unsellable.setter
    def is_unsellable(self, val: bool):
        self._data[0] &= (0xFF - 0x04)
        self._data[0] |= (0x04*val)

    @property
    def is_key_item(self) -> bool:
        return bool(self._data[0] & 0x08)

    @is_key_item.setter
    def is_key_item(self, val: bool):
        self._data[0] &= (0xFF - 0x08)
        self._data[0] |= (0x08*val)

    @property
    def ngplus_carryover(self) -> bool:
        return not self._data[0] & 0x10

    @ngplus_carryover.setter
    def ngplus_carryover(self, val: bool):
        val = bool(val)
        self._data[0] &= 0xFF - 0x10
        self._data[0] |= 0x10*(val is False)

    def get_equipable_by(self) -> list[ctenums.CharID]:
        equip_list = []
        for char in list(ctenums.CharID):
            bitmask = 0x80 >> int(char)
            if self._data[3] & bitmask:
                equip_list.append(char)

        return equip_list

    def set_equipable_by(
            self,
            chars: typing.Union[ctenums.CharID,
                                typing.Iterable[ctenums.CharID]]
    ):
        if isinstance(chars, ctenums.CharID):
            chars = [chars]

        equip_byte = 0
        for char in chars:
            bitmask = 0x80 >> int(char)
            equip_byte |= bitmask

        self._data[3] = equip_byte


class WeaponStats(ItemData):
    '''Class for weapon stats.  Includes WeaponEffects.'''
    SIZE = 5
    ROM_START = 0x0C0262
    MIN_ID = 0
    MAX_ID = int(ctenums.ItemID.WEAPON_END_5A)-1

    @property
    def attack(self) -> int:
        '''Base attack of the weapon.'''
        return self._data[0]

    @attack.setter
    def attack(self, val: int):
        self._data[0] = val

    @property
    def critical_rate(self) -> int:
        '''Base critical rate of the weapon.'''
        return self._data[2]

    @critical_rate.setter
    def critical_rate(self, val: int):
        if val < 0:
            val = 0
        elif val > 100:
            val = 100

        self._data[2] = val

    @property
    def effect_id(self) -> WeaponEffects:
        '''The weapon effect on this weapon.'''
        return WeaponEffects(self._data[3])

    @effect_id.setter
    def effect_id(self, val: WeaponEffects):
        # validate?
        self._data[3] = int(val)

    @property
    def has_effect(self) -> bool:
        '''Whether the weapon has an effect.'''
        return self._data[4] == 1

    @has_effect.setter
    def has_effect(self, val: bool):
        self._data[4] = int(val)

    def get_effect_string(self):
        '''Returns a string representation of this weapon's effect.'''

        # TODO: Move this out of the class?
        if self.has_effect:
            return _weapon_effect_abbrev_dict[self.effect_id]
        return ''


class ArmorStats(ItemData):
    '''Class for stats of armors and helms.'''
    SIZE = 3
    ROM_START = 0x0C047E
    MIN_ID = int(ctenums.ItemID.WEAPON_END_5A)
    MAX_ID = int(ctenums.ItemID.HELM_END_94)-1

    @property
    def defense(self) -> int:
        '''Base defense value.'''
        return self._data[0]

    @defense.setter
    def defense(self, val: int):
        self._data[0] = val

    @property
    def effect_id(self) -> ArmorEffects:
        '''ArmorEffects of this armor.'''
        return ArmorEffects(self._data[1])

    @effect_id.setter
    def effect_id(self, val: ArmorEffects):
        # validate?
        if val == ArmorEffects.NONE:
            self.has_effect = False
        else:
            self.has_effect = True

        self._data[1] = int(val)

    @property
    def has_effect(self) -> bool:
        '''Whether this armor has an effect or not.'''
        return self._data[2] == 1

    @has_effect.setter
    def has_effect(self, val: bool):
        self._data[2] = int(val)

    def get_effect_string(self):
        '''Returns a string representation of this armor's effect.'''
        if self.has_effect:
            return _armor_status_abbrev_dict[self.effect_id]
        return ''


class Type_09_Buffs(ctenums.StrIntEnum):
    '''
    Buffs with a type of 9.  Used by Accessories.

    The type of a buff is an index into the array of stats which indicates
    the byte to modify.
    '''
    BERSERK = 0x80
    BARRIER = 0x40
    MP_REGEN = 0x20
    UNK_10 = 0x10
    SPECS = 0x08
    SHIELD = 0x04
    SHADES = 0x02
    UNK_01 = 0x01

    def get_abbrev(self) -> str:
        '''Get an abbreviated string of the buff.  For Item descriptions.'''
        type_09_abbrev: dict[Type_09_Buffs, str] = {
            Type_09_Buffs.BERSERK: 'Bers',
            Type_09_Buffs.BARRIER: 'Bar',
            Type_09_Buffs.MP_REGEN: 'RegMP',
            Type_09_Buffs.UNK_10: '?',
            Type_09_Buffs.SPECS: '+50%Dmg',
            Type_09_Buffs.SHIELD: 'Shld',
            Type_09_Buffs.SHADES: '+25%Dmg',
            Type_09_Buffs.UNK_01: '?'
        }

        return type_09_abbrev[self]


class Type_05_Buffs(ctenums.StrIntEnum):
    '''
    Buffs with a type of 5.  Used by Accessories.  Presently, only the
    autorevive status (Greendream) uses this type.

    The type of a buff is an index into the array of stats which indicates
    the byte to modify.
    '''

    GREENDREAM = 0x80

    def get_abbrev(self) -> str:
        '''Get an abbreviated string of the buff.  For Item descriptions.'''
        if self == Type_05_Buffs.GREENDREAM:
            return 'Autorev'

        raise ValueError("Undefined Buff Type")


class Type_06_Buffs(ctenums.StrIntEnum):
    '''
    Buffs with a type of 6.  Used by Accessories.

    The type of a buff is an index into the array of stats which indicates
    the byte to modify.
    '''
    PROT_STOP = 0x80
    PROT_POISON = 0x40
    PROT_SLOW = 0x20
    PROT_HPDOWN = 0x10  # ?
    PROT_LOCK = 0x08
    PROT_CHAOS = 0x04
    PROT_SLEEP = 0x02
    PROT_BLIND = 0x01

    def get_abbrev(self) -> str:
        '''Get an abbreviated string of the buff.  For Item descriptions.'''
        status_abbrev = {
            Type_06_Buffs.PROT_STOP: 'Stp',
            Type_06_Buffs.PROT_POISON: 'Psn',
            Type_06_Buffs.PROT_SLOW: 'Slw',
            Type_06_Buffs.PROT_HPDOWN: 'HPdn',
            Type_06_Buffs.PROT_LOCK: 'Lck',
            Type_06_Buffs.PROT_CHAOS: 'Chs',
            Type_06_Buffs.PROT_SLEEP: 'Slp',
            Type_06_Buffs.PROT_BLIND: 'Bnd'
        }

        return status_abbrev[self]


class Type_08_Buffs(ctenums.StrIntEnum):
    '''
    Buffs with a type of 8.  Used by Accessories.

    The type of a buff is an index into the array of stats which indicates
    the byte to modify.
    '''

    HASTE = 0x80
    EVADE = 0x40

    def get_abbrev(self) -> str:
        '''Get an abbreviated string of the buff.  For Item descriptions.'''
        type_08_abbrev: dict[Type_08_Buffs, str] = {
            Type_08_Buffs.HASTE: 'Haste',
            Type_08_Buffs.EVADE: '2xEvd'
        }

        return type_08_abbrev[self]


_Buff = typing.Union[Type_05_Buffs, Type_06_Buffs, Type_08_Buffs,
                     Type_09_Buffs]
_BuffList = typing.Iterable[_Buff]


def get_buff_string(buffs: typing.Union[_Buff, _BuffList]) -> str:
    '''
    Return a string representation of the _Buff or _BuffList.  In the case of
    a _BuffList, all buffs must be of the same type.
    '''
    if isinstance(buffs, typing.Iterable):
        if not buffs:
            return ''

        buff_types = list(set(type(buff) for buff in buffs))
        buffs = list(set(buffs))

        if len(buff_types) > 1:
            raise TypeError('Buff list has multiple types.')

        buff_type = buff_types[0]
        if buff_type in (Type_05_Buffs, Type_09_Buffs, Type_08_Buffs):
            buff_str = '/'.join(x.get_abbrev() for x in buffs)
        elif buff_type == Type_06_Buffs:
            if len(buffs) == 8:
                buff_str = 'P:All'
            else:
                buff_str = 'P:'+'/'.join(x.get_abbrev() for x in buffs)

        return buff_str

    raise TypeError("Invalid Buff Type")


# We are not going to do much with accessories because they are so weird.
class AccessoryStats(ItemData):
    '''Class for accessory stats.'''
    SIZE = 4
    ROM_START = 0x0C052C
    MIN_ID = int(ctenums.ItemID.HELM_END_94)
    MAX_ID = int(ctenums.ItemID.PRISMSPECS)

    @property
    def has_battle_buff(self) -> bool:
        '''whether the accessory has a _Buff.'''
        return bool(self._data[1] & 0x80)

    @has_battle_buff.setter
    def has_battle_buff(self, val: bool):
        self._data[1] &= (0xFF - 0x80)
        self._data[1] |= (0x80 & (val*0xFF))

    def _get_buff_type(self):
        '''The type of the _Buff.  Only used internally.'''
        if not self.has_battle_buff:
            return None
        if self._data[2] == 0x05:
            return Type_05_Buffs
        if self._data[2] == 0x06:
            return Type_06_Buffs
        if self._data[2] == 0x08:
            return Type_08_Buffs
        if self._data[2] == 0x09:
            return Type_09_Buffs

        raise ValueError('Invalid buff type')

    def _get_buff_type_index(self, buff: _Buff) -> int:
        '''Get offset into stat array for byte modified by the buff.'''
        if isinstance(buff, Type_05_Buffs):
            return 5
        if isinstance(buff, Type_06_Buffs):
            return 6
        if isinstance(buff, Type_08_Buffs):
            return 8
        if isinstance(buff, Type_09_Buffs):
            return 9
        raise ValueError('Invalid buff type')

    @property
    def battle_buffs(self) -> list[_Buff]:
        '''List of buffs this accessory has.'''
        BuffType = self._get_buff_type()
        return [x for x in list(BuffType) if self._data[3] & x]

    @battle_buffs.setter
    def battle_buffs(self, val: typing.Union[_Buff, _BuffList]):

        if not self.has_battle_buff:
            raise ValueError('Adding buffs to item without buffs set.')

        if not isinstance(val, typing.Iterable):
            val = [val]

        if not val:
            self._data[3] = 0
        else:
            buffs = list(set(val))
            types = list(set(type(x) for x in buffs))

            if len(types) != 1:
                raise TypeError('Multiple types of buffs')

            buff_type = types[0]
            type_val = {
                Type_05_Buffs: 5,
                Type_06_Buffs: 6,
                Type_08_Buffs: 8,
                Type_09_Buffs: 9
            }

            buff_type_val = type_val[buff_type]
            self._data[2] = buff_type_val

            buff_byte = functools.reduce(
                lambda a, b: a | b,
                buffs,
                0
            )

            self._data[3] = buff_byte

    @property
    def has_stat_boost(self) -> bool:
        '''Whether this accessory has a stat boost.'''
        return bool(self._data[1] & 0x40)

    @has_stat_boost.setter
    def has_stat_boost(self, val: bool):
        if val:
            self._data[1] |= 0x40
        else:
            self._data[1] &= (0xFF-0x40)

    @property
    def stat_boost_index(self):
        '''
        The index of the stat boost had by this accessory.

        Unsure of behavior if has_stat_boost is False.
        '''
        if not self.has_stat_boost:
            # raise exception?
            return 0
        return self._data[2]

    @stat_boost_index.setter
    def stat_boost_index(self, val: int):
        if not self.has_stat_boost:
            # raise Exception
            pass
        else:
            self._data[2] = val

    @property
    def has_counter_effect(self) -> bool:
        '''Whether accessory grants a counter effect.'''
        return bool(self._data[0] & 0x40)

    @has_counter_effect.setter
    def has_counter_effect(self, val: bool):
        if val:
            self._data[0] |= 0x40
        else:
            self._data[0] &= (0xFF-0x40)

    @property
    def has_normal_counter_mode(self) -> bool:
        '''Whether accessory counters with a basic attack.'''
        return bool(self.has_counter_effect and self._data[2] & 0x80)

    # non-normal = atb counter
    @has_normal_counter_mode.setter
    def has_normal_counter_mode(self, normal_mode: bool):
        if self.has_counter_effect:
            if normal_mode:
                self._data[2] |= 0x80
            else:
                self._data[2] &= 0x7F
        else:
            # raise exception
            pass

    @property
    def counter_rate(self):
        '''Percentage chance of counter effect triggering.'''
        if self.has_counter_effect:
            return self._data[3]

        raise ValueError("Counter Effect Not Set")

    @counter_rate.setter
    def counter_rate(self, val: int):
        if self.has_counter_effect:
            self._data[3] = val
        else:
            # raise exception?  Force counter mode on?
            raise ValueError("Counter Effect Not Set")


class AccessorySecondaryStats(ItemSecondaryData):
    SIZE = 4
    ROM_START = 0x0C0A1C
    MIN_ID = int(ctenums.ItemID.HELM_END_94)
    MAX_ID = int(ctenums.ItemID.PRISMSPECS)


class GearSecondaryStats(ItemSecondaryData):
    '''
    Class for gear secondary stats. Adds stat boosts and elemental protection.
    '''
    SIZE = 6
    ROM_START = 0x0C06A4
    MIN_ID = 0
    MAX_ID = int(ctenums.ItemID.MERMAIDCAP)

    elem_bit_dict = {
            ctenums.Element.LIGHTNING: 0x80,
            ctenums.Element.SHADOW: 0x40,
            ctenums.Element.ICE: 0x20,
            ctenums.Element.FIRE: 0x10
    }

    elem_abbrev_dict = {
            ctenums.Element.LIGHTNING: 'Li',
            ctenums.Element.SHADOW: 'Sh',
            ctenums.Element.ICE: 'Wa',
            ctenums.Element.FIRE: 'Fi'
    }

    @property
    def stat_boost_index(self) -> int:
        '''Index of StatBoost on this item.'''
        return self._data[4]

    @stat_boost_index.setter
    def stat_boost_index(self, val: int):
        self._data[4] = val

    @property
    def elemental_protection_magnitude(self):
        '''
        Amount of protection granted by this gear.

        Percent reduction is round(100 - 400/(4+prot_mag)).
        '''
        return self._data[5] & 0x0F

    @elemental_protection_magnitude.setter
    def elemental_protection_magnitude(self, val: int):
        if val > 0x0F:
            val = 0x0F
        elif val < 0:
            val = 0

        self._data[5] &= 0xF0
        self._data[5] |= val

    @classmethod
    def prot_mag_to_percent(cls, prot_mag: int):
        '''Get the protection magnitude as a percentage reduction.'''
        return round(100 - 400/(4+prot_mag))

    def set_protect_element(self, element: ctenums.Element,
                            has_protection: bool):
        '''
        Sets the elements that this gear protects against.
        '''
        if element == ctenums.Element.NONELEMENTAL:
            print('Warning: Gear cannot protect against nonelemental.')
            return

        elem_bit = self.elem_bit_dict[element]

        if has_protection:
            bit_mask = elem_bit
            self._data[5] |= bit_mask
        else:
            bit_mask = 0xFF - elem_bit
            self._data[5] &= bit_mask

    def get_protection_desc_str(self) -> str:
        '''
        Gets a string representation of this gear's elemental protection.
        For descriptions.
        '''
        mag = self.prot_mag_to_percent(self.elemental_protection_magnitude)
        elems = self.get_protected_elements()

        elem_str = '/'.join(self.elem_abbrev_dict[elem]
                            for elem in elems)

        if mag == 0 or not elems:
            return ''

        return f'R:{elem_str} {mag}%'

    def get_protected_elements(self) -> list[ctenums.Element]:
        '''
        Gets the elements that this gear protects against.
        '''
        elements = [
            elem for elem in self.elem_bit_dict
            if self.elem_bit_dict[elem] & self._data[5]
        ]

        return elements

    def get_stat_string(self):
        '''
        Gets a string representing these stats.  For spoilers/testing.
        '''
        price_str = f'Price: {self.price}'
        equip_str = 'Equppable by: ' \
            + ', '.join(str(x) for x in self.get_equipable_by())
        prot_mag = 400 / (4+self.elemental_protection_magnitude)
        prot_mag = 100 - prot_mag
        if prot_mag == 0 or not self.get_protected_elements:
            prot_str = 'No Elemental Protection'
        else:
            prot_str = f'Protects {prot_mag:.0f}% vs ' \
                + ', '.join(str(x) for x in self.get_protected_elements())

        return '\n'.join((price_str, equip_str, prot_str))


class ConsumableKeySecondaryStats(ItemSecondaryData):
    '''Class for Consumable and Key Item Stats.'''
    SIZE = 3
    ROM_START = 0x0C0ABC
    MIN_ID = 0xBC
    MAX_ID = 0xF1

    def get_equipable_by(self):
        raise TypeError("Consumables are not Equippable")

    def set_equipable_by(self, chars):
        raise TypeError("Consumables are not Equippable")


class ConsumableKeyEffect(ItemData):
    '''
    Class for Consumable and Key Item Effects.
    '''
    SIZE = 4
    ROM_START = 0x0C05CC
    MIN_ID = int(ctenums.ItemID.ACCESSORY_END_BC)
    MAX_ID = 0xF1

    @property
    def heals_in_menu(self):
        '''Can the item be used to heal in the menu.'''
        return self._data[0] == 0x80

    @heals_in_menu.setter
    def heals_in_menu(self, val: bool):
        self._data[0] &= 0x7F
        self._data[0] |= (0x80 * val)

    @property
    def heals_in_battle_only(self):
        '''
        Whether the item can only be used to heal in battle.

        I believe this is only for revives.
        '''
        return self._data[0] == 0x04

    @heals_in_battle_only.setter
    def heals_in_battle_only(self, val: bool):
        bit = 0x04
        self._data[0] &= (0xFF - bit)
        self._data[0] |= (bit * val)

    @property
    def heals_at_save(self):
        '''Whether the item can only be used at save points.'''
        return self._data[0] == 0x08

    @heals_at_save.setter
    def heals_at_save(self, val: bool):
        if val:
            self._data[0] = 0x08
        else:
            self._data[0] &= 0xF7

    @property
    def base_healing(self) -> int:
        '''
        Base healing.  Healing is base*multiplier.

        Warning:  Things are different between menu and battle.
        '''
        return self._data[3] & 0x3F

    @base_healing.setter
    def base_healing(self, val: int):
        val = min(0x3F, val)
        self._data[3] &= 0xC0
        self._data[3] |= val

    @property
    def heal_multiplier(self) -> int:
        '''
        Healing Multiplier.  Healing is base*multiplier.

        Warning:  Things are different between menu and battle.
        '''
        return self._data[2] & 0x0F

    @heal_multiplier.setter
    def heal_multiplier(self, val: int):
        val = min(0x0F, val)
        self._data[2] &= 0xF0
        self._data[2] |= val

    @property
    def heals_hp(self) -> bool:
        '''Whether this item heals hp.'''
        return bool(self._data[1] & 0x80)

    @heals_hp.setter
    def heals_hp(self, val: bool):
        if val:
            self._data[1] |= 0x80
        else:
            self._data[1] &= 0x7F

    @property
    def heals_mp(self) -> bool:
        '''Whether this item heals mp.'''
        return bool(self._data[1] & 0x40)

    @heals_mp.setter
    def heals_mp(self, val: bool):
        if val:
            self._data[1] |= 0x40
        else:
            self._data[1] &= 0xBF

    def get_heal_amount(self) -> int:
        '''The total healing amount.  Base*Multiplier.'''
        return self.base_healing*self.heal_multiplier


Stats = typing.Union[
    WeaponStats, ArmorStats, AccessoryStats, ConsumableKeyEffect
]

SecStats = typing.Union[
    GearSecondaryStats, AccessorySecondaryStats, ConsumableKeySecondaryStats
]


class Item:
    def __init__(self,
                 stats: typing.Union[WeaponStats, ArmorStats,
                                     AccessoryStats, ConsumableKeyEffect],
                 secondary_stats: typing.Union[GearSecondaryStats,
                                               AccessorySecondaryStats,
                                               ConsumableKeySecondaryStats],
                 name_bytes: bytes,
                 desc_bytes: bytes):
        self.stats = stats
        self.secondary_stats = secondary_stats
        self.name = bytearray(name_bytes)
        self.desc = bytearray(desc_bytes)

    def to_jot_json(self):
        return {
            'name': self.get_name_as_str(True),
            'desc': self.get_desc_as_str(),
            'price': self.price
        }

    def __eq__(self, other):
        return (
            self.stats == other.stats and
            self.secondary_stats == other.secondary_stats and
            self.name == other.name and
            self.desc == other.desc
        )

    def is_armor(self):
        return isinstance(self.stats, ArmorStats)

    def is_weapon(self):
        return isinstance(self.stats, WeaponStats)

    def is_accessory(self):
        return isinstance(self.stats, AccessoryStats)

    @property
    def price(self) -> int:
        return self.secondary_stats.price

    @price.setter
    def price(self, val: int):
        self.secondary_stats.price = val

    def get_stat_boost_ind(self):
        if isinstance(self.secondary_stats, GearSecondaryStats):
            return self.secondary_stats.stat_boost_index
        if isinstance(self.stats, AccessoryStats):
            if self.stats.has_stat_boost:
                return self.stats.stat_boost_index
            return None
        return None

    @classmethod
    def _determine_types(
            cls,
            item_id: ctenums.ItemID
    ) -> typing.Tuple[typing.Type[Stats], typing.Type[SecStats]]:

        S = typing.Type[Stats]
        stat_types: typing.Tuple[S, S, S, S] = (
            WeaponStats, ArmorStats, AccessoryStats, ConsumableKeyEffect
        )

        SS = typing.Type[SecStats]
        secondary_types: typing.Tuple[SS, SS, SS] = (
            GearSecondaryStats, AccessorySecondaryStats,
            ConsumableKeySecondaryStats
        )

        primary_stat_type: S
        secondary_stat_type: SS

        for stat_type in stat_types:
            if stat_type.MIN_ID <= item_id <= stat_type.MAX_ID:
                primary_stat_type = stat_type
                break

        for sec_stat_type in secondary_types:
            if sec_stat_type.MIN_ID <= item_id <= sec_stat_type.MAX_ID:
                secondary_stat_type = sec_stat_type
                break

        return primary_stat_type, secondary_stat_type

    @classmethod
    def get_name_from_rom(cls, rom: bytes, item_id: ctenums.ItemID) -> bytes:
        names_start_addr = 0x0C0B5E
        name_size = 0xB
        name_st = names_start_addr + item_id*name_size
        name_end = name_st + name_size

        name_b = bytes(rom[name_st:name_end])
        return name_b

    def write_name_to_rom(self, rom: WritableBytes, item_id: ctenums.ItemID):
        names_start_addr = 0x0C0B5E
        name_size = 0xB
        name_st = names_start_addr + item_id*name_size
        name_end = name_st + name_size

        # print(bytes(self.name))
        # print(self.name)
        rom[name_st:name_end] = self.name

    def get_name_as_str(self, remove_prefix: bool = False):
        if remove_prefix:
            start = 1
        else:
            start = 0
        return str(ctstrings.CTNameString(self.name[start:]))

    def set_name_from_str(self, name_str: str):
        self.name = ctstrings.CTNameString.from_string(name_str, 11)

    def get_desc_as_str(self):
        return ctstrings.CTString.ct_bytes_to_ascii(
            self.desc[0:-1]
        )

    def set_desc_from_str(self, name_str: str):
        desc = ctstrings.CTString.from_str(name_str)
        if desc[-1] != 0:
            desc.append(0)

        desc.compress()
        self.desc = desc

    @classmethod
    def get_desc_ptr_file_start_from_rom(cls, rom: bytes):
        # Putting item desc ptr start into memory
        # $C2/F317 A2 B1 2E    LDX #$2EB1
        # $C2/F31A 8E 0D 02    STX $020D  [$7E:020D]
        # $C2/F31D A9 CC       LDA #$CC
        # $C2/F31F 8D 0F 02    STA $020F  [$7E:020F]
        local_ptr_st = int.from_bytes(rom[0x02F318:0x02F318+2], 'little')
        bank = byteops.to_file_ptr(int(rom[0x02F31E]) << 16)

        return local_ptr_st + bank

    @classmethod
    def get_desc_from_rom(cls, rom: bytes, item_id: ctenums.ItemID) -> bytes:

        desc_ptr_file_st = cls.get_desc_ptr_file_start_from_rom(rom)
        desc_ptr_st = desc_ptr_file_st + 2*item_id
        bank = desc_ptr_st & 0xFF0000
        local_ptr = int.from_bytes(rom[desc_ptr_st:desc_ptr_st+2], 'little')
        desc_st = bank + local_ptr

        desc_end = desc_st
        while rom[desc_end] != 0:
            desc_end += 1

        desc_end += 1

        desc_b = bytes(rom[desc_st: desc_end])
        return desc_b

    @classmethod
    def from_rom(cls, rom: bytes, item_id: ctenums.ItemID):
        Primary, Secondary = cls._determine_types(item_id)

        stats = Primary.from_rom(rom, item_id)
        secondary_stats = Secondary.from_rom(rom, item_id)

        name = cls.get_name_from_rom(rom, item_id)
        desc = cls.get_desc_from_rom(rom, item_id)

        return cls(stats, secondary_stats, name, desc)

    def __str__(self):
        ret_str = str(ctstrings.CTNameString(self.name)) + '\n'
        ret_str += str(self.stats) + '\n'
        ret_str += str(self.secondary_stats) + '\n'
        ret_str += ctstrings.CTString.ct_bytes_to_ascii(self.desc)
        return ret_str


class ItemDB:
    def __init__(self,
                 item_dict: Optional[dict[ctenums.ItemID, Item]] = None,
                 stat_boosts: Optional[typing.Iterable[StatBoost]] = None):
        if item_dict is None:
            item_dict = {}
        self.item_dict = dict(item_dict)

        if stat_boosts is None:
            stat_boosts = []
        self.stat_boosts = list(stat_boosts)

    def __getitem__(self, index):
        return self.item_dict[index]

    def __setitem__(self, index, value):
        self.item_dict[index] = value

    @property
    def base_hp_healing(self):
        tonic = self.item_dict[ctenums.ItemID.TONIC]
        return tonic.stats.base_healing

    @base_hp_healing.setter
    def base_hp_healing(self, val: int):
        val = min(val, 0x3F)

        healing_item_ids = (x for x in list(ctenums.ItemID)
                            if x >= ctenums.ItemID.TONIC
                            and x <= ctenums.ItemID.LAPIS)

        for item_id in healing_item_ids:
            item = self[item_id]
            if item.stats.heals_hp and item.stats.heal_multiplier != 0xF:
                item.stats.base_healing = val

    @property
    def base_mp_healing(self):
        tonic = self.item_dict[ctenums.ItemID.ETHER]
        return tonic.stats.base_healing

    @base_mp_healing.setter
    def base_mp_healing(self, val: int):
        val = min(val, 0x3F)

        healing_item_ids = (x for x in list(ctenums.ItemID)
                            if x >= ctenums.ItemID.TONIC
                            and x <= ctenums.ItemID.LAPIS)

        for item_id in healing_item_ids:
            item = self[item_id]
            if item.stats.heals_mp and item.stats.heal_multiplier != 0xF:
                item.stats.base_healing = val

    @classmethod
    def from_rom(cls, rom: bytes):
        item_dict = {
            item_id: Item.from_rom(rom, item_id)
            for item_id in list(ctenums.ItemID)
        }

        max_statboost_ind = 0
        for item_id in item_dict:
            item = item_dict[item_id]
            boost_index = item.get_stat_boost_ind()
            if boost_index is None:
                boost_index = 0

            max_statboost_ind = max(boost_index, max_statboost_ind)

        statboost_count = max_statboost_ind + 1

        statboosts = [StatBoost.from_rom(rom, i)
                      for i in range(statboost_count)]

        return cls(item_dict, statboosts)

    def update_all_descriptions(self):
        for item_id in self.item_dict:
            self.update_description(item_id)

    def update_description(self, item_id):
        if item_id == ctenums.ItemID.NONE:
            return

        item = self.item_dict[item_id]
        IID = ctenums.ItemID
        if isinstance(item.stats, AccessoryStats):
            if item_id in (ctenums.ItemID.RAGE_BAND,
                           ctenums.ItemID.FRENZYBAND):
                rate = item.stats.counter_rate
                if item.stats.has_normal_counter_mode:
                    type_str = 'basic atk.'
                else:
                    type_str = 'ATB fill.'

                desc_str = f'{rate}% counter w/ {type_str}{{null}}'
                item.desc = ctstrings.CTString.from_str(desc_str)
            elif item_id in (IID.SILVERERNG, IID.GOLD_ERNG,
                             IID.SILVERSTUD, IID.GOLD_STUD,
                             IID.WALLET):
                # Do nothing because their item stats are junk data or we're
                # not messing with them
                pass
            else:

                start_str = None
                if item_id in (IID.GOLD_ROCK, IID.SILVERROCK, IID.WHITE_ROCK,
                               IID.BLACK_ROCK, IID.BLUE_ROCK):
                    tech_names = {
                        IID.GOLD_ROCK: 'GrandDream',
                        IID.SILVERROCK: 'SpinStrike',
                        IID.WHITE_ROCK: 'PoyozoDance',
                        IID.BLACK_ROCK: 'DarkEternal',
                        IID.BLUE_ROCK: 'OmegaFlare',
                    }
                    start_str = tech_names[item_id]
                elif item_id == IID.HERO_MEDAL:
                    # start_str = 'Masa C:50%'
                    pass
                elif item_id in (IID.SIGHTSCOPE, IID.ROBORIBBON):
                    start_str = 'Show HP'

                buff_str = None
                if item.stats.has_battle_buff:
                    buffs = item.stats.battle_buffs
                    buff_str = get_buff_string(buffs)

                boost_str = None
                if item.stats.has_stat_boost:
                    boost_ind = item.get_stat_boost_ind()
                    boost = self.stat_boosts[boost_ind]
                    boost_str = boost.stat_string()

                desc_parts = []
                for x in (start_str, buff_str, boost_str):
                    if x is not None:
                        desc_parts.append(x)

                desc_str = ' '.join(x for x in desc_parts) + '{null}'
                item.desc = ctstrings.CTString.from_str(desc_str)

            return

        if isinstance(item.stats, ConsumableKeyEffect):
            stat_strs = []
            if item.stats.heals_hp:
                stat_strs.append('HP')

            if item.stats.heals_mp:
                stat_strs.append('MP')

            stat_str = '/'.join(x for x in stat_strs)

            if item.stats.heal_multiplier == 0x0F:
                mag_str = 'All'
            else:
                mag_str = str(item.stats.get_heal_amount())

            if item.stats.heals_in_menu:
                string = 'Restores ' + mag_str + ' ' + stat_str
                # Item targeting is not in this data.
                # Vanilla Mid Tonic == Lapis
                # So until we handle that data too, hardcode the Lapis desc.
                if item_id == ctenums.ItemID.LAPIS:
                    string += ' to Party'

                string += '{null}'

                item.desc = ctstrings.CTString.from_str(string)
            elif item.stats.heals_at_save:
                string = 'Restores ' + mag_str + ' ' + stat_str \
                    + ' at Save Pts.{null}'
                item.desc = ctstrings.CTString.from_str(string)
            elif item.stats.heals_in_battle_only:
                if item_id == ctenums.ItemID.REVIVE:
                    heal_amt = item.stats.get_heal_amount()
                    string = f'Revives fallen ally w/ {heal_amt} HP{{null}}'
                    item.desc = ctstrings.CTString.from_str(string)

            return

        stat_str = ''
        eff_str = ''
        if isinstance(item.stats, ArmorStats):
            armor = item.stats.defense
            res_str = item.secondary_stats.get_protection_desc_str()
            if res_str:
                stat_str = f'D:{armor} {res_str} '
            else:
                stat_str = f'D:{armor} '
            eff_str = item.stats.get_effect_string()

        elif isinstance(item.stats, WeaponStats):
            stat_str = f'A:{item.stats.attack} C:{item.stats.critical_rate}% '
            eff_str = item.stats.get_effect_string()
        else:
            stat_str = ''

        ind = item.get_stat_boost_ind()
        if ind is not None:
            boost = self.stat_boosts[ind]
            boost_str = boost.stat_string()
            if boost_str:
                boost_str += ' '
        else:
            boost_str = ''

        item.desc = ctstrings.CTString.from_str(
            stat_str + boost_str + eff_str + '{null}'
        )

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):

        # Everything but the descs are easy
        rom = ct_rom.rom_data.getbuffer()
        for item_id in self.item_dict:
            item = self.item_dict[item_id]
            item.stats.write_to_rom(rom, item_id)
            item.secondary_stats.write_to_rom(rom, item_id)
            item.write_name_to_rom(rom, item_id)

        for ind, boost in enumerate(self.stat_boosts):
            boost.write_to_rom(rom, ind)

        desc_ptr_st = Item.get_desc_ptr_file_start_from_rom(rom)
        bank = desc_ptr_st & 0xFF0000
        upper_bound = bank
        lower_bound = upper_bound + 0x010000

        # fs = freespace.FreeSpace(0x600000, True)

        for item_index in range(0xF2):
            ptr_st = desc_ptr_st + 2*item_index
            ptr = int.from_bytes(rom[ptr_st:ptr_st+2], 'little')

            desc_st = bank + ptr
            desc_len = len(
                Item.get_desc_from_rom(rom, ctenums.ItemID(item_index))
            )

            desc_end = desc_st + desc_len
            lower_bound = min(lower_bound, desc_st)
            upper_bound = max(upper_bound, desc_end)

            # used = freespace.FSWriteType.MARK_USED
            # fs.mark_block((desc_st, desc_end), used)

        del rom  # Have to delete reference to MemoryView for other writes

        desc_ptr_space = 0xF2*2
        desc_space = sum(len(self.item_dict[x].desc)
                         for x in self.item_dict)
        total_space = desc_ptr_space+desc_space

        rom_data = ct_rom.rom_data
        fs = rom_data.space_manager
        FSW = ctrom.freespace.FSWriteType

        fs.mark_block((desc_ptr_st, desc_ptr_st+desc_ptr_space),
                      FSW.MARK_FREE)
        fs.mark_block((lower_bound, upper_bound),
                      FSW.MARK_FREE)

        write_pos = fs.get_free_addr(total_space)
        bank_byte = byteops.to_rom_ptr(write_pos) >> 16

        rom_data.seek(0x02F318)
        rom_data.write(int.to_bytes(write_pos & 0x00FFFF, 2, 'little'))
        rom_data.seek(0x02F31E)
        rom_data.write(bytes([bank_byte]))

        ptr_pos = write_pos
        desc_pos = write_pos + 2*0xF2
        for i in range(0xF2):

            local_ptr = 0x00FFFF & desc_pos
            rom_data.seek(ptr_pos)
            rom_data.write(local_ptr.to_bytes(2, 'little'), FSW.MARK_USED)
            ptr_pos += 2

            if i in self.item_dict:
                item_id = ctenums.ItemID(i)
                rom_data.seek(desc_pos)
                desc = self.item_dict[item_id].desc
                rom_data.write(desc, FSW.MARK_USED)
                desc_pos += len(desc)

        rom_data.seek(0x01DA6B)
        rom_data.write(int.to_bytes(self.base_hp_healing, 2, 'little'))

        rom_data.seek(0x02B180)
        rom_data.write(int.to_bytes(0x80 | self.base_hp_healing, 1, 'little'))

        rom_data.seek(0x01DAE4)
        rom_data.write(int.to_bytes(self.base_mp_healing, 2, 'little'))

        rom_data.seek(0x01DB09)
        rom_data.write(int.to_bytes(self.base_mp_healing, 2, 'little'))

        rom_data.seek(0x02B187)
        rom_data.write(int.to_bytes(0x80 | self.base_mp_healing, 1, 'little'))

        # fs.print_blocks()

    def to_jot_json(self):
        return {str(x): self.item_dict[x] for x in self.item_dict}
