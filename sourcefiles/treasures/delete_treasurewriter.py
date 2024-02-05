'''
This module provides data types for manipulating spots in the game which can
give a reward.  It also provides an association of ctenums.TreasureID to the
appropriate objects as in a base Jets of Time rom.
'''

import abc
import typing

import byteops
import ctenums
import ctrom
import cttypes as ctt


from eventcommand import EventCommand as EC


RewardType = typing.Union[ctenums.ItemID, int]

class Treasure(abc.ABC):
    '''
    ABC representing a place in the game that can hold a treasure.
    '''
    def __init__(self, reward: RewardType = ctenums.ItemID.MOP):
        self.reward = reward

    def to_jot_json(self):
        return str(self.reward)

    @abc.abstractmethod
    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        pass


class ChestRW(ctt.RomRW):

    def __init__(self, ptr_to_ptr_table: int = 0x00A751):
        self.ptr_to_ptr_table = ptr_to_ptr_table

    def get_data_start(self, ct_rom: ctrom.CTRom) -> int:
        rom = ct_rom.rom_data
        rom.seek(self.ptr_to_ptr_table)

        ptr_table_st = int.from_bytes(rom.read(3), 'little')
        ptr_table_st = byteops.to_file_ptr(ptr_table_st)

        bank = ptr_table_st & 0xFF0000

        rom.seek(ptr_table_st)
        first_ptr = int.from_bytes(rom.read(2), 'little') + bank

        return first_ptr

    def read_data_from_ctrom(self,
                             ct_rom: ctrom.CTRom,
                             num_bytes: int,
                             record_num: int = 0,
                             data_start: int = None) -> bytearray:

        if data_start is None:
            data_start = self.get_data_start(ct_rom)

        ct_rom.rom_data.seek(data_start + num_bytes*record_num)
        return bytearray(ct_rom.rom_data.read(num_bytes))

    def write_data_to_ct_rom(self,
                             ct_rom: ctrom.CTRom,
                             data: bytes,
                             record_num: int = 0,
                             data_start: int = None):
        '''
        Write data to a ctrom.CTRom.  If the target data is arranged in 
        records of length len(data), write to record number record_num.
        '''
        if data_start is None:
            data_start = self.get_data_start(ct_rom)

        ct_rom.rom_data.seek(data_start + len(data)*record_num)
        ct_rom.rom_data.write(data)


    def free_data_on_ct_rom(self, ct_rom: ctrom.CTRom,
                            num_bytes: int,
                            record_num: int = 0,
                            start_addr: int = None,
                            data_start: int = None):
        '''
        Mark the data on the ROM that would be read/written as free
        '''
        space_man = ct_rom.rom_data.space_manager

        if data_start is None:
            data_start = self.get_data_start(ct_rom)

        start = data_start + num_bytes*record_num
        end = start + num_bytes

        space_man.mark_block((start, end),
                             ctrom.freespace.FSWriteType.MARK_FREE)


