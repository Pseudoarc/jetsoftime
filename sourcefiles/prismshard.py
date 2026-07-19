'''
This module is dedicated to manipluating the prismshard quest, especially
removing cutscenes which eat up time.
'''
from typing import Optional

import ctenums
import ctrom
# import ctevent
import eventcommand
# import eventfunction
from maps import locationtypes

# These are just abbreviations that make writing event code less painful.
# Importing this way instead of a global EC = eventcommand.EventCommand is
# so that users can't write EC = whatever and blow up stuff from eventcommand.
from eventcommand import EventCommand as EC, FuncSync as FS, Operation as OP
from eventfunction import EventFunction as EF


def update_prismshard_quest(ct_rom: ctrom.CTRom):
    set_quest_activation_flags(ct_rom)
    alter_lobby_guard_activation(ct_rom)
    fix_basement_music(ct_rom)
    alter_shard_spot_pickup(ct_rom)
    accelerate_end_scene(ct_rom)
    shorten_shard_turn_in_script(ct_rom)
    modify_present_guards_and_king(ct_rom)


def modify_present_guards_and_king(ct_rom: ctrom.CTRom):
    """
    Do not have the guards in the 1000 castle block the throne.
    This removes the need for Marle when turning the shard in.
    Also hide
    """
    script = ct_rom.script_manager.get_script(
        ctenums.LocID.GUARDIA_THRONEROOM_1000
    )

    blocker_guard_obj_ids = (0x15, 0x16)
    for obj_id in blocker_guard_obj_ids:
        pos = script.find_exact_command(
            EC.if_mem_op_value(0x7F00A1, OP.BITWISE_AND_NONZERO, 0x40, 1, 0),
            script.get_object_start(obj_id)
        )
        script.delete_jump_block(pos)

    pos = script.get_function_start(0xD, 0)
    script.insert_commands(
        EF().add_if(
            # If treasury
            EC.if_mem_op_value(0x7F00A1, OP.BITWISE_AND_NONZERO, 0x40, 1, 0),
            EF().add_if_else(
                # If trial complete
                EC.if_mem_op_value(0x7F0050, OP.BITWISE_AND_NONZERO, 0x40, 1, 0),
                EF(),  # nothing
                EF().add(EC.remove_object(0xD))  # else hide king
                .add(EC.return_cmd()).add(EC.end_cmd())
            )
        ).get_bytearray(), pos
    )


def set_quest_activation_flags(ct_rom: ctrom.CTRom):
    '''
    Set some additional flags when turning in the prismshard to the king.
    1) Set 0x7F0069 = 0x10 so that the Marle is ready to smash the window.
    2) Set 0x7F0050 & 0x08 to remove the gnasher fight in the basement.
    The flags must be set both in guardia throne room and in the king's bed
    in case he's sick.
    '''

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.GUARDIA_THRONEROOM_600
    )

    hook_cmd = EC.set_bit(0x7F00A1, 0x40)
    hook_pos = script.find_exact_command(hook_cmd,
                                         script.get_function_start(0x13, 1),
                                         script.get_function_end(0x13, 1))
    hook_pos += len(hook_cmd)

    func = EF()
    (
        func
        .add(EC.assign_val_to_mem(0x10, 0x7F0069, 1))  # trial progress max
        .add(EC.set_bit(0x7F0050, 0x08))  # beaten rats downstairs
    )
    script.insert_commands(func.get_bytearray(), hook_pos)

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.KINGS_CHAMBER_600
    )

    # Remove Marle check from sick king
    pos, _ = script.find_command([0xCF],
                              script.get_function_start(0xB, 1)
    )
    script.delete_commands(pos, 1)

    hook_pos = script.find_exact_command(hook_cmd,
                                         script.get_function_start(0xB, 1))
    script.insert_commands(func.get_bytearray(), hook_pos)


def alter_lobby_guard_activation(ct_rom: ctrom.CTRom):
    '''
    The memory 0x7E0350 must be set to 0 before doing the scene cutaways.
    This usually happens earlier in the quest but since we skip those scenes,
    we do it when the guards are interacted with.

    Also, set the music to change for the trial scene when the guards are
    interacted with.
    '''
    script = ct_rom.script_manager.get_script(ctenums.LocID.COURTROOM_LOBBY)
    hook_cmd = EC.call_obj_function(2, 4, 3, FS.HALT)  # Marle knows a way in
    hook_pos = script.find_exact_command(hook_cmd,
                                         script.get_function_start(8, 1),
                                         script.get_function_end(8, 1))

    script.insert_commands(
        (
            EF()
            .add(EC.assign_val_to_mem(1, 0x7F01ED, 1))  # keep song
            .add(eventcommand.get_command(bytes.fromhex('EC880101')))
            # ^ Weird song state change
            .add(eventcommand.get_command(b'\xEA\x23'))  # song play
            .add(EC.assign_val_to_mem(0, 0x7E0350, 1))
        ).get_bytearray(),
        hook_pos
    )


