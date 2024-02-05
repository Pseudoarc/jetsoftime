'''
Module that re-implements statcompute and
'''
from __future__ import annotations
from enum import auto
from typing import Optional

import itemdata

import ctenums
import ctrom
import cttypes as ctt


class PCStat(ctenums.StrIntEnum):
    POWER = auto()
    STAMINA = auto()
    SPEED = auto()
    MAGIC = auto()
    HIT = auto()
    EVADE = auto()
    MAGIC_DEFENSE = auto()


_elem_bit_dict: dict[ctenums.Element, int] = {
    ctenums.Element.LIGHTNING: 0x8,
    ctenums.Element.SHADOW: 0x4,
    ctenums.Element.ICE: 0x2,
    ctenums.Element.FIRE: 0x1
}


class StatBlock(ctt.BinaryData):
    '''
    A class for accessing the 0x50 byte block of stats for each PC.

    Note that this class does not enforce game logic on the stats.  For
    example, this class allows setting of current stats even though the
    current stats can be computed from base stats and level.  More basically,
    setting the level does not automatically cause current stats to increase.
    '''
    SIZE = 0x50
    # The following snippet moves more than just the statblocks, but the
    # statblocks are at the start of the moved portion.
    # $C2/9583 A2 00 00    LDX #$0000
    # $C2/9586 A0 00 26    LDY #$2600
    # $C2/9589 A9 7F 02    LDA #$027F
    # $C2/958C 54 7E CC    MVN CC 7E
    ROM_RW = ctt.LocalPointerRW(0x02958E, 0x029584)

    _cur_stat_offset_dict: dict[PCStat, int] = {
        PCStat.POWER: 0xB,
        PCStat.STAMINA: 0xC,
        PCStat.SPEED: 0xD,
        PCStat.MAGIC: 0xE,
        PCStat.HIT: 0xF,
        PCStat.EVADE: 0x10,
        PCStat.MAGIC_DEFENSE: 0x11
    }

    _base_stat_offset_dict: dict[PCStat, int] = {
        PCStat.POWER: 0x2F,
        PCStat.STAMINA: 0x30,
        PCStat.SPEED: 0x31,
        PCStat.MAGIC: 0x34,
        PCStat.HIT: 0x32,
        PCStat.EVADE: 0x33,
        PCStat.MAGIC_DEFENSE: 0x35
    }

    # Byte Properties

    char_id = ctt.byte_prop(0, ret_type=ctenums.CharID)
    # Note that the resisted element is resisted at 20%.
    _element_resisted = ctt.byte_prop(1, 0xF0)

    @property
    def innate_element_resisted(self) -> ctenums.Element:
        elems = (elem for elem in _elem_bit_dict
                 if _elem_bit_dict[elem] & self._element_resisted)

        if not elems:
            return ctenums.Element.NONELEMENTAL  # Means no resistance

        return next(elems)  # CT just checks the first set bit.

    @innate_element_resisted.setter
    def innate_element_resisted(self, element: ctenums.Element):
        self._element_resisted = _elem_bit_dict[element]

    all_techs_learned = ctt.byte_prop(1, 0x10)
    current_hp = ctt.bytes_prop(3, 2)
    max_hp = ctt.bytes_prop(5, 2)
    current_mp = ctt.bytes_prop(7, 2)
    max_mp = ctt.bytes_prop(9, 2)
    current_pow = ctt.byte_prop(_cur_stat_offset_dict[PCStat.POWER])
    current_stm = ctt.byte_prop(_cur_stat_offset_dict[PCStat.STAMINA])
    current_spd = ctt.byte_prop(_cur_stat_offset_dict[PCStat.SPEED])
    current_mag = ctt.byte_prop(_cur_stat_offset_dict[PCStat.MAGIC])
    current_hit = ctt.byte_prop(_cur_stat_offset_dict[PCStat.HIT])
    current_evd = ctt.byte_prop(_cur_stat_offset_dict[PCStat.EVADE])
    current_mdf = ctt.byte_prop(_cur_stat_offset_dict[PCStat.MAGIC_DEFENSE])

    def get_current_stat(self, stat: PCStat):
        return self[self._cur_stat_offset_dict[stat]]

    def set_current_stat(self, stat: PCStat, new_value: int):
        self[self._cur_stat_offset_dict[stat]] = new_value

    level = ctt.byte_prop(0x12)
    xp = ctt.bytes_prop(0x13, 3)
    # It looks like 0x16, 0x17 are storing total TP earned?
    # Unused but also incorrect since it ignores double tp bug.

    # 0x1B and 0x1C are Unused according to Warrior Workshop.  We're going to
    # use 0x1B (always 0 in vanilla) to store the reassignment for dc flag.

    # Use 0x80 to see whether we're using it as a reassignment and use 0x7F
    # (really 0x07) to store the reassigned_char
    assigned_char = ctt.byte_prop(0x1B, 0x7F, ret_type=ctenums.CharID)
    is_reassigned = ctt.byte_prop(0x1B, 0x80)

    # Warrior Workshop indicates statuses are stored in 0x24 - 0x26

    equipped_helm = ctt.byte_prop(0x27, ret_type=ctenums.ItemID)
    equipped_armor = ctt.byte_prop(0x28, ret_type=ctenums.ItemID)
    equipped_weapon = ctt.byte_prop(0x29, ret_type=ctenums.ItemID)
    equipped_accessory = ctt.byte_prop(0x2A, ret_type=ctenums.ItemID)

    xp_to_next_level = ctt.bytes_prop(0x2B, 2)
    tp_to_next_level = ctt.bytes_prop(0x2D, 2)

    # Important to note that base stats come in a different order than current
    # stats.
    base_pow = ctt.byte_prop(_base_stat_offset_dict[PCStat.POWER])
    base_stm = ctt.byte_prop(_base_stat_offset_dict[PCStat.STAMINA])
    # Base speed is not actually used.
    base_spd = ctt.byte_prop(_base_stat_offset_dict[PCStat.SPEED])
    base_hit = ctt.byte_prop(_base_stat_offset_dict[PCStat.HIT])
    base_evd = ctt.byte_prop(_base_stat_offset_dict[PCStat.EVADE])
    base_mag = ctt.byte_prop(_base_stat_offset_dict[PCStat.MAGIC])
    base_mdf = ctt.byte_prop(_base_stat_offset_dict[PCStat.MAGIC_DEFENSE])

    def get_base_stat(self, stat: PCStat):
        return self[self._base_stat_offset_dict[stat]]

    def set_base_stat(self, stat: PCStat, new_value: int):
        self[self._base_stat_offset_dict[stat]] = new_value

    # For our purposes, this is where we stop.  The rest of the stat block is
    # computed at run time (0xFF on ROM)
    # Stats w/ equipment in 0x36 - 0x3D
    # Computed ATK in 0x3D
    # Computed DEF in 0x3E
    # Computed HP in 0x3F - 0x41
    # The rest might be animation related... or memory cursor?


