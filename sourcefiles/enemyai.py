'''Module for Reading and Manipulating Enemy AI Scripts.'''

from __future__ import annotations
from typing import Optional, Union

import byteops
from ctenums import EnemyID
import ctrom
import ctstrings

_action_lens = [
    4, 4, 6, 1, 1, 3, 1, 4, 1, 2, 3, 5, 4, 3, 1, 2, 4, 10, 16, 3,
    10, 16, 12
]

WritableBytes = Union[bytearray, memoryview]


class AISpaceException(Exception):
    '''Exception to raise when the AI Scripts overflow their space.'''


def print_bytes(data: bytes, pos: Optional[int] = None,
                length: Optional[int] = None):
    '''Helper function for printing bytes in hex.'''
    print(bytes_to_str(data, pos, length))


def bytes_to_str(data: bytes, pos: Optional[int] = None,
                 length: Optional[int] = None):
    '''Convert bytes to a hex string.'''
    if pos is None:
        start = 0
    else:
        start = pos

    if length is None:
        end = len(data)
    else:
        end = start+length

    return ' '.join(f'{x:02X}' for x in data[start:end])


class BattleMessages:
    '''Class to store messages that appear during battle.'''
    PTR_TABLE_LOCAL_PTR = 0x0D0299
    PTR_TABLE_ROM_BANK_PTR = 0x0D02A0

    def __init__(self,
                 strings: Optional[dict[int, ctstrings.CTString]] = None):

        if strings is None:
            strings = {}

        str_dict = {
            x: strings[x] for x in range(0x100)
            if x in strings
        }

        self._strings = str_dict

    def __getitem__(self, index) -> ctstrings.CTString:
        return self._strings[index]

    def __setitem__(self, index: int, string: ctstrings.CTString):
        self._strings[index] = ctstrings.CTString(string)

    def get_msg_as_str(self, index):
        '''Convert the battle message at index to a string.'''
        return self._strings[index].to_ascii()

    def set_msg_from_str(self, index: int, value: str):
        '''Converts the given string to a CTString and sets it at index.'''
        ct_str = ctstrings.CTString.from_str(value)
        if ct_str[-1] != 0:
            ct_str.append(0)
        ct_str.compress()
        self._strings[index] = ct_str

    @classmethod
    def get_ptr_table_file_ptr_from_rom(cls, rom: bytes) -> int:
        '''Find where the battle message pointer table is on the rom.'''
        # ASM Writes 0xCCCBC9 (start of battle msg pointer table) to memory
        # $CD/0298 A2 C9 CB    LDX #$CBC9
        # $CD/029B 8E 0D 02    STX $020D  [$7E:020D]
        # $CD/029E 48          PHA
        # $CD/029F A9 CC       LDA #$CC
        # $CD/02A1 8D 0F 02    STA $020F  [$7E:020F]

        local_ptr = int.from_bytes(rom[0x0D0299:0x0D0299+2], 'little')
        bank = rom[0x0D02A0]
        abs_rom_ptr = bank * 0x10000 + local_ptr
        abs_file_ptr = byteops.to_file_ptr(abs_rom_ptr)

        return abs_file_ptr

    @classmethod
    def set_ptr_table_ptr(cls, rom: WritableBytes, new_file_ptr: int):
        '''Update the location of the battle message pointer table on rom.'''
        local_ptr = new_file_ptr & 0x00FFFF
        bank = byteops.to_rom_ptr(new_file_ptr) >> 16

        rom[cls.PTR_TABLE_LOCAL_PTR:cls.PTR_TABLE_LOCAL_PTR+2] = \
            int.to_bytes(local_ptr, 2, 'little')
        rom[cls.PTR_TABLE_ROM_BANK_PTR] = bank

    @classmethod
    def from_rom(cls, rom: bytes, aidb: Optional[EnemyAIDB] = None):
        '''Read the battle messages from the rom as a BattleMessages object.'''
        # The only reliable way to determine how many strings there are is
        # to scan through the enemy AI.
        if aidb is None:
            aidb = EnemyAIDB.from_rom(rom)

        used_msg_ids = list(aidb.used_msgs)

        abs_file_ptr = cls.get_ptr_table_file_ptr_from_rom(rom)
        bank = abs_file_ptr & 0xFF0000
        str_dict = {}

        for ind in sorted(used_msg_ids):
            ptr_loc = abs_file_ptr + 2*ind
            ptr = int.from_bytes(rom[ptr_loc:ptr_loc+2], 'little')
            ptr += bank

            end = ptr
            while rom[end] != 0x00:
                end += 1

            ct_string = ctstrings.CTString(rom[ptr:end+1])
            str_dict[ind] = ct_string

        return cls(str_dict)

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        '''Write the battle messages back to the rom.'''
        max_ptr_ind = max(self._strings.keys())
        total_str_len = sum(len(x) for x in self._strings.values())
        total_space_needed = 2*(max_ptr_ind+1) + total_str_len

        # Vanilla size: 0x0CDDC6 - 0CCBC9 = 0x11FD
        # Vanilla start: 0x0CCBC9
        ptr_table_st = self.get_ptr_table_file_ptr_from_rom(
            ct_rom.rom_data.getbuffer()
        )

        # Try vanilla location, otherwise use freespace.
        # This maybe is an issue and we need to explicitly free the vanilla
        # space and just let freespace do its thing.
        if ptr_table_st == 0x0CCBC9 and total_space_needed <= 0x11FD:
            write_pos = 0x0CCBC9
        else:
            space_man = ct_rom.rom_data.space_manager
            write_pos = space_man.get_free_addr(total_space_needed)

        rom = ct_rom.rom_data
        data_pos = write_pos + 2*(max_ptr_ind+1)
        for ind in range(max_ptr_ind):
            ptr_loc = write_pos + 2*ind
            rom.seek(ptr_loc)
            rom.write(int.to_bytes(data_pos & 0x00FFFF, 2, 'little'))
            ptr_loc += 2

            if ind in self._strings:
                rom.seek(data_pos)
                string = self._strings[ind]
                rom.write(string)
                data_pos += len(string)

        self.set_ptr_table_ptr(rom.getbuffer(), write_pos)

    def __str__(self):
        ret_str = ''
        for ind in self._strings:
            ret_str += f'{ind:02X}: {self._strings[ind].to_ascii()}\n'

        return ret_str