def fix_basement_music(ct_rom: ctrom.CTRom):
    '''
    Give the basement a music of 0xFF so that it doesn't try to overwrite
    whatever song is being played.  Then control the music by explicitly
    playing what is appropriate based on quest completion.
    '''
    locs = (ctenums.LocID.GUARDIA_BASEMENT,
            ctenums.LocID.GUARDIA_REAR_STORAGE)

    LD = locationtypes.LocationData
    for loc_id in locs:
        data = LD.from_rom(ct_rom.rom_data.getbuffer(), loc_id)
        data.music = 0xFF
        data.write_to_rom(ct_rom.rom_data.getbuffer(), loc_id)

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.GUARDIA_BASEMENT
    )

    hook_pos = script.get_function_start(0, 0)

    music_func = (
        EF()
        .add_if_else(
            # If quest is complete
            EC.if_mem_op_value(0x7F0050, OP.BITWISE_AND_NONZERO, 0x40, 1, 0),
            EF(),  # do nothing
            EF().add_if_else(
                # elif castle is on lockdown
                EC.if_mem_op_value(0x7F006A, OP.BITWISE_AND_NONZERO, 0x80,
                                   1, 0),
                EF(),  # Do nothing b/c playing a different song
                # Play the ocean palace music
                EF().add(eventcommand.get_command(b'\xEA\x31'))
            )
        )
    )

    script.insert_commands(music_func.get_bytearray(), hook_pos)


def alter_shard_spot_pickup(ct_rom: ctrom.CTRom):
    '''
    Finally, change the activation of the rainbow shell to
      1) Lock down the castle if the boss hasn't been beaten,
      2) Don't cut away to the trial,
    '''
    script = ct_rom.script_manager.get_script(
        ctenums.LocID.GUARDIA_REAR_STORAGE
    )

    # The shell is Object 0x09 touch, but it calls out to Object 2 arb 0.
    new_touch = (
        EF()
        .add_if(
            EC.if_mem_op_value(0x7F00A2, OP.BITWISE_AND_NONZERO, 0x80, 1, 0),
            EF().add(EC.return_cmd())
        )
        .add(EC.assign_val_to_mem(ctenums.ItemID.MOP, 0x7F0200, 1))
        .add_if_else(
            EC.check_active_pc(ctenums.CharID.MARLE, 0),
            EF().add(EC.decision_box(
                script.add_py_string(
                    "Should {marle} take the {item}?{line break}"
                    "   Yes.{line break}"
                    "   No.{null}"
                ), 1, 2
            )).add_if(
                EC.if_result_equals(1, 0),
                EF().add(EC.generic_command(0xE7, 0x2C, 0x02))
                .add(EC.move_party(0x33, 0x0D, 0x32, 0xC, 0x36, 0xC))
                .add(EC.call_obj_function(2, 3, 3, FS.HALT))
                .add(EC.move_party(0x34, 0xD, 0x34, 0xD, 0x34, 0xD))
                .add(EC.party_follow())
                .add_if_else(
                    # If trial complete
                    EC.if_mem_op_value(0x7F0050, OP.BITWISE_AND_NONZERO, 0x40,
                                       1, 0),
                    # Just start plyaing castle music again
                    EF().add(eventcommand.get_command(b'\xEA\x0C')),
                    # else
                    EF()
                    .add(EC.set_bit(0x7F006A, 0x80))  # castle lockdown
                    .add(EC.assign_val_to_mem(1, 0x7F01ED, 1))  # set keep song
                    .add(eventcommand.get_command(bytes.fromhex('EC880101')))
                    # ^ Weird song state change
                    .add(eventcommand.get_command(b'\xEA\x23'))  # song play
                )
            ),
            EF().add(EC.auto_text_box(
                script.add_py_string(
                    "Only {marle} can take the {item}.{null}"
                )
            ))
        ).add(EC.return_cmd())
    )
    script.set_function(9, 2, new_touch)

    # Now change Marle's bit.
    hook_cmd = EC.call_obj_function(2, 3, 3, FS.HALT)
    hook_pos = script.find_exact_command(hook_cmd,
                                         script.get_function_start(9, 2),
                                         script.get_function_end(9, 2))
    hook_pos += len(hook_cmd)

    # If the trial is not complete (Yakra XIII spot dead), then lock the
    # castle down when the item is given.
    func = EF()
    (
        func
        .add(EC.move_party(0x34, 0xD, 0x34, 0xD, 0x34, 0xD))
        .add(EC.party_follow())
        .add_if_else(
            # If trial complete
            EC.if_mem_op_value(0x7F0050, OP.BITWISE_AND_NONZERO, 0x40,
                               1, 0),
            # Just start plyaing castle music again
            EF().add(eventcommand.get_command(b'\xEA\x0C')),
            # else
            EF()
            .add(EC.set_bit(0x7F006A, 0x80))  # castle lockdown
            .add(EC.assign_val_to_mem(1, 0x7F01ED, 1))  # set keep song
            .add(eventcommand.get_command(bytes.fromhex('EC880101')))
            # ^ Weird song state change
            .add(eventcommand.get_command(b'\xEA\x23'))  # song play
        )
    )

    # A note on the above.  You have to set keepsong before the state change
    # stuff, otherwise, the song will just end instead of repeating the
    # dramatic part.

    # script.insert_commands(func.get_bytearray(), hook_pos)

    # Now eliminate the part of the function (obj2, arb0) that does the
    # cutaway to the trial.
    del_cmd = EC.set_bit(0x7F00A2, 0x80)
    del_st = script.find_exact_command(del_cmd,
                                       script.get_function_start(2, 3),
                                       script.get_function_end(2, 3))
    del_st += len(del_cmd)

    del_end = script.find_exact_command(EC.return_cmd(),
                                        del_st)
    script.delete_commands_range(del_st, del_end)


