import copy

import byteops
import ctenums
import ctevent
import ctrom

from eventcommand import EventCommand as EC
from eventfunction import EventFunction as EF

import freespace
from maps import locationtypes as lt


def duplicate_map(fsrom: freespace.FSRom,
                  exits: lt.LocExits, orig_loc_id, dup_loc_id):
    '''Duplicates a map and the exits.'''
    orig_exits = exits.get_exits(orig_loc_id)
    exits.delete_exits(dup_loc_id)
    exits.add_exits(dup_loc_id, orig_exits)

    duplicate_location_data(fsrom, orig_loc_id, dup_loc_id)


def duplicate_heckran_map(fsrom: freespace.FSRom,
                          exits: lt.LocExits, dup_loc_id):
    '''Duplicates the map the Heckran is on and alters the exits to match.'''
    # Change the exit leading into Heckran to go to the new map
    hc_river_exits = exits.get_exits(0x31)
    alter_exit = hc_river_exits[4]
    alter_exit.dest_loc = dup_loc_id
    exits.set_exit(0x31, 4, alter_exit.get_bytearray())

    # Copy the location information (except events)
    duplicate_location_data(fsrom, 0x2F, dup_loc_id)

    # Copy the exits to the new map
    hc_passage_exits = exits.get_exits(0x2F)
    exits.delete_exits(dup_loc_id)
    exits.add_exits(dup_loc_id, hc_passage_exits)

    # Write the result
    # exits.write_to_fsrom(fsrom)


# Except for events
def duplicate_location_data(fsrom: freespace.FSRom, loc_id, dup_loc_id):
    # I think all you have to do is change the LocationData and update the
    # exits?

    orig_data = lt.LocationData.from_rom(fsrom.getbuffer(), loc_id)
    dup_data = lt.LocationData.from_rom(fsrom.getbuffer(), dup_loc_id)
    orig_data.event_id = dup_data.event_id
    orig_data.write_to_rom(fsrom.getbuffer(), dup_loc_id)


# Moving old bossrando functions in here
def duplicate_zenan_bridge(ct_rom: ctrom.CTRom,
                           dup_loc_id: ctenums.LocID):

    fsrom = ct_rom.rom_data
    script_man = ct_rom.script_manager

    # Copy the exists of the original Zenan Bridge to the copy
    exits = lt.LocExits.from_rom(fsrom)
    duplicate_map(fsrom, exits, ctenums.LocID.ZENAN_BRIDGE, dup_loc_id)
    exits.write_to_fsrom(fsrom)

    # Copy the script of the original Zenan Bridge to the copy
    script = script_man.get_script(ctenums.LocID.ZENAN_BRIDGE)
    new_script = copy.deepcopy(script)

    # In the original script, the party runs off the screen, the screen
    # scrolls left, and then the Zombor fight begins.  To avoid sprite limits
    # we are going to warp to the Zenan copy when the team runs off the screen.

    # The part where the team runs off the screen is in obj1, func1
    start = script.get_function_start(0x01, 0x00)
    end = script.get_function_end(0x01, 0x00)

    move_party = EC.move_party(0x86, 0x08, 0x88, 0x7, 0x89, 0x0A)
    pos = script.find_exact_command(move_party, start, end)

    # Insert the transition commands after the party moves
    new_move_party = EC.move_party(0x8B, 0x08, 0x8B, 0x7, 0x8B, 0x0A)

    # pos += len(new_move_party)

    change_loc = EC.change_location(dup_loc_id, 0x08, 0x08)

    # Make the string of new commands.
    # After the party runs off, the screen fades out and we change location
    insert_cmds = EF()
    (
        insert_cmds
        .add(new_move_party)
        .add(EC.darken(1))
        .add(EC.fade_screen())
        .add(change_loc)
    )

    script.insert_commands(insert_cmds.get_bytearray(), pos)
    script.delete_commands(pos+len(insert_cmds), 1)

    # after the move party in the normal script, each pc strikes a pose and the
    # screen scrolls (4 commands). We'll delete those commands because they'll
    # never get executed since we're changing location.
    pos += len(insert_cmds.get_bytearray())
    script.delete_commands(pos, 4)

    # Now, trim down the event for the duplicate map by removing the skeletons
    # other than the ones that make Zombor and the guards.
    unneeded_objs = sorted(
        (0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x15, 0x16, 0x17),
        reverse=True
    )

    for obj in unneeded_objs:
        new_script.remove_object(obj)

    # Trim down obj0, func0 so that all it does is get the party in position
    # for the fight... and preserve the string index of course.  Nobody
    # would forget to preserve the string index, right?
    string_index = new_script.get_string_index()
    string_index_cmd = EC.set_string_index(string_index)

    new_startup_func = EF()
    (
        new_startup_func
        .add(string_index_cmd)
        .add(EC.return_cmd())
        .add(move_party)
        .add(EC.end_cmd())
    )

    # TODO: Instead of a move party command, get conditionals, etc working
    #       in eventcommand.py so that I can write a short script to set
    #       initial coordinates in startup functions of player objs

    # Finally, set the new function and set the new script.
    new_script.set_function(0, 0, new_startup_func)
    script_man.set_script(new_script, ctenums.LocID.ZENAN_BRIDGE_BOSS)


