from __future__ import annotations
import math
from typing import Tuple

from byteops import to_little_endian, get_value_from_bytes
from enum import Enum, IntEnum, auto


# Small enum to store the synchronization scheme when a function is called
class FuncSync(Enum):
    '''Enum of synchronization schemes for event object function calls.'''
    HALT = auto()
    CONT = auto()
    SYNC = auto()


class Operation(IntEnum):
    '''Enum of operations permitted in event commands'''
    EQUALS = 0
    NOT_EQUALS = 1
    GREATER_THAN = 2
    LESS_THAN = 3
    GREATER_OR_EQUAL = 4
    LESS_OR_EQUAL = 5
    BITWISE_AND_NONZERO = 6
    BITWISE_OR_NONZERO = 7


def is_script_mem(addr: int) -> bool:
    '''Whether an address is in the local script memory.'''
    return 0x7F0200 <= addr < 0x7F0400


def is_local_mem(addr: int):
    '''Whether the address is in the flag memory [0x7F0000,0x7F0200).'''
    return (
        not is_script_mem(addr) and
        0x7F0000 <= addr < 0x7F0200
    )


def is_memory_addr(addr: int):
    return 0x7E0000 < addr < 0x800000


def is_bank_7E(addr: int):
    return 0x7E0000 <= addr < 0x7F0000


def get_offset(script_addr):
    if script_addr % 2 != 0:
        raise ValueError('Script address must be even.')

    return (script_addr - 0x7F0200) // 2