class _HPMPGrowth(ctt.BinaryData):
    SIZE = 8

    def growth_at_level(self, level: int):
        for ind in range(4):
            max_level = self[2*ind]
            if level <= max_level:
                return self[2*ind + 1]
        raise ValueError(f"Couldn't find {level} in growth data")

    def cumulative_growth_at_level(self, level: int):
        total_growth = 0
        current_level = 0

        for ind in range(4):
            max_level = self[2*ind]
            growth_rate = self[2*ind+1]

            while current_level <= min(max_level, level):
                total_growth += growth_rate
                current_level += 1

        return total_growth

    def get_difference(self, from_level: int, to_level: int):
        '''
        Returns the change in HP/MP when going from from_level to to_level.
        The value may be negative when from_level > to_level.
        '''
        return (
            self.cumulative_growth_at_level(to_level) -
            self.cumulative_growth_at_level(from_level)
        )

    def __str__(self):
        ret = self.__class__.__name__ + ':\n'
        for ind in range(4):
            thresh, incr = self[2*ind], self[2*ind+1]
            ret += f'    Until level {thresh}, {incr} per level\n'

        return ret


class HPGrowth(_HPMPGrowth):
    ROM_RW = ctt.AbsPointerRW(0x01F886)


class MPGrowth(_HPMPGrowth):
    ROM_RW = ctt.AbsPointerRW(0x01F8D1)