# From https://www.chronocompendium.com/Term/Enemy_AI.html
_target_str = {
    0x00: 'Nothing',
    0x01: 'All PCs',
    0x02: 'All Enemies',
    0x03: 'Self',
    0x04: 'Attacking PC',
    0x05: 'Random PC',
    0x06: 'Nearest PC',
    0x07: 'Farthest PC',
    0x08: 'PC with lowest HP',
    0x09: 'PCs with 0x1D flags set',
    0x0A: 'PCs with any negative status',
    0x0B: 'PCs with 0x1F flags set',
    0x0C: 'PCs with +Evade, Haste',
    0x0D: 'PCs with shades, specs, shield, barrier, berserk, mp regen',
    0x0E: 'Sleeping PCs',
    0x0F: 'Stopped PCs',
    0x10: 'Chaotic PCs',
    0x11: 'Shielded PCs',
    0x12: 'Barriered PCs',
    0x13: 'PCs with Unused Status 2.10',
    0x14: 'PCs with 1.08 set',
    0x15: 'Other enemies',
    0x16: 'Living enemies',
    0x17: 'Nearest enemy',
    0x18: 'Farthest enemy',
    0x19: 'Enemy with lowest HP',
    0x1A: 'Other enemies with 0x1D flags set',
    0x1B: 'All enemies with 0x1D flags set',
    0x1C: 'Other enemies with negative status',
    0x1D: 'All enemies with negative status',
    0x1E: 'Other enemies with 0x1F flags set',
    0x1F: 'All enemies with 0x1F flags set',
    0x20: 'Other sleeping enemies',
    0x21: 'Other stopped enemies',
    0x22: 'Other chaotic enemies',
    0x23: 'Other barriered enemies',
    0x24: 'Other enemies with 0x1D.02 set',
    0x25: 'Other enemies with 0x19.01 set',
    0x26: 'Other enemy with lowest HP',
    0x27: 'Enemy 03',
    0x28: 'Enemy 04',
    0x29: 'Enemy 05',
    0x2A: 'Enemy 06',
    0x2B: 'Enemy 07',
    0x2C: 'Enemy 08',
    0x2D: 'Enemy 09',
    0x2E: 'Enemy 0A',
    0x2F: 'Random enemy with $7E:AF15.80 set',
    0x30: 'PC1',
    0x31: 'PC2',
    0x32: 'PC3',
    0x33: 'Enemy 3',
    0x34: 'Enemy 4',
    0x35: 'Enemy 5',
    0x36: 'Enemy 6',
    0x37: 'PC with highest HP',
    0x38: 'Random other enemy'
}


