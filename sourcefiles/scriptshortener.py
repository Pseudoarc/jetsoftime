'''Module for shortening various event scripts for the randomizer.'''
from typing import Optional

import ctrom
import ctenums

import eventcommand

from eventcommand import EventCommand as EC, FuncSync as FS
from eventfunction import EventFunction as EF


def shorten_fritz_script(ct_rom: ctrom.CTRom):
    '''
    Remove most of Fritz's dialog and remove his father entirely.
    '''
    script = ct_rom.script_manager.get_script(ctenums.LocID.TRUCE_MARKET)

    pos: Optional[int]
    pos = script.find_exact_command(
        EC.call_obj_function(8, 3, 5, FS.HALT),  # Dad entering
        script.get_function_start(0, 3),
        script.get_function_end(0, 4)
    )
    script.delete_commands(pos, 1)

    # Fritz's text is in obj9, touch (2)
    # 1) Come on in!
    # 2) Crono, I owe you one.
    # 3) I was up the creek .... <--- Remove this one
    # 4) Hope my dad never hears about this.
    pos, cmd = script.find_command([0xBB],
                                   script.get_function_start(9, 2))
    pos, cmd = script.find_command([0xBB], pos+len(cmd))
    pos, _ = script.find_command([0xBB], pos+len(cmd))
    script.delete_commands(pos, 1)


def shorten_lavos_crash_script(ct_rom: ctrom.CTRom):
    '''
    After Lavos falls in 65m BC, there's a long scene on the cliffside.
    Remove all unneeded pauses from this scene
    '''

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.PREHISTORIC_CANYON
    )

    start = script.get_function_start(0, 0)
    end = script.get_function_end(0, 0)

    pos: Optional[int] = start

    # First, remove all pauses
    while True:
        pos, _ = script.find_command_opt([0xAD], pos, end)
        if pos is None:
            break

        script.delete_commands(pos, 1)

    # Put a slight pause after the lavos scream
    pos = script.find_exact_command(
        EC.generic_command(0xEA, 0x3A), start
    ) + 2

    script.insert_commands(EC.pause(3.0).to_bytearray(), pos)
    pos, _ = script.find_command([0xEB], pos)

    script.delete_commands(pos, 5)  # Delete a second scream and wind song

    # Next command is scroll layers.
    # Make the scroll larger in magnitude, cut it off after 1.75 seconds.
    cmd = eventcommand.get_command(script.data, pos)
    cmd.args[0] = 0x0900
    script.data[pos:pos+len(cmd)] = cmd.to_bytearray()
    pos += len(cmd)
    script.insert_commands(EC.pause(1.75).to_bytearray(), pos)

    # Add the missing function call to make the 3rd sparke move away.
    pos, _ = script.find_command([2], pos)

    script.insert_commands(
        EC.call_obj_function(1, 4, 3, FS.CONT).to_bytearray(),
        pos
    )


def shorten_pop_turnin(ct_rom: ctrom.CTRom):
    '''
    Give the player an option to watch the Giant's claw appear.
    In either case, remove unimportant dialog.
    '''
    loc_id = ctenums.LocID.WEST_CAPE
    script = ct_rom.script_manager.get_script(loc_id)

    # Toma will ask whether you want to see the giant's claw
    toma_obj = 9

    string_id = script.add_py_string(
        "TOMA: You know where that is, right?{line break}"
        "   Yes{line break}"
        "   No{null}"
    )

    st = script.get_function_start(toma_obj, 2)
    end = script.get_function_end(toma_obj, 2)

    flag_cmd = EC.set_bit(0x7F01AC, 0x40)
    block_st = script.find_exact_command(flag_cmd, st, end)
    block_end = script.find_exact_command(EC.return_cmd(), block_st, end)

    warp_func = EF.from_bytearray(script.data[block_st: block_end])
    script.delete_commands_range(block_st, block_end)  # Leave the return

    warp_choice_func = (
        EF()
        .add(EC.decision_box(string_id, 1, 2))
        .add_if(
            EC.if_result_equals(2, 1),
            warp_func
        )
    )
    script.insert_commands(warp_choice_func.get_bytearray(), block_st)

    # Now the function will return if we say we know where the claw is.
    # Go back to the caller, Obj8, Activate and call Toma's exit.
    st = script.get_function_start(8, 1)
    end = script.get_function_end(8, 1)
    orig_call_cmd = EC.call_obj_function(9, 2, 6, FS.HALT)
    extra_call_cmd = EC.call_obj_function(9, 1, 6, FS.HALT)

    # Inserting at the end of a block is always weird.  Do the insert first
    # so that the if bounds don't shorten.
    pos: Optional[int]
    pos = script.find_exact_command(orig_call_cmd, st, end)
    new_calls = EF().add(orig_call_cmd).add(extra_call_cmd)
    script.insert_commands(new_calls.get_bytearray(), pos)

    pos += len(new_calls)
    script.delete_commands(pos, 1)

    # Now, speed up some of the movement and pauses.
    st = script.get_function_start(1, 3)
    pos, _ = script.find_command([0x89], st)
    script.data[pos+1] = 0x20  # speed command

    def reduce_pause(pos: Optional[int], end: int):
        while True:
            pos, cmd = script.find_command_opt([0xBA, 0xBD], pos, end)

            if pos is None:
                break

            if cmd.command == 0xBD:
                script.data[pos] = 0xBA
            elif cmd.command == 0xBA:
                script.data[pos] = 0xB9

            pos += len(cmd)

    pos = script.get_function_start(9, 1)
    end = script.get_function_end(9, 2)
    reduce_pause(pos, end)

    pos = script.get_function_start(8, 1)
    end = script.get_function_end(8, 1)
    reduce_pause(pos, end)

    new_speed = 0x20
    cmd = EC.generic_command(0x89, new_speed)
    pos = script.get_function_start(9, 1)
    script.insert_commands(cmd.to_bytearray(), pos)

    pos = script.get_function_start(9, 2)
    script.insert_commands(cmd.to_bytearray(), pos)

    pos = script.get_function_start(9, 1)
    end = script.get_function_end(9, 2)

    while True:
        pos, cmd = script.find_command_opt([0x9C, 0x92], pos, end)

        if pos is None:
            break

        mag = script.data[pos+2]
        mag = (mag * 0x10) // new_speed
        script.data[pos+2] = mag

        pos += len(cmd)


def shorten_all_scripts(ct_rom: ctrom.CTRom):
    shorten_fritz_script(ct_rom)
    shorten_lavos_crash_script(ct_rom)
    shorten_pop_turnin(ct_rom)
