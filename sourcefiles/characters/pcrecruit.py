'''Class for setting pc recruit spots.'''
from __future__ import annotations

import typing
from typing import Optional

import ctenums
import ctrom


class ScriptParseException(Exception):
    '''Raise when the script does not follow the expected pattern.'''


class RecruitSpot(typing.Protocol):
    '''Protocol for recruit spots.  Has PC and a way to write to rom.'''
    held_char: ctenums.CharID

    # Still explicitly defining this in implementing classes
    def to_jot_json(self):
        return str(self.held_char)

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        '''Write the held_char to the recruitment spot on the CTRom.'''


# All CharRecruits are script-based
# Parameters are self explanatory except for load_obj_id and recruit_obj_id
# Sometimes the character sprite is located in a different object than the code
# which actually adds the character to the team.  So the sprite's object is
# load_obj_id and the code that adds the character is recruit_obj_id
class CharRecruit(RecruitSpot):
    '''
    Class for a normal (non-starter) recruitment spot.
    '''
    # Indexed by ctenums.CharID, so load_cmds[ctenums.CharID.Crono]
    # is Crono's load cmd
    load_cmds = [0x57, 0x5C, 0x62, 0x6A, 0x68, 0x6C, 0x6D]

    def __init__(self, held_char: ctenums.CharID,
                 loc_id: ctenums.LocID,
                 load_obj_id: int,
                 recruit_obj_id: int):
        self.held_char = held_char
        self.loc_id = loc_id
        self.load_obj_id = load_obj_id
        self.recruit_obj_id = recruit_obj_id

    def to_jot_json(self):
        return str(self.held_char)

    # This might be poor naming, but the writing goes to the script manager
    # of the ct_rom.  A separate call has to commit those changes to the rom.
    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        script_manager = ct_rom.script_manager
        script = script_manager.get_script(self.loc_id)

        start = script.get_object_start(self.load_obj_id)
        end = script.get_object_end(self.load_obj_id)

        # First find the load command that's already in the script
        # There should be a LoadPC (not in party) command before any other
        # pc-related commands.  This has command id = 0x81.

        pos, cmd = script.find_command_opt([0x81], start, end)

        if pos is None:
            raise ScriptParseException(
                f"Couldn't find initial load: loc={self.loc_id}, "
                f"load_obj_id={self.load_obj_id}")

        script.data[pos+1] = int(self.held_char)

        # orig_char = ctenums.CharID(cmd.args[0])
        # orig_load_cmd = CharRecruit.load_cmds[orig_char]
        target_load_cmd = CharRecruit.load_cmds[self.held_char]

        # Now handle the recruitment
        pos = script.get_object_start(self.recruit_obj_id)
        end = script.get_object_end(self.recruit_obj_id)

        while pos < end:
            # character manip commands:
            # 0x81 - Load out of party charater: 1st arg pc_id
            # 0xD2 - If PC is active: 1st arg pc_id
            # 0xCF - If PC is recruited: 1st arg pc_id
            # 0xC8 - Special Dialog (name): 1st arg pc_id | 0xC0
            # 0xD0 - Add PC to Reserve: 1st arg pc_id
            # the load command is pc-specific, 0 arg

            (pos, cmd) = \
                script.find_command_opt(
                    [0x81, 0xD2, 0xCF, 0xC8, 0xD0, 0xD3] +
                    CharRecruit.load_cmds,
                    pos, end
                )

            if pos is None:
                break

            # cmds that just need the pc id written
            if cmd.command in [0x81, 0xD2, 0xCF, 0xD0, 0xD3]:
                script.data[pos+1] = int(self.held_char)
            elif cmd.command == 0xC8:
                if script.data[pos+1] in range(0xC0, 0xC8):
                    script.data[pos+1] = int(self.held_char | 0xC0)
                else:
                    pass
                    # script.data[pos+1] = int(self.held_char)
            elif cmd.command in CharRecruit.load_cmds:
                script.data[pos] = target_load_cmd

            else:
                raise ValueError(f"Uncaught command ({cmd.command:02X})")

            pos += len(cmd)