# TODO: Avoid repeating the parsing code in every method.
#       (1) Put the script data into a higher level structure that's more
#           simple to interate through.
#       ...OR...
#       (2) Make one parsing function with hooks for other callables to be
#           called during parsing.
#       Probably (1).
class AIScript:
    ''' Class to store an AI Script.'''
    def __init__(self,
                 script_bytes: bytes = b'\xFF\xFF',
                 start_pos: int = 0):
        self.uses_secondary_atk = False
        self.tech_usage: list[int] = []
        self.battle_msg_usage: list[int] = []
        self._data = bytearray()

        # Actually sets the above.  In its own function because it may need
        # to be called outside of object construction.
        self._parse_bytes(script_bytes, start_pos)

    @classmethod
    def find_command(cls, cmd_bytes: bytes, cmd_id: int) -> list[int]:
        ''' Find a given command in the AI Script.'''
        pos = 0
        cmd_inds = []
        for block in range(2):
            while cmd_bytes[pos] != 0xFF:
                while cmd_bytes[pos] != 0xFE:  # Conditions
                    pos += 4

                pos += 1  # Skip terminal 0xFE
                while cmd_bytes[pos] != 0xFE:  # Actions
                    action_id = cmd_bytes[pos]

                    if action_id == cmd_id:
                        cmd_inds.append(pos)

                    if action_id == 0xFF:
                        break
                    size = _action_lens[action_id]
                    pos += size
                pos += 1  # Skip terminal 0xFE
            pos += 1  # Skip terminal 0xFF

        return cmd_inds

    def get_copy(self) -> AIScript:
        '''Returns a deep copy of self.'''
        new_script = AIScript()
        new_script._data = bytearray(self._data)
        new_script.tech_usage = list(self.tech_usage)
        new_script.battle_msg_usage = list(self.battle_msg_usage)
        new_script.uses_secondary_atk = self.uses_secondary_atk

        return new_script

    def change_tech_usage(self, from_tech_id, to_tech_id) -> int:
        '''
        Change the tech used in the script.  Returns number of changes made.
        '''
        pos = 0
        num_changes = 0

        if from_tech_id not in self.tech_usage:
            # print('Warning: tech not in self.tech_usage.')
            pass

        if from_tech_id == to_tech_id:
            return 0

        for block in range(2):
            while self._data[pos] != 0xFF:
                while self._data[pos] != 0xFE:  # Conditions
                    pos += 4

                pos += 1  # Skip terminal 0xFE
                while self._data[pos] != 0xFE:  # Actions
                    action_id = self._data[pos]

                    # The actual tech changing bit
                    if action_id in (2, 0x12):
                        tech_id = self._data[pos+1]
                        if tech_id == from_tech_id:
                            self._data[pos+1] = to_tech_id
                            num_changes += 1

                    if action_id == 0xFF:
                        break

                    size = _action_lens[action_id]
                    pos += size
                pos += 1  # Skip terminal 0xFE
            pos += 1  # Skip terminal 0xFF

        if num_changes > 0 and from_tech_id not in self.tech_usage:
            print('Warning: Made changes when tech not in self.tech_usage')

        if num_changes > 0:
            if from_tech_id in self.tech_usage:
                self.tech_usage.remove(from_tech_id)
            self.tech_usage.append(to_tech_id)

        return num_changes

    def get_as_bytearray(self):
        '''Returns the script's data as a bytearray.'''
        return bytearray(self._data)

    def _parse_bytes(self, data: bytes, start_pos: int = 0):
        '''
        Determine the tech usage, message usage, and secondary attack usage.
        Will insert missing 0xFE terminators if needed.
        '''
        pos = start_pos
        tech_usage = []
        msg_usage = []
        uses_secondary_atk = False

        FE_ins_pos: list[int] = []

        for block in range(2):
            while data[pos] != 0xFF:
                while data[pos] != 0xFE:  # Conditions
                    pos += 4

                pos += 1  # Skip terminal 0xFE
                while data[pos] != 0xFE:  # Actions
                    action_id = data[pos]

                    if action_id == 1 and data[pos+1] == 1:
                        uses_secondary_atk = True

                    if action_id in (2, 0x12):
                        tech_used = data[pos+1]
                        tech_usage.append(tech_used)

                    if action_id in (0x02, 0x0A, 0x0B, 0x0C, 0x0D, 0x0F,
                                     0x10, 0x11, 0x12, 0x14, 0x15, 0x16):
                        size = _action_lens[action_id]
                        msg_used = data[pos+size-1]
                        msg_usage.append(msg_used)

                    if action_id == 0xFF:
                        # insert at start so list is in reverse order
                        FE_ins_pos.insert(0, pos)
                        break
                    size = _action_lens[action_id]
                    pos += size
                pos += 1  # Skip terminal 0xFE
            pos += 1  # Skip terminal 0xFF

        # Fix buggy ai scripts that don't have a terminal 0xFE.
        # Only 0x7F (Red Beast)
        new_data = bytearray(data[start_pos:pos])
        for ins_pos in FE_ins_pos:
            new_data.insert(ins_pos, 0xFE)

        self._data = new_data
        self.tech_usage = list(set(tech_usage))
        self.battle_msg_usage = list(set(msg_usage))
        self.uses_secondary_atk = uses_secondary_atk

    def __len__(self):
        return len(self._data)

    def __str__(self):
        ret_str = ''
        pos = 0
        for block in range(2):

            if block == 0:
                ret_str += 'Actions:\n'
            else:
                ret_str += 'Reactions:\n'

            while self._data[pos] != 0xFF:
                while self._data[pos] != 0xFE:  # Conditions
                    ret_str += bytes_to_str(self._data[pos:pos+4])
                    ret_str += '\n'
                    pos += 4

                pos += 1  # Skip terminal 0xFE
                while self._data[pos] != 0xFE:  # Actions
                    action_id = self._data[pos]
                    if action_id == 0xFF:
                        break

                    size = _action_lens[action_id]
                    ret_str += '\t'
                    ret_str += bytes_to_str(self._data[pos:pos+size])
                    ret_str += '\n'
                    pos += size
                pos += 1  # Skip terminal 0xFE
            pos += 1  # Skip terminal 0xFF

        return ret_str