class ChestTreasureData(ctt.BinaryData):
    '''
    This class represents the data on the rom for a treasure chest.
    '''
    SIZE = 4
    ROM_RW = ChestRW(0x00A751)

    x_coord = ctt.byte_prop(0)
    y_coord = ctt.byte_prop(1)
    has_gold = ctt.bytes_prop(2, 2, 0x8000)

    @property
    def gold(self) -> int:
        if not self.has_gold:
            raise ValueError('Chest data is not set to contain gold')

        return byteops.get_masked_range(self, 2, 2, 0x7FFF) * 2

    @gold.setter
    def gold(self, gold_amt: int):
        if gold_amt < 0:
            raise ValueError('Gold must be non-negative.')

        if gold_amt > 0xFFFE:
            raise ValueError('Gold must be at most 0xFFFE = 65534')

        self.has_gold = True
        byteops.set_masked_range(self, 2, 2, 0x7FFF, gold_amt // 2)

    _is_empty = ctt.bytes_prop(2, 2, 0x4000)

    @property
    def is_empty(self) -> bool:
        if self.has_gold:
            return False

        return self._is_empty

    _held_item = ctt.bytes_prop(2, 2, 0x3FFF, ret_type=ctenums.ItemID)

    @property
    def held_item(self) -> ctenums.ItemID:
        if self.has_gold:
            raise ValueError('Chest data is set to contain gold.')

        return self._held_item

    @held_item.setter
    def held_item(self, item: ctenums.ItemID):
        item = ctenums.ItemID(item)
        if item == ctenums.ItemID.NONE:
            self._is_empty = True
            self.has_gold = False
            self._held_item = 0

        self.has_gold = False
        self._is_empty = False
        self._held_item = item

    def is_copying_location(self) -> bool:
        return self.x_coord == self.y_coord == 0


    @property
    def reward(self) -> RewardType:
        if self.is_empty:
            return ctenums.ItemID.NONE

        if self.has_gold:
            return self.gold

        return self._held_item

    @reward.setter
    def reward(self, val: RewardType):
        if isinstance(val, ctenums.ItemID):
            self.held_item = val

        self.gold = val

    @property
    def copy_location(self) -> ctenums.LocID:
        if self.x_coord != 0 or self.y_coord != 0:
            raise ValueError('X and Y coordinates are nonzero')

        return ctenums.LocID(int.from_bytes(self[2:4], 'little'))

    @copy_location.setter
    def copy_location(self, loc_id: ctenums.LocID):
        self.x_coord = 0
        self.y_coord = 0

        self[2:4] = int.to_bytes(loc_id, 2, 'little')


class ChestTreasure(Treasure):
    '''
    A class which represents a treasure chest.
    '''
    def __init__(self, chest_index: int,
                 reward: RewardType = ctenums.ItemID.MOP):
        Treasure.__init__(self, reward)
        self.chest_index = chest_index

    def write_to_ctrom(self, ct_rom: ctrom.CTRom,
                       data_start: int = None):

        chest_rw = ChestRW(0x00A751)
        if data_start is None:
            data_start = chest_rw.get_data_start(ct_rom)

        # Read that current chest on the rom and just update the reward part
        current_data = ChestTreasureData(
            chest_rw.read_data_from_ctrom(
                ct_rom, ChestTreasureData.SIZE, self.chest_index, data_start
            )
        )
        current_data.reward = self.reward
        chest_rw.write_data_to_ct_rom(
            ct_rom, current_data, self.chest_index, data_start
        )


class ScriptTreasure(Treasure):
    '''
    A class for writing rewards to places in a script where a reward can be
    gained.
    '''
    def __init__(self, location: ctenums.LocID,
                 object_id: int, function_id: int,
                 reward: RewardType = ctenums.ItemID.MOP, item_num=0):
        Treasure.__init__(self, reward)
        self.location = location
        self.object_id = object_id
        self.function_id = function_id
        self.item_num = item_num

    def __repr__(self):
        x = (
            f"{type(self).__name__}(location={self.location}, " +
            f"object_id={self.object_id}, function_id={self.function_id},  " +
            f"held_item={self.held_item}, "
            f"item_num={self.item_num})"
        )
        return x

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        '''
        Insert the desired reward into the event script on the ctrom.
        '''
        script = ct_rom.script_manager.get_script(self.location)
        fn_start = script.get_function_start(self.object_id, self.function_id)
        fn_end = script.get_function_end(self.object_id, self.function_id)

        pos = fn_start
        num_mem_set_cmds_found = 0
        mem_set_pos = None

        num_add_rwd_cmds_found = 0
        add_rwd_pos = None

        while True:
            # Commands:
            #   0x4E - Set script memory.  Look for setting 0x7F0200 (item)
            #   0xCA - Add item.
            #   0xCD - Add gold.

            # Loop until we reach the appropriate number of set memory and
            # add gold/item commands
            pos, cmd = script.find_command([0x4E, 0xCA, 0xCD], pos, fn_end)

            if pos is None:
                raise ValueError('Failed to find item setting commands.')

            if cmd.command == 0x4E:
                # Writing to 0x7F0200 is means the last argument is 0
                if cmd.args[-1] == 0:
                    num_mem_set_cmds_found += 1
                    if num_mem_set_cmds_found == self.item_num+1:
                        mem_set_pos = pos
            elif cmd.command in (0xCA, 0xCD):
                num_add_rwd_cmds_found += 1
                if num_add_rwd_cmds_found == self.item_num+1:
                    add_rwd_pos = pos

            if mem_set_pos is not None and add_rwd_pos is not None:
                break

            pos += len(cmd)

        # The mem setting and reward adding should be paired up.  So we should
        # have the same number of each.
        if num_mem_set_cmds_found != num_add_rwd_cmds_found:
            err_str = self.__repr__().replace('\n', '\n\t')
            err_str += \
                'Error in setting item:\n\t{err_str}\n'\
                f'mem_set count = {num_mem_set_cmds_found} but '\
                f'reward count = {num_add_rwd_cmds_found}'
            raise ValueError(err_str)

        text_cmds = [0xBB, 0xC1, 0xC2]

        if isinstance(self.reward, ctenums.ItemID):
            # Update the got reward text.
            if self.reward == ctenums.ItemID.NONE:
                # Change the Got item text.
                new_str_ind = script.add_py_string(
                    "{line break}           Got Nothing!{null}"
                )
            else:
                new_str_ind = script.add_py_string(
                    "{line break}          Got 1 {item}!{null}"
                )

            pos, cmd = script.find_command(text_cmds, mem_set_pos, fn_end)
            script.data[pos+1] = new_str_ind

            # Update the mem_set and add_rwd locations
            script.data[mem_set_pos+1] = int(self.reward)
            script.data[add_rwd_pos+1] = int(self.reward)

        else:  # The reward is gold
            new_str_ind = script.add_py_string(
                f"{{line break}}           Got {self.reward}G!{{null}}"
            )
            pos, cmd = script.find_command(text_cmds, mem_set_pos, fn_end)
            script.data[pos+1] = new_str_ind

            add_gold_cmd = EC.add_gold(self.reward)

            # Note, we do insert then add because of weirdness if this happens
            # to be at the end of an if-block.
            script.insert_commands(add_gold_cmd.to_bytearray(), add_rwd_pos)
            script.delete_commands(add_rwd_pos+len(add_gold_cmd), 1)

            # Also note, we keep the mem set command intact in case we ever
            # want to use this method to set this ScriptTreasure another time.


class BekklerTreasure(ScriptTreasure):
    '''
    Treasure type for setting the Bekkler key item.  Needs extra work because
    the check is split over two locations.
    '''
    def __init__(self,
                 location: ctenums.LocID,
                 object_id: int, function_id: int,
                 held_item: ctenums.ItemID = ctenums.ItemID.MOP,
                 item_num=0,
                 bekkler_location: ctenums.LocID = ctenums.LocID.BEKKLERS_LAB,
                 bekkler_object_id: int = 0x0B,
                 bekkler_function_id: int = 0x01):
        ScriptTreasure.__init__(
            self, location, object_id, function_id, held_item, item_num
        )

        self.bekkler_location = bekkler_location
        self.bekkler_object_id = bekkler_object_id
        self.bekkler_function_id = bekkler_function_id

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        ScriptTreasure.write_to_ctrom(self, ct_rom)
        self.write_bekkler_name_to_ct_rom(ct_rom)

    def write_bekkler_name_to_ct_rom(self, ct_rom: ctrom.CTRom):
        script = ct_rom.script_manager.get_script(self.bekkler_location)

        st = script.get_function_start(self.bekkler_object_id,
                                       self.bekkler_function_id)
        end = script.get_function_end(self.bekkler_object_id,
                                      self.bekkler_function_id)

        pos, _ = script.find_command([0x4F], st, end)
        script.data[pos+1] = int(self.held_item)

            

def get_complete_treasure_dict() -> dict[ctenums.TreasureID, Treasure]:
    '''
    Return a dictionary of all possible TreasureIDs to their corresponding
    treasure objects.
    '''
    LocID = ctenums.LocID
    TID = ctenums.TreasureID

    ret_dict: dict[TID, LocID] = {
        TID.TRUCE_MAYOR_1F: ChestTreasure(0x02),
        TID.TRUCE_MAYOR_2F: ChestTreasure(0x03),
        TID.KINGS_ROOM_1000: ChestTreasure(0x04),
        TID.QUEENS_ROOM_1000: ChestTreasure(0x05),
        TID.GUARDIA_BASEMENT_1: ChestTreasure(0x06),
        TID.GUARDIA_BASEMENT_2: ChestTreasure(0x07),
        TID.GUARDIA_BASEMENT_3: ChestTreasure(0x08),
        # non-cs
        TID.GUARDIA_JAIL_FRITZ_STORAGE: ChestTreasure(0x09),
        # end non-cs
        TID.FOREST_RUINS: ChestTreasure(0x0A),
        TID.HECKRAN_CAVE_SIDETRACK: ChestTreasure(0x0B),
        TID.HECKRAN_CAVE_ENTRANCE: ChestTreasure(0x0C),
        TID.HECKRAN_CAVE_1: ChestTreasure(0x0D),
        TID.HECKRAN_CAVE_2: ChestTreasure(0x0E),
        TID.PORRE_MAYOR_2F: ChestTreasure(0x0F),
        # non-cs
        TID.GUARDIA_JAIL_CELL: ChestTreasure(0x10),
        TID.GUARDIA_JAIL_OMNICRONE_1: ChestTreasure(0x11),
        TID.GUARDIA_JAIL_OMNICRONE_2: ChestTreasure(0x12),
        TID.GUARDIA_JAIL_OMNICRONE_3: ChestTreasure(0x13),
        TID.GUARDIA_JAIL_HOLE_1: ChestTreasure(0x14),
        TID.GUARDIA_JAIL_HOLE_2: ChestTreasure(0x15),
        TID.GUARDIA_JAIL_OUTER_WALL: ChestTreasure(0x16),
        TID.GUARDIA_JAIL_OMNICRONE_4: ChestTreasure(0x17),
        TID.GUARDIA_JAIL_FRITZ: ChestTreasure(0x18),
        # end non-cs
        TID.GIANTS_CLAW_KINO_CELL: ChestTreasure(0x19),
        TID.GIANTS_CLAW_TRAPS: ChestTreasure(0x1A),
        TID.TRUCE_CANYON_1: ChestTreasure(0x1B),
        TID.TRUCE_CANYON_2: ChestTreasure(0x1C),
        TID.KINGS_ROOM_600: ChestTreasure(0x1D),
        TID.QUEENS_ROOM_600: ChestTreasure(0x1E),
        TID.ROYAL_KITCHEN: ChestTreasure(0x1F),
        # non-cs
        TID.MAGUS_CASTLE_RIGHT_HALL: ChestTreasure(0x20),
        # end non-cs
        TID.MANORIA_CATHEDRAL_1: ChestTreasure(0x21),
        TID.MANORIA_CATHEDRAL_2: ChestTreasure(0x22),
        TID.MANORIA_CATHEDRAL_3: ChestTreasure(0x23),
        TID.MANORIA_INTERIOR_1: ChestTreasure(0x24),
        TID.MANORIA_INTERIOR_2: ChestTreasure(0x25),
        TID.MANORIA_INTERIOR_3: ChestTreasure(0x26),
        TID.MANORIA_INTERIOR_4: ChestTreasure(0x27),
        TID.CURSED_WOODS_1: ChestTreasure(0x28),
        TID.CURSED_WOODS_2: ChestTreasure(0x29),
        TID.FROGS_BURROW_RIGHT: ChestTreasure(0x2A),
        TID.DENADORO_MTS_SCREEN2_1: ChestTreasure(0x2B),
        TID.DENADORO_MTS_SCREEN2_2: ChestTreasure(0x2C),
        TID.DENADORO_MTS_SCREEN2_3: ChestTreasure(0x2D),
        TID.DENADORO_MTS_FINAL_1: ChestTreasure(0x2E),
        TID.DENADORO_MTS_FINAL_2: ChestTreasure(0x2F),
        TID.DENADORO_MTS_FINAL_3: ChestTreasure(0x30),
        TID.DENADORO_MTS_WATERFALL_TOP_1: ChestTreasure(0x31),
        TID.DENADORO_MTS_WATERFALL_TOP_2: ChestTreasure(0x32),
        TID.DENADORO_MTS_WATERFALL_TOP_3: ChestTreasure(0x33),
        TID.DENADORO_MTS_WATERFALL_TOP_4: ChestTreasure(0x34),
        TID.DENADORO_MTS_WATERFALL_TOP_5: ChestTreasure(0x35),
        TID.DENADORO_MTS_ENTRANCE_1: ChestTreasure(0x36),
        TID.DENADORO_MTS_ENTRANCE_2: ChestTreasure(0x37),
        TID.DENADORO_MTS_SCREEN3_1: ChestTreasure(0x38),
        TID.DENADORO_MTS_SCREEN3_2: ChestTreasure(0x39),
        TID.DENADORO_MTS_SCREEN3_3: ChestTreasure(0x3A),
        TID.DENADORO_MTS_SCREEN3_4: ChestTreasure(0x3B),
        TID.DENADORO_MTS_AMBUSH: ChestTreasure(0x3C),
        TID.DENADORO_MTS_SAVE_PT: ChestTreasure(0x3D),
        TID.FIONAS_HOUSE_1: ChestTreasure(0x3E),
        TID.FIONAS_HOUSE_2: ChestTreasure(0x3F),
        # Block of non-Chronosanity chests
        TID.SUNKEN_DESERT_B1_NW: ChestTreasure(0x40),
        TID.SUNKEN_DESERT_B1_NE: ChestTreasure(0x41),
        TID.SUNKEN_DESERT_B1_SE: ChestTreasure(0x42),
        TID.SUNKEN_DESERT_B1_SW: ChestTreasure(0x43),
        TID.SUNKEN_DESERT_B2_NW: ChestTreasure(0x44),
        TID.SUNKEN_DESERT_B2_N: ChestTreasure(0x45),
        TID.SUNKEN_DESERT_B2_E: ChestTreasure(0x46),
        TID.SUNKEN_DESERT_B2_SE: ChestTreasure(0x47),
        TID.SUNKEN_DESERT_B2_SW: ChestTreasure(0x48),
        TID.SUNKEN_DESERT_B2_W: ChestTreasure(0x49),
        TID.SUNKEN_DESERT_B2_CENTER: ChestTreasure(0x4A),
        TID.MAGUS_CASTLE_GUILLOTINE_1: ChestTreasure(0x4B),
        TID.MAGUS_CASTLE_GUILLOTINE_2: ChestTreasure(0x4C),
        TID.MAGUS_CASTLE_SLASH_ROOM_1: ChestTreasure(0x4D),
        TID.MAGUS_CASTLE_SLASH_ROOM_2: ChestTreasure(0x4E),
        TID.MAGUS_CASTLE_STATUE_HALL: ChestTreasure(0x4F),
        TID.MAGUS_CASTLE_FOUR_KIDS: ChestTreasure(0x50),
        TID.MAGUS_CASTLE_OZZIE_1: ChestTreasure(0x51),
        TID.MAGUS_CASTLE_OZZIE_2: ChestTreasure(0x52),
        TID.MAGUS_CASTLE_ENEMY_ELEVATOR: ChestTreasure(0x53),
        # end non-CS block
        TID.OZZIES_FORT_GUILLOTINES_1: ChestTreasure(0x54),
        TID.OZZIES_FORT_GUILLOTINES_2: ChestTreasure(0x55),
        TID.OZZIES_FORT_GUILLOTINES_3: ChestTreasure(0x56),
        TID.OZZIES_FORT_GUILLOTINES_4: ChestTreasure(0x57),
        TID.OZZIES_FORT_FINAL_1: ChestTreasure(0x58),
        TID.OZZIES_FORT_FINAL_2: ChestTreasure(0x59),
        TID.GIANTS_CLAW_CAVES_1: ChestTreasure(0x5A),
        TID.GIANTS_CLAW_CAVES_2: ChestTreasure(0x5B),
        TID.GIANTS_CLAW_CAVES_3: ChestTreasure(0x5C),
        TID.GIANTS_CLAW_CAVES_4: ChestTreasure(0x5D),
        TID.GIANTS_CLAW_ROCK: ChestTreasure(0x5E),
        TID.GIANTS_CLAW_CAVES_5: ChestTreasure(0x5F),
        TID.YAKRAS_ROOM: ChestTreasure(0x60),
        TID.MANORIA_SHRINE_SIDEROOM_1: ChestTreasure(0x61),
        TID.MANORIA_SHRINE_SIDEROOM_2: ChestTreasure(0x62),
        TID.MANORIA_BROMIDE_1: ChestTreasure(0x63),
        TID.MANORIA_BROMIDE_2: ChestTreasure(0x64),
        TID.MANORIA_BROMIDE_3: ChestTreasure(0x65),
        TID.MANORIA_SHRINE_MAGUS_1: ChestTreasure(0x66),
        TID.MANORIA_SHRINE_MAGUS_2: ChestTreasure(0x67),
        TID.BANGOR_DOME_SEAL_1: ChestTreasure(0x68),
        TID.BANGOR_DOME_SEAL_2: ChestTreasure(0x69),
        TID.BANGOR_DOME_SEAL_3: ChestTreasure(0x6A),
        TID.TRANN_DOME_SEAL_1: ChestTreasure(0x6B),
        TID.TRANN_DOME_SEAL_2: ChestTreasure(0x6C),
        TID.LAB_16_1: ChestTreasure(0x6D),
        TID.LAB_16_2: ChestTreasure(0x6E),
        TID.LAB_16_3: ChestTreasure(0x6F),
        TID.LAB_16_4: ChestTreasure(0x70),
        TID.ARRIS_DOME_RATS: ChestTreasure(0x71),
        TID.ARRIS_DOME_SEAL_1: ChestTreasure(0x72),
        TID.ARRIS_DOME_SEAL_2: ChestTreasure(0x73),
        TID.ARRIS_DOME_SEAL_3: ChestTreasure(0x74),
        TID.ARRIS_DOME_SEAL_4: ChestTreasure(0x75),
        # Non-CS
        TID.REPTITE_LAIR_SECRET_B2_NE_RIGHT: ChestTreasure(0x76),
        #
        TID.LAB_32_1: ChestTreasure(0x77),
        # Non-CS
        TID.LAB_32_RACE_LOG: ChestTreasure(0x78),
        # end non-cs
        TID.FACTORY_LEFT_AUX_CONSOLE: ChestTreasure(0x79),
        TID.FACTORY_LEFT_SECURITY_RIGHT: ChestTreasure(0x7A),
        TID.FACTORY_LEFT_SECURITY_LEFT: ChestTreasure(0x7B),
        TID.FACTORY_RIGHT_FLOOR_TOP: ChestTreasure(0x7C),
        TID.FACTORY_RIGHT_FLOOR_LEFT: ChestTreasure(0x7D),
        TID.FACTORY_RIGHT_FLOOR_BOTTOM: ChestTreasure(0x7E),
        TID.FACTORY_RIGHT_FLOOR_SECRET: ChestTreasure(0x7F),
        TID.FACTORY_RIGHT_CRANE_UPPER: ChestTreasure(0x80),
        TID.FACTORY_RIGHT_CRANE_LOWER: ChestTreasure(0x81),
        TID.FACTORY_RIGHT_INFO_ARCHIVE: ChestTreasure(0x82),
        # Non-CS
        TID.FACTORY_RUINS_GENERATOR: ChestTreasure(0x83),
        # end non-cs
        TID.SEWERS_1: ChestTreasure(0x84),
        TID.SEWERS_2: ChestTreasure(0x85),
        TID.SEWERS_3: ChestTreasure(0x86),
        # Non-CS
        TID.DEATH_PEAK_SOUTH_FACE_KRAKKER: ChestTreasure(0x87),
        TID.DEATH_PEAK_SOUTH_FACE_SPAWN_SAVE: ChestTreasure(0x88),
        TID.DEATH_PEAK_SOUTH_FACE_SUMMIT: ChestTreasure(0x89),
        TID.DEATH_PEAK_FIELD: ChestTreasure(0x8A),
        # End Non-CS block
        TID.GENO_DOME_1F_1: ChestTreasure(0x8B),
        TID.GENO_DOME_1F_2: ChestTreasure(0x8C),
        TID.GENO_DOME_1F_3: ChestTreasure(0x8D),
        TID.GENO_DOME_1F_4: ChestTreasure(0x8E),
        TID.GENO_DOME_ROOM_1: ChestTreasure(0x8F),
        TID.GENO_DOME_ROOM_2: ChestTreasure(0x90),
        TID.GENO_DOME_PROTO4_1: ChestTreasure(0x91),
        TID.GENO_DOME_PROTO4_2: ChestTreasure(0x92),
        TID.FACTORY_RIGHT_DATA_CORE_1: ChestTreasure(0x93),
        TID.FACTORY_RIGHT_DATA_CORE_2: ChestTreasure(0x94),
        # Non-CS
        TID.DEATH_PEAK_KRAKKER_PARADE: ChestTreasure(0x95),
        TID.DEATH_PEAK_CAVES_LEFT: ChestTreasure(0x96),
        TID.DEATH_PEAK_CAVES_CENTER: ChestTreasure(0x97),
        TID.DEATH_PEAK_CAVES_RIGHT: ChestTreasure(0x98),
        # End Non-CS block
        TID.GENO_DOME_2F_1: ChestTreasure(0x99),
        TID.GENO_DOME_2F_2: ChestTreasure(0x9A),
        TID.GENO_DOME_2F_3: ChestTreasure(0x9B),
        TID.GENO_DOME_2F_4: ChestTreasure(0x9C),
        TID.MYSTIC_MT_STREAM: ChestTreasure(0x9D),
        TID.FOREST_MAZE_1: ChestTreasure(0x9E),
        TID.FOREST_MAZE_2: ChestTreasure(0x9F),
        TID.FOREST_MAZE_3: ChestTreasure(0xA0),
        TID.FOREST_MAZE_4: ChestTreasure(0xA1),
        TID.FOREST_MAZE_5: ChestTreasure(0xA2),
        TID.FOREST_MAZE_6: ChestTreasure(0xA3),
        TID.FOREST_MAZE_7: ChestTreasure(0xA4),
        TID.FOREST_MAZE_8: ChestTreasure(0xA5),
        TID.FOREST_MAZE_9: ChestTreasure(0xA6),
        # Non-CS
        TID.REPTITE_LAIR_SECRET_B1_SW: ChestTreasure(0xA7),
        TID.REPTITE_LAIR_SECRET_B1_NE: ChestTreasure(0xA8),
        TID.REPTITE_LAIR_SECRET_B1_SE: ChestTreasure(0xA9),
        TID.REPTITE_LAIR_SECRET_B2_SE_RIGHT: ChestTreasure(0xAA),
        TID.REPTITE_LAIR_SECRET_B2_NE_OR_SE_LEFT: ChestTreasure(0xAB),
        TID.REPTITE_LAIR_SECRET_B2_SW: ChestTreasure(0xAC),
        # End non-CS block
        TID.REPTITE_LAIR_REPTITES_1: ChestTreasure(0xAD),
        TID.REPTITE_LAIR_REPTITES_2: ChestTreasure(0xAE),
        TID.DACTYL_NEST_1: ChestTreasure(0xAF),
        TID.DACTYL_NEST_2: ChestTreasure(0xB0),
        TID.DACTYL_NEST_3: ChestTreasure(0xB1),
        # Non-CS
        TID.GIANTS_CLAW_THRONE_1: ChestTreasure(0xB2),
        TID.GIANTS_CLAW_THRONE_2: ChestTreasure(0xB3),
        # TYRANO_LAIR_THRONE: 0xB4 (Unused?)
        TID.TYRANO_LAIR_TRAPDOOR: ChestTreasure(0xB5),
        TID.TYRANO_LAIR_KINO_CELL: ChestTreasure(0xB6),
        # TYRANO_LAIR Unused? : 0xB7
        TID.TYRANO_LAIR_MAZE_1: ChestTreasure(0xB8),
        TID.TYRANO_LAIR_MAZE_2: ChestTreasure(0xB9),
        TID.TYRANO_LAIR_MAZE_3: ChestTreasure(0xBA),
        TID.TYRANO_LAIR_MAZE_4: ChestTreasure(0xBB),
        # 0xBC - 0xCF - BLACK_OMEN
        TID.BLACK_OMEN_AUX_COMMAND_MID: ChestTreasure(0xBC),
        TID.BLACK_OMEN_AUX_COMMAND_NE: ChestTreasure(0xBD),
        TID.BLACK_OMEN_GRAND_HALL: ChestTreasure(0xBE),
        TID.BLACK_OMEN_NU_HALL_NW: ChestTreasure(0xBF),
        TID.BLACK_OMEN_NU_HALL_W: ChestTreasure(0xC0),
        TID.BLACK_OMEN_NU_HALL_SW: ChestTreasure(0xC1),
        TID.BLACK_OMEN_NU_HALL_NE: ChestTreasure(0xC2),
        TID.BLACK_OMEN_NU_HALL_E: ChestTreasure(0xC3),
        TID.BLACK_OMEN_NU_HALL_SE: ChestTreasure(0xC4),
        TID.BLACK_OMEN_ROYAL_PATH: ChestTreasure(0xC5),
        TID.BLACK_OMEN_RUMINATOR_PARADE: ChestTreasure(0xC6),
        TID.BLACK_OMEN_EYEBALL_HALL: ChestTreasure(0xC7),
        TID.BLACK_OMEN_TUBSTER_FLY: ChestTreasure(0xC8),
        TID.BLACK_OMEN_MARTELLO: ChestTreasure(0xC9),
        TID.BLACK_OMEN_ALIEN_SW: ChestTreasure(0xCA),
        TID.BLACK_OMEN_ALIEN_NE: ChestTreasure(0xCB),
        TID.BLACK_OMEN_ALIEN_NW: ChestTreasure(0xCC),
        TID.BLACK_OMEN_TERRA_W: ChestTreasure(0xCD),
        TID.BLACK_OMEN_TERRA_ROCK: ChestTreasure(0xCE),
        TID.BLACK_OMEN_TERRA_NE: ChestTreasure(0xCF),
        # end non-cs
        TID.ARRIS_DOME_FOOD_STORE: ChestTreasure(0xD0),
        TID.MT_WOE_2ND_SCREEN_1: ChestTreasure(0xD1),
        TID.MT_WOE_2ND_SCREEN_2: ChestTreasure(0xD2),
        TID.MT_WOE_2ND_SCREEN_3: ChestTreasure(0xD3),
        TID.MT_WOE_2ND_SCREEN_4: ChestTreasure(0xD4),
        TID.MT_WOE_2ND_SCREEN_5: ChestTreasure(0xD5),
        TID.MT_WOE_3RD_SCREEN_1: ChestTreasure(0xD6),
        TID.MT_WOE_3RD_SCREEN_2: ChestTreasure(0xD7),
        TID.MT_WOE_3RD_SCREEN_3: ChestTreasure(0xD8),
        TID.MT_WOE_3RD_SCREEN_4: ChestTreasure(0xD9),
        TID.MT_WOE_3RD_SCREEN_5: ChestTreasure(0xDA),
        TID.MT_WOE_1ST_SCREEN: ChestTreasure(0xDB),
        TID.MT_WOE_FINAL_1: ChestTreasure(0xDC),
        TID.MT_WOE_FINAL_2: ChestTreasure(0xDD),
        # Non-cs
        TID.OCEAN_PALACE_MAIN_S: ChestTreasure(0xDE),
        TID.OCEAN_PALACE_MAIN_N: ChestTreasure(0xDF),
        TID.OCEAN_PALACE_E_ROOM: ChestTreasure(0xE0),
        TID.OCEAN_PALACE_W_ROOM: ChestTreasure(0xE1),
        TID.OCEAN_PALACE_SWITCH_NW: ChestTreasure(0xE2),
        TID.OCEAN_PALACE_SWITCH_SW: ChestTreasure(0xE3),
        TID.OCEAN_PALACE_SWITCH_NE: ChestTreasure(0xE4),
        TID.OCEAN_PALACE_SWITCH_SECRET: ChestTreasure(0xE5),
        TID.OCEAN_PALACE_FINAL: ChestTreasure(0xE6),
        # end non-cs
        # FACTORY_RUINS_UNUSED: 0xE7
        TID.GUARDIA_TREASURY_1: ChestTreasure(0xE8),
        TID.GUARDIA_TREASURY_2: ChestTreasure(0xE9),
        TID.GUARDIA_TREASURY_3: ChestTreasure(0xEA),
        TID.QUEENS_TOWER_600: ChestTreasure(0xEB),
        # Non-cs block
        TID.MAGUS_CASTLE_LEFT_HALL: ChestTreasure(0xEC),
        TID.MAGUS_CASTLE_UNSKIPPABLES: ChestTreasure(0xED),
        TID.MAGUS_CASTLE_PIT_E: ChestTreasure(0xEE),
        TID.MAGUS_CASTLE_PIT_NE: ChestTreasure(0xEF),
        TID.MAGUS_CASTLE_PIT_NW: ChestTreasure(0xF0),
        TID.MAGUS_CASTLE_PIT_W: ChestTreasure(0xF1),
        # end non-cs
        TID.KINGS_TOWER_600: ChestTreasure(0xF2),
        TID.KINGS_TOWER_1000: ChestTreasure(0xF3),
        TID.QUEENS_TOWER_1000: ChestTreasure(0xF4),
        TID.GUARDIA_COURT_TOWER: ChestTreasure(0xF5),
        TID.PRISON_TOWER_1000: ChestTreasure(0xF6),
        # GIANTS_CLAW_MAZE Unused: 0xF7
        # DEATH_PEAK_CLIFF Unused: 0xF8
        # Script Chests:
        # Weirdness with Northern Ruins.
        # There's a variable set, only for these
        # locations indicating whether you're in the
        #   0x7F10A3 & 0x10 ->  600
        #   0x7F10A3 & 0x20 -> 1000
        TID.NORTHERN_RUINS_BASEMENT_600: ScriptTreasure(
            location=LocID.NORTHERN_RUINS_BASEMENT,
            object_id=0x08,
            function_id=0x01,
            item_num=1
        ),
        # Frog locked one
        TID.NORTHERN_RUINS_BASEMENT_1000: ScriptTreasure(
            location=LocID.NORTHERN_RUINS_BASEMENT,
            object_id=0x08,
            function_id=0x01,
            item_num=0
        ),
        TID.NORTHERN_RUINS_ANTECHAMBER_LEFT_1000: ScriptTreasure(
            location=LocID.NORTHERN_RUINS_ANTECHAMBER,
            object_id=0x08,
            function_id=0x01,
            item_num=0
        ),
        TID.NORTHERN_RUINS_ANTECHAMBER_LEFT_600: ScriptTreasure(
            location=LocID.NORTHERN_RUINS_ANTECHAMBER,
            object_id=0x08,
            function_id=0x01,
            item_num=1
        ),
        TID.NORTHERN_RUINS_ANTECHAMBER_SEALED_1000: ScriptTreasure(
            location=LocID.NORTHERN_RUINS_ANTECHAMBER,
            object_id=0x10,
            function_id=0x01,
            item_num=0
        ),
        TID.NORTHERN_RUINS_ANTECHAMBER_SEALED_600: ScriptTreasure(
            location=LocID.NORTHERN_RUINS_ANTECHAMBER,
            object_id=0x10,
            function_id=0x01,
            item_num=1
        ),
        TID.NORTHERN_RUINS_BACK_LEFT_SEALED_1000: ScriptTreasure(
            location=LocID.NORTHERN_RUINS_BACK_ROOM,
            object_id=0x10,
            function_id=0x01,
            item_num=0
        ),
        TID.NORTHERN_RUINS_BACK_LEFT_SEALED_600: ScriptTreasure(
            location=LocID.NORTHERN_RUINS_BACK_ROOM,
            object_id=0x10,
            function_id=0x01,
            item_num=1
        ),
        TID.NORTHERN_RUINS_BACK_RIGHT_SEALED_1000: ScriptTreasure(
            location=LocID.NORTHERN_RUINS_BACK_ROOM,
            object_id=0x11,
            function_id=0x01,
            item_num=0
        ),
        TID.NORTHERN_RUINS_BACK_RIGHT_SEALED_600: ScriptTreasure(
            location=LocID.NORTHERN_RUINS_BACK_ROOM,
            object_id=0x11,
            function_id=0x01,
            item_num=1
        ),
        TID.TRUCE_INN_SEALED_600: ScriptTreasure(
            location=LocID.TRUCE_INN_600_2F,
            object_id=0x0C,
            function_id=1,
        ),
        TID.TRUCE_INN_SEALED_1000: ScriptTreasure(
            location=LocID.TRUCE_INN_1000,
            object_id=0x11,
            function_id=0x01
        ),
        TID.PYRAMID_LEFT: ScriptTreasure(
            location=LocID.FOREST_RUINS,
            object_id=0x13,
            function_id=0x01
        ),
        TID.PYRAMID_RIGHT: ScriptTreasure(
            location=LocID.FOREST_RUINS,
            object_id=0x14,
            function_id=0x01
        ),
        TID.PORRE_ELDER_SEALED_1: ScriptTreasure(
            location=LocID.PORRE_ELDER,
            object_id=0x0D,
            function_id=0x01
        ),
        TID.PORRE_ELDER_SEALED_2: ScriptTreasure(
            location=LocID.PORRE_ELDER,
            object_id=0x0E,
            function_id=0x01
        ),
        TID.PORRE_MAYOR_SEALED_1: ScriptTreasure(
            location=LocID.PORRE_MAYOR_2F,
            object_id=0x09,
            function_id=0x01
        ),
        TID.PORRE_MAYOR_SEALED_2: ScriptTreasure(
            location=LocID.PORRE_MAYOR_2F,
            object_id=0x0A,
            function_id=0x01
        ),
        TID.GUARDIA_CASTLE_SEALED_600: ScriptTreasure(
            location=LocID.GUARDIA_CASTLE_KINGS_TOWER_600,
            object_id=0x08,
            function_id=0x01
        ),
        TID.GUARDIA_FOREST_SEALED_600: ScriptTreasure(
            location=LocID.GUARDIA_FOREST_600,
            object_id=0x3E,
            function_id=0x01
        ),
        TID.GUARDIA_FOREST_SEALED_1000: ScriptTreasure(
            location=LocID.GUARDIA_FOREST_DEAD_END,
            object_id=0x12,
            function_id=0x01
        ),
        TID.GUARDIA_CASTLE_SEALED_1000: ScriptTreasure(
            location=LocID.GUARDIA_CASTLE_KINGS_TOWER_1000,
            object_id=0x08,
            function_id=0x01
        ),
        TID.HECKRAN_SEALED_1: ScriptTreasure(
            location=LocID.HECKRAN_CAVE_PASSAGEWAYS,
            object_id=0x0C,
            function_id=0x01,
            item_num=0
        ),
        TID.HECKRAN_SEALED_2: ScriptTreasure(
            location=LocID.HECKRAN_CAVE_PASSAGEWAYS,
            object_id=0x0C,
            function_id=0x01,
            item_num=1
        ),
        TID.MAGIC_CAVE_SEALED: ScriptTreasure(
            location=LocID.MAGIC_CAVE_INTERIOR,
            object_id=0x19,
            function_id=0x01
        ),
        # Key Items
        TID.REPTITE_LAIR_KEY: ScriptTreasure(
            LocID.REPTITE_LAIR_AZALA_ROOM,
            object_id=0x00,
            function_id=0x00
        ),
        TID.MELCHIOR_KEY: ScriptTreasure(
            location=LocID.GUARDIA_REAR_STORAGE,
            object_id=0x17,
            function_id=0x1
        ),
        TID.FROGS_BURROW_LEFT: ScriptTreasure(location=LocID.FROGS_BURROW,
                                              object_id=0x0A,
                                              function_id=0x01),
        TID.MT_WOE_KEY: ScriptTreasure(location=LocID.MT_WOE_SUMMIT,
                                       object_id=0x08,
                                       function_id=0x01),
        TID.FIONA_KEY: ScriptTreasure(location=LocID.FIONAS_SHRINE,
                                      object_id=0x08,
                                      function_id=0x04),
        TID.ARRIS_DOME_DOAN_KEY: ScriptTreasure(
            location=LocID.ARRIS_DOME,
            object_id=0x0F,
            function_id=0x2),
        TID.SUN_PALACE_KEY: ScriptTreasure(location=LocID.SUN_PALACE,
                                           object_id=0x11,
                                           function_id=0x01),
        TID.GENO_DOME_KEY: ScriptTreasure(
            location=LocID.GENO_DOME_MAINFRAME,
            object_id=0x01,
            function_id=0x04
        ),
        TID.GIANTS_CLAW_KEY: ScriptTreasure(
            location=LocID.GIANTS_CLAW_TYRANO,
            object_id=0x0A,
            function_id=0x01
        ),
        TID.KINGS_TRIAL_KEY: ScriptTreasure(
            location=LocID.GUARDIA_REAR_STORAGE,
            object_id=0x02,
            function_id=0x03
        ),
        TID.ZENAN_BRIDGE_KEY: ScriptTreasure(LocID.GUARDIA_THRONEROOM_600,
                                             object_id=0x0F,
                                             function_id=0x00),
        TID.SNAIL_STOP_KEY: ScriptTreasure(LocID.SNAIL_STOP,
                                           object_id=0x09,
                                           function_id=0x01),
        TID.LAZY_CARPENTER: ScriptTreasure(LocID.CHORAS_CARPENTER_1000,
                                           object_id=0x08,
                                           function_id=0x01),
        TID.TABAN_KEY: ScriptTreasure(LocID.LUCCAS_WORKSHOP,
                                      object_id=0x08,
                                      function_id=0x01,
                                      item_num=0),
        TID.DENADORO_MTS_KEY: ScriptTreasure(
            location=LocID.CAVE_OF_MASAMUNE,
            object_id=0x0A,
            function_id=0x2
        ),
        # Other Script Treasures
        TID.TABAN_GIFT_HELM: ScriptTreasure(LocID.LUCCAS_WORKSHOP,
                                            object_id=0x08,
                                            function_id=0x01,
                                            item_num=1),
        TID.TABAN_GIFT_WEAPON: ScriptTreasure(LocID.LUCCAS_WORKSHOP,
                                              object_id=0x08,
                                              function_id=0x01,
                                              item_num=2),
        TID.TRADING_POST_RANGED_WEAPON: ScriptTreasure(
            location=LocID.IOKA_TRADING_POST,
            object_id=0x0C,
            function_id=0x04,
            item_num=0
        ),
        TID.TRADING_POST_ACCESSORY: ScriptTreasure(
            location=LocID.IOKA_TRADING_POST,
            object_id=0x0C,
            function_id=0x04,
            item_num=1
        ),
        TID.TRADING_POST_TAB: ScriptTreasure(
            location=LocID.IOKA_TRADING_POST,
            object_id=0x0C,
            function_id=0x04,
            item_num=2
        ),
        TID.TRADING_POST_MELEE_WEAPON: ScriptTreasure(
            location=LocID.IOKA_TRADING_POST,
            object_id=0x0C,
            function_id=0x04,
            item_num=3
        ),
        TID.TRADING_POST_ARMOR: ScriptTreasure(
            location=LocID.IOKA_TRADING_POST,
            object_id=0x0C,
            function_id=0x04,
            item_num=4
        ),
        TID.TRADING_POST_HELM: ScriptTreasure(
            location=LocID.IOKA_TRADING_POST,
            object_id=0x0C,
            function_id=0x04,
            item_num=5
        ),
        TID.JERKY_GIFT: ScriptTreasure(
            location=LocID.PORRE_MAYOR_1F,
            object_id=0x08,
            function_id=0x01,
            item_num=0
        ),
        TID.DENADORO_ROCK: ScriptTreasure(
            location=LocID.DENADORO_MTS_MASAMUNE_EXTERIOR,
            object_id=0x01,
            function_id=0x07
        ),
        TID.LARUBA_ROCK: ScriptTreasure(
            location=LocID.LARUBA_RUINS,
            object_id=0x0D,
            function_id=0x01
        ),
        TID.KAJAR_ROCK: ScriptTreasure(
            location=LocID.KAJAR_ROCK_ROOM,
            object_id=0x08,
            function_id=0x01
        ),
        # VanillaRando/Extended Keys treausures
        # These will not be valid outside of VanillaRando
        # TID.BEKKLER_KEY: BekklerTreasure(
        #     location=LocID.CRONOS_ROOM,
        #     object_id=0x13, function_id=1,
        #     item_num=0,
        #     bekkler_location=LocID.BEKKLERS_LAB,
        #     bekkler_object_id=0xB, bekkler_function_id=1
        # ),
        # TID.CYRUS_GRAVE_KEY: ScriptTreasure(
        #     location=LocID.NORTHERN_RUINS_HEROS_GRAVE,
        #     object_id=5, function_id=8, item_num=0
        # ),
        # TID.SUN_KEEP_2300: ScriptTreasure(
        #     LocID.SUN_KEEP_2300, 8, 1
        # ),
        # TID.OZZIES_FORT_KEY: ScriptTreasure(
        #     LocID.OZZIES_FORT_THRONE_INCOMPETENCE, 8, 2
        # )
        # Tabs later if they're going to be randomized
        # GUARDIA_FOREST_POWER_TAB_600: auto()
        # GUARDIA_FOREST_POWER_TAB_1000: auto()
        # SUN_KEEP_POWER_TAB_600: auto()
        # MEDINA_ELDER_SPEED_TAB: auto()
        # MEDINA_ELDER_MAGIC_TAB: auto()
    }

    return ret_dict