class TPThresholds(ctt.BinaryData):
    SIZE = 0x10
    ROM_RW = ctt.AbsPointerRW(0x01F3F4)

    def get_threshold(self, tech_level: int):
        thresh_b = self[tech_level*2: tech_level*2+2]
        return int.from_bytes(thresh_b, 'little')

    def set_threshold(self, tech_level: int, new_thresh: int):
        new_thresh_b = new_thresh.to_bytes(2, 'little')
        self[tech_level*2:tech_level*2+2] = new_thresh_b

    def __str__(self):
        return ' '.join(f'{self.get_threshold(i):04X}' for i in range(8))


class XPThreshholds(ctt.BinaryData):
    '''
    Class for storing XP needed to gain a level.
    '''
    SIZE = 99*2
    ROM_RW = ctt.AbsPointerRW(0x01F83E)

    def get_xp_for_level(self, level: int):
        '''
        Get XP needed to go from level-1 to level
        '''
        return int.from_bytes(self[level*2:level*2+2], 'little')

    def set_xp_for_level(self, level: int):
        '''
        Set the amount of xp needed to go from level-1 to level.
        '''
        self[2*level: 2*level+2] = level.to_bytes(2, 'little')

    def get_cum_xp_for_level(self, level: int):
        '''
        Get XP needed to go from 1 to level.
        '''
        return sum(self.get_xp_for_level(i) for i in range(1, level+1))


class StatGrowth(ctt.BinaryData):
    SIZE = 7
    # $C1/F64A 69 FA 25    ADC #$25FA
    # ...
    # $C1/F656 BF 00 00 CC LDA $CC0000,x
    ROM_RW = ctt.LocalPointerRW(0x01F659, 0x01F64B)

    _stat_offset_dict: dict[PCStat, int] = {
        PCStat.POWER: 0,
        PCStat.STAMINA: 1,
        PCStat.SPEED: 2,
        PCStat.MAGIC: 5,
        PCStat.HIT: 3,
        PCStat.EVADE: 4,
        PCStat.MAGIC_DEFENSE: 6
    }

    pow_growth = ctt.byte_prop(_stat_offset_dict[PCStat.POWER])
    stm_growth = ctt.byte_prop(_stat_offset_dict[PCStat.STAMINA])
    # Speed growth is unused
    spd_growth = ctt.byte_prop(_stat_offset_dict[PCStat.SPEED])
    hit_growth = ctt.byte_prop(_stat_offset_dict[PCStat.HIT])
    evd_growth = ctt.byte_prop(_stat_offset_dict[PCStat.EVADE])
    mag_growth = ctt.byte_prop(_stat_offset_dict[PCStat.MAGIC])
    mdf_growth = ctt.byte_prop(_stat_offset_dict[PCStat.MAGIC_DEFENSE])

    def get_stat_growth(self, stat: PCStat):
        return self[self._stat_offset_dict[stat]]

    def set_stat_growth(self, stat: PCStat, new_value: int):
        self[self._stat_offset_dict[stat]] = new_value


