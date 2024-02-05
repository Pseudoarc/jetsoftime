from __future__ import annotations
import enum
from pathlib import Path
from typing import ByteString, Optional, Union, Tuple

from ctdecompress import compress, decompress, get_compressed_length, \
    get_compressed_packet
from ctenums import LocID
from byteops import get_value_from_bytes, to_little_endian, to_file_ptr, \
    to_rom_ptr
import ctstrings
from eventcommand import EventCommand as EC, get_command
from eventfunction import EventFunction as EF
from freespace import FSRom, FSWriteType


class FunctionID(enum.IntEnum):
    '''Convenience enum for TF-style object function naming.'''
    STARTUP = 0
    ACTIVATE = 1
    TOUCH = 2
    ARBITRARY_0 = 3
    ARBITRARY_1 = 4
    ARBITRARY_2 = 5
    ARBITRARY_3 = 6
    ARBITRARY_4 = 7
    ARBITRARY_5 = 8
    ARBITRARY_6 = 9
    ARBITRARY_7 = 0xA
    ARBITRARY_8 = 0xB
    ARBITRARY_9 = 0xC
    ARBITRARY_A = 0xD
    ARBITRARY_B = 0xE
    ARBITRARY_C = 0xF


class CommandNotFoundException(Exception):
    '''Raise when a find_command call fails.'''


def get_compressed_script(rom: ByteString, event_id: int):
    '''
    Gets the compressed event packet for the given event_id.

    Note: event_id is not the same as location id.
    '''
    # Location events pointers are located on the rom starting at 0x3CF9F0
    # Each location has (I think) an index into this list of pointers.  The
    # pointers definitely do not occur in the same order as the locations.

    event_ptr_st = 0x3CF9F0

    # Each event pointer is an absolute, 3 byte pointer
    start = event_ptr_st + 3*event_id

    event_ptr = \
        get_value_from_bytes(rom[start:start+3])
    event_ptr = to_file_ptr(event_ptr)

    return get_compressed_packet(rom, event_ptr)


def get_loc_event_ptr(rom: ByteString, loc_id: int) -> int:
    '''Get a the address of a location's event packet.'''
    # Location data begins at 0x360000.
    # Each record is 14 bytes.  Bytes 8 and 9 (0-indexed) hold an index into
    # the pointer table for event scripts.

    loc_data_st = 0x360000
    event_ind_st = loc_data_st + 14*loc_id + 8

    loc_script_ind = get_value_from_bytes(rom[event_ind_st:event_ind_st+2])

    event_ptr_st = 0x3CF9F0

    # Each event pointer is an absolute, 3 byte pointer
    start = event_ptr_st + 3*loc_script_ind
    event_ptr = \
        get_value_from_bytes(rom[start:start+3])

    event_ptr = to_file_ptr(event_ptr)

    return event_ptr


def get_location_script(rom, loc_id):
    # Location data begins at 0x360000.
    # Each record is 14 bytes.  Bytes 8 and 9 (0-indexed) hold an index into
    # the pointer table for event scripts.

    loc_data_st = 0x360000
    event_ind_st = loc_data_st + 14*loc_id + 8

    loc_script_ind = get_value_from_bytes(rom[event_ind_st:event_ind_st+2])

    # print(f"Script Index = {loc_script_ind:04X}")

    return get_compressed_script(rom, loc_script_ind)