class EventCommand:

    str_commands = [0xBB, 0xC0, 0xC1, 0xC2, 0xC3, 0xC4]
    str_arg_pos = [0, 0, 0, 0, 0, 0]

    fwd_jump_commands = [0x10, 0x12, 0x13, 0x14, 0x15, 0x16, 0x18, 0x1A,
                         0x27, 0x28, 0x2D, 0x30, 0x31, 0x34, 0x35, 0x36,
                         0x37, 0x38, 0x39, 0x3B, 0x3C, 0x3F, 0x40, 0x41,
                         0x42, 0x43, 0x44, 0xC9, 0xCC, 0xCF, 0xD2]

    change_loc_commands = [0xDC, 0xDD, 0xDE, 0xDF, 0xE0, 0xE1, 0xE2]
    # the number of bytes to jump is always the last arg
    fwd_jump_arg_pos = [-1 for i in range(len(fwd_jump_commands))]

    back_jump_commands = [0x11]
    back_jump_arg_pos = [-1]

    conditional_commands = [x for x in fwd_jump_commands
                            if x != 0x10]
    jump_commands = fwd_jump_commands + back_jump_commands

    def __init__(self, command, num_args,
                 arg_lens, arg_descs,
                 name, desc):
        self.command = command
        self.num_args = num_args
        self.arg_lens = arg_lens
        self.arg_descs = arg_descs
        self.name = name
        self.desc = desc

        # These are the actual arguments from the string of bytes in the script
        self.args = []

        # These are the decoded args
        self.logical_args = []

    def __eq__(self, other):
        return self.command == other.command and self.args == other.args

    # Returns coordinates in pixels
    def get_pixel_coordinates(self) -> Tuple[int, int]:
        if self.command == 0x8B:
            return (self.args[0]*0x10+8, self.args[1]*0x10+0x10)

        if self.command == 0x8D:
            return (self.args[0] >> 4, self.args[1] >> 4)

        raise AttributeError('This command does not set coordinates.')

    def to_bytearray(self) -> bytearray:

        x = bytearray()
        x.append(self.command)

        if self.command == 0x4E:
            x += b''.join(to_little_endian(self.args[i], self.arg_lens[i])
                          for i in range(len(self.args)-1))
            x += self.args[-1]
        else:
            x += b''.join(to_little_endian(self.args[i], self.arg_lens[i])
                          for i in range(len(self.args)))

        return x

    @staticmethod
    def set_explore_mode(is_on: bool) -> EventCommand:
        ret_cmd = event_commands[0xE3].copy()
        ret_cmd.args = [0]
        if is_on:
            ret_cmd.args[0] = 1
        else:
            ret_cmd.args[0] = 0

        return ret_cmd

    @staticmethod
    def set_controllable_once() -> EventCommand:
        return EventCommand.generic_zero_arg(0xAF)

    @staticmethod
    def set_controllable_infinite() -> EventCommand:
        return EventCommand.generic_zero_arg(0xB0)

    @staticmethod
    def party_follow() -> EventCommand:
        return EventCommand.generic_zero_arg(0xDA)

    @staticmethod
    def move_party(pc1_x, pc1_y, pc2_x, pc2_y, pc3_x, pc3_y):
        ret_cmd = event_commands[0xD9].copy()
        ret_cmd.args = [pc1_x, pc1_y, pc2_x, pc2_y, pc3_x, pc3_y]
        return ret_cmd

    @staticmethod
    def change_location(location, x_coord, y_coord, facing=0,
                        unk=0, wait_vblank=True) -> EventCommand:
        # There are many different change location commands.  I'll update this
        # as I understand their differences.
        if wait_vblank:
            cmd = 0xE1
        else:
            cmd = 0xE0

        ret_cmd = event_commands[cmd].copy()
        ret_cmd.args = [0, 0, 0]

        ret_cmd.args[0] = (facing & 0x03) << 0xB
        ret_cmd.args[0] |= (unk & 0x03) << 0x9
        ret_cmd.args[0] |= location

        ret_cmd.args[1] = x_coord
        ret_cmd.args[2] = y_coord

        return ret_cmd

    @staticmethod
    def fade_screen() -> EventCommand:
        return EventCommand.generic_zero_arg(0xF2)

    @staticmethod
    def darken(duration) -> EventCommand:
        return EventCommand.generic_one_arg(0xF0, duration)

    @staticmethod
    def load_pc_always(pc_id: int) -> EventCommand:
        return EventCommand.generic_one_arg(0x81, int(pc_id))

    @staticmethod
    def load_pc_in_party(pc_id: int) -> EventCommand:
        if pc_id == 0:
            cmd_id = 0x57
        elif pc_id == 1:
            cmd_id = 0x5C
        elif pc_id == 2:
            cmd_id = 0x62
        elif pc_id == 3:
            cmd_id = 0x6A
        elif pc_id == 4:
            cmd_id = 0x68
        elif pc_id == 5:
            cmd_id = 0x6C
        elif pc_id == 6:
            cmd_id = 0x6D

        return EventCommand.generic_zero_arg(cmd_id)

    @staticmethod
    def load_npc(npc_id: int) -> EventCommand:
        return EventCommand.generic_one_arg(0x82, npc_id)

    @staticmethod
    def load_enemy(enemy_id: int, slot_number: int,
                   is_static: bool = False) -> EventCommand:
        # maybe validate?
        # enemy id in [0, 0xFF], slot id in [0, A]
        slot_arg = slot_number | 0x80*(is_static)
        x = EventCommand.generic_two_arg(0x83, int(enemy_id), slot_arg)
        return x

    @staticmethod
    def set_reset_bits(address: int, bitmask: int,
                       set_bits: bool = True) -> EventCommand:
        if not is_script_mem(address):
            raise ValueError('set_bits must opertate on script memory.')

        if not address % 2 == 0:
            raise ValueError('set_bits must operate on even addresses.')

        if not 0 <= bitmask < 0x100:
            raise ValueError('bitmask must be in [0, 0x100)')

        offset = (address - 0x7F0200)//2
        if set_bits:
            return EventCommand.generic_two_arg(0x69, bitmask, offset)

        return EventCommand.generic_two_arg(0x67, bitmask, offset)

    @staticmethod
    def set_reset_bit(address: int, bit: int, set_bit: bool) -> EventCommand:

        # For addresses in [0x7F0000, 0x7F0200) we can access any byte.
        # For bytes past 0x7F00FF we set the 0x80 bit of the byte indicating
        # the bit to set.
        if 0x7F0000 <= address < 0x7F0200:
            overflow = 0x80 * (address >= 0x7F0100)
            offset = address % 0x100
            if set_bit:
                cmd_id = 0x65
            else:
                cmd_id = 0x66
        # For addresses in script memory, [0x7F0200, 0x7F0400), we can only
        # access the even bytes.
        elif 0x7F0200 <= address < 0x7F0400:
            overflow = 0
            if address % 2 == 1:
                print(
                    'Warning: Script memory addresses must be even.  '
                    'Rounding down.'
                )
                address -= 1
            offset = (address - 0x7F0200)//2
            if set_bit:
                cmd_id = 0x63
            else:
                cmd_id = 0x64
        else:
            raise SystemExit(f'Error: Address {address:06X} out of range.')

        bit_byte = overflow | int(math.log2(bit))
        ret_cmd = EventCommand.generic_two_arg(cmd_id, bit_byte, offset)

        return ret_cmd

    @staticmethod
    def set_bit(address: int, bit: int) -> EventCommand:
        return EventCommand.set_reset_bit(address, bit, True)

    @staticmethod
    def reset_bit(address: int, bit: int) -> EventCommand:
        return EventCommand.set_reset_bit(address, bit, False)

    @staticmethod
    def set_object_drawing_status(obj_id: int, is_drawn: bool) -> EventCommand:
        if is_drawn:
            x = EventCommand.generic_one_arg(0x7C, obj_id*2)
        else:
            x = EventCommand.generic_one_arg(0x7D, obj_id*2)

        return x

    @staticmethod
    def set_own_drawing_status(is_drawn):
        if is_drawn:
            cmd_id = 0x90
        else:
            cmd_id = 0x91

        x = event_commands[cmd_id].copy()
        return x

    @staticmethod
    def remove_object(object_id: int) -> EventCommand:
        return EventCommand.generic_one_arg(0xA, 2*object_id)

    @staticmethod
    def vector_move(angle: int, magnitude: int,
                    keep_facing: bool) -> EventCommand:
        hex_angle = (0x100 * angle)//360
        cmd_mag = magnitude*2

        if keep_facing:
            return EventCommand.generic_two_arg(0x9C, hex_angle, cmd_mag)

        return EventCommand.generic_two_arg(0x92, hex_angle, cmd_mag)

    @staticmethod
    def call_pc_function(
            pc_id: int, fn_id: int, priority: int, sync: FuncSync
    ) -> EventCommand:
        if sync == FuncSync.HALT:
            cmd_id = 7
        elif sync == FuncSync.SYNC:
            cmd_id = 6
        elif sync == FuncSync.CONT:
            cmd_id = 5

        return EventCommand.generic_command(
            cmd_id, pc_id*2, (priority << 4) | fn_id
        )

    @staticmethod
    def call_obj_function(obj_id: int,
                          fn_id: int,
                          priority: int,
                          sync: FuncSync) -> EventCommand:

        # Format is:
        #   1st byte is command
        #   2nd byte is 2*object number
        #   3rd byte is prio in upper 8 bits, fn number in lower 8 bits

        if sync == FuncSync.HALT:
            cmd_id = 4
        elif sync == FuncSync.SYNC:
            cmd_id = 3
        elif sync == FuncSync.CONT:
            cmd_id = 2
        else:
            # Maybe an error message?  But we are using enums so no other
            # input should be possible.
            pass

        obj_byte = obj_id * 2

        # Validate fn_id, prio are between 0 and 15 inclusive
        if not 0 <= priority <= 0xF:
            print(f"Error: priority ({priority}) not between 0 and 15")

        if not 0 <= fn_id <= 0xF:
            print(f"Error: fn_id ({fn_id}) not between 0 and 15")

        # really mixture of prio and fn_id
        prio_byte = (priority << 4) | fn_id

        ret = event_commands[cmd_id].copy()
        ret.args = [obj_byte, prio_byte]

        return ret

    @staticmethod
    def copy_tiles(src_left: int, src_top: int, src_right: int, src_bot: int,
                   dest_left: int, dest_top: int,
                   copy_l1: bool = False,
                   copy_l2: bool = False,
                   copy_l3: bool = False,
                   copy_props: bool = False,
                   unk_0x10: bool = False,
                   unk_0x20: bool = False,
                   wait_vblank: bool = True) -> EventCommand:

        if src_left > src_right:
            raise SystemExit('Error, left > right')

        if src_top > src_bot:
            raise SystemError('Error: top > bot')

        if wait_vblank:
            cmd = 0xE4
        else:
            cmd = 0xE5

        ret_cmd = event_commands[cmd].copy()
        ret_cmd.args = [0 for i in range(ret_cmd.num_args)]

        ret_cmd.args[0:6] = [src_left, src_top, src_right, src_bot,
                             dest_left, dest_top]

        flags = (copy_l1) + (copy_l2 << 1) + (copy_l3 << 2) + \
            (copy_props << 3) + (unk_0x10 << 4) + (unk_0x20 << 5)
        ret_cmd.args[6] = flags

        return ret_cmd

    @staticmethod
    def get_blank_command(cmd_id: int) -> EventCommand:
        ret_cmd = event_commands[cmd_id].copy()
        ret_cmd.args = [0 for i in range(ret_cmd.num_args)]
        return ret_cmd

    @staticmethod
    def generic_command(*args) -> EventCommand:
        ret_cmd = event_commands[args[0]].copy()
        ret_cmd.args = list(args[1:])

        return ret_cmd

    @staticmethod
    def generic_zero_arg(cmd_id: int) -> EventCommand:
        ret = event_commands[cmd_id].copy()
        return ret

    # one arg, 1 byte
    @staticmethod
    def generic_one_arg(cmd_id: int, arg) -> EventCommand:
        ret = event_commands[cmd_id].copy()
        ret.args = [arg]
        return ret

    # two args, 1 byte each
    @staticmethod
    def generic_two_arg(cmd_id: int,
                        arg0: int,
                        arg1: int) -> EventCommand:
        ret = event_commands[cmd_id].copy()
        ret.args = [arg0, arg1]
        return ret

    @staticmethod
    def return_cmd() -> EventCommand:
        return EventCommand.generic_zero_arg(0)

    @staticmethod
    def break_cmd() -> EventCommand:
        return EventCommand.generic_zero_arg(0xB1)

    @staticmethod
    def end_cmd() -> EventCommand:
        return EventCommand.generic_zero_arg(0xB2)

    @staticmethod
    def add_gold(gold_amt: int) -> EventCommand:
        return EventCommand.generic_command(0xCD, gold_amt)

    @staticmethod
    def add_item(item_id: int) -> EventCommand:
        return EventCommand.generic_one_arg(0xCA, item_id)

    @staticmethod
    def remove_item(item_id: int) -> EventCommand:
        return EventCommand.generic_command(0xCB, item_id)

    @staticmethod
    def get_item_count(item_id: int, script_addr: int) -> EventCommand:
        if not is_script_mem(script_addr):
            raise ValueError('Address must be script memory.')

        offset = get_offset(script_addr)
        return EventCommand.generic_command(0xD7, item_id, offset)

    @staticmethod
    def if_storyline_counter_lt(storyline_val: int, jump_bytes: int):
        return EventCommand.generic_command(0x18, storyline_val, jump_bytes)

    @staticmethod
    def if_has_item(item_id: int, jump_bytes: int) -> EventCommand:
        return EventCommand.generic_two_arg(0xC9, int(item_id), jump_bytes)

    @staticmethod
    def if_mem_op_value(
            address: int, operation: Operation,
            value: int, num_bytes: int,  bytes_jump: int
    ) -> EventCommand:
        # TODO: Should do some validation here.  Lots of overlap with
        #       assign_val_to_mem

        operator = int(operation)

        if address in range(0x7F0000, 0x7F0200):
            cmd_id = 0x16
            if num_bytes != 1:
                raise ValueError(
                    '[0x7F0000, 0x7F0200) range requires 1 byte width.'
                )

            # Accessing the upper 0x100 bytes is done by ORing the operation
            # with 0x80
            if address >= 0x7F0100:
                operator |= 0x80

            offset = address % 0x100

        elif address in range(0x7F0200, 0x7F0400):
            if address % 2 != 0:
                print('Warning: Even address required. Rounding down.')
                address = address - 1

            offset = (address - 0x7F0200) // 2
            if num_bytes == 1:
                cmd_id = 0x12
            elif num_bytes == 2:
                cmd_id = 0x13
            else:
                print('Warning: Bad byte width.  Using 2.')
                num_bytes = 2
                cmd_id = 0x13

        ret_cmd = event_commands[cmd_id].copy()
        ret_cmd.args = [offset, value, operator, bytes_jump]

        return ret_cmd

    @staticmethod
    def set_storyline_counter(val: int) -> EventCommand:
        return EventCommand.assign_val_to_mem(val, 0x7F0000, 1)

    @staticmethod
    def increment_mem(script_addr: int, num_bytes: int = 1) -> EventCommand:
        if not is_script_mem(script_addr):
            raise ValueError('Can only increment script memory')

        if num_bytes == 1:
            cmd_id = 0x71
        else:
            cmd_id = 0x72

        offset = get_offset(script_addr)

        return EventCommand.generic_command(cmd_id, offset)

    @staticmethod
    def add_value_to_mem(value: int, script_addr: int):
        if not is_script_mem(script_addr):
            raise ValueError('Can only add to script memory')

        if not 0 <= value < 0x100:
            raise ValueError('Can only add values in [0, 0x100)')

        cmd = event_commands[0x5B].copy()
        cmd.args = [value, get_offset(script_addr)]

        return cmd

    @staticmethod
    def assign_mem_to_mem(
            from_addr: int,
            to_addr: int,
            num_bytes: int
    ) -> EventCommand:

        if num_bytes not in (1, 2):
            raise ValueError('Num bytes must be 1 or 2')

        if is_script_mem(from_addr) and is_script_mem(to_addr):
            # arg 1: offset of from_addr
            # arg 2: offset of to_addr
            cmd_args = [get_offset(from_addr), get_offset(to_addr)]
            if num_bytes == 1:
                cmd_id = 0x51
            else:
                cmd_id = 0x52
        elif is_local_mem(from_addr) and is_script_mem(to_addr):
            # arg 1: from_addr - 0x7F0000
            # arg 2: offset of to_addr
            cmd_args = [from_addr - 0x7F0000, get_offset(to_addr)]
            if num_bytes == 1:
                cmd_id = 0x53
            else:
                cmd_id = 0x54
        elif is_script_mem(from_addr) and is_local_mem(to_addr):
            # arg 1: offset of from_addr
            # arg 2: to_addr - 0x7F0000
            cmd_args = [get_offset(from_addr), to_addr - 0x7F0000]
            if num_bytes == 1:
                cmd_id = 0x58
            else:
                cmd_id = 0x59
        elif is_bank_7E(from_addr) and is_script_mem(to_addr):
            # arg 1: from_addr (3 bytes)
            # arg 2: (0x7F0200 - to_addr) / 2 -- check int?
            cmd_args = [from_addr, get_offset(to_addr)]
            if num_bytes == 1:
                cmd_id = 0x48
            else:
                cmd_id = 0x49
        elif is_script_mem(from_addr) and is_memory_addr(to_addr):
            # arg 1: to_addr (3 bytes)
            # arg 2: (from_addr - 0x7F000) / 2
            cmd_args = [to_addr, get_offset(from_addr)]
            if num_bytes == 1:
                cmd_id = 0x4C
            else:
                cmd_id = 0x4D

        cmd = event_commands[cmd_id].copy()
        cmd.args = cmd_args

        return cmd

    @staticmethod
    def assign_val_to_mem(
            val: int, address: int, num_bytes: int
    ) -> EventCommand:
        '''
        Generate an EventCommand that writes val to adddress.

        Paramters:
        val (int): The value to be written
        address (int): The address in [0x7E0000, 0x7FFFFF] to write to
        num_bytes (int):  The number of bytes to write to.  Either 1 or 2.

        Returns:
        An eventcommand.EventCommand which will perform the write.
        '''

        # First some validation.
        # Make sure that num_bytes is 1 or 2.  Otherwise try to guess it from
        # the value.
        if num_bytes not in (1, 2):
            print(f'Warning: num_bytes ({num_bytes}) must be 1 or 2.')
            if val < (1 << 8):
                print('Setting num_bytes to 1')
                num_bytes = 1
            else:
                print('Setting num_bytes to 2')
                num_bytes = 2

        # Make sure that the value fits in num_bytes
        if val < 0:
            print(f"Warning: Value ({val} < 0).  Setting to 0.")
            val = 0

        max_val = (1 << num_bytes*8) - 1
        if val > max_val:
            print(f"Warning: Value ({val}) exceeds maximum ({max_val}). "
                  f"Truncating to {max_val}")
            val = max_val

        # Make sure that the target address is in RAM - [0x7E0000, 0x7FFFFF]
        if not (0x7E0000 <= address <= 0x7FFFFF):
            raise SystemExit(
                'Address not in RAM memory range [0x7E0000, 0x7FFFFF]'
            )

        # There are three types of assignments depending on the memory range
        #   1) Script memory: [0x7F0200, 0x7F03FF]
        #   2) Bank 7F: [0x7F0000, 0x7FFFFF]
        #   3) All Ram: [0x7E0000, 0x7FFFFF]
        # Each range has its own assignment commands with variants for 1 and
        # 2 bytes.
        if 0x7F0200 <= address <= 0x7F03FF and address % 2 == 0:
            if num_bytes == 1:
                cmd_id = 0x4F
            else:
                cmd_id = 0x50

            offset = (address - 0x7F0200) // 2
            out_cmd = event_commands[cmd_id].copy()
            out_cmd.args = [val, offset]
        elif 0x7F0000 <= address <= 0x7FFFFF:
            if 0x7F0200 <= address <= 0x7F03FF:
                # This means the user provided an odd adddress so we're
                # falling back to the bank 7F command
                print(
                    f"Warning: address ({address: 06X}) is in script memory "
                    "but has an odd address.  Using bank 7F command."
                )

            if num_bytes == 1:
                out_cmd = event_commands[0x56].copy()
                offset = (address - 0x7F0000)
                out_cmd.args = [val, offset]
            else:
                out_cmd = event_commands[0x4B].copy()
                out_cmd.args = [address, val]
        else:
            if num_bytes == 1:
                cmd_id = 0x4A
            else:
                cmd_id = 0x4B

            out_cmd = event_commands[cmd_id].copy()
            out_cmd.args = [address, val]

        return out_cmd

    # Reminder that jumps in CT are always computed as being a jump from the
    # last byte of the jump command.  This is what the jump_bytes argument is.
    @staticmethod
    def jump_back(jump_bytes: int) -> EventCommand:
        return EventCommand.generic_one_arg(0x11, jump_bytes)

    @staticmethod
    def jump_forward(jump_bytes: int) -> EventCommand:
        return EventCommand.generic_one_arg(0x10, jump_bytes)

    @staticmethod
    def name_pc(char_id: int) -> EventCommand:
        return EventCommand.generic_command(0xC8, 0xC0 | char_id)

    @staticmethod
    def switch_pcs() -> EventCommand:
        return EventCommand.generic_command(0xC8, 0x00)

    @staticmethod
    def check_active_pc(char_id: int, jump_bytes: int) -> EventCommand:
        return EventCommand.generic_two_arg(0xD2, char_id, jump_bytes)

    @staticmethod
    def check_recruited_pc(char_id: int, jump_bytes: int) -> EventCommand:
        return EventCommand.generic_two_arg(0xCF, char_id, jump_bytes)

    @staticmethod
    def add_pc_to_active(char_id: int) -> EventCommand:
        return EventCommand.generic_command(0xD3, char_id)

    @staticmethod
    def add_pc_to_reserve(char_id: int) -> EventCommand:
        return EventCommand.generic_command(0xD0, char_id)

    @staticmethod
    def get_object_coordinates(obj_id: int,
                               x_addr: int,
                               y_addr: int) -> EventCommand:
        return EventCommand.generic_command(
            0x21, obj_id*2,
            get_offset(x_addr),
            get_offset(y_addr)
        )

    @staticmethod
    def set_own_coordinates_from_mem(x_addr, y_addr) -> EventCommand:
        return EventCommand.generic_command(0x8C,
                                            get_offset(x_addr),
                                            get_offset(y_addr))

    @staticmethod
    def set_object_coordinates_pixels(x_coord: int,
                                      y_coord: int) -> EventCommand:
        return EventCommand.generic_command(0x8D, x_coord << 4, y_coord << 4)

    @staticmethod
    def set_object_coordinates_tile(x_coord: int,
                                    y_coord: int) -> EventCommand:
        '''
        Sets an object's coordinates to be on the given tile coordinates.
        '''

        #
        return EventCommand.generic_command(0x8B, x_coord, y_coord)

    @staticmethod
    def set_object_coordinates_auto(px_x_coord: int,
                                    px_y_coord: int) -> EventCommand:
        tile_x = px_x_coord - 0x8
        tile_y = px_y_coord - 0x10

        if (tile_x & 0xF) == 0 and (tile_y & 0xF) == 0:
            tile_x >>= 4
            tile_y >>= 4
            return EventCommand.set_object_coordinates_tile(tile_x, tile_y)

        return EventCommand.set_object_coordinates_pixels(
            px_x_coord, px_y_coord
        )

    #  Here x and y are assumed to be pixel coordinates
    @staticmethod
    def set_object_coordinates(x: int, y: int,
                               shift: bool = True) -> EventCommand:
        # print(f"set: ({x:04X}, {y:04X})")

        # Command 0x8B works based on tiles while 0x8D works on pixels.
        # It should be that the two differ by a factor of 16, but it doesn't
        # match up.
        if x % 16 == 0 and y % 16 == 0 and shift is True:
            return EventCommand.generic_two_arg(0x8B, x >> 4, y >> 4)

        # Two notes on setting commands by pixels:
        #   (1) You have to multiply pixel number by 16 for the command.
        #       I think the game gets confused if the low order bits are
        #       not 0.
        #   (2) When setting based on pixels, it doesn't seem to match
        #       tiles.  The pixels seem to need to be shifted by 0x80 to
        #       match.
        shift_x, shift_y = 0, 0
        if shift:
            shift_x, shift_y = 0x80, 0x100
        return EventCommand.generic_two_arg(0x8D,
                                            (x << 4) + shift_x,
                                            (y << 4) + shift_y)

    @staticmethod
    def set_string_index(str_ind_rom: int) -> EventCommand:
        return EventCommand.generic_one_arg(0xB8, str_ind_rom)

    @staticmethod
    def special_dialog(dialog_id: int) -> EventCommand:
        return EventCommand.generic_one_arg(0xC8, dialog_id)

    @staticmethod
    def rename_character(char_id: int) -> EventCommand:
        return EventCommand.special_dialog(0xC0 | char_id)

    @staticmethod
    def replace_characters() -> EventCommand:
        return EventCommand.special_dialog(0x00)

    @staticmethod
    def decision_box(str_id: int, first_line: int, last_line: int,
                     mode_str: str = 'auto'):
        mode_str = mode_str.lower()
        if mode_str not in ('auto', 'top', 'bottom'):
            mode_str = 'auto'

        if mode_str == 'auto':
            cmd_id = 0xC0
        elif mode_str == 'top':
            cmd_id = 0xC3
        else:
            cmd_id = 0xC4

        if first_line not in range(0, 4):
            raise ValueError('First line must be in range(0, 4)')

        if last_line not in range(0, 4):
            raise ValueError('Last line must be in range(0, 4)')

        lines_byte = first_line << 2
        lines_byte |= last_line

        return EventCommand.generic_command(cmd_id, str_id, lines_byte)

    @staticmethod
    def if_result_equals(result_val: int, jump_bytes) -> EventCommand:
        return EventCommand.generic_command(0x1A, result_val, jump_bytes)

    # TODO: merge these two textbox commands
    @staticmethod
    def auto_text_box(string_id: int) -> EventCommand:
        return EventCommand.generic_one_arg(0xBB, string_id)

    @staticmethod
    def text_box(string_id: int, top: bool = True) -> EventCommand:
        if top:
            return EventCommand.generic_one_arg(0xC1, string_id)

        return EventCommand.generic_one_arg(0xC2, string_id)

    @staticmethod
    def script_speed(speed: int) -> EventCommand:
        speed = min(speed, 0x80)
        return EventCommand.generic_one_arg(0x87, speed)

    @staticmethod
    def check_run_button(bytes_jump: int = 0) -> EventCommand:
        return EventCommand.generic_command(0x30, bytes_jump)

    @staticmethod
    def pause(duration_secs: float):
        if duration_secs == 0.25:
            return EventCommand.generic_zero_arg(0xB9)
        if duration_secs == 0.5:
            return EventCommand.generic_zero_arg(0xBA)
        if duration_secs == 1:
            return EventCommand.generic_zero_arg(0xBC)
        if duration_secs == 2:
            return EventCommand.generic_zero_arg(0xBD)

        num_ticks = int(duration_secs*0x10)
        return EventCommand.generic_one_arg(0xAD, num_ticks)

    def copy(self) -> EventCommand:
        ret_command = EventCommand(-1, 0, [], [], '', '')
        ret_command.command = self.command
        ret_command.num_args = self.num_args
        ret_command.arg_lens = self.arg_lens[:]
        ret_command.arg_descs = self.arg_descs[:]
        ret_command.name = self.name
        ret_command.desc = self.desc

        ret_command.args = self.args[:]

        return ret_command

    def __len__(self):
        return 1 + sum(self.arg_lens)

    def __str__(self):
        if self.command == 0x4E:
            ret_str = f"{self.command:02X} " + self.name + ' ' + \
                ' '.join(f"{self.args[i]:0{2*self.arg_lens[i]}X}"
                         for i in range(len(self.args)-1))
            ret_str += '('
            ret_str += ' '.join(f'{x:02X}' for x in self.args[-1])
            ret_str += ')'
        else:
            ret_str = f"{self.command:02X} " + self.name + ' ' + \
                ' '.join(f"{self.args[i]:0{2*self.arg_lens[i]}X}"
                         for i in range(len(self.args)))
        return ret_str