def duplicate_maps_on_ctrom(ct_rom: ctrom.CTRom):

    fsrom = ct_rom.rom_data
    script_man = ct_rom.script_manager

    # First do Heckran's Cave Passageways
    exits = lt.LocExits.from_rom(fsrom)
    duplicate_heckran_map(fsrom, exits, ctenums.LocID.HECKRAN_CAVE_NEW)

    exits.write_to_fsrom(fsrom)

    script = script_man.get_script(ctenums.LocID.HECKRAN_CAVE_PASSAGEWAYS)

    # Notes for Hecrkan editing:
    #   - Remove 1, 2, 0xC, 0xE, 0xF, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16,
    #         0x17, 0x18
    #   - Heckran's object was 0xD, now 0xA (3 removed prior)
    #   - Can clean up object 0 because it controls multiple encounters, but
    #     There's no real value to doing so.

    new_script = copy.deepcopy(script)
    del_objs = [0x18, 0x17, 0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x10, 0xF,
                0xE, 0xC, 2, 1]
    for x in del_objs:
        new_script.remove_object(x)

    script_man.set_script(new_script, ctenums.LocID.HECKRAN_CAVE_NEW)

    # Now do King's Trial
    #   - In location 0x1B9 (Courtroom Lobby) change the ChangeLocation
    #     command of Obj8, Activate.  It's after a 'If Marle in party' command.

    script = script_man.get_script(ctenums.LocID.COURTROOM_LOBBY)

    # Find the if Marle is in party command
    (pos, cmd) = script.find_command_opt([0xD2],
                                         script.get_function_start(8, 1),
                                         script.get_function_end(8, 1))
    if pos is None or cmd.args[0] != 1:
        raise ctevent.CommandNotFoundException(
            "Error finding command (kings trial 1)")

    # Find the changelocation in this conditional block
    jump_target = pos + cmd.args[-1] - 1
    (pos, cmd) = script.find_command([0xDC, 0xDD, 0xDE,
                                      0xDF, 0xE0, 0xE1],
                                     pos, jump_target)

    loc = cmd.args[0]
    # The location is in bits 0x01FF of the argument.
    # Keep whatever the old bits have in 0xFE00 put put in the new location
    loc = (loc & 0xFE00) + int(ctenums.LocID.KINGS_TRIAL_NEW)
    script.data[pos+1:pos+3] = byteops.to_little_endian(loc, 2)

    # Note, the script manager hands the actual object, so when edited there's
    # no need to script_man.set_script it

    # Duplicate King's Trial location, 0x1B6, to 0xC1
    duplicate_location_data(fsrom,
                            ctenums.LocID.KINGS_TRIAL,
                            ctenums.LocID.KINGS_TRIAL_NEW)

    # Copy and edit script to remove objects
    script = script_man.get_script(ctenums.LocID.KINGS_TRIAL)
    new_script = copy.deepcopy(script)

    # Can delete:
    #   - Object 0xB: The false witness against the king
    #   - Object 0xC: The paper the chancellor holds up in trial (small)
    #   - Object 0xD: The blue sparkle left by the Yakra key
    # This might not be enough.  Maybe the soldiers can go too?  The scene will
    # be changed, but it's worth it?

    del_objs = [0x19, 0x0C, 0x0B]
    for x in del_objs:
        new_script.remove_object(x)

    # New Yakra XII object is 0xB for boss rando purposes
    script_man.set_script(new_script, ctenums.LocID.KINGS_TRIAL_NEW)


def main():
    pass


if __name__ == '__main__':
    main()