class StarterChar:
    '''Class for setting a starter character.'''
    def __init__(self,
                 loc_id: ctenums.LocID = ctenums.LocID.LOAD_SCREEN,
                 object_id: int = 0,
                 function_id: int = 0,
                 held_char: ctenums.CharID = ctenums.CharID.CRONO,
                 starter_num=0):
        self.loc_id = loc_id
        self.object_id = object_id
        self.function_id = function_id
        self.held_char = held_char
        self.starter_num = starter_num

    def to_jot_json(self):
        return str(self.held_char)

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        '''Write this starter to the CTRom.'''
        script_manager = ct_rom.script_manager
        script = script_manager.get_script(self.loc_id)

        start = script.get_function_start(self.object_id, self.function_id)
        end = script.get_function_end(self.object_id, self.function_id)

        num_name_char = 0
        num_add_party = 0

        pos: Optional[int] = start
        while (num_name_char < self.starter_num+1 or
               num_add_party < self.starter_num+1):

            # 0xD3 - Add to active party: 1st arg pc_id
            # 0xC8 - Special Dialog (name): 1st arg pc_id | 0xC0
            pos, cmd = script.find_command_opt([0xD3, 0xC8], pos, end)

            if pos is None:
                raise ScriptParseException(
                    f"{self.loc_id} {self.object_id} {self.function_id}"
                    "Error: Hit end of function before finding character."
                )

            if cmd.command == 0xD3:
                # print("Found add party")
                if num_add_party == self.starter_num:
                    script.data[pos+1] = int(self.held_char)

                num_add_party += 1
            elif cmd.command == 0xC8:
                dialog_id = script.data[pos+1]
                if dialog_id in range(0xC0, 0xC8):
                    # print("Found name char")
                    if num_name_char == self.starter_num:
                        script.data[pos+1] = int(self.held_char) | 0xC0

                    num_name_char += 1

            pos += len(cmd)


def get_base_recruit_dict() -> dict[ctenums.RecruitID, RecruitSpot]:
    '''
    Get a dict RecruitID -> RecruitSpot which has the standard JoT recruits.
    '''

    CharID = ctenums.CharID
    RecruitID = ctenums.RecruitID
    LocID = ctenums.LocID

    # char assignments are completely arbitrary here
    char_assign_dict: dict[ctenums.RecruitID, RecruitSpot] = {
            RecruitID.STARTER_1: StarterChar(
                held_char=CharID.CRONO,
                starter_num=0  # A little bothered by the 0 vs 1 here
            ),
            RecruitID.STARTER_2: StarterChar(
                held_char=CharID.MAGUS,
                starter_num=1
            ),
            RecruitID.CATHEDRAL: CharRecruit(
                held_char=CharID.LUCCA,
                loc_id=LocID.MANORIA_SANCTUARY,
                load_obj_id=0x19,
                recruit_obj_id=0x19
            ),
            RecruitID.CASTLE: CharRecruit(
                held_char=CharID.MARLE,
                loc_id=LocID.GUARDIA_QUEENS_CHAMBER_600,
                load_obj_id=0x17,
                recruit_obj_id=0x18
            ),
            RecruitID.FROGS_BURROW: CharRecruit(
                held_char=CharID.FROG,
                loc_id=LocID.FROGS_BURROW,
                load_obj_id=0x0F,
                recruit_obj_id=0x0F
            ),
            RecruitID.DACTYL_NEST: CharRecruit(
                held_char=CharID.AYLA,
                loc_id=LocID.DACTYL_NEST_SUMMIT,
                load_obj_id=0x0D,
                recruit_obj_id=0x0D
            ),
            RecruitID.PROTO_DOME: CharRecruit(
                held_char=CharID.ROBO,
                loc_id=LocID.PROTO_DOME,
                load_obj_id=0x18,
                recruit_obj_id=0x18
            )
        }

    return char_assign_dict