# The strategy is to handle the event very similarly to how the game does.
# The event is just one big list of commands with pointers giving the starts
# of relevant entities (objects, functions).
class Event:

    _flux_path: Path = Path(__file__).parent / 'flux'

    def __init__(self):
        self.num_objects = 0

        # self.extra_ptr_st = 0
        # self.script_st = 0

        self.data = bytearray()

        self.modified_strings = False
        self.strings = []

    def get_bytearray(self) -> bytearray:
        return bytearray([self.num_objects]) + self.data

    @staticmethod
    def from_rom_location(rom: ByteString, loc_id: int) -> Event:
        ''' Read an event from the specified game location. '''

        ptr = get_loc_event_ptr(rom, loc_id)
        return Event.from_rom(rom, ptr)

    @staticmethod
    def from_flux(filename: str):
        '''Reads a .flux file and loads it into an Event'''
        with Event._get_flux_path(filename).open('rb') as infile:
            flux = bytearray(infile.read())

        # These first bytes are used internally by TF, but they don't seem
        # to matter for our purposes.  If we want to write flux files we'll
        # have to figure those out.
        script_start = 0x17
        script_len = get_value_from_bytes(flux[0x13:0x15])
        script_end = script_start+script_len

        ret_script = Event()

        ret_script.num_objects = flux[0x17]
        ret_script.data = flux[0x18:script_end]

        # Now for strings... This is the ugly part.
        num_strings = flux[script_end]
        ret_script.strings = [
            ctstrings.CTString.from_ascii('error!{null}')
            for x in range(num_strings)
        ]

        # a few more blank/unknown bytes after number of strings
        pos = script_end + 4

        while pos < len(flux):
            string_ind = flux[pos]

            # if string_ind != cur_string_ind:
            #     print(
            #         f"Expected {cur_string_ind:02X}, found {string_ind:02X}"
            #     )
            #     exit()
            string_len = flux[pos+1]
            pos += 2

            # The byte after the string length byte is optional.
            # If present, value N means add 0x80*(N-1) to the length.
            # Being present means having a value in the unprintable range
            # (value < 0x20).
            if flux[pos] < 12:
                string_len += 0x80*(flux[pos]-1)
                pos += 1

            string_end = pos + string_len

            cur_string = flux[pos:string_end]
            # Remove non-printable characters from the string.  Flux seems to
            # put each ascii char in 16 bits, so there are many 0x00s.

            # We used to clear out all unprintable ascii, but then found out
            # that TF uses some \r\n as actual string linebreaks.  So now we
            # only clear out the 0s and handle the rest in ctstrings.

            cur_string = \
                bytearray([x for x in cur_string if x != 0])

            # alias to save keystrokes
            CTString = ctstrings.CTString

            ct_str = CTString.from_ascii(cur_string.decode('ascii'))
            ct_str.compress()

            ret_script.strings[string_ind] = ct_str

            pos += string_len

        # end while pos < len(flux)

        if num_strings != len(ret_script.strings):
            raise ValueError(f"Expected {num_strings} strings.  "
                             f"Found {len(ret_script.strings)}")

        ret_script.modified_strings = True

        return ret_script

    @classmethod
    def from_rom(cls, rom: ByteString, ptr: int) -> Event:
        ret_event = Event()

        event = decompress(rom, ptr)

        # Note: The game itself writes all pointers as offsets from the initial
        # byte that gives the number of objects.  So we're going to store the
        # script data without that initial byte so that the offsets are actual
        # indices into the data.
        ret_event.data = event[1:]
        ret_event.num_objects = event[0]

        # According to Geiger's notes, sometimes there are extra pointers.
        # I might just throw them away, but potentially these can be associated
        # with an (obj, func) and updated as need be.
        # ret_event.extra_ptr_st = 32*ret_event.num_objects
        # ret_event.script_st = get_value_from_bytes(event[0:2])

        # Build the strings up.
        ret_event.__init_strings(rom)

        return ret_event

    def print_fn_starts(self):
        for i in range(self.num_objects):
            print(f"Object {i:02X}")
            print(' '.join(f"{self.get_function_start(i,j):04X}"
                           for j in range(8)))
            print(' '.join(f"{self.get_function_start(i,j):04X}"
                           for j in range(8, 16)))

    def add_py_string(self, new_string: str) -> int:
        ct_str = ctstrings.CTString.from_str(new_string)
        ct_str.compress()

        return self.add_string(ct_str)

    def add_string(self, new_string: bytearray) -> int:
        self.strings.append(new_string)
        self.modified_strings = True
        return len(self.strings) - 1

    def get_obj_strings(self, obj_id: int) -> dict[int, bytearray]:

        if obj_id >= self.num_objects:
            raise ValueError(f"Error: requested object {obj_id:02X} " +
                             f"(max {self.num_objects-1:02X}")

        pos = self.get_object_start(obj_id)
        end = self.get_object_end(obj_id)

        string_indices = set()

        while pos < end:
            cmd = get_command(self.data, pos)

            if cmd in EC.str_commands:
                string_indices.add(cmd.args[0])

            pos += len(cmd)

        ret_dict = {
            index: bytearray(self.strings[index])
            for index in string_indices
        }

        return ret_dict

    # Find the string index of an event
    def get_string_index(self):

        start = self.get_function_start(0, 0)
        end = self.get_object_end(0)

        pos = start
        found = False
        while pos < end:
            cmd = get_command(self.data, pos)

            if cmd.command == 0xB8:
                string_index = cmd.args[0]
                found = True
                # Can maybe just return here.  There should only be one

            pos += len(cmd)

        if not found:
            print("Warning: No string index.")
            return None

        return string_index

    # Using the FS object's getbuffer() gives a memoryview which doesn't
    # support bytearray's .index method.  This is a stupid short method to
    # extract a string starting at a given address.
    @classmethod
    def __get_ct_string(cls, rom: ByteString, start_ptr: int) -> bytearray:
        end_ptr = start_ptr

        while rom[end_ptr] != 0 and end_ptr < len(rom):
            end_ptr += 1

        if end_ptr == len(rom):
            raise ValueError('Error, failed to find string end.')

        return bytearray(rom[start_ptr:end_ptr+1])

    # This is only called during initialization of a script
    # We need access to the whole rom to look up the strings used by the script
    def __init_strings(self, rom: ByteString):

        # First find the location where string pointers are stored by finding
        # the "string index" command in the script.
        pos = self.get_object_start(0)

        str_pos = None
        while pos < len(self.data):
            cmd = get_command(self.data, pos)

            if cmd.command == 0xB8:
                str_pos = cmd.args[0]
                # print(cmd)

                # The string index should only be set once
                # break

            pos += len(cmd)

        self.modified_strings = False
        # indices that are used
        str_indices = set()

        # addresses in the script data where an index is located
        # store these to go back and update the indices if we have to
        str_addrs = []

        pos = self.get_object_start(0)
        while pos < len(self.data):
            cmd = get_command(self.data, pos)

            if cmd.command in EC.str_commands:
                # string index argument is 0th arg
                str_indices.add(cmd.args[0])
                str_addrs.append(pos+1)

            pos += len(cmd)

        # turn str_indices into a sorted list
        str_indices_list = sorted(list(str_indices))
        self.strings = []

        if str_indices:
            if str_pos is None:
                raise ValueError('Strings present but no string index set.')

            bank = (str_pos >> 16) << 16
            bank = to_file_ptr(bank)

            for index in str_indices_list:
                # string ptrs are 2 byte ptrs local to the string_pos bank
                ptr_st = to_file_ptr(str_pos+2*index)
                str_st = get_value_from_bytes(rom[ptr_st:ptr_st+2])+bank

                self.strings.append(Event.__get_ct_string(rom, str_st))

                # print(' '.join(f"{x:02X}" for x in self.strings[-1]))
                # input()

            # Go back to the script and update the indices if any changed

            for addr in str_addrs:
                new_ind = str_indices_list.index(self.data[addr])

                if new_ind != self.data[addr]:
                    self.modified_strings = True
                    self.data[addr] = new_ind

        # end if there are any strings

    def get_object_start(self, obj_id: int) -> int:
        return get_value_from_bytes(self.data[32*obj_id: 32*obj_id+2])

    def get_object_end(self, obj_id: int) -> int:
        if obj_id == self.num_objects - 1:
            return len(self.data)

        return self.get_object_start(obj_id+1)

    # Normal warning to make sure the function is nonempty before using
    # this value.
    def get_function_start(self, obj_id: int, func_id: int) -> int:
        ptr = 32*obj_id + 2*func_id
        return get_value_from_bytes(self.data[ptr:ptr+2])

    def get_function_end(self, obj_id: int, func_id: int) -> int:
        start = self.get_function_start(obj_id, func_id)

        # print(f"{start:04X}")

        next_ptr_st = 32*obj_id + 2*func_id + 2

        for ptr in range(next_ptr_st, self.num_objects*32, 2):
            next_fn_st = get_value_from_bytes(self.data[ptr:ptr+2])
            # print("f{next_fn_st:04X}")
            if next_fn_st != start:
                return next_fn_st

        # If we get here, we didn't find a nonempty function after the given
        # function.  So our function goes to the end of the data.
        return len(self.data)

    def get_function(self, obj_id: int, func_id: int) -> EF:
        start = self.get_function_start(obj_id, func_id)
        end = self.get_function_end(obj_id, func_id)

        return EF.from_bytearray(self.data[start:end])

    # This isn't what I want/what is needed.  Avoid.
    # def get_object(self, obj_id: int) -> bytearray:
    #     start = self.get_function_start(obj_id, 0)
    #     end = self.get_function_end(obj_id, 0)

    #     return self.data[start:end]

    # Completely remove an object from the script.
    # Worried about what might happen if some of those extra pointers point
    # to routines in the deleted object.
    def remove_object(self, obj_id: int, remove_calls: bool = True):

        if remove_calls:
            self.__remove_shift_object_calls(obj_id)

        obj_st = self.get_object_start(obj_id)

        if obj_id == self.num_objects-1:
            obj_end = len(self.data)
        else:
            obj_end = self.get_object_start(obj_id+1)

        obj_len = obj_end-obj_st

        # print(f"{obj_st+1:04X} - {obj_end+1:04X}")
        # input()

        self.__shift_starts(obj_st, -obj_len)
        self.__shift_starts(-1, -32)

        del self.data[obj_st:obj_end]
        del self.data[32*obj_id:32*(obj_id+1)]

        self.num_objects -= 1

    def __shift_object_calls(self, obj_id: int, is_deletion: bool):
        # Remove all calls to object 0xC's functions
        calls = [2, 3, 4]
        draw_status = [0x7C, 0x7D]
        processing = [0x0A, 0x0B, 0x0C]

        obj_cmds = calls + draw_status + processing

        pos: Optional[int] = self.get_function_start(0, 0)
        end = len(self.data)
        while True:
            (pos, cmd) = self.find_command_opt(obj_cmds,
                                               pos, end)
            if pos is None:
                break
            # It just so happens that the draw status commands and the object
            # call commands use 2*obj_id and have the object in arg0
            if cmd.command in obj_cmds:
                if cmd.args[0] == 2*obj_id and is_deletion:
                    # print(f"deleted [{pos:04X}] " + str(cmd))
                    # input()
                    self.delete_commands(pos, 1)
                    end = len(self.data)
                else:
                    if cmd.args[0] >= 2*obj_id:
                        # print('shifting')
                        # print(f"[{pos:04X}] " + str(cmd))
                        # input()
                        if is_deletion:
                            self.data[pos+1] -= 2
                        else:
                            self.data[pos+1] += 2
                    pos += len(cmd)

    def __remove_shift_object_calls(self, obj_id):
        # Remove all calls to object 0xC's functions
        calls = [2, 3, 4]
        draw_status = [0x7C, 0x7D]
        processing = [0x0A, 0x0B, 0x0C]

        obj_cmds = calls + draw_status + processing

        pos = self.get_function_start(0, 0)
        end = len(self.data)
        while True:
            (pos, cmd) = self.find_command_opt(obj_cmds,
                                               pos, end)
            if pos is None:
                break
            # It just so happens that the draw status commands and the object
            # call commands use 2*obj_id and have the object in arg0
            if cmd.command in obj_cmds:
                if cmd.args[0] == 2*obj_id:
                    # print(f"deleted [{pos:04X}] " + str(cmd))
                    # input()
                    self.delete_commands(pos, 1)
                    end = len(self.data)
                else:
                    if cmd.args[0] > 2*obj_id:
                        # print('shifting')
                        # print(f"[{pos:04X}] " + str(cmd))
                        # input()
                        self.data[pos+1] -= 2
                    pos += len(cmd)

    def remove_object_calls(self, obj_id):
        # Remove all calls to object 0xC's functions
        pos = self.get_function_start(0, 0)
        end = len(self.data)
        while True:
            (pos, cmd) = self.find_command_opt([2, 3, 4],
                                               pos, end)
            if pos is None:
                break
            if cmd.args[0] == 2*obj_id:
                # print(f"deleted [{pos:04X}] " + str(cmd))
                # input()
                self.delete_commands(pos, 1)
                end = len(self.data)
            else:
                pos += len(cmd)

    def print_func_starts(self, obj_id: int):

        for i in range(16):
            st = 32*obj_id + 2*i
            print(f"{get_value_from_bytes(self.data[st:st+2])+1: 04X}")

    # This will break if the object has references to other objects' fns
    def append_copy_object(self, obj_id: int):

        if self.num_objects == 0x40:
            raise IndexError("No room for additional objects.")

        obj_start = self.get_object_start(obj_id)
        obj_end = self.get_function_end(obj_id, 0xF)

        obj_ptrs = self.data[32*obj_id:32*(obj_id+1)]
        for ptr in range(0, 32, 2):
            ptr_loc = get_value_from_bytes(obj_ptrs[ptr:ptr+2])
            shift = -obj_start + len(self.data) + 32
            obj_ptrs[ptr:ptr+2] = to_little_endian(ptr_loc + shift, 2)

        obj_data = self.data[obj_start:obj_end]

        self.data[32*self.num_objects:32*self.num_objects] = obj_ptrs[:]

        for ptr in range(0, 32*self.num_objects, 2):
            ptr_loc = get_value_from_bytes(self.data[ptr:ptr+2])
            self.data[ptr:ptr+2] = to_little_endian(ptr_loc+32, 2)

        self.data.extend(obj_data)
        self.num_objects += 1

        return self.num_objects-1

    def append_empty_object(self) -> int:
        '''Makes space for new object.  Returns new object id.'''

        if self.num_objects == 0x40:
            raise IndexError("No room for additional objects.")

        # Account for the 32 bytes of pointers we're about to add here
        end_b = to_little_endian(len(self.data)+32, 2)

        new_ptrs = b''.join(end_b for i in range(16))
        self.data[32*self.num_objects:32*self.num_objects] = new_ptrs

        # shift all old pointers by 32
        for i in range(self.num_objects*16):
            ptr_st = 2*i
            old_ptr = get_value_from_bytes(self.data[ptr_st:ptr_st+2])
            self.data[ptr_st:ptr_st+2] = to_little_endian(old_ptr+32, 2)

        # Now it's safe to increment the number of objects
        self.num_objects += 1

        return self.num_objects-1

    def insert_copy_object(self, copy_id: int, ins_id: int):
        '''
        Insert a copy of object copy_id into spot ins_id.
        Will break if the object calls other object functions.
        '''

        orig_obj_st = self.get_function_start(copy_id, 0)
        orig_obj_ptrs = [
            int.from_bytes(self.data[32*copy_id+2*ind: 32*copy_id+2*ind+2],
                           'little') - orig_obj_st
            for ind in range(0x10)
        ]

        if copy_id == self.num_objects - 1:
            orig_obj_end = len(self.data)
        else:
            orig_obj_end = self.get_function_start(copy_id+1, 0)

        object_data = self.data[orig_obj_st: orig_obj_end]

        insert_pos = self.get_function_start(ins_id, 0)
        ins_obj_ptrs = [ptr+insert_pos for ptr in orig_obj_ptrs]
        ins_obj_ptrs_b = b''.join(
            int.to_bytes(ptr, 2, 'little')
            for ptr in ins_obj_ptrs
        )

        # Shift jumps for insertion of new pointers and data.
        self.__shift_jumps(insert_pos, insert_pos, len(object_data))
        self.__shift_jumps(0, 0, 32)

        self.__shift_starts(insert_pos-1, len(object_data))
        self.__shift_object_calls(ins_id, is_deletion=False)

        self.data[insert_pos:insert_pos] = object_data
        self.data[32*ins_id:32*ins_id] = ins_obj_ptrs_b
        self.num_objects += 1
        self.__shift_starts(-1, 32)

    def _function_is_linked(self, obj_id, func_id) -> bool:
        '''
        Determine whether a function links to another object's function.
        '''
        this_obj_st = self.get_object_start(obj_id)
        if obj_id == self.num_objects - 1:
            next_obj_st = len(self.data)
        else:
            next_obj_st = self.get_object_start(obj_id+1)

        this_fn_st = self.get_function_start(obj_id, func_id)
        return not (this_obj_st <= this_fn_st < next_obj_st)

    def _function_is_empty(self, obj_id, func_id) -> bool:
        '''
        Determine whether a function is empty (links to previous function)
        '''

        if func_id == 0:
            return False

        given_start = self.get_function_start(obj_id, func_id)
        for ind in range(func_id - 1, -1, -1):
            prev_start = self.get_function_start(obj_id, ind)
            if prev_start == given_start:
                return True

        return False

    def _function_is_real(self, obj_id, func_id) -> bool:
        return not (self._function_is_empty(obj_id, func_id) or
                    self._function_is_linked(obj_id, func_id))

    def _get_next_true_start(self, obj_id: int, func_id: int) -> int:
        '''
        Find the start of the next real function (non-empty, non-linked)
        '''
        # print(f'Finding true start after {obj_id:2X}, {func_id:02X}')
        true_end = None

        for ind in range(func_id+1, 0x10):
            if self._function_is_real(obj_id, ind):
                true_end = self.get_function_start(obj_id, ind)
                break

        if true_end is None:
            if obj_id == self.num_objects - 1:
                true_end = len(self.data)
            else:
                true_end = self.get_object_start(obj_id+1)

        return true_end

    def _set_function_start(self, obj_id, func_id, new_start):
        ptr_st = obj_id*32 + func_id*2
        self.data[ptr_st:ptr_st+2] = int.to_bytes(new_start, 2, 'little')

    def set_function(self, obj_id: int, func_id: int,
                     ev_func: EF):
        self.set_function_new(obj_id, func_id, ev_func)

    def set_function_new(self, obj_id: int, func_id: int,
                         ev_func: EF):
        '''
        Version of set_function that tries to handle linked functions.
        '''

        # for i in range(0x10):
        #     is_linked = self._function_is_linked(obj_id, i)
        #     is_empty = self._function_is_empty(obj_id, i)
        #     start = self.get_function_start(obj_id, i)

        #     print(f'Function {i:02X}: {start+1:04X}, empty={is_empty}, '
        #           f'linked={is_linked}')

        # Find the first real function before this one.
        # The true start is the end (next true start) from that point.
        true_start = None
        for ind in range(func_id-1, -1, -1):
            if self._function_is_real(obj_id, ind):
                true_start = self._get_next_true_start(obj_id, ind)
                break

        if true_start is None:
            true_start = self.get_object_start(obj_id)

        if true_start is None:
            raise ValueError('Unable to find real function')

        true_end = self._get_next_true_start(obj_id, func_id)

        if len(ev_func) == 0:
            # This is annoying because we're making a function empty
            # TODO: check on this case
            pass

        # self.insert_commands(ev_func.get_bytearray(), true_start)
        # self.delete_commands_range(true_start+len(ev_func),
        #                            true_end+len(ev_func))
        # print(ev_func, len(ev_func))

        shift = len(ev_func) - (true_end-true_start)

        empty_end = 0x10
        for ind in range(func_id+1, 0x10):
            if self._function_is_real(obj_id, ind):
                empty_end = ind
                break

        # Set the empty functions immediately following the changed function
        for ind in range(func_id+1, empty_end):
            if self._function_is_empty(obj_id, ind) and \
               not self._function_is_linked(obj_id, ind):
                self._set_function_start(obj_id, ind, true_start)

        for ind in range(empty_end, 0x10):
            start = self.get_function_start(obj_id, ind)
            if start >= true_start:
                self._set_function_start(obj_id, ind,
                                         start+shift)

        self._set_function_start(obj_id, func_id, true_start)
        for obj_ind in range(self.num_objects):
            if obj_ind == obj_id:
                continue

            for func_ind in range(0x10):
                func_st = self.get_function_start(obj_ind, func_ind)
                if func_st >= true_start:
                    self._set_function_start(obj_ind, func_ind,
                                             func_st + shift)

        self.data[true_start:true_end] = ev_func.get_bytearray()

        # for i in range(0x10):
        #     is_linked = self._function_is_linked(obj_id, i)
        #     is_empty = self._function_is_empty(obj_id, i)
        #     start = self.get_function_start(obj_id, i)

        #     print(f'Function {i:02X}: {start+1:04X}, empty={is_empty}, '
        #           f'linked={is_linked}')

    def set_function_old(self, obj_id: int, func_id: int,
                         ev_func: EF):
        '''Sets the given EventFunction in the script.'''

        # The main difficulty is figuring out where the function should
        # actually begin.  The default behavior of CT scripts is that
        # unused functions are given the starting point of the last used
        # function.

        # print(obj_id, func_id)

        func_st_ptr = 32*obj_id + 2*func_id
        func_st = \
            get_value_from_bytes(self.data[func_st_ptr:func_st_ptr+2])

        # print(f"func start: {func_st+1:04X}")

        empty_func = False
        # +1 to match TF for debug
        # print(f"Function start: {func_st+1:04X}")
        if func_id != 0:
            prev_st = \
                get_value_from_bytes(self.data[func_st_ptr-2:
                                               func_st_ptr])

            # print(f"Prev start: {prev_st+1:04X}")

            if prev_st == func_st:
                # print("empty func")
                empty_func = True

        # We need to look ahead to figure out where the current function
        # ends.  If the function is empty we'll set the start there as well.

        ptr = func_st_ptr + 2
        found = False

        # last_ptr is going to keep track of how many empty functions there
        # are after the function we're setting.  The empty functions after
        # should have their starts set to the start of this function.
        last_ptr = ptr

        for ptr in range(func_st_ptr+2, 32*self.num_objects, 2):
            ptr_loc = get_value_from_bytes(self.data[ptr:ptr+2])
            if ptr_loc != func_st:
                found = True
                func_end = ptr_loc
                last_ptr = ptr

                if empty_func:
                    func_st = ptr_loc

                break

        # If we didn't find a different location in any of the remaining
        # ptrs, then we are adding to the end of the data
        if not found:
            func_end = len(self.data)
            func_st = len(self.data)
            last_ptr = 32*self.num_objects

        # By here we should have sorted out what the real start and end
        # positions should be
        old_size = func_end - func_st
        new_size = len(ev_func.get_bytearray())
        shift = new_size - old_size

        # print(f"{func_st+1:04X} to {func_end+1:04X}")

        self.data[func_st:func_end] = ev_func.get_bytearray()

        # Now shift all of the pointers after the one for the function we set
        # TODO: Make sure that function starts are really monotone
        for ptr in range(0, 32*self.num_objects, 2):
            ptr_loc = get_value_from_bytes(self.data[ptr:ptr+2])
            if ptr_loc >= func_st:
                self.data[ptr:ptr+2] = to_little_endian(ptr_loc+shift, 2)

        # Go back and rewrite the target function pointer and all empty
        # functions afterwards.
        for ptr in range(func_st_ptr, last_ptr, 2):
            self.data[ptr:ptr+2] = to_little_endian(func_st, 2)
    # End set_function

    # delete a whole dang object.  Needed for cleaning up some scripts with
    # extra, unused objects.  Also removes references to the deleted
    # object (call obj function, visibility, etc) and shifts all other calls
    # to objects past the removed one by 1.
    def delete_object(self, obj_id: int):
        # print(f"delete obj {obj_id:02X}")
        # We're going to assume that the init functions (function 0) always
        # have real start locations.  It would be crazy if this were not so.
        start = self.get_function_start(obj_id, 0)

        # doing this instead of start of obj_id+1 to avoid out of bounds
        end = self.get_function_end(obj_id, 0xF)

        obj_len = end-start

        # We're also going to assume that there are no jumps that jump
        # between objects, so it's safe to delete the data, shift the
        # pointers and move on with our lives.

        # Shift Pointers.  Don't forget the extra 32 when the ptrs go.

        for ptr in range(0, 32*(obj_id), 2):
            ptr_loc = get_value_from_bytes(self.data[ptr:ptr+2])
            self.data[ptr:ptr+2] = to_little_endian(ptr_loc-32, 2)

        for ptr in range(32*(obj_id+1), 32*self.num_objects, 2):
            ptr_loc = get_value_from_bytes(self.data[ptr:ptr+2])

            self.data[ptr:ptr+2] = to_little_endian(ptr_loc-obj_len-32, 2)

        # delete object data and pointers
        del self.data[start:end]
        del self.data[32*obj_id:32*(obj_id+1)]

        # update object count
        self.num_objects -= 1

        self.remove_object_calls(obj_id)
        self.__shift_calls_back(obj_id)

    def set_string_index(self, rom_ptr: int):

        start = self.get_function_start(0, 0)
        end = self.get_function_end(0, 0)

        pos, _ = self.find_command_opt([0xB8], start, end)

        # TODO: Worry whether there are multiple string index commands.
        #       Should keep searching and delete extra ones.
        if pos is None:
            # No string index set
            if not self.strings:
                # No strings set.  Do nothing probably.
                pass
            else:
                # The script started with no strings, but we added one.
                # Insert a string index command
                cmd = EC.set_string_index(rom_ptr)
                self.insert_commands(cmd.to_bytearray(), start)
        else:
            str_ind_bytes = to_little_endian(rom_ptr, 3)
            self.data[pos+1:pos+4] = str_ind_bytes

    def find_command_opt(
            self, cmd_ids: list[int],
            start_pos: Optional[int] = None,
            end_pos: Optional[int] = None
    ) -> Tuple[Optional[int], EC]:
        '''
        A version of find_command which will return None if the command is
        not found.
        '''

        if start_pos is None or start_pos < 0:
            start_pos = self.get_object_start(0)

        if end_pos is None or end_pos > len(self.data):
            end_pos = len(self.data)

        # print(f"{start_pos:04X}, {end_pos:04X}")

        pos = start_pos
        while pos < end_pos:
            cmd = get_command(self.data, pos)

            if cmd.command in cmd_ids:
                return (pos, cmd)

            pos += len(cmd)

        # returning colorcrash so mypy doesn't want Optional[Event]
        return (None, EC.get_blank_command(1))

    def find_command(
            self, cmd_ids: list[int],
            start_pos: Optional[int] = None,
            end_pos: Optional[int] = None
    ) -> Tuple[int, EC]:
        '''
        A version of find_command that will always return a position and
        command.  Will raise CommandNotFoundException if the command can not
        be found.
        '''
        ret_pos, ret_cmd = self.find_command_opt(cmd_ids, start_pos, end_pos)

        if ret_pos is None:
            raise CommandNotFoundException

        return ret_pos, ret_cmd

    def find_exact_command_opt(
            self, find_cmd: EC,
            start_pos: Optional[int] = None,
            end_pos: Optional[int] = None) -> Optional[int]:
        '''
        Version of find_exact_command which will return None if the command
        is not found.
        '''

        if start_pos is None or start_pos < 0:
            start_pos = self.get_object_start(0)

        if end_pos is None or end_pos > len(self.data):
            end_pos = len(self.data)

        jump_cmds = EC.fwd_jump_commands + EC.back_jump_commands

        pos = start_pos
        while pos < end_pos:
            cmd = get_command(self.data, pos)

            if cmd == find_cmd:
                return pos
            if (
                    cmd.command in jump_cmds and
                    cmd.command == find_cmd.command and
                    cmd.args[0:-1] == find_cmd.args[0:-1]
            ):
                return pos

            pos += len(cmd)

        return None

    def find_exact_command(
            self, find_cmd: EC,
            start_pos: Optional[int] = None,
            end_pos: Optional[int] = None) -> int:
        '''
        Finds the command given.  Does not match the exact bytes jumped if
        given a jump command.  Raises CommandNotFoundException if the command
        is not found.
        '''
        pos = self.find_exact_command_opt(find_cmd, start_pos, end_pos)

        if pos is None:
            raise CommandNotFoundException

        return pos

    # Helper method to shift all jumps by a given amount.  Typically this
    # is called for removals/insertions.
    #   - All forward jumps before before_pos will be shifted forward by
    #     shift_mag (shift can be negative).
    #   - All backward jumps after after_pos will be shifted backward by
    #     shift
    # The two usual use cases area
    #   (1) We are inserting some commands at a position x:
    #       Then before_pos == after_pos == x and shift is the total length
    #       of the inserted commands.
    #   (2) We are deleting commands on some interval [a,b):
    #       Then before_pos = a, after_pos = b and shift is a-b (neg).
    def __shift_jumps(self, before_pos: int,
                      after_pos: int,
                      shift: int):

        pos: Optional[int] = self.get_object_start(0)

        jmp_cmds = EC.fwd_jump_commands + EC.back_jump_commands

        while True:
            # Find the next jump command
            (pos, cmd) = self.find_command_opt(jmp_cmds, pos)

            if pos is None:
                break

            jump_mult = 2*(cmd.command in EC.fwd_jump_commands)-1
            jump_target = pos + len(cmd) + cmd.args[-1]*jump_mult - 1

            # For backwards jumps, we need to count the bytes of the command
            # within the bounds of the jump block.
            cmd_bound = pos
            if jump_mult == -1:
                cmd_bound += len(cmd)

            # This has been wrong a few times.  Let's be clear.
            # We only shift if [before_pos, after_pos) is contained in
            # (start, end).  We don't shift when before_pos == start
            # because this means either the insertion will happen prior
            # to the jump (before_pos == after_pos) or the deletion would
            # include the jump command.
            start = min(cmd_bound, jump_target)
            end = max(cmd_bound, jump_target)

            if before_pos == after_pos:
                can_shift_aft = (end > after_pos)
            else:
                can_shift_aft = (end >= after_pos)

            if can_shift_aft and start < before_pos:
                arg_offset = len(cmd) - cmd.arg_lens[-1]
                self.data[pos+arg_offset] += shift
            else:
                pass
                # print('not shifting')
                # input()

            pos += len(cmd)

    # Helper method for dealing with insertions and deletions.
    # All function starts strictly exceeding start_thresh will be shifted
    # by shift.
    # The three usual use cases area
    #   (1) We are inserting some commands at a position x:
    #       Then start_thresh == x and shift is the total length
    #       of the inserted commands.
    #   (2) We are deleting commands on some interval [a,b):
    #       Then start_thresh = a and shift=a-b (neg).
    #   (3) All function starts must be shifted forward or backwards because
    #       the pointer block expanded/contracted.  Use start_thresh <=0 and
    #       shift will be +/- a multiple of 32.
    def __shift_starts(self, start_thresh: int, shift: int):
        for ptr in range(32*self.num_objects-2, -2, -2):
            ptr_loc = get_value_from_bytes(self.data[ptr:ptr+2])

            if ptr_loc > start_thresh:
                self.data[ptr:ptr+2] = to_little_endian(ptr_loc+shift, 2)

    def __shift_calls_back(self, deleted_obj: int):
        pos: Optional[int] = self.get_function_start(0, 0)
        end = len(self.data)
        while True:
            (pos, cmd) = self.find_command_opt([2, 3, 4],
                                               pos, end)
            if pos is None:
                break

            if cmd.args[0] > 2*deleted_obj:
                # print(f"shifted [{pos:04X}] " + str(cmd))
                # input()
                self.data[pos+1] -= 2

            pos += len(cmd)

    def __shift_calls_forward(self, inserted_obj: int):
        pos: Optional[int] = self.get_function_start(0, 0)
        end = len(self.data)
        while True:
            (pos, cmd) = self.find_command_opt([2, 3, 4],
                                               pos, end)
            if pos is None:
                break

            if cmd.args[0] > 2*inserted_obj:
                # print(f"shifted [{pos:04X}] " + str(cmd))
                # input()
                self.data[pos+1] += 2

            pos += len(cmd)

    def replace_command(self, from_cmd: EC, to_cmd: EC,
                        start: Optional[int] = None,
                        end: Optional[int] = None):
        if start is None:
            start = self.get_object_start(0)

        if end is None:
            end = len(self.data)

        pos: Optional[int] = start
        while True:
            pos = self.find_exact_command_opt(from_cmd)

            if pos is None:
                break

            self.insert_commands(to_cmd.to_bytearray(), pos)
            pos += len(to_cmd)

            self.delete_commands(pos, 1)

    # This is for short removals
    def delete_commands(self, del_pos: int, num_commands: int = 1):

        pos = del_pos
        cmd_len = 0

        for _ in range(num_commands):
            if pos >= len(self.data):
                print("Error: Deleting out of script's range.")
                raise ValueError

            cmd = get_command(self.data, pos)
            cmd_len += len(cmd)
            pos += len(cmd)

        pos = del_pos

        self.__shift_jumps(before_pos=pos,
                           after_pos=pos+cmd_len,
                           shift=-cmd_len)

        self.__shift_starts(start_thresh=del_pos,
                            shift=-cmd_len)

        del self.data[del_pos:del_pos+cmd_len]

    def delete_commands_range(self, del_start_pos: int, del_end_pos: int):

        if del_start_pos > del_end_pos:
            raise ValueError("Start after end.")

        pos = del_start_pos
        length_to_delete = del_end_pos - del_start_pos
        deleted_length = 0
        while deleted_length < length_to_delete:
            cmd = get_command(self.data, pos)
            self.delete_commands(pos)
            deleted_length += len(cmd)

        if deleted_length != length_to_delete:
            print('Warning: Last deleted command exceeded del_end_pos')

    def delete_jump_block(self, pos: int):
        '''Delete the conditional block beginning at the given offset.'''
        cmd_id = self.data[pos]
        if cmd_id not in EC.fwd_jump_commands:
            raise ValueError("Position does not point to a jump")

        cmd = get_command(self.data, pos)
        jump_bytes = cmd.args[-1]
        target = pos + jump_bytes + len(cmd) - 1

        self.delete_commands_range(pos, target)

    def get_jump_block(self, pos: int, include_if: bool = False) -> EF:
        '''Return the contents of a conditional block as an EventFunction'''
        cmd_id = self.data[pos]
        if cmd_id not in EC.fwd_jump_commands:
            raise ValueError("Position does not point to a jump")

        cmd = get_command(self.data, pos)
        jump_bytes = cmd.args[-1]
        target = pos + jump_bytes + len(cmd) - 1

        start = pos
        if not include_if:
            start += len(cmd)

        return EF.from_bytearray(self.data[start: target])

    def delete_command_from_function(
            self,
            cmd_ids: list[int],
            obj_id: int, fn_id: int,
            start: Optional[int] = None,
            end: Optional[int] = None) -> Optional[int]:
        find_start = self.get_function_start(obj_id, fn_id)
        find_end = self.get_function_end(obj_id, fn_id)

        if start is not None and find_start < start < find_end:
            find_start = start

        if end is not None and find_start < end < find_end:
            find_end = end

        pos, _ = self.find_command_opt(cmd_ids, find_start, find_end)
        if pos is not None:
            self.delete_commands(pos, 1)

        return pos

    # This is for short additions.  In particular no string additions are
    # allowed here.
    def insert_commands(self, new_commands: bytearray, ins_position: int):
        # First, look for jump commands prior to the position that jump after
        # the position

        # print(ins_position)
        # print(f"{ins_position: 04X}")
        # input()

        # Finally simplifying this using the __shift methods
        self.__shift_jumps(ins_position, ins_position, len(new_commands))
        self.__shift_starts(ins_position, len(new_commands))

        self.data[ins_position:ins_position] = new_commands


    @staticmethod
    def _get_flux_path(filename: Union[Path, str]) -> Path:
        '''Coerce filename path to use flux from "flux" directory in package instead of relative to CWD.

        If filename starts with './flux/', it is replaced with the location of "flux" directory.
        '''
        parts = Path(filename).parts
        if parts[0] == 'flux':
            # strip off leading './flux/' if included in filename
            parts = parts[1:]
        return Path(Event._flux_path, *parts)