# Many descriptions are copied from the db's 'Event\ Commands.txt'
event_commands = \
    [EventCommand(i, -1, [], [], '', '') for i in range(0x100)]

event_commands[0] = \
    EventCommand(0, 0, [], [],
                 'Return',
                 'Returns context, but doesn\'t quit')

event_commands[1] = \
    EventCommand(1, 0, [], [],
                 'Color Crash',
                 'Crashes.  Presumed leftover debug command.')

event_commands[2] = \
    EventCommand(2, 2, [1, 1],
                 ['aa: part of offset to pointer to load',
                  'po: p - priority, o-part of Offset to pointer'],
                 'Call Event.',
                 'Call Event.  Will wait only if new thread has higher' +
                 'priority, instantly returns if object is dead or busy')

event_commands[3] = \
    EventCommand(3, 2, [1, 1],
                 ['aa: part of offset to pointer to load',
                  'po: p - priority, o - part of offset to pointer'],
                 'Call Event.',
                 'Call Event. waits until execution starts (will wait' +
                 'indefinitely if current thread has lower priority than' +
                 'new one)')

event_commands[4] = \
    EventCommand(4, 2, [1, 1],
                 ['aa: part of offset to pointer to load',
                  'po: p - priority, o - part of offset to pointer'],
                 'Call Event',
                 'Call Event. Will wait on execution.')

event_commands[5] = \
    EventCommand(5, 2, [1, 1],
                 ['cc: PC',
                  'po: Priority, part of Offset to pointer'],
                 'Call PC Event',
                 'Call PC Event. Will wait only if new thread has higher' +
                 'priority, instantly returns if object is dead or busy')

event_commands[6] = \
    EventCommand(6, 2, [1, 1],
                 ['cc: PC',
                  'po: Priority, part of Offset to pointer'],
                 'Call PC Event',
                 'Call PC Event. waits until execution starts (will wait' +
                 'indefinitely if current thread has lower priority than' +
                 'new one)')

event_commands[7] = \
    EventCommand(7, 2, [1, 1],
                 ['cc: PC',
                  'po: Priority, part of Offset to pointer'],
                 'Call PC Event',
                 'Call PC Event. Will wait on execution.')

event_commands[8] = \
    EventCommand(8, 0, [], [],
                 'Object Activation',
                 'Turn off object activate & touch (PC can\'t interact)')

event_commands[9] = \
    EventCommand(9, 0, [], [],
                 'Object Deactivation',
                 'Turn on object activate & touch.)')

event_commands[0xA] = \
    EventCommand(0xA, 1, [1],
                 ['oo: Object to remove.'],
                 'Remove Object',
                 'Turn off object activate & touch (PC can\'t interact)')

event_commands[0xB] = \
    EventCommand(0xB, 1, [1],
                 ['oo: Object to disable.'],
                 'Disable Processing.',
                 'Turn off script processing.')

event_commands[0xC] = \
    EventCommand(0xC, 1, [1],
                 ['oo: Object to ensable.'],
                 'Enable Processing.',
                 'Turn on script processing.')