class TechLevelRW(ctt.LocalPointerRW):

    def write_data_to_ct_rom(self, ct_rom: ctrom.CTRom,
                             data: bytes,
                             record_num: int = 0):
        mark_used = ctrom.freespace.FSWriteType.MARK_USED
        ctt.LocalPointerRW.write_data_to_ct_rom(self, ct_rom, data, record_num)
        start = ctt.LocalPointerRW.get_data_start_from_ctrom(self, ct_rom)

        # Write current tech level
        ct_rom.rom_data.seek(start+record_num)
        ct_rom.rom_data.write(data[0:1])
        # Write techs learned bitfield
        ct_rom.rom_data.seek(start+record_num+7)
        ct_rom.rom_data.write(self.int_to_bitfield(data[0]), mark_used)

    def free_data_on_ct_rom(self, ct_rom: ctrom.CTRom, num_bytes: int,
                            record_num: int = 0):
        ctt.LocalPointerRW.free_data_on_ct_rom(self, ct_rom, num_bytes,
                                               record_num)
        mark_free = ctrom.freespace.FSWriteType.MARK_FREE
        start = self.get_data_start_from_ctrom(ct_rom)
        start += 7
        ct_rom.rom_data.space_manager.mark_block(
            (start, start+num_bytes), mark_free
        )

    @staticmethod
    def int_to_bitfield(data: int) -> bytes:
        return bytes([0x100 - (1 << (8-data))])


class TechLevel(ctt.BinaryData):
    '''
    Class for keeping track of a player's tech level.
    '''
    SIZE = 1
    # This is also copying all player stats, so take care when repointing.
    # $C2/9583 A2 00 00    LDX #$0000   # source offset
    # $C2/9586 A0 00 26    LDY #$2600
    # $C2/9589 A9 7F 02    LDA #$027F
    # $C2/958C 54 7E 4F    MVN CC 7E
    ROM_RW = TechLevelRW(0x02958E, 0x029584, 0x230)

    tech_level = ctt.byte_prop(
        0, 0xFF,
        input_filter=lambda obj, val: min(max(val, 0), 8)
    )