# Find the length of a location's event script
def get_compressed_event_length(rom: ByteString, loc_id: int) -> int:
    ptr = get_loc_event_ptr(rom, loc_id)
    return get_compressed_length(rom, ptr)


# Class for reading scripts from an FSRom and writing them back out.
# The main job of this class is to avoid reading the same script many times
# when changing a location's key items, sealed chests, bosses, etc.
# Writes back to the rom respect the FSRom's free space.
class ScriptManager:

    def __init__(self, fsrom: FSRom,
                 location_list: list[LocID],
                 loc_data_ptr=0x360000,
                 event_data_ptr=0x3CF9F0):
        self.fsrom = fsrom

        self.script_dict: dict[LocID, Event] = {}
        self.orig_len_dict: dict[LocID, int] = {}

        # TODO: Just read the ptr from the rom since we have it.
        self.loc_data_ptr = loc_data_ptr
        self.event_data_ptr = event_data_ptr

        for loc_id in location_list:
            self.script_dict[loc_id] = \
                Event.from_rom_location(self.fsrom.getbuffer(), loc_id)
            self.orig_len_dict[loc_id] = \
                get_compressed_event_length(self.fsrom.getbuffer(), loc_id)

    # A note:  If a script obtained by get_script is edited it will edit
    # the copy in the manager.  This is how I think it should be since
    # making copies, editing copies and then re-setting the manager is
    # clunky.
    def get_script(self, loc_id: LocID) -> Event:
        if loc_id not in self.script_dict:
            self.script_dict[loc_id] = \
                Event.from_rom_location(self.fsrom.getbuffer(), loc_id)
            self.orig_len_dict[loc_id] = \
                get_compressed_event_length(self.fsrom.getbuffer(), loc_id)

        return self.script_dict[loc_id]

    def set_script(self, script, loc_id: LocID):
        if loc_id not in self.script_dict:
            self.orig_len_dict[loc_id] = \
                get_compressed_event_length(self.fsrom.getbuffer(), loc_id)

        self.script_dict[loc_id] = script

    def free_script(self, loc_id: LocID):
        script = self.get_script(loc_id)
        script_ptr = get_loc_event_ptr(self.fsrom.getbuffer(), loc_id)
        script_compr_len = self.orig_len_dict[loc_id]

        spaceman = self.fsrom.space_manager

        if script.modified_strings:
            # Do something to free the strings.
            # This will take some more sophistication to do correctly.
            pass

        spaceman.mark_block((script_ptr, script_ptr+script_compr_len),
                            FSWriteType.MARK_FREE)

    # writes the script to the specified locations
    def write_script_to_rom(self, loc_id: LocID, free_old: bool = True):
        # print('calling wstr', loc_id)

        spaceman = self.fsrom.space_manager

        if free_old:
            self.free_script(loc_id)

        script = self.get_script(loc_id)

        if script.modified_strings:
            # We need to find space for the new strings
            strings_len = sum(len(x) for x in script.strings)
            ptrs_len = 2*len(script.strings)
            total_len = strings_len + ptrs_len

            # Note: fsrom doesn't let the block cross bank boundaries
            string_index = spaceman.get_free_addr(total_len)

            # str_pos tracks where the pointer needs to point
            str_pos = string_index % 0x10000 + ptrs_len
            self.fsrom.seek(string_index)

            # Write the pointers
            for i in range(len(script.strings)):
                self.fsrom.write(to_little_endian(str_pos, 2),
                                 FSWriteType.MARK_USED)
                str_pos += len(script.strings[i])

            # Write the strings immediately afterwards
            for x in script.strings:
                self.fsrom.write(x, FSWriteType.MARK_USED)

            script.set_string_index(to_rom_ptr(string_index))

        # The rest is mostly straightforward
        compr_event = compress(script.get_bytearray())
        script_ptr = spaceman.get_free_addr(len(compr_event))

        self.fsrom.seek(script_ptr)
        self.fsrom.write(compr_event, FSWriteType.MARK_USED)

        # Now write the location's pointer
        event_ind_st = self.loc_data_ptr + 14*loc_id + 8

        loc_script_ind = \
            get_value_from_bytes(
                self.fsrom.getbuffer()[event_ind_st:event_ind_st+2])

        # Each event pointer is an absolute, 3 byte pointer
        loc_ptr = self.event_data_ptr + 3*loc_script_ind

        self.fsrom.seek(loc_ptr)
        self.fsrom.write(to_little_endian(to_rom_ptr(script_ptr), 3))

        # When the script is written, update the orig len and modified_strings.
        # Just in case we end up modifying and writing again.
        script.modified_strings = False
        self.orig_len_dict[loc_id] = len(compr_event)
    # End of write_script_to_rom
# End class ScriptManager


def main():
    pass


if __name__ == '__main__':
    main()