class EnemyAIDB:
    '''Class to store all AI Scripts along with battle messages.'''
    PTR_TO_AI_PTRS = 0x01AFD7

    # Unused 0xFF is actually used for missing enemies.
    # Not preserving that script can lead to weirdness.
    unused_enemies = (
        EnemyID.LAVOS_3_CENTER_UNK_0B, EnemyID.LAVOS_GIGA_GAIA_RIGHT,
        EnemyID.LAVOS_GIGA_GAIA_LEFT, EnemyID.LAVOS_SUPPORT_UNK_1F,
        EnemyID.LAVOS_SUPPORT_UNK_21, EnemyID.OCTOBINO,
        EnemyID.UNKNOWN_3C, EnemyID.UNKNOWN_44, EnemyID.UNKNOWN_5A,
        EnemyID.UNKNOWN_60, EnemyID.LAVOS_SUPPORT_UNK_67,
        EnemyID.LAVOS_SUPPORT_UNK_77, EnemyID.LAVOS_SUPPORT_UNK_78,
        EnemyID.UNKNOWN_BF, EnemyID.LAVOS_GUARDIAN, EnemyID.LAVOS_HECKRAN,
        EnemyID.LAVOS_ZOMBOR_UPPER, EnemyID.LAVOS_MASA_MUNE,
        EnemyID.LAVOS_NIZBEL, EnemyID.LAVOS_MAGUS, EnemyID.LAVOS_TANK_HEAD,
        EnemyID.LAVOS_TANK_LEFT, EnemyID.LAVOS_TANK_RIGHT,
        EnemyID.LAVOS_GUARDIAN_LEFT, EnemyID.LAVOS_GUARDIAN_RIGHT,
        EnemyID.LAVOS_ZOMBOR_BOTTOM, EnemyID.LAVOS_TYRANO_AZALA,
        EnemyID.LAVOS_TYRANO, EnemyID.LAVOS_GIGA_GAIA_HEAD,
        EnemyID.LAVOS_UNK_E8, EnemyID.LAVOS_UNK_E9, EnemyID.LAVOS_UNK_EA,
        EnemyID.JOHNNY, EnemyID.MAGUS_NO_NAME, EnemyID.UNUSED_FC,
        EnemyID.UNUSED_FD, EnemyID.UNUSED_FE, #EnemyID.UNUSED_FF
    )

    def __init__(self,
                 scripts: Optional[dict[EnemyID, AIScript]] = None,
                 msgs: Optional[BattleMessages] = None):

        if scripts is None:
            scripts = {}

        self.scripts = {x: AIScript() for x in list(EnemyID)}
        for enemy_id in scripts:
            self.scripts[enemy_id] = scripts[enemy_id].get_copy()

        if msgs is None:
            msgs = BattleMessages()
        self.battle_msgs = msgs

        self.tech_to_enemy_usage: dict[int, list[int]] = \
            {x: [] for x in range(0x100)}
        self._build_usage()

    def _build_usage(self):
        used_enemy_ids = (x for x in self.scripts
                          if x not in self.unused_enemies)

        used_msg_ids = []

        for enemy_id in used_enemy_ids:
            script = self.scripts[enemy_id]

            used_msg_ids.extend(script.battle_msg_usage)

            for tech in script.tech_usage:
                self.tech_to_enemy_usage[tech].append(enemy_id)

        self.unused_techs = [
            tech_id for tech_id in range(0x100)
            if not self.tech_to_enemy_usage[tech_id]
            and tech_id not in (0xFE, 0xFF)
        ]

        self.used_msgs = list(set(used_msg_ids))

    def change_tech_in_ai(self,
                          enemy_id: int,
                          from_tech_id: int,
                          to_tech_id: int):
        '''
        Change all instances of using tech from_tech_id to to_tech_id
        '''

        # print(f'Changing {enemy_id} tech {from_tech_id:02X} '
        #       f'to {to_tech_id:02X}')
        script = self.scripts[EnemyID(enemy_id)]
        num_changes = script.change_tech_usage(from_tech_id, to_tech_id)

        if num_changes > 0:
            if to_tech_id in self.unused_techs:
                self.unused_techs.remove(to_tech_id)

            self.tech_to_enemy_usage[from_tech_id].remove(enemy_id)
            if enemy_id not in self.tech_to_enemy_usage[to_tech_id]:
                self.tech_to_enemy_usage[to_tech_id].append(enemy_id)

    def change_enemy_ai(self, changed_enemy_id, copied_enemy_id):
        '''Copy one enemy's AI to another spot.  Update usage stats.'''
        new_script = self.scripts[copied_enemy_id].get_copy()
        orig_script = self.scripts[changed_enemy_id]

        self.scripts[changed_enemy_id] = new_script

        for tech_id in orig_script.tech_usage:
            self.tech_to_enemy_usage[tech_id].remove(changed_enemy_id)

            if not self.tech_to_enemy_usage[tech_id] \
               and tech_id not in self.unused_techs:
                self.unused_techs.append(tech_id)

        for tech_id in new_script.tech_usage:
            self.tech_to_enemy_usage[tech_id].append(changed_enemy_id)

    def get_total_length(self):
        ''' Get the total space requirements of the AI Scripts.'''
        length = 0
        for enemy_id in list(EnemyID):
            if enemy_id not in self.unused_enemies:
                length += len(self.scripts[enemy_id])

        return length

    # Note: Every script is OK except for Johnny (0xF4) which spills into the
    #       next script.  No pointers go to the same script.
    @classmethod
    def from_rom(cls, rom: bytes, restrict_enemies: bool = True):
        '''Read the AI data from the given CTRom.'''
        ai_ptr_start = int.from_bytes(
            rom[cls.PTR_TO_AI_PTRS:cls.PTR_TO_AI_PTRS+3],
            'little'
        )
        ai_ptr_start = byteops.to_file_ptr(ai_ptr_start)

        scripts = {}
        for enemy_id in list(EnemyID):
            if enemy_id not in cls.unused_enemies:
                ptr_st = ai_ptr_start + 2*enemy_id
                ptr = int.from_bytes(rom[ptr_st:ptr_st+2], 'little')
                ptr += 0x0C0000
                scripts[enemy_id] = AIScript(rom, ptr)

        ret_aidb = cls(scripts)
        battle_msgs = BattleMessages.from_rom(rom, ret_aidb)
        ret_aidb.battle_msgs = battle_msgs

        return ret_aidb

    @classmethod
    def from_ctrom(cls, ct_rom: ctrom.CTRom):
        '''Read the AI data from the given CTRom.'''
        return cls.from_rom(ct_rom.rom_data.getbuffer())

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        '''Writes out new AI data to the given CTRom.'''
        # For now, we are confident that removing the unused enemies will
        # leave space for whatever we do.

        # TODO:  Write the pointers anywhere free (contiguous) in bank 0C.
        #        Write the scripts anywhere free (wherever) in bank 0C.
        rom = ct_rom.rom_data
        ai_ptr_start = int.from_bytes(
            rom.getbuffer()[self.PTR_TO_AI_PTRS:self.PTR_TO_AI_PTRS+3],
            'little'
        )
        ai_ptr_pos = byteops.to_file_ptr(ai_ptr_start)

        ai_data_pos = 0x0C8D08
        ai_data_end = 0x0CCBC9

        # This should never be an issue with the removed enemies
        write_length = self.get_total_length()
        if write_length > ai_data_end - ai_data_pos:
            raise AISpaceException

        for i in range(0x100):
            enemy_id = EnemyID(i)
            ptr = ai_data_pos & 0x00FFFF

            rom.seek(ai_ptr_pos)
            rom.write(ptr.to_bytes(2, 'little'))
            ai_ptr_pos += 2

            rom.seek(ai_data_pos)
            if enemy_id not in self.unused_enemies:
                script = self.scripts[enemy_id]
                payload = script.get_as_bytearray()
                rom.write(payload)
                ai_data_pos += len(payload)

        if self.battle_msgs is not None:
            self.battle_msgs.write_to_ctrom(ct_rom)