class PCStatData:
    '''
    A class for storing the PC-specific stat information.  Note that this does
    not include xp thresholds because that is shared among all PCs.

    Note that this class is for storing the data, not for implementing the
    game logic behind stats.
    '''
    def __init__(self,
                 stat_block: StatBlock,
                 stat_growth: StatGrowth,
                 hp_growth: HPGrowth,
                 mp_growth: MPGrowth,
                 tech_level: TechLevel,
                 tp_threshholds: TPThresholds):
        self.stat_block = StatBlock(stat_block)
        self.stat_growth = StatGrowth(stat_growth)
        self.hp_growth = HPGrowth(hp_growth)
        self.mp_growth = MPGrowth(mp_growth)
        self.tech_level = TechLevel(tech_level)
        self.tp_threshholds = TPThresholds(tp_threshholds)

    def to_jot_json(self):
        # Copying from the old statcompute.py
        stats = {
            'max_hp': self.stat_block.max_hp,
            'max_mp': self.stat_block.max_mp,
            'level': self.stat_block.level
        }
        stat_ids = [PCStat.POWER, PCStat.STAMINA, PCStat.SPEED, PCStat.HIT,
                    PCStat.EVADE, PCStat.MAGIC, PCStat.MAGIC_DEFENSE]
        stat_names = ['pow', 'stm', 'spd', 'hit', 'evd', 'mag', 'mdf']

        for stat_id, name in zip(stat_ids, stat_names):
            stats[name] = self.stat_block.get_current_stat(stat_id)
            stats[name+'_growth'] = \
                self.stat_block.get_base_stat(stat_id)

        ret_dict = {}
        if self.stat_block.is_reassigned:
            ret_dict['assignment'] = str(self.stat_block.assigned_char)
        ret_dict['stats'] = stats
        return ret_dict

    @classmethod
    def read_from_ctrom(cls, ct_rom: ctrom.CTRom,
                        pc_id: ctenums.CharID) -> PCStatData:
        # pc_id = int(pc_id)
        stat_block = StatBlock.read_from_ctrom(ct_rom, pc_id)
        stat_growth = StatGrowth.read_from_ctrom(ct_rom, pc_id)
        hp_growth = HPGrowth.read_from_ctrom(ct_rom, pc_id)
        mp_growth = MPGrowth.read_from_ctrom(ct_rom, pc_id)
        tech_level = TechLevel.read_from_ctrom(ct_rom, pc_id)
        tp_threshholds = TPThresholds.read_from_ctrom(ct_rom, pc_id)

        return PCStatData(stat_block, stat_growth, hp_growth, mp_growth,
                          tech_level, tp_threshholds)

    def write_to_ctrom(self, ct_rom: ctrom.CTRom, pc_id: ctenums.CharID):
        # pc_id = int(pc_id)
        self.stat_block.write_to_ctrom(ct_rom, pc_id)
        self.stat_growth.write_to_ctrom(ct_rom, pc_id)
        self.hp_growth.write_to_ctrom(ct_rom, pc_id)
        self.mp_growth.write_to_ctrom(ct_rom, pc_id)
        self.tech_level.write_to_ctrom(ct_rom, pc_id)
        self.tp_threshholds.write_to_ctrom(ct_rom, pc_id)

    def get_spoiler_string(
            self,
            item_db: Optional[itemdata.ItemDB] = None) -> str:
        '''
        Returns a formatted multi-line string of the the stats in this object.

        One deficiency is that equipment is printed out using the enum name
        rather than looking up the actual item name.
        '''
        sb = self.stat_block
        sg = self.stat_growth
        ret = ''
        ret += f'Level: {sb.level}\t'
        ret += f'Tech Level: {self.tech_level.tech_level}\n'
        ret += f'Max HP: {sb.max_hp}\tMax MP: {sb.max_mp}\n'

        cur_stats = (
            sb.current_pow, sb.current_stm, sb.current_spd,
            sb.current_hit, sb.current_evd, sb.current_mag,
            sb.current_mdf
        )
        cur_stats_str = ' '.join(str(x).rjust(3) for x in cur_stats)
        growths = (
            sg.pow_growth, sg.stm_growth, sg.spd_growth,
            sg.hit_growth, sg.evd_growth, sg.mag_growth,
            sg.mdf_growth
        )
        growths_str = ' '.join(str(x).rjust(3) for x in growths)

        if item_db is None:
            wpn_str = str(sb.equipped_weapon)
            helm_str = str(sb.equipped_helm)
            armor_str = str(sb.equipped_armor)
            acc_str = str(sb.equipped_accessory)
        else:
            wpn_str = item_db[sb.equipped_weapon].get_name_as_str(True)
            helm_str = item_db[sb.equipped_helm].get_name_as_str(True)
            armor_str = item_db[sb.equipped_armor].get_name_as_str(True)
            acc_str = item_db[sb.equipped_accessory].get_name_as_str(True)

        ret += 'Pow Stm Spd Hit Evd Mag Mdf\n'
        ret += cur_stats_str + ' (Current Stats)\n'
        ret += growths_str + ' (Growth/Level, 100 growth = 1 point)\n'
        ret += 'Equipment: \n'
        ret += 'Weapon: '.rjust(15) + wpn_str + '\n'
        ret += 'Helmet: '.rjust(15) + helm_str + '\n'
        ret += 'Armor: '.rjust(15) + armor_str + '\n'
        ret += 'Accessory: '.rjust(15) + acc_str + '\n'

        return ret

    def __str__(self):
        return self.get_spoiler_string(None)