event_commands[0xD] = \
    EventCommand(0xD, 1, [1],
                 ['pp: NPC movement properties.'],
                 'NPC Movement Properties.',
                 'Unknown details.')

event_commands[0xE] = \
    EventCommand(0xE, 1, [1],
                 ['pp: Position on tile'],
                 'NPC Positioning.',
                 'Unknown details.')

event_commands[0xF] = \
    EventCommand(0xF, 0, [],
                 [],
                 'Set NPC Facing (up)',
                 'Overlaps A6 . Should be same with a hard coded 00 value.')

event_commands[0x10] = \
    EventCommand(0x10, 1, [1],
                 ['jj: Bytes to jump forward'],
                 'Jump Forward',
                 'Jumps execution forward.')

event_commands[0x11] = \
    EventCommand(0x11, 1, [1],
                 ['jj: Bytes to jump backwards'],
                 'Jump Backwards',
                 'Jumps execution backwards.')

event_commands[0x12] = \
    EventCommand(0x12, 4, [1, 1, 1, 1],
                 ['aa: Offset into SNES memory (*2, + 0x7F0200)',
                  'vv: Value used in operation',
                  'oo: Index for operation pointer',
                  'jj: Bytes to jump of operation evaluates False'],
                 'If',
                 'Jumps execution if condition evaluates false.')

event_commands[0x13] = \
    EventCommand(0x13, 4, [1, 2, 1, 1],
                 ['aa: Offset into SNES memory (*2, + 0x7F0200)',
                  'vvvv: Value used in operation',
                  'oo: Index for operation pointer',
                  'jj: Bytes to jump of operation evaluates False'],
                 'If',
                 'Jumps execution if operation evaluates false.')

event_commands[0x14] = \
    EventCommand(0x14, 4, [1, 1, 1, 1],
                 ['aa: Offset into SNES memory (*2, + 0x7F0200)',
                  'bb: Offset into SNES memory (*2, + 0x7F0200)',
                  'oo: Index for operation pointer',
                  'jj: Bytes to jump of operation evaluates False'],
                 'If',
                 'Jumps execution if operation evaluates false.  ' +
                 'Partial overlap with 0x16.')

event_commands[0x15] = \
    EventCommand(0x15, 4, [1, 1, 1, 1],
                 ['aa: Offset into SNES memory (*2, + 0x7F0200)',
                  'bb: Offset into SNES memory (*2, + 0x7F0200)',
                  'oo: Index for operation pointer',
                  'jj: Bytes to jump of operation evaluates False'],
                 'If',
                 'Jumps execution if operation evaluates false.  ' +
                 'Two byte operand version of 0x14.')

event_commands[0x16] = \
    EventCommand(0x16, 4, [1, 1, 1, 1],
                 ['aa: Offset into SNES memory (*2, + 0x7F0200)',
                  'vv: Value used in operation.',
                  'oo: Index for operation pointer',
                  'jj: Bytes to jump if operation evaluates False'],
                 'If',
                 'Jumps execution if condition evaluates false.  ' +
                 'Two byte operand version of 0x14.')

event_commands[0x17] = \
    EventCommand(0x17, 0, [],
                 [],
                 'Set NPC Facing (down)',
                 'Overlaps A6 . Should be same with a hard coded 01 value.')

event_commands[0x18] = \
    EventCommand(0x18, 2, [1, 1],
                 ['vv: Storyline point to check for.',
                  'jj: Bytes to jump if storyline point reached or passed.'],
                 'Check Storyline',
                 'Overlaps A6 . Should be same with a hard coded 00 value.')

event_commands[0x19] = \
    EventCommand(0x19, 1, [1],
                 ['aa: Address to load result from (*2, +7F0200)'],
                 'Get Result',
                 'Overlaps 1C . Should be same with a hard coded 00 value.')

event_commands[0x1A] = \
    EventCommand(0x1A, 2, [1, 1],
                 ['rr: Target result',
                  'jj: Bytes to jump if result does not match target'],
                 'Jump Result',
                 'Jumps if result does not match target.')

event_commands[0x1B] = \
    EventCommand(0x1B, 0, [],
                 [],
                 'Set NPC Facing (left)',
                 'Overlaps A6 . Should be same with a hard coded 02 value.')

event_commands[0x1C] = \
    EventCommand(0x1C, 1, [2],
                 ['aaaa: Address to load result from (+7F0000)'],
                 'Get Result',
                 'Overlapped by 0x19.')

event_commands[0x1D] = \
    EventCommand(0x1D, 0, [],
                 [],
                 'Set NPC Facing (right)',
                 'Overlaps A6 . Should be same with a hard coded 03 value.')

event_commands[0x1E] = \
    EventCommand(0x1E, 1, [1],
                 ['nn: NPC to change facing for.'],
                 'Set NPC Facing (up)',
                 'Overlaps A6.')

event_commands[0x1F] = \
    EventCommand(0x1F, 1, [1],
                 ['nn: NPC to change facing for.'],
                 'Set NPC Facing (down)',
                 'Overlaps A6.')

event_commands[0x20] = \
    EventCommand(0x20, 1, [1],
                 ['oo: Offset to store to (*2, +7F0200)'],
                 'Get PC1',
                 'Gets PC1 id and stores in memory')

event_commands[0x21] = \
    EventCommand(0x21, 3, [1, 1, 1],
                 ['oo: Object (/2)',
                  'aa: Offset to store X Coord to (*2, +7F0200)',
                  'bb: Offset to store X Coord to (*2, +7F0200)'],
                 'Get Object Coords',
                 'Store object coords to memory.  Overlapped by 0x22.')

event_commands[0x22] = \
    EventCommand(0x22, 3, [1, 1, 1],
                 ['cc: PC (/2)',
                  'aa: Offset to store X Coord to (*2, +7F0200)',
                  'bb: Offset to store X Coord to (*2, +7F0200)'],
                 'Get PC Coords',
                 'Store PC coords to memory.  Overlaps 0x21.')

event_commands[0x23] = \
    EventCommand(0x23, 2, [1, 1],
                 ['cc: PC (/2)',
                  'aa: Offset to store to (*2, +7F0200)'],
                 'Get Obj Facing',
                 'Store object facing to memory.  Overlapped by 0x24.')

event_commands[0x24] = \
    EventCommand(0x24, 2, [1, 1],
                 ['cc: PC (/2)',
                  'aa: Offset to store to (*2, +7F0200)'],
                 'Get PC Facing',
                 'Store PC facing to memory.  Overlaps 0x23.')

event_commands[0x25] = \
    EventCommand(0x25, 1, [1],
                 ['nn: NPC to change facing for.'],
                 'Set NPC Facing (left)',
                 'Overlaps A6.')

event_commands[0x26] = \
    EventCommand(0x26, 1, [1],
                 ['nn: NPC to change facing for.'],
                 'Set NPC Facing (right)',
                 'Overlaps A6.')

event_commands[0x27] = \
    EventCommand(0x27, 2, [1, 1],
                 ['oo: Object Number (/2)',
                  'jj: Bytes to jump if object is not visible.'],
                 'Check Object Status',
                 'Jump when object is not visible' +
                 '(offcreen, not loaded, hidden)')

event_commands[0x28] = \
    EventCommand(0x28, 2, [1, 1],
                 ['oo: Object Number (/2)',
                  'jj: Bytes to jump if object is not in battle range.'],
                 'Check Battle Range',
                 'Jump when object is out or range for battle.')

event_commands[0x29] = \
    EventCommand(0x29, 1, [1],
                 ['ii: Index (+0x80)'],
                 'Set NPC Facing (right)',
                 'Loads ASCII text from 0x3DA000')

event_commands[0x2A] = \
    EventCommand(0x2A, 0, [],
                 [],
                 'Unknown 0x2A',
                 'Sets 0x04 Bit of 0x7E0154')

event_commands[0x2B] = \
    EventCommand(0x2B, 0, [],
                 [],
                 'Unknown 0x2B',
                 'Sets 0x08 Bit of 0x7E0154')

event_commands[0x2C] = \
    EventCommand(0x2C, 2, [1, 1],
                 ['Unknown', 'Unknown'],
                 'Unknown 0x2C',
                 'Unknown')

event_commands[0x2D] = \
    EventCommand(0x2D, 1, [1],
                 ['jj: Bytes to jump if no button pressed.'],
                 'Check Button Pressed',
                 'Jumps if no buttons are pressed (0x7E00F8')

event_commands[0x2E] = \
    EventCommand(0x2E, 1, [1],
                 ['m?: Mode'],
                 'Color Math',
                 'No description given.')

event_commands[0x2F] = \
    EventCommand(0x2F, 2, [1, 1],
                 ['??: Unknown', '??: Unknown'],
                 'Unknown 0x2F',
                 'Unknown.  Stores to 0x7E0BE3 and 0x7E0BE4.' +
                 'Appears to have something to do with scrolling layers')

event_commands[0x30] = \
    EventCommand(0x30, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump No Dash',
                 'Jump if dash is not pressed.')

event_commands[0x31] = \
    EventCommand(0x31, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump No Confirm',
                 'Jump if confirm button is not pressed.')

event_commands[0x32] = \
    EventCommand(0x32, 0, [],
                 [],
                 'Unknown 0x32',
                 'Overlaps 0x2A, sets 0x10 Bit of 0x7E0154.')

event_commands[0x33] = \
    EventCommand(0x33, 1, [1],
                 ['pp: palette to change to.'],
                 'Change Palette',
                 'Changes the calling object\'s palette.')

event_commands[0x34] = \
    EventCommand(0x34, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump A Button',
                 'Jump if A is not pressed.')

event_commands[0x35] = \
    EventCommand(0x35, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump B Button',
                 'Jump if B is not pressed.')

event_commands[0x36] = \
    EventCommand(0x36, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump X Button',
                 'Jump if X is not pressed.')

event_commands[0x37] = \
    EventCommand(0x37, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump Y Button',
                 'Jump if Y is not pressed.')

event_commands[0x38] = \
    EventCommand(0x38, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump L Button',
                 'Jump if L is not pressed.')

event_commands[0x39] = \
    EventCommand(0x39, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump R Button',
                 'Jump if R is not pressed.')

event_commands[0x3A] = event_commands[0x01]
event_commands[0x3A].command = 0x3A
event_commands[0x3A].desc += 'Alias of 0x01.'

event_commands[0x3B] = \
    EventCommand(0x3B, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump No Dash',
                 'Jump if dash has not been pressed since last check.')

event_commands[0x3C] = \
    EventCommand(0x3C, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump No Confirm',
                 'Jump if confirm has not been pressed since last check.')

event_commands[0x3D] = event_commands[0x01]
event_commands[0x3D].command = 0x3D
event_commands[0x3D].desc += 'Alias of 0x01.'

event_commands[0x3E] = event_commands[0x01]
event_commands[0x3E].command = 0x3E
event_commands[0x3E].desc += 'Alias of 0x01.'

event_commands[0x3F] = \
    EventCommand(0x3F, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump No A',
                 'Jump if A has not been pressed since last check.')