def accelerate_end_scene(ct_rom: ctrom.CTRom):
    '''
    Make the final cutscene with Marle and the king play more quickly by
    removing pauses and reducing the number of times animations loop.
    '''

    # Use new map from boss rando modifications
    script = ct_rom.script_manager.get_script(
        ctenums.LocID.KINGS_TRIAL_NEW
    )

    pos: Optional[int] = script.get_function_start(2, 6)
    while True:
        pos, cmd = script.find_command_opt([0xAD, 0xB7, 0xF0, 0xEB], pos,
                                           script.get_function_end(2, 6))
        if pos is None:
            break

        if cmd.command == 0xAD:  # pause
            script.delete_commands(pos, 1)
        elif cmd.command == 0xB7:  # loop animation
            script.data[pos+2] = max(1, script.data[pos+2]//2)
            pos += len(cmd)
        elif cmd.command == 0xEB:  # fade volume
            script.data[pos+1] = max(1, script.data[pos+1]//8)
            pos += len(cmd)
        else:  # cmd.command == 0xF0  # darken
            script.data[pos+1] = max(1, script.data[pos+1]//4)
            pos += len(cmd)


def shorten_shard_turn_in_script(ct_rom: ctrom.CTRom):
    '''
    Reduce some dialogue when asking the king to retrieve the shell.
    '''
    script = ct_rom.script_manager.get_script(
        ctenums.LocID.GUARDIA_THRONEROOM_600
    )

    # Remove the Marle block on the King
    pos, _ = script.find_command(
        [0xCF],  # if pc recruited
        script.get_function_start(0x13, 1)
    )
    script.delete_commands(pos, 1)

    # Remove everything leading up to "Done! I shall...."
    # Now the king interaction is just him saying he'll get the shell
    # followed by someone saying thanks.
    del_st = script.find_exact_command(
        EC.darken(0xF8),
        script.get_function_start(0x13, 1),
        script.get_function_end(0x13, 1)
    )

    del_end = script.find_exact_command(
        EC.generic_command(0xAA, 0x3),
        del_st, script.get_function_end(0x13, 1)
    )

    script.delete_commands_range(del_st, del_end)

    # Remove all of the knight captain commands
    del_st = script.find_exact_command(
        EC.if_mem_op_value(0x7F0101, OP.LESS_THAN, 2, 1, 0),
        del_st
    )
    last_cmd = EC.call_obj_function(0x0D, 4, 4, FS.HALT)
    del_end = script.find_exact_command(last_cmd, del_st) + len(last_cmd)

    script.delete_commands_range(del_st, del_end)

    # Remove the extra frog dialog that can trigger.
    pos = script.find_exact_command(
        EC.party_follow(),
        script.get_function_start(0x13, 1),
        script.get_function_end(0x13, 1)
    )

    func = (
        EF()
        .add(EC.party_follow())
        .add(EC.return_cmd())
    )

    script.insert_commands(func.get_bytearray(), pos)
    pos += len(func)
    script.delete_commands(pos, 1)


def main():
    ct_rom = ctrom.CTRom.from_file('./roms/shard_test.sfc', True)

    ct_rom.rom_data.space_manager.mark_block(
        (0x480000, 0x500000),
        ctrom.freespace.FSWriteType.MARK_FREE
    )

    update_prismshard_quest(ct_rom)
    ct_rom.write_all_scripts_to_rom()

    with open('./roms/shard_test_out.sfc', 'wb') as outfile:
        outfile.write(ct_rom.rom_data.getvalue())


if __name__ == '__main__':
    main()