class PCStatsManager:
    '''
    A class for managing each character's stats.  Also includes data that
    influences all characters, such as XP required to gain levels.
    '''
    def __init__(
            self,
            pc_stat_dict: Optional[dict[ctenums.CharID, PCStatData]] = None,
            xp_thresholds: Optional[XPThreshholds] = None):

        self.pc_stat_dict: dict[ctenums.CharID, PCStatData] = {}

        # Copy over entries from parameter pc_stat_dict
        if pc_stat_dict is not None:
            for pc_id in list(ctenums.CharID):
                if pc_id in pc_stat_dict:
                    pc_stats = pc_stat_dict[pc_id]
                    # Copy data to avoid reference issues.
                    self.pc_stat_dict[pc_id] = \
                        PCStatData(pc_stats.stat_block,
                                   pc_stats.stat_growth,
                                   pc_stats.hp_growth,
                                   pc_stats.mp_growth,
                                   pc_stats.tech_level,
                                   pc_stats.tp_threshholds)

        if xp_thresholds is None:
            xp_thresholds = XPThreshholds(
                bytes([0 for x in range(XPThreshholds.SIZE)])
            )
        else:
            self.xp_thresholds = XPThreshholds(xp_thresholds)

    def to_jot_json(self):
        return {
            str(k): self.pc_stat_dict[k].to_jot_json() for k in ctenums.CharID
        }

    @classmethod
    def from_ctrom(cls, ct_rom: ctrom.CTRom) -> PCStatsManager:
        xp_thresholds = XPThreshholds.read_from_ctrom(ct_rom)

        pc_stat_dict = dict()
        for pc_id in list(ctenums.CharID):
            pc_stat_dict[pc_id] = PCStatData.read_from_ctrom(ct_rom, pc_id)

        return PCStatsManager(pc_stat_dict, xp_thresholds)

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        self.xp_thresholds.write_to_ctrom(ct_rom)

        for pc_id in ctenums.CharID:
            self.pc_stat_dict[pc_id].write_to_ctrom(ct_rom, pc_id)

    @staticmethod
    def get_stat_max(stat: PCStat):
        if stat == PCStat.SPEED:
            return 16
        return 99

    # Methods for actually manipulating stats in a way that respects game
    # logic.
    def get_stat_growth(self, pc_id: ctenums.CharID, stat: PCStat):
        sg = self.pc_stat_dict[pc_id].stat_growth
        return sg.get_stat_growth(stat)

    def set_stat_growth(self, pc_id: ctenums.CharID, stat: PCStat,
                        new_value: int):
        sg = self.pc_stat_dict[pc_id].stat_growth
        sg.set_stat_growth(stat, new_value)
        self._update_stat(pc_id, stat)

    def get_base_stat(self, pc_id: ctenums.CharID, stat: PCStat) -> int:
        sb = self.pc_stat_dict[pc_id].stat_block
        return sb.get_base_stat(stat)

    def set_base_stat(self, pc_id: ctenums.CharID, stat: PCStat,
                      new_value: int):
        max_value = self.get_stat_max(stat)
        new_value = min(max_value, new_value)

        sb = self.pc_stat_dict[pc_id].stat_block
        sb.set_base_stat(stat, new_value)
        self._update_stat(pc_id, stat)

    def get_current_stat(self, pc_id: ctenums.CharID, stat: PCStat) -> int:
        '''
        Gets the value of a PC's current stat.

        Current stat just means the value at the PC's current level.
        '''
        sb = self.pc_stat_dict[pc_id].stat_block
        return sb.get_current_stat(stat)

    def set_current_stat(self, pc_id: ctenums.CharID, stat: PCStat,
                         new_value: int):
        '''
        Sets the value of a PC's current stat.

        This really should never be called except for speed.  Speed is unique
        in that the base value and growth are ignored by the game.  Instead,
        the current stat is all that matters.
        '''
        max_value = self.get_stat_max(stat)
        new_value = min(max_value, new_value)

        sb = self.pc_stat_dict[pc_id].stat_block
        sb.set_current_stat(stat, new_value)
        self._update_stat(pc_id, stat)  # Will undo the change except for SPD

    def get_character_assignment(
            self, pc_id: ctenums.CharID) -> ctenums.CharID:
        sb = self.pc_stat_dict[pc_id].stat_block

        if sb.is_reassigned:
            return sb.assigned_char
        return sb.char_id

    def set_character_assignment(self, pc_id: ctenums.CharID,
                                 assigned_pc_id: ctenums.CharID):
        sb = self.pc_stat_dict[pc_id].stat_block

        if sb.is_reassigned:
            print('Warning: Assigning to already assigned character. '
                  'Tech data must be rebuilt.')

        sb.is_reassigned = True
        sb.assigned_char = assigned_pc_id
        
    def _update_stats(self, pc_id: ctenums.CharID):
        for stat in list(PCStat):
            self._update_stat(pc_id, stat)

    def _update_stat(self, pc_id: ctenums.CharID, stat: PCStat):
        '''
        Use the base and stat growth to determine the new current stat.

        The exception is speed which the game does not grow but instead just
        trusts the 'current_spd' value.
        '''
        if stat == PCStat.SPEED:
            return

        stat_data = self.pc_stat_dict[pc_id]
        sb = stat_data.stat_block
        base_stat = sb.get_base_stat(stat)
        stat_growth = stat_data.stat_growth.get_stat_growth(stat)
        new_value = base_stat + (sb.level-1)*stat_growth//100
        sb.set_current_stat(stat, new_value)

    def get_equipped_weapon(self, pc_id: ctenums.CharID) -> ctenums.ItemID:
        stat_block = self.pc_stat_dict[pc_id].stat_block
        return stat_block.equipped_weapon

    def set_equipped_weapon(self, pc_id: ctenums.CharID,
                            new_weapon: ctenums.ItemID):
        stat_block = self.pc_stat_dict[pc_id].stat_block
        stat_block.equipped_weapon = new_weapon

    def get_equipped_armor(self, pc_id: ctenums.CharID) -> ctenums.ItemID:
        stat_block = self.pc_stat_dict[pc_id].stat_block
        return stat_block.equipped_armor

    def set_equipped_armor(self, pc_id: ctenums.CharID,
                           new_armor: ctenums.ItemID):
        stat_block = self.pc_stat_dict[pc_id].stat_block
        stat_block.equipped_armor = new_armor

    def get_equipped_helm(self, pc_id: ctenums.CharID) -> ctenums.ItemID:
        stat_block = self.pc_stat_dict[pc_id].stat_block
        return stat_block.equipped_helm

    def set_equipped_helm(self, pc_id: ctenums.CharID,
                          new_helm: ctenums.ItemID):
        stat_block = self.pc_stat_dict[pc_id].stat_block
        stat_block.equipped_helm = new_helm

    def get_equipped_accessory(self, pc_id: ctenums.CharID) -> ctenums.ItemID:
        stat_block = self.pc_stat_dict[pc_id].stat_block
        return stat_block.equipped_accessory

    def set_equipped_accessory(self, pc_id: ctenums.CharID,
                               new_accessory: ctenums.ItemID):
        stat_block = self.pc_stat_dict[pc_id].stat_block
        stat_block.equipped_accessory = new_accessory

    def get_level(self, pc_id: ctenums.CharID) -> int:
        return self.pc_stat_dict[pc_id].stat_block.level

    def set_level(self, pc_id: ctenums.CharID, new_level: int):
        '''
        Sets the level of the given character and adjusts their stats
        accordingly.
        '''
        stat_data = self.pc_stat_dict[pc_id]

        hp_growth = stat_data.hp_growth
        mp_growth = stat_data.mp_growth
        stat_block = stat_data.stat_block

        orig_level = stat_block.level
        stat_block.max_hp += hp_growth.get_difference(orig_level, new_level)
        stat_block.current_hp = stat_block.max_hp

        stat_block.max_mp += mp_growth.get_difference(orig_level, new_level)
        stat_block.current_mp = stat_block.max_mp

        stat_block.level = new_level
        self._update_stats(pc_id)
        stat_block.xp_to_next_level = \
            self.xp_thresholds.get_xp_for_level(new_level+1)

    def get_tech_level(self, pc_id) -> int:
        return self.pc_stat_dict[pc_id].tech_level.tech_level

    def set_tech_level(self, pc_id: ctenums.CharID, new_tech_level: int):
        stat_data = self.pc_stat_dict[pc_id]
        stat_block = stat_data.stat_block

        # This is stupid, but tech_level is an object with RW info, so
        # we have to do tech_level.tech_level.
        if new_tech_level >= 8:
            stat_data.tech_level.tech_level = 8
            stat_block.all_techs_learned = True
            stat_block.tp_to_next_level = 0xFFFF
        else:
            stat_data.tech_level.tech_level = new_tech_level
            stat_block.all_techs_learned = False
            stat_block.tp_to_next_level = \
                stat_data.tp_threshholds.get_threshold(new_tech_level)