event_commands[0x40] = \
    EventCommand(0x40, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump No B',
                 'Jump if B has not been pressed since last check.')

event_commands[0x41] = \
    EventCommand(0x41, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump No X',
                 'Jump if X has not been pressed since last check.')

event_commands[0x42] = \
    EventCommand(0x42, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump No Y',
                 'Jump if Y has not been pressed since last check.')

event_commands[0x43] = \
    EventCommand(0x43, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump No L',
                 'Jump if L has not been pressed since last check.')

event_commands[0x44] = \
    EventCommand(0x44, 1, [1],
                 ['jj: Number of bytes to jump'],
                 'Jump No R',
                 'Jump if R has not been pressed since last check.')

event_commands[0x45] = event_commands[0x01]
event_commands[0x45].command = 0x45
event_commands[0x45].desc += 'Alias of 0x01.'

event_commands[0x46] = event_commands[0x01]
event_commands[0x46].command = 0x46
event_commands[0x46].desc += 'Alias of 0x01.'

event_commands[0x47] = \
    EventCommand(0x47, 1, [1],
                 ['ll: limit on animations (unknown meaning).'],
                 'Animation Limiter',
                 'Limits which animations can be performed.  ' +
                 'Used to avoid slowdown in high activity scenes.')

event_commands[0x48] = \
    EventCommand(0x48, 2, [3, 1],
                 ['aaaaaa: Address to load from.',
                  'oo: Offset to store to (*2, +7F0200)'],
                 'Assignment',
                 'Assign from any address to local script memory (1 byte)')

event_commands[0x49] = \
    EventCommand(0x49, 2, [3, 1],
                 ['aaaaaa: Address to load from.',
                  'oo: Offset to store to (*2, +7F0200)'],
                 'Assignment',
                 'Assign from any address to local script memory (2 bytes)')

event_commands[0x4A] = \
    EventCommand(0x4A, 2, [3, 1],
                 ['aaaaaa: SNES Address to store to.',
                  'vv: Value to load'],
                 'Assignment',
                 'Assign value (1 byte) to any memory address.')

event_commands[0x4B] = \
    EventCommand(0x4B, 2, [3, 2],
                 ['aaaaaa: SNES Address to store to.',
                  'vvvv: Value to load'],
                 'Assignment',
                 'Assign value (2 byte) to any memory address.')

event_commands[0x4C] = \
    EventCommand(0x4C, 2, [3, 1],
                 ['aaaaaa: SNES Address to store to.',
                  'oo: Offset to load from (*2, +7F0200)'],
                 'Assignment',
                 'Assign value (1 byte) to local script memory.')

event_commands[0x4D] = \
    EventCommand(0x4D, 2, [3, 1],
                 ['aaaaaa: SNES Address to store to.',
                  'oo: Offset to load from (*2, +7F0200)'],
                 'Assignment',
                 'Assign value (2 bytes) to local script memory.')

# Will need special case in parser
event_commands[0x4E] = \
    EventCommand(0x4E, 4, [2, 1, 2, 1],
                 ['aaaa: Destination bank address',
                  'bb: Destination bank',
                  'cc: Bytes to copy + 2.  Data follows command.'],
                 'Memory Copy',
                 'Copy data from script to memory')

event_commands[0x4F] = \
    EventCommand(0x4F, 2, [1, 1],
                 ['vv: Value to store',
                  'oo: Offset to store to (*2, +7F0200)'],
                 'Assignment (Val to Mem)',
                 'Assign value (1 byte) to local script memory.')

event_commands[0x50] = \
    EventCommand(0x50, 2, [2, 1],
                 ['vvvv: Value to store',
                  'oo: Offset to store to (*2, +7F0200)'],
                 'Assignment (Val to Mem)',
                 'Assign value (2 bytes) to local script memory.')

event_commands[0x51] = \
    EventCommand(0x51, 2, [1, 1],
                 ['aa: Offset to load from (*2, +7F0200)',
                  'oo: Offset to store to (*2, +7F0200)'],
                 'Assignment (Mem to Mem)',
                 'Assign local memory to local memory (1 byte).')

event_commands[0x52] = \
    EventCommand(0x52, 2, [1, 1],
                 ['aa: Offset to load from (*2, +7F0200)',
                  'oo: Offset to store to (*2, +7F0200)'],
                 'Assignment (Mem to Mem)',
                 'Assign local memory to local memory (2 bytes).')

event_commands[0x53] = \
    EventCommand(0x53, 2, [2, 1],
                 ['aaaa: Offset to load from (+7F0000)',
                  'oo: Offset to store to (*2, +7F0200)'],
                 'Assignment (Mem to Mem)',
                 'Assign bank 7F memory to local memory (1 byte).')

event_commands[0x54] = \
    EventCommand(0x54, 2, [2, 1],
                 ['aaaa: Offset to load from (+7F0000)',
                  'oo: Offset to store to (*2, +7F0200)'],
                 'Assignment (Mem to Mem)',
                 'Assign bank 7F memory to local memory (2 bytes).')

event_commands[0x55] = \
    EventCommand(0x55, 1, [1],
                 ['oo: Offset to store to (*2, +7F0200)'],
                 'Get Storyline Counter',
                 'Assign storyline counter to local memory.')

event_commands[0x56] = \
    EventCommand(0x56, 2, [1, 2],
                 ['vv: Value to Store',
                  'aaaa: Offset to store to (+7F0000)'],
                 'Assignment (Value to Mem)',
                 'Assign value to bank 7F memory.')

event_commands[0x57] = \
    EventCommand(0x57, 0, [],
                 [],
                 'Load Crono',
                 'Load Crono if in party.')

event_commands[0x58] = \
    EventCommand(0x58, 2, [1, 2],
                 ['oo: Offset to load from (*2, +7F0200)',
                  'aaaa: Address to store to (+7F0000)'],
                 'Assignment (Mem to Mem)',
                 'Assign local memory to bank 7F memory (1 byte).')

event_commands[0x59] = \
    EventCommand(0x59, 2, [1, 2],
                 ['oo: Offset to load from (*2, +7F0200)',
                  'aaaa: Address to store to (+7F0000)'],
                 'Assignment (Mem to Mem)',
                 'Assign local memory to bank 7F memory (2 bytes).')

event_commands[0x5A] = \
    EventCommand(0x5A, 1, [1],
                 ['vv: Value to assign'],
                 'Assign Storyline',
                 'Assign value to storyline (0x7F0000)')

event_commands[0x5B] = \
    EventCommand(0x5B, 2, [1, 1],
                 ['vv: Value to add',
                  'oo: Offset in memory to add to (*2, +7F0200)'],
                 'Add (Val to Mem)',
                 'Add a value to local memory.')

event_commands[0x5C] = \
    EventCommand(0x5C, 0, [],
                 [],
                 'Load Marle',
                 'Load Marle if in party.')

event_commands[0x5D] = \
    EventCommand(0x5D, 2, [1, 1],
                 ['oo: Offset in memory to load from (*2, +7F0200)',
                  'aa: Offset in memory to add to (*2, +7F0200)'],
                 'Add (Mem to Mem)',
                 'Add from local memory to local memory (1 byte)')

event_commands[0x5E] = \
    EventCommand(0x5E, 2, [1, 1],
                 ['oo: Offset in memory to load from (*2, +7F0200)',
                  'aa: Offset in memory to add to (*2, +7F0200)'],
                 'Add (Mem to Mem)',
                 'Add from local memory to local memory (2 bytes)')

event_commands[0x5F] = \
    EventCommand(0x5F, 2, [1, 1],
                 ['vv: Value to subtract',
                  'oo: Offset in memory to subtract from (*2, +7F0200)'],
                 'Subtract (Val to Mem)',
                 'Subtract a value from local memory (1 byte).')

event_commands[0x60] = \
    EventCommand(0x60, 2, [2, 1],
                 ['vvvv: Value to subtract',
                  'oo: Offset in memory to subtract from (*2, +7F0200)'],
                 'Subtract (Val to Mem)',
                 'Subtract a value from local memory (2 bytes).')

event_commands[0x61] = \
    EventCommand(0x61, 2, [1, 1],
                 ['oo: Offset in memory to load from (*2, +7F0200)',
                  'aa: Offset in memory to subtract from (*2, +7F0200)'],
                 'Add (Mem to Mem)',
                 'Subtract local memory from local memory (1 byte?)')

event_commands[0x62] = \
    EventCommand(0x62, 0, [],
                 [],
                 'Load Lucca',
                 'Load Lucca if in party.')

event_commands[0x63] = \
    EventCommand(0x63, 2, [1, 1],
                 ['bb: Bit to set.',
                  'oo: Offset in memory to set bit in (*2, +7F0200)'],
                 'Set Bit',
                 'Set bit in local memory')

event_commands[0x64] = \
    EventCommand(0x64, 2, [1, 1],
                 ['bb: Bit to reset.',
                  'oo: Offset in memory to reset bit in (*2, +7F0200)'],
                 'Reset Bit',
                 'Reset bit in local memory')

event_commands[0x65] = \
    EventCommand(0x65, 2, [1, 1],
                 ['bs: 0x80 set -> add 0x100 to aa. Set bit 0x1 << s.',
                  'aa: Offset in memory to set bit in (+7F0000)'],
                 'Set Bit',
                 'Set bit in bank 7F.  Usually storyline-related.')

event_commands[0x66] = \
    EventCommand(0x66, 2, [1, 1],
                 ['bs: 0x80 set -> add 0x100 to aa. Reset bit 0x1 << s.',
                  'aa: Offset in memory to reset bit in (+7F0000)'],
                 'Reset Bit',
                 'Reset bit in bank 7F.  Usually storyline-related.')

event_commands[0x67] = \
    EventCommand(0x67, 2, [1, 1],
                 ['bb: Bits to keep.'
                  'oo: Offset in memory to reset bits in (*2, +7F0200)'],
                 'Reset Bits',
                 'Reset bits in local memory')

event_commands[0x68] = \
    EventCommand(0x68, 0, [],
                 [],
                 'Load Frog',
                 'Load Frog if in party.')

event_commands[0x69] = \
    EventCommand(0x69, 2, [1, 1],
                 ['bb: Bits to set.'
                  'oo: Offset in memory to reset bits in (*2, +7F0200)'],
                 'Set Bits',
                 'Set bits in local memory')

event_commands[0x6A] = \
    EventCommand(0x6A, 0, [],
                 [],
                 'Load Robo',
                 'Load Robo if in party.')

event_commands[0x6B] = \
    EventCommand(0x6B, 2, [1, 1],
                 ['bb: Bits to toggle.'
                  'oo: Offset in memory to toggle bits in (*2, +7F0200)'],
                 'Toggle Bits',
                 'Toggle bits in local memory')

event_commands[0x6C] = \
    EventCommand(0x6C, 0, [],
                 [],
                 'Load Ayla',
                 'Load Ayla if in party.')

event_commands[0x6D] = \
    EventCommand(0x6D, 0, [],
                 [],
                 'Load Magus',
                 'Load Magus if in party.')

event_commands[0x6E] = event_commands[0x01]
event_commands[0x6E].command = 0x46
event_commands[0x6E].desc += 'Alias of 0x01.'

event_commands[0x6F] = \
    EventCommand(0x6F, 2, [1, 1],
                 ['ss: length of shift.'
                  'oo: Offset in memory to shift bits in (*2, +7F0200)'],
                 'Shift Bits',
                 'Shift bits in local memory')

event_commands[0x70] = event_commands[0x01]
event_commands[0x70].command = 0x70
event_commands[0x70].desc += 'Alias of 0x01.'

event_commands[0x71] = \
    EventCommand(0x71, 1, [1],
                 ['oo: Offset to increment (*2, +7F0200)'],
                 'Increment',
                 'Increment local memory (1 byte).')

event_commands[0x72] = \
    EventCommand(0x72, 1, [1],
                 ['oo: Offset to increment (*2, +7F0200)'],
                 'Increment',
                 'Increment local memory (2 bytes).')

event_commands[0x73] = \
    EventCommand(0x73, 1, [1],
                 ['oo: Offset to decrement (*2, +7F0200)'],
                 'Decrement',
                 'Decrement local memory (1 byte).')

event_commands[0x74] = event_commands[0x01]
event_commands[0x74].command = 0x74
event_commands[0x74].desc += 'Alias of 0x01.'

event_commands[0x75] = \
    EventCommand(0x75, 1, [1],
                 ['oo: Offset to set (*2, +7F0200)'],
                 'Set Byte',
                 'Set local memory to 1 (0xFF?) (1 byte).')

event_commands[0x76] = \
    EventCommand(0x76, 1, [1],
                 ['oo: Offset to set (*2, +7F0200)'],
                 'Set Byte',
                 'Set local memory to 1 (0xFF?) (2 bytes).')

event_commands[0x77] = \
    EventCommand(0x77, 1, [1],
                 ['oo: Offset to set (*2, +7F0200)'],
                 'Reset Byte',
                 'Reset local memory to 0 (1 byte?).')

event_commands[0x78] = event_commands[0x01]
event_commands[0x78].command = 0x78
event_commands[0x78].desc += 'Alias of 0x01.'

event_commands[0x79] = event_commands[0x01]
event_commands[0x79].command = 0x79
event_commands[0x79].desc += 'Alias of 0x01.'

event_commands[0x7A] = \
    EventCommand(0x7A, 3, [1, 1, 1],
                 ['xx: X-coordinate of jump',
                  'yy: Y-coordinate of jump',
                  'hh: height/speed of jump'],
                 'NPC Jump',
                 'Jump NPC to an unoccupied, walkable spot.')

event_commands[0x7B] = \
    EventCommand(0x7B, 4, [1, 1, 1, 1],
                 ['dd: Related to destination',
                  'ee: Related to destination',
                  'ff: Speed/Height?',
                  'gg: Speed/Height?'],
                 'NPC Jump',
                 'Unused command related to NPC jumping.')

event_commands[0x7C] = \
    EventCommand(0x7C, 1, [1],
                 ['oo: Object to turn drawing on for.'],
                 'Turn Drawing On',
                 'Turn drawing on for the given object.  Overlaps 0x90.')

event_commands[0x7D] = \
    EventCommand(0x7D, 1, [1],
                 ['oo: Object to turn drawing off for.'],
                 'Turn Drawing Off',
                 'Turn drawing off for the given object.  Overlaps 0x90.')

event_commands[0x7E] = \
    EventCommand(0x7E, 0, [],
                 [],
                 'Turn Drawing Off',
                 'Turn drawing off.  Uses value 80.  Overlaps 0x90.')

event_commands[0x7F] = \
    EventCommand(0x7F, 1, [1],
                 ['oo: Offset to store random number at (*2, +7F0200)'],
                 'Random',
                 'Load random data into local memory.')

event_commands[0x80] = \
    EventCommand(0x80, 1, [1],
                 ['cc: PC to load'],
                 'Load PC',
                 'Load PC if the PC is in the party.')

event_commands[0x81] = \
    EventCommand(0x81, 1, [1],
                 ['xx: PC to load'],
                 'Load PC',
                 'Load PC regardless of party status.')

event_commands[0x82] = \
    EventCommand(0x82, 1, [1],
                 ['xx: PC to load'],
                 'Load NPC',
                 'Load NPC')

event_commands[0x83] = \
    EventCommand(0x83, 2, [1, 1],
                 ['ee: Enemy to load',
                  'ii: Enemy Data (0x80 status, 0x7F slot)'],
                 'Load Enemy',
                 'Load Enemy into given target slot')

event_commands[0x84] = \
    EventCommand(0x84, 1, [1],
                 ['pp: NPC solidity properties'],
                 'NPC Solidity',
                 'Alter NPC solidity properties')

event_commands[0x85] = event_commands[0x01]
event_commands[0x85].command = 0x85
event_commands[0x85].desc += 'Alias of 0x01.'

event_commands[0x86] = event_commands[0x01]
event_commands[0x86].command = 0x86
event_commands[0x86].desc += 'Alias of 0x01.'

event_commands[0x87] = \
    EventCommand(0x87, 1, [1],
                 ['ss: Script Timing (0 fastest, 0x80 stop)'],
                 'Script Speed',
                 'Alter speed of script execution.')

# Argument number varies depending on mode
event_commands[0x88] = \
    EventCommand(0x88, 1, [1],
                 ['m?: mode'],
                 'Mem Copy',
                 'Long description in db.')

event_commands[0x89] = \
    EventCommand(0x89, 1, [1],
                 ['ss: Speed of movement'],
                 'NPC Speed',
                 'Alter speed of NPCs.')

event_commands[0x8A] = \
    EventCommand(0x8A, 1, [1],
                 ['oo: Offset to load speed from (*2, 7F0200)'],
                 'NPC Speed',
                 'Alter speed of NPCs from local memory.')

event_commands[0x8B] = \
    EventCommand(0x8B, 2, [1, 1],
                 ['xx: X-coordinate',
                  'yy: Y-coordinate'],
                 'Set Object Position',
                 'Place object at given coordinates.')

event_commands[0x8C] = \
    EventCommand(0x8C, 2, [1, 1],
                 ['aa: Offset to load x-coordinate from (*2, 7F0200)',
                  'bb: Offset to load y-coordinate from (*2, 7F0200)'],
                 'Set Object Position',
                 'Place object at given coordinates from local memory.')

event_commands[0x8D] = \
    EventCommand(0x8D, 2, [2, 2],
                 ['xxxx: X-coordinate in pixels',
                  'yyyy: Y-coordinate in pixels'],
                 'Set Object Pixel Position',
                 'Place object at given pixel coordinates.')

event_commands[0x8E] = \
    EventCommand(0x8E, 1, [1],
                 ['pp: Priority (0x80 mode, rest ???)'],
                 'Set Sprite Priority',
                 'Set Sprite Priority')

event_commands[0x8F] = \
    EventCommand(0x8F, 1, [1],
                 ['cc: PC to follow'],
                 'Follow at Distance',
                 'Follow the given character at a distance.')

event_commands[0x90] = \
    EventCommand(0x90, 0, [],
                 [],
                 'Drawing On',
                 'Turn object drawing on')

event_commands[0x91] = \
    EventCommand(0x91, 0, [],
                 [],
                 'Drawing On',
                 'Turn object drawing off. Uses value 00 (?). Overlaps 0x90')

event_commands[0x92] = \
    EventCommand(0x92, 2, [1, 1],
                 ['dd: Direction of movement (0x40 = 90 deg, 0 = right)',
                  'mm: Magnitude of movement'],
                 'Vector Move',
                 'Move object along given vector.')

event_commands[0x93] = event_commands[0x01]
event_commands[0x93].command = 0x93
event_commands[0x93].desc += 'Alias of 0x01.'

event_commands[0x94] = \
    EventCommand(0x94, 1, [1],
                 ['oo: Object to follow'],
                 'Follow Object',
                 'Follow the given object.')

event_commands[0x95] = \
    EventCommand(0x95, 1, [1],
                 ['cc: PC to follow'],
                 'Follow PC',
                 'Follow the given PC')

event_commands[0x96] = \
    EventCommand(0x96, 2, [1, 1],
                 ['xx: X-coordinate',
                  'yy: Y-coordinate'],
                 'NPC move',
                 'Move the given NPC (to given coordinates? vector?)')

event_commands[0x97] = \
    EventCommand(0x97, 2, [1, 1],
                 ['aa: Offset to load x-coordinate from (*2, 7F0200)',
                  'bb: Offset to load y-coordinate from (*2, 7F0200)'],
                 'NPC move',
                 'Move the given NPC with coordinates from local memory.')

event_commands[0x98] = \
    EventCommand(0x98, 2, [1, 1],
                 ['oo: Object',
                  'mm: Distance to travel'],
                 'Move Toward',
                 'Move toward the given object.')

event_commands[0x99] = \
    EventCommand(0x99, 2, [1, 1],
                 ['cc: PC',
                  'mm: Distance to travel'],
                 'Move Toward',
                 'Move toward the given PC. Overlaps 0x98.')

event_commands[0x9A] = \
    EventCommand(0x9A, 3, [1, 1],
                 ['xx: X-coordinate',
                  'yy: Y-coordinate',
                  'mm: Distance to travel'],
                 'Move Toward Coordinates',
                 'Move toward the given coordinates.')

event_commands[0x9B] = event_commands[0x01]
event_commands[0x9B].command = 0x9B
event_commands[0x9B].desc += 'Alias of 0x01.'

event_commands[0x9C] = \
    EventCommand(0x9C, 2, [1, 1],
                 ['dd: Direction of movement (0x40 = 90 deg, 0 = right)',
                  'mm: Magnitude of movement'],
                 'Vector Move',
                 'Move object along given vector.  Does not change facing.')

event_commands[0x9D] = \
    EventCommand(0x9D, 2, [1, 1],
                 ['aa: Offset to load direction from (*2, +7F0200)' +
                  '(0x40 = 90 deg, 0 = right)',
                  'bb: Offset to load magnitude from (*2, +7F0200)'],
                 'Vector Move',
                 'Move object along given vector.  Does not change facing.')

event_commands[0x9E] = \
    EventCommand(0x9D, 1, [1],
                 ['oo: Object (/2) to move to'],
                 'Vector Move to Object',
                 'Move to given object. Does not change facing.  ' +
                 'Overlapped by 0x9F')

event_commands[0x9F] = \
    EventCommand(0x9D, 1, [1],
                 ['oo: Object (/2) to move to'],
                 'Vector Move to Object',
                 'Move to given object. Does not change facing.  ' +
                 'Overlaps 0x9E')

event_commands[0xA0] = \
    EventCommand(0xA0, 2, [1, 1],
                 ['xx: X-coordinate.',
                  'yy: Y-coordinate.'],
                 'Animated Move',
                 'Move while playing an animation.')

event_commands[0xA1] = \
    EventCommand(0xA1, 2, [1, 1],
                 ['aa: Offset (*2, +7F0200) to load x-coordinate from',
                  'bb: Offset (*2, +7F0200) to load y-coordinate from'],
                 'Animated Move',
                 'Move while playing an animation.')

event_commands[0xA2] = event_commands[0x01]
event_commands[0xA2].command = 0xA2
event_commands[0xA2].desc += 'Alias of 0x01.'

event_commands[0xA3] = event_commands[0x01]
event_commands[0xA3].command = 0xA3
event_commands[0xA3].desc += 'Alias of 0x01.'

event_commands[0xA4] = event_commands[0x01]
event_commands[0xA4].command = 0xA4
event_commands[0xA4].desc += 'Alias of 0x01.'

event_commands[0xA5] = event_commands[0x01]
event_commands[0xA5].command = 0xA5
event_commands[0xA5].desc += 'Alias of 0x01.'

event_commands[0xA6] = \
    EventCommand(0xA6, 1, [1],
                 ['ff: Facing (0 = up, 1 = down, 2 = left, 3 = right)'],
                 'NPC Facing',
                 'Set NPC facing. Overlapped by 0x17')

event_commands[0xA7] = \
    EventCommand(0xA7, 1, [1],
                 ['oo: Offset to load facing from (*2, +7F0200)'],
                 'NPC Facing',
                 'Set NPC facing. Overlaps 0xA6')

event_commands[0xA8] = \
    EventCommand(0xA8, 1, [1],
                 ['oo: Object (/2) to face.'],
                 'NPC Facing',
                 'Set NPC to face object. Overlapped by 0xA9.')

event_commands[0xA9] = \
    EventCommand(0xA9, 1, [1],
                 ['cc: PC (/2) to face.'],
                 'NPC Facing',
                 'Set NPC to face PC. Overlaps 0xA9.')

event_commands[0xAA] = \
    EventCommand(0xAA, 1, [1],
                 ['aa: Animation to play'],
                 'Animation',
                 'Play animation. Loops.')

event_commands[0xAB] = \
    EventCommand(0xAB, 1, [1],
                 ['aa: Animation to play'],
                 'Animation',
                 'Play animation.')

event_commands[0xAC] = \
    EventCommand(0xAC, 1, [1],
                 ['aa: Animation to play'],
                 'Static Animation',
                 'Play static animation.')

event_commands[0xAD] = \
    EventCommand(0xAD, 1, [1],
                 ['tt: Time to wait in 1/16 seconds.'],
                 'Pause',
                 'Pause')

event_commands[0xAE] = \
    EventCommand(0xAE, 0, [],
                 [],
                 'Reset Animation',
                 'Resets the object\'s animation.')

event_commands[0xAF] = \
    EventCommand(0xAF, 0, [],
                 [],
                 'Exploration.',
                 'Allows player to control PCs (single controller check).')

event_commands[0xB0] = \
    EventCommand(0xB0, 0, [],
                 [],
                 'Exploration.',
                 'Allows player to control PCs (infinite controller check).')

event_commands[0xB1] = \
    EventCommand(0xB1, 0, [],
                 [],
                 'Break',
                 'End command for arbitrary access contexts.  ' +
                 'Sets conditions for loops to end.  ' +
                 'Advances to next command.')

event_commands[0xB2] = \
    EventCommand(0xB2, 0, [],
                 [],
                 'End',
                 'End command for arbitrary access contexts.  ' +
                 'Sets conditions for loops to end.')

event_commands[0xB3] = \
    EventCommand(0xB3, 0, [],
                 [],
                 'Animation',
                 'Should be equivalent to 0xAA with hardcoded 00')

event_commands[0xB4] = \
    EventCommand(0xB4, 0, [],
                 [],
                 'Animation',
                 'Should be equivalent to 0xAA with hardcoded 01')

event_commands[0xB5] = \
    EventCommand(0xB5, 1, [1],
                 ['oo: Object'],
                 'Move to Object',
                 'Loops 0x94.')

event_commands[0xB6] = \
    EventCommand(0xB6, 1, [1],
                 ['cc: PC'],
                 'Move to PC',
                 'Loops 0x95.')

event_commands[0xB7] = \
    EventCommand(0xB7, 2, [1, 1],
                 ['aa: Animation',
                  'll: Number of loops'],
                 'Loop Animation',
                 'Play animation some number of times.')

event_commands[0xB8] = \
    EventCommand(0xB8, 1, [3],
                 ['aaaaaa: Address to set string index to.'],
                 'String Index',
                 'Sets String Index.')

event_commands[0xB9] = \
    EventCommand(0xB9, 0, [],
                 [],
                 'Pause 1/4',
                 'Pauses 1/4 second.')

event_commands[0xBA] = \
    EventCommand(0xBA, 0, [],
                 [],
                 'Pause 1/2',
                 'Pauses 1/2 second.')

event_commands[0xBB] = \
    EventCommand(0xBB, 1, [1],
                 ['ss: String displayed'],
                 'Personal Textbox',
                 'Displays textbox.  Closes after leaving.')

event_commands[0xBC] = \
    EventCommand(0xBC, 0, [],
                 [],
                 'Pause 1',
                 'Pauses 1 second.')

event_commands[0xBD] = \
    EventCommand(0xBD, 0, [],
                 [],
                 'Pause 2',
                 'Pauses 2 seconds.')

event_commands[0xBE] = event_commands[0x01]
event_commands[0xBE].command = 0xBE
event_commands[0xBE].desc += 'Alias of 0x01.'

event_commands[0xBF] = event_commands[0x01]
event_commands[0xBF].command = 0xBF
event_commands[0xBF].desc += 'Alias of 0x01.'

# Dec box = decision box?
event_commands[0xC0] = \
    EventCommand(0xC0, 2, [1, 1],
                 ['ss: String Displayed',
                  'll: 03 - last line, 0C - first line.'],
                 'Dec Box Auto',
                 'Decision box.  Auto top/bottom.  Stores 00 to 7E0130.')

event_commands[0xC1] = \
    EventCommand(0xC1, 1, [1],
                 ['ss: String Displayed'],
                 'Textbox Top',
                 'Textbox displayed at top of screen.')

event_commands[0xC2] = \
    EventCommand(0xC2, 1, [1],
                 ['ss: String Displayed'],
                 'Textbox Bottom',
                 'Textbox displayed at bottom of screen.')

event_commands[0xC3] = \
    EventCommand(0xC3, 2, [1, 1],
                 ['ss: String Displayed',
                  'll: 03 - last line, 0C - first line.'],
                 'Dec Box Auto',
                 'Decision box at top.  Stores 01 to 7E0130. Overlaps 0xC0')

event_commands[0xC4] = \
    EventCommand(0xC4, 2, [1, 1],
                 ['ss: String Displayed',
                  'll: 03 - last line, 0C - first line.'],
                 'Dec Box Bottom',
                 'Decision box at bottom.  Stores 01 to 7E0130. Overlaps 0xC0')

event_commands[0xC5] = event_commands[0x01]
event_commands[0xC5].command = 0xC5
event_commands[0xC5].desc += 'Alias of 0x01.'

event_commands[0xC6] = event_commands[0x01]
event_commands[0xC6].command = 0xC6
event_commands[0xC6].desc += 'Alias of 0x01.'

event_commands[0xC7] = \
    EventCommand(0xC7, 1, [1],
                 ['oo: Offset (*2, +7F0200) to load item from'],
                 'Add Item',
                 'Add item stored in local memory to inventory.')

event_commands[0xC8] = \
    EventCommand(0xC8, 1, [1],
                 ['dd: Dialog to display'],
                 'Special Dialog',
                 'Special Dialog.')

event_commands[0xC9] = \
    EventCommand(0xC9, 2, [1, 1],
                 ['ii: Item to check for',
                  'jj: Bytes to jump if item not present'],
                 'Check Inventory',
                 'Jump if item not present in inventory.')

event_commands[0xCA] = \
    EventCommand(0xCA, 1, [1],
                 ['ii: Item to add'],
                 'Add Item',
                 'Add item to inventory.')

event_commands[0xCB] = \
    EventCommand(0xCB, 1, [1],
                 ['ii: Item to remove'],
                 'Remove Item',
                 'Remove item from inventory.')

event_commands[0xCC] = \
    EventCommand(0xCC, 2, [2, 1],
                 ['gggg: Gold to check for',
                  'jj: Bytes to jump if not enough gold.'],
                 'Check Gold',
                 'Jump if the player does not have enough gold.')

event_commands[0xCD] = \
    EventCommand(0xCD, 1, [2],
                 ['gggg: Gold to add'],
                 'Add Gold',
                 'Add Gold.')

event_commands[0xCE] = \
    EventCommand(0xCE, 1, [2],
                 ['gggg: Gold to remove.'],
                 'Remove Gold',
                 'Remove Gold.')

event_commands[0xCF] = \
    EventCommand(0xCF, 2, [1, 1],
                 ['cc: PC to check for',
                  'jj: Bytes to jump if PC not recruited'],
                 'Check Recruited',
                 'Check if a PC is recruited.')

event_commands[0xD0] = \
    EventCommand(0xD0, 1, [1],
                 ['cc: PC to add'],
                 'Add Reserve',
                 'Add PC to the reserve party.')

event_commands[0xD1] = \
    EventCommand(0xD1, 1, [1],
                 ['cc: PC to remove'],
                 'Remove PC',
                 'Remove PC (from party? recruited?)')

event_commands[0xD2] = \
    EventCommand(0xD2, 2, [1, 1],
                 ['cc: PC to check for',
                  'jj: Bytes to jump if PC not active'],
                 'Check Active PC',
                 'Jump if PC not active.  May check and load?')

event_commands[0xD3] = \
    EventCommand(0xD3, 1, [1],
                 ['cc: PC to add'],
                 'Add PC to Party',
                 'Add PC to Party.')

event_commands[0xD4] = \
    EventCommand(0xD4, 1, [1],
                 ['cc: PC to reserve'],
                 'Move to Reserve',
                 'Move PC to reserve party.')

event_commands[0xD5] = \
    EventCommand(0xD5, 2, [1, 1],
                 ['cc: PC to equip',
                  'ii: Item to equip'],
                 'Equip Item',
                 'Equip PC with an item.')

event_commands[0xD6] = \
    EventCommand(0xD6, 1, [1],
                 ['cc: PC to remove'],
                 'Remove Active PC',
                 'Remove PC from active party.')

event_commands[0xD7] = \
    EventCommand(0xD7, 2, [1, 1],
                 ['ii: Item to check quantity of',
                  'oo: Offset to store quantity (*2, +7F0200)'],
                 'Get Item Quantity',
                 'Get quantity of item in inventory.')

event_commands[0xD8] = \
    EventCommand(0xD8, 2, [1, 1],
                 ['ffff: Various flags for battle'],
                 'Battle',
                 'Battle.')

event_commands[0xD9] = \
    EventCommand(0xD9, 6, [1, 1, 1, 1, 1, 1],
                 ['uu: PC1 x-coord',
                  'vv: PC1 y-coord',
                  'ww: PC2 x-coord',
                  'xx: PC2 y-coord',
                  'yy: PC3 x-coord',
                  'zz: PC3 y-coord'],
                 'Move Party',
                 'Move party to specified coordinates.')

event_commands[0xDA] = \
    EventCommand(0xDA, 0, [],
                 [],
                 'Party Follow',
                 'Makes PC2 and PC3 follow PC1.')

event_commands[0xDB] = event_commands[0x01]
event_commands[0xDB].command = 0xDB
event_commands[0xDB].desc += 'Alias of 0x01.'

event_commands[0xDC] = \
    EventCommand(0xDC, 3, [2, 1, 1],
                 ['llll: 01FF - location to change to, ' +
                  '0600 - facing, 1800 - ???, 8000 - unused',
                  'xx: X-coord',
                  'yy: Y-coord'],
                 'Change Location',
                 'Instantly moves party to another location.')

event_commands[0xDD] = \
    EventCommand(0xDD, 3, [2, 1, 1],
                 ['llll: 01FF - location to change to, ' +
                  '0600 - facing, 1800 - ???, 8000 - unused',
                  'xx: X-coord',
                  'yy: Y-coord'],
                 'Change Location',
                 'Instantly moves party to another location.')

event_commands[0xDE] = \
    EventCommand(0xDE, 3, [2, 1, 1],
                 ['llll: 01FF - location to change to, ' +
                  '0600 - facing, 1800 - ???, 8000 - unused',
                  'xx: X-coord',
                  'yy: Y-coord'],
                 'Change Location',
                 'Instantly moves party to another location. Overlaps 0xDD.')

event_commands[0xDF] = \
    EventCommand(0xDF, 3, [2, 1, 1],
                 ['llll: 01FF - location to change to, ' +
                  '0600 - facing, 1800 - ???, 8000 - unused',
                  'xx: X-coord',
                  'yy: Y-coord'],
                 'Change Location',
                 'Instantly moves party to another location. Overlaps 0xE1.')

event_commands[0xE0] = \
    EventCommand(0xE0, 3, [2, 1, 1],
                 ['llll: 01FF - location to change to, ' +
                  '0600 - facing, 1800 - ???, 8000 - unused',
                  'xx: X-coord',
                  'yy: Y-coord'],
                 'Change Location',
                 'Instantly moves party to another location.')

event_commands[0xE1] = \
    EventCommand(0xE1, 3, [2, 1, 1],
                 ['llll: 01FF - location to change to, ' +
                  '0600 - facing, 1800 - ???, 8000 - unused',
                  'xx: X-coord',
                  'yy: Y-coord'],
                 'Change Location',
                 'Instantly moves party to another location. Waits vsync.')

event_commands[0xE2] = \
    EventCommand(0xE2, 4, [1, 1, 1, 1],
                 ['aa: Offset (*2, +7F0200) to load from',
                  'bb: Offset (*2, +7F0200) to load from',
                  'cc: Offset (*2, +7F0200) to load from',
                  'dd: Offset (*2, +7F0200) to load from'],
                 'Change Location',
                 'Instantly moves party to another location.  ' +
                 'Uses local memory to get paramters.  See e.g. E1.')

event_commands[0xE3] = \
    EventCommand(0xE3, 1, [1],
                 ['tt: Toggle value.  On - Can explore, Off- cannot.'],
                 'Explore Mode',
                 'Set whether the party can freely move.')

event_commands[0xE4] = \
    EventCommand(0xE4, 7, [1, 1, 1, 1, 1, 1, 1],
                 ['ll: X-coord of top left corner of source',
                  'tt: Y-coord of top left corner of source',
                  'rr: X-coord of bottom right corner of source',
                  'bb: Y-coord of bottom right corner of soucre',
                  'xx: X-coord of destination',
                  'yy: Y-coord of destination',
                  'ff: Bitfield (see long notes in db)'],
                 'Copy Tiles',
                 'Copies tiles (from data onto map?)')

event_commands[0xE5] = \
    EventCommand(0xE5, 7, [1, 1, 1, 1, 1, 1, 1],
                 ['ll: X-coord of top left corner of source',
                  'tt: Y-coord of top left corner of source',
                  'rr: X-coord of bottom right corner of source',
                  'bb: Y-coord of bottom right corner of soucre',
                  'xx: X-coord of destination',
                  'yy: Y-coord of destination',
                  'ff: Bitfield (see long notes in db)'],
                 'Copy Tiles',
                 'Copies tiles (from data onto map?)')

event_commands[0xE6] = \
    EventCommand(0xE6, 3, [2, 1, 1],
                 ['????: Unknown',
                  'll: Layers to scroll bitfield',
                  '??: Unknown'],
                 'Scroll Layers',
                 'Scroll Layers')

event_commands[0xE7] = \
    EventCommand(0xE7, 2, [1, 1],
                 ['xx: X-coordinate',
                  'yy: Y-coordinate'],
                 'Scroll Screen',
                 'Scroll Screen')

event_commands[0xE8] = \
    EventCommand(0xE8, 1, [1],
                 ['ss: Sound Effect'],
                 'Play Sound',
                 'Plays a sound.')

event_commands[0xE9] = event_commands[0x01]
event_commands[0xE9].command = 0xE9
event_commands[0xE9].desc += 'Alias of 0x01.'

event_commands[0xEA] = \
    EventCommand(0xEA, 1, [1],
                 ['ss: Song'],
                 'Play Song',
                 'Plays a song.')

event_commands[0xEB] = \
    EventCommand(0xEB, 2, [1, 1],
                 ['ss: Speed of change',
                  'vv: Volume (0xFF=normal)'],
                 'Change Volume',
                 'Change Volume.')

event_commands[0xEC] = \
    EventCommand(0xEC, 3, [1, 1, 1],
                 ['cc: Command',
                  '??: Unknown',
                  '??: Unknown'],
                 'All Purpose Sound',
                 'All Purpose Sound Command.')

event_commands[0xED] = \
    EventCommand(0xED, 0, [],
                 [],
                 'Wait for Silence',
                 'Wait for Silence')

event_commands[0xEE] = \
    EventCommand(0xEE, 0, [],
                 [],
                 'Wait for Song End',
                 'Wait for Song End')

event_commands[0xEF] = event_commands[0x01]
event_commands[0xEF].command = 0xEF
event_commands[0xEF].desc += 'Alias of 0x01.'

event_commands[0xF0] = \
    EventCommand(0xF0, 1, [1],
                 ['bb: Amount to darken'],
                 'Darken Screen',
                 'Darken Screen')

# Variable length
event_commands[0xF1] = \
    EventCommand(0xF1, 2, [1, 1],
                 ['cc: 0xE0 - 3 bit BGR color, 0x1F - Intensity',
                  '(dd): 0x80 add/sub mode only if cc != 0'],
                 'Color Addition',
                 'Color Addition')

event_commands[0xF2] = \
    EventCommand(0xF2, 0, [],
                 [],
                 'Fade Out',
                 'Fade Out')

event_commands[0xF3] = \
    EventCommand(0xF3, 0, [],
                 [],
                 'Wait for Brighten End',
                 'Wait for brighten end.')

event_commands[0xF4] = \
    EventCommand(0xF4, 1, [1],
                 ['rr: Shake Screen, 00 = off'],
                 'Shake Screen',
                 'Shake screen.')

event_commands[0xF5] = event_commands[0x01]
event_commands[0xF5].command = 0xF5
event_commands[0xF5].desc += 'Alias of 0x01.'

event_commands[0xF6] = event_commands[0x01]
event_commands[0xF6].command = 0xF6
event_commands[0xF6].desc += 'Alias of 0x01.'

event_commands[0xF7] = event_commands[0x01]
event_commands[0xF7].command = 0xF7
event_commands[0xF7].desc += 'Alias of 0x01.'

event_commands[0xF8] = \
    EventCommand(0xF8, 0, [],
                 [],
                 'Restore hp/mp.',
                 'Restore hp/mp.')

event_commands[0xF9] = \
    EventCommand(0xF9, 0, [],
                 [],
                 'Restore hp.',
                 'Restore hp.')

event_commands[0xFA] = \
    EventCommand(0xFA, 0, [],
                 [],
                 'Restore mp.',
                 'Restore mp.')

event_commands[0xFB] = event_commands[0x01]
event_commands[0xFB].command = 0xFB
event_commands[0xFB].desc += 'Alias of 0x01.'

event_commands[0xFC] = event_commands[0x01]
event_commands[0xFC].command = 0xFC
event_commands[0xFC].desc += 'Alias of 0x01.'

event_commands[0xFD] = event_commands[0x01]
event_commands[0xFD].command = 0xFD
event_commands[0xFD].desc += 'Alias of 0x01.'

event_commands[0xFE] = \
    EventCommand(0xFE, 17, [1 for i in range(17)],
                 ['Unknown' for i in range(17)],
                 'Unknown Geometry',
                 'Something relating to on screen geometry')

event_commands[0xFF] = \
    EventCommand(0xFF, 1, [1],
                 ['ss: Scene to play'],
                 'Mode 7 Scene',
                 'Mode 7 Scene.')


def get_command(buf: bytes, offset: int = 0) -> EventCommand:

    command_id = buf[offset]
    command = event_commands[command_id].copy()

    # print(command)
    # input()

    if command_id == 0x2E:
        mode = buf[offset+1] >> 4
        if mode in [4, 5]:
            command.arg_lens = [1, 1, 1, 1, 1]
        elif mode == 8:
            command.arg_lens = [1, 1, 2]
        else:
            print(f"{command_id:02X}: Error, Unknown Mode")
    elif command_id == 0x4E:
        # Data to copy follows command.  Shove data in last arg.
        data_len = get_value_from_bytes(buf[offset+4:offset+6]) - 2
        command.arg_lens = [2, 1, 2, data_len]
    elif command_id == 0x88:
        mode = buf[offset+1] >> 4
        if mode == 0:
            command.arg_lens = [1]
        elif mode in [2, 3]:
            command.arg_lens = [1, 1, 1]
        elif mode in [4, 5]:
            command.arg_lens = [1, 1, 1, 1]
        elif mode == 8:
            # bytes to copy follow command
            copy_len = buf[offset+2] - 2
            command.arg_lens = [1, 1, 1, copy_len]
        else:
            print(f"{command_id:02X}: Error, Unknown Mode")
    elif command_id == 0xF1:
        color = buf[offset+1]
        if color == 0:
            command.arg_lens = [1]
        else:
            command.arg_lens = [1, 1]
    elif command_id == 0xFF:  # Mode7 scenes can be weird
        scene = buf[offset+1]
        if scene == 0x90:
            command.arg_lens = [1, 1, 1, 1]
        if scene == 0x97:
            command.arg_lens = [1, 1, 1]

    # Now we can use arg_lens to extract the args
    pos = offset + 1
    command.args = []

    if command.command == 0x4E:
        for i in command.arg_lens[0:-1]:
            command.args.append(get_value_from_bytes(buf[pos:pos+i]))
            pos += i

        command.args.append(
            bytearray(buf[pos:pos+command.arg_lens[-1]])
        )
        pos += command.arg_lens[-1]
    else:
        for i in command.arg_lens:
            command.args.append(get_value_from_bytes(buf[pos:pos+i]))
            pos += i

    return command
