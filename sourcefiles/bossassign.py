'''Collection of functions for assigning random bosses to boss spots.'''
from __future__ import annotations

import functools
import typing

import bossrandotypes as rotypes
import ctenums
import ctrom
import ctevent
import eventcommand

from eventcommand import EventCommand as EC, FuncSync as FS
from eventfunction import EventFunction as EF

from ctenums import EnemyID


# Functions for finding the set coordinate commands in a particular function
def get_first_coord_cmd_pos(
        script: ctevent.Event,
        obj_id: int, fn_id: int) -> int:
    '''
    Find the offset in script.data of the first set coordinate command in the
    given object and function.
    '''
    start = script.get_function_start(obj_id, fn_id)
    end = script.get_function_end(obj_id, fn_id)
    pos = script.find_command([0x8B, 0x8D], start, end)[0]  # ret pos, cmd

    return pos


def get_last_coord_cmd_pos(script: ctevent.Event,
                           obj_id: int, fn_id: int) -> int:
    '''
    Find the offset in script.data of the last set coordinate command in the
    given object and function.
    '''
    pos: typing.Optional[int]
    pos = script.get_function_start(obj_id, fn_id)
    end = script.get_function_end(obj_id, fn_id)
    prev_pos = None

    while True:
        pos, cmd = script.find_command_opt([0x8B, 0x8D], pos, end)

        if pos is None:
            break

        prev_pos = pos
        pos += len(cmd)

    if prev_pos is None:
        raise ValueError('No coordinate commands found')

    return prev_pos


# Helper functions for updating objects to new enemies/coordinates
def set_object_boss(script: ctevent.Event,
                    obj_id: int, boss_id: int, boss_slot: int,
                    ignore_jumps: bool = True):
    '''
    Sets the given object to load enemy boss_id into slot boss_slot in the
    object's startup function.
    '''
    start = script.get_object_start(obj_id)
    end = script.get_function_end(obj_id, 0)

    pos = start
    while pos < end:

        cmd = eventcommand.get_command(script.data, pos)

        if cmd.command in EC.fwd_jump_commands and ignore_jumps:
            pos += (cmd.args[-1] - 1)
        elif cmd.command == 0x83:
            is_static = cmd.args[1] & 0x80
            cmd.args[0], cmd.args[1] = boss_id, (boss_slot | is_static)
            script.data[pos:pos+len(cmd)] = cmd.to_bytearray()
            break

        pos += len(cmd)


def set_object_coordinates(script: ctevent.Event, obj_id: int,
                           pixel_x: int, pixel_y: int,
                           ignore_jumps: bool = True, fn_id: int = 0,
                           force_pixel_coords: bool = False):
    '''
    Sets the given object to appear at pixel coordinates pixel_x, pixel_y.
    ignore_jumps: Sometimes the given object and function has extra logic in
                  if blocks (e.g. attract mode).  If set to true, coordinate
                  commands inside of if blocks will be ignored.
    force_pixel_coords: If set to True, use direct pixel coordinates even when
                        the coordinates could resolve to a tile coordinate.
    '''
    cmd_fn: typing.Callable[[int, int], EC]
    if force_pixel_coords:
        cmd_fn = EC.set_object_coordinates_pixels
    else:
        cmd_fn = EC.set_object_coordinates_auto

    start = script.get_function_start(obj_id, fn_id)
    end = script.get_function_end(obj_id, fn_id)

    pos = start
    while pos < end:

        cmd = eventcommand.get_command(script.data, pos)

        if cmd.command in EC.fwd_jump_commands and ignore_jumps:
            pos += (cmd.args[-1] - 1)
        elif cmd.command in [0x8B, 0x8D]:
            new_coord_cmd = cmd_fn(pixel_x, pixel_y)
            # print(f"x={x:04X}, y={y:04X}")
            # print(new_coord_cmd)
            # input()

            # The pixel-based and tile-based commands have different lengths.
            # If the new coordinates don't match the old, you have to do a
            # delete/insert.
            if new_coord_cmd.command == cmd.command:
                script.data[pos:pos+len(new_coord_cmd)] = \
                    new_coord_cmd.to_bytearray()
            else:
                script.insert_commands(new_coord_cmd.to_bytearray(),
                                       pos)
                script.delete_commands(pos+len(new_coord_cmd), 1)
            break

        pos += len(cmd)


def are_pixel_coords_forced(
        first_x_px: int,
        first_y_px: int,
        boss: rotypes.BossScheme
        ) -> bool:
    '''
    Determine whether a boss placed at (first_x_px, first_y_px) requires
    pixel coordinates or can use tile coordinates.
    '''
    x_coords = [first_x_px + part.displacement[0] for part in boss.parts]
    y_coords = [first_y_px + part.displacement[1] for part in boss.parts]

    x_tileable = functools.reduce(
        lambda val, item: val and ((item-8) & 0xF == 0), x_coords, True
    )

    y_tileable = functools.reduce(
        lambda val, item: val and (item & 0xF == 0), y_coords, True
    )

    return not (x_tileable and y_tileable)


def fix_bad_animations(
        script: ctevent.Event,
        obj_id: typing.Optional[int] = None,
        fn_id: typing.Optional[int] = None,
        start: typing.Optional[int] = None,
        end: typing.Optional[int] = None,
        static_removals: typing.Optional[list[int]] = None
        ):
    '''
    Remove all static animaion commands from the given object and function.
    Optionally, the search for static animations can be bound to [start, end).
    '''
    if start is None:
        if obj_id is None:
            raise ValueError(
                'If start is None then obj_id must be present'
            )
        if fn_id is None:
            start = script.get_function_start(obj_id, 0)
        else:
            start = script.get_function_start(obj_id, fn_id)

    if end is None:
        if obj_id is None:
            raise ValueError(
                'If end is None then obj_id must be present'
            )

        if fn_id is None:
            end = script.get_object_end(obj_id)
        else:
            end = script.get_function_end(obj_id, fn_id)

    pos: typing.Optional[int] = start
    while True:
        pos, cmd = script.find_command_opt([0xAC], pos, end)

        if pos is None:
            break

        # Note: Doing something less intrusive like using Animaion 0 does not
        #       work with some enemies (mutants, maybe others?)
        if static_removals is None or cmd.args[0] in static_removals:
            script.delete_commands(pos, 1)
        else:
            pos += len(cmd)


# General Scheme for setting one-part boss spots
def set_generic_one_spot_boss_script(
        script: ctevent.Event,
        boss: rotypes.BossScheme,
        boss_obj: int,
        show_pos_fn: typing.Optional[typing.Callable[[ctevent.Event], int]],
        last_coord_fn: typing.Callable[[ctevent.Event], int],
        first_x: typing.Optional[int] = None,
        first_y: typing.Optional[int] = None,
        pixel_coords: bool = False,
        is_shown: bool = False):
    '''
    Sets the boss in a one-spot location.
    - script: the Event data for the location to set the boss in.
    - boss: the BossScheme (coords, slots, displacements) set in the Event
    - boss_obj: the object in the event which contains the boss
    - show_pos_fn: An Event -> int function which finds the position in the
        event where extra boss parts should appear.
    - last_coord_fn:  An Event -> int function which finds the position in the
        event where the boss's final position before the battle is set.
    - first_x, first_y: The boss's position before the battle is set.  These
        can be read from the script using last_coord_fn, but some bosses
        require special casing.
    - pixel_coords:  Designate whether first_x, first_y are pixel coordinates.
    - is_shown:  Designate whether the boss starts shown.  This is used to
        determine whether extra parts need to begin drawn or not.
    '''

    # Write the new load into the boss object
    part = boss.parts[0]
    set_object_boss(script, boss_obj, part.enemy_id, part.slot)

    pos = None
    if first_x is None or first_y is None:
        pos = last_coord_fn(script)
        cmd = eventcommand.get_command(script.data, pos)

        first_x, first_y = cmd.get_pixel_coordinates()
        pixel_coords = True

    # Determine whether it's necessary to use pixel coordinates
    if not pixel_coords:
        pixel_x = (first_x >> 4) + 8
        pixel_y = (first_y >> 4) + 0x10
    else:
        pixel_x = first_x
        pixel_y = first_y

    use_pixel_coords = are_pixel_coords_forced(pixel_x, pixel_y, boss)

    # rewrite the last coordinate command if needed
    if use_pixel_coords and pos is not None:
        # pos is still valid from last_coord_fn
        new_cmd = EC.set_object_coordinates_pixels(pixel_x, pixel_y)

        script.insert_commands(new_cmd.to_bytearray(), pos)
        script.delete_commands(pos+len(new_cmd), 1)

    show = EF()

    # Add new objects for the additional boss parts if needed.
    # Simultaneously build up the list of commands to show the extra parts.
    for i in range(1, len(boss.parts)):
        new_obj = append_boss_object(script, boss, i, pixel_x, pixel_y,
                                     use_pixel_coords, is_shown)
        show.add(EC.set_object_drawing_status(new_obj, True))

    # Add the show commands if needed
    if not is_shown:
        if show_pos_fn is None:
            raise ValueError(
                "Must Provide show_pos_fn if boss is not intially visible"
            )
        show_pos = show_pos_fn(script)
        script.insert_commands(show.get_bytearray(), show_pos)


def set_generic_one_spot_boss(
        ct_rom: ctrom.CTRom,
        boss: rotypes.BossScheme,
        loc_id: int,
        boss_obj: int,
        show_pos_fn: typing.Optional[typing.Callable[[ctevent.Event], int]],
        last_coord_fn: typing.Callable[[ctevent.Event], int],
        first_x: typing.Optional[int] = None,
        first_y: typing.Optional[int] = None,
        is_shown: bool = False
):
    '''
    Set any one spot location's boss.

    Params:
        ctrom: has the script manager to get scripts from
        boss: A BossScheme object with the boss's coordinates/slots
        loc_id: The id of the location to write to
        boss_obj: The id of the one spot boss's object in the script
        show_pos_fn: A function to determine how to find the insertion point
                     after the objects have been added.
        first_x: The x-coordinate of the boss when show_pos is hit.  This
                 should be after all movement is done.
        first_y: The same as first_x but for the y_coordinate
        is_shown: Should the boss be shown by default.  Usually this is False.
    '''
    script_manager = ct_rom.script_manager
    script = script_manager.get_script(ctenums.LocID(loc_id))

    set_generic_one_spot_boss_script(script, boss, boss_obj,
                                     show_pos_fn, last_coord_fn,
                                     first_x, first_y, is_shown=is_shown)


def append_boss_object(script: ctevent.Event,
                       boss: rotypes.BossScheme, part_index: int,
                       first_x_px: int,
                       first_y_px: int,
                       force_pixel_coords: bool = False,
                       is_shown: bool = False) -> int:
    '''Make a barebones object to make a boss part and hide it.'''
    new_id = boss.parts[part_index].enemy_id
    new_slot = boss.parts[part_index].slot

    # Pray these don't come up negative.  They shouldn't?
    new_x = first_x_px + boss.parts[part_index].displacement[0]
    new_y = first_y_px + boss.parts[part_index].displacement[1]

    if force_pixel_coords:
        coord_cmd = EC.set_object_coordinates_pixels(new_x, new_y)
    else:
        coord_cmd = EC.set_object_coordinates_auto(new_x, new_y)

    # Make the new object
    init = (
        EF()
        .add(EC.load_enemy(new_id, new_slot))
        .add(coord_cmd)
        .add(EC.set_own_drawing_status(is_shown))
        .add(EC.return_cmd())
        .add(EC.end_cmd())
    )

    act = EF()
    act.add(EC.return_cmd())

    obj_id = script.append_empty_object()
    script.set_function(obj_id, 0, init)
    script.set_function(obj_id, 1, act)

    return obj_id


# Begin list of assignment functions.  They have a loc_id parameter in case
# we end up needing to duplicate a map for some reason.
def set_manoria_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.MANORIA_COMMAND):
    '''Sets the boss of Manoria Cathedral'''
    # 0xC6 is Yakra's map - Manoria Command
    boss_obj = 0xA
    # first_x, first_y = 0x80, 0xA0

    script = ct_rom.script_manager.get_script(loc_id)

    good_ids = (EnemyID.YAKRA, EnemyID.YAKRA_XIII)
    if boss.parts[0].enemy_id not in good_ids:
        fix_bad_animations(script, obj_id=boss_obj)

    set_generic_one_spot_boss_script(
        script, boss, boss_obj,
        lambda s: s.get_function_end(0xA, 3) - 1,
        lambda s: get_first_coord_cmd_pos(s, boss_obj, 0)
    )


def set_heckrans_cave_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.HECKRAN_CAVE_NEW):
    '''Sets the boss of Heckran's cave.'''
    # Heckran is in 0xC0 now.  Used to be 0x2F - HECKRAN_CAVE_PASSAGEWAYS
    script = ct_rom.script_manager.get_script(loc_id)

    boss_obj = 0xA
    # first_x, first_y = 0x340, 0x190

    good_anim_ids = (
        EnemyID.HECKRAN, EnemyID.DALTON_PLUS, EnemyID.ATROPOS_XR,
        EnemyID.SLASH_SWORD, EnemyID.SUPER_SLASH, EnemyID.NIZBEL,
        EnemyID.NIZBEL_II, EnemyID.YAKRA, EnemyID.YAKRA_XIII,
        EnemyID.MASA_MUNE, EnemyID.MUD_IMP
    )
    if boss.parts[0].enemy_id not in good_anim_ids:
        fix_bad_animations(script, obj_id=boss_obj)

    set_generic_one_spot_boss_script(
        script, boss, boss_obj,
        lambda scr: scr.get_function_end(0xA, 1)-1,
        lambda scr: get_first_coord_cmd_pos(scr, boss_obj, 1)
    )


def set_denadoro_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.CAVE_OF_MASAMUNE
):
    '''Sets the boss of Denadoro Mountains.'''
    # 0x97 is M&M's map - Cave of the Masamune
    boss_obj = 0x14

    # first_x, first_y = 0x80, 0xE0

    set_generic_one_spot_boss(
        ct_rom, boss, loc_id, boss_obj,
        lambda s: s.get_function_end(0x14, 4) - 1,
        lambda s: get_first_coord_cmd_pos(s, boss_obj, 0)
    )


def set_reptite_lair_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.REPTITE_LAIR_AZALA_ROOM):
    '''Sets the boss of the Reptite Lair'''
    # 0x121 is Nizbel's map - Reptite Lair Azala's Room
    # loc_id = 0x121
    boss_obj = 0x9

    # first_x, first_y = 0x370, 0xC0

    set_generic_one_spot_boss(
        ct_rom, boss, loc_id, boss_obj,
        lambda s: s.get_function_end(0x9, 4) - 1,
        lambda s: get_first_coord_cmd_pos(s, boss_obj, 4)
    )


def set_magus_castle_flea_spot_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.MAGUS_CASTLE_FLEA):
    '''Sets the boss of the Flea spot in Magus's Castle'''
    # 0xAD is Flea's map - Castle Magus Throne of Magic
    # loc_id = 0xAD

    boss_obj = 0xC

    # first_x, first_y = 0x70, 0x150
    def last_coord_fn(script: ctevent.Event) -> int:
        # Flea's spot has an extra bit for attract mode.  So we have to skip
        # over that instead of use the default last coord function.

        pos: typing.Optional[int]
        pos = script.get_function_start(boss_obj, 0)
        end = script.get_function_end(boss_obj, 0)
        for i in range(2):
            pos, cmd = script.find_command([0x8B, 0x8D], pos, end)

            if i == 0:
                pos += len(cmd)

        return pos

    def show_pos_fn(script: ctevent.Event) -> int:
        # The location to insert is a bit before the second battle in this
        # function.  The easiest marker is a 'Mem.7F020C = 01' command.
        # In bytes it is '7506'
        pos = script.find_exact_command(EC.generic_one_arg(0x75, 0x06),
                                        script.get_function_start(0xC, 0))

        return pos
    # end show_pos_fn

    set_generic_one_spot_boss(ct_rom, boss, loc_id, boss_obj, show_pos_fn,
                              last_coord_fn)
# End set_magus_castle_flea_spot_boss


# Note:  Zombor parts can still have some issues, but damage is mostly visible.
#        Is this a vanilla issue?  Sprite priority?
# Note:  Mud Imp crashes this spot.  How?  Are the beast graphics that big?
#        Uses: Middle Ages person, skeletons, boss stuff.
def set_magus_castle_slash_spot_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.MAGUS_CASTLE_SLASH):
    '''Sets the boss of the Slash spot in Magus's castle.'''
    # 0xA9 is Slash's map - Castle Magus Throne of Strength
    # loc_id = 0xA9
    script = ct_rom.script_manager.get_script(loc_id)

    if boss.parts[0].enemy_id in [EnemyID.ELDER_SPAWN_SHELL,
                                  EnemyID.LAVOS_SPAWN_SHELL]:
        # Some sprite issue with overlapping slots?
        # If the shell is the static part, it will be invisible until it is
        # interacted with.
        boss.make_part_first(1)

    # Slash's spot is ugly because there's a second Slash object that's used
    # for one of the endings (I think?).  You really have to set both of them
    # to the boss you want, otherwise you're highly likely to hit graphics
    # limits.
    set_object_boss(script, 0xC, boss.parts[0].enemy_id,
                    boss.parts[0].slot)

    # The real, used Slash is in object 0xB.
    boss_obj = 0xB

    # Read coords from the last_coord_fn command
    # first_x, first_y = 0x80, 0x240

    def last_coord_fn(script: ctevent.Event) -> int:
        pos, _ = script.find_command([0x8B, 0x8D],
                                     script.get_function_start(0xB, 1),
                                     script.get_function_end(0xB, 1))

        return pos

    def show_pos_fn(script: ctevent.Event) -> int:
        pos = script.find_exact_command(EC.generic_one_arg(0xE8, 0x8D),
                                        script.get_function_start(0xB, 1))

        return pos

    # Slash has animations that most bosses can not do.
    # It's probably better to use good_anim_ids because there are so few that
    # actually look good.  Ideally a dict EnemyID -> replacement anim ids.
    good_anim_ids = (EnemyID.SLASH_SWORD, EnemyID.SUPER_SLASH,
                     EnemyID.ATROPOS_XR)

    if boss.parts[0].enemy_id not in good_anim_ids:
        pos: typing.Optional[int]
        pos = script.get_function_start(0xB, 1)
        end = script.get_function_end(0xB, 1)

        while True:
            # Find animation commands and destroy them
            pos, _ = script.find_command_opt([0xAC], pos, end)

            if pos is None:
                break

            script.delete_commands(pos, 1)

    set_generic_one_spot_boss_script(script, boss, boss_obj,
                                     show_pos_fn, last_coord_fn)
# End set_magus_castle_slash_spot_boss


def set_ozzies_fort_flea_plus_spot_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.OZZIES_FORT_FLEA_PLUS):
    '''Sets the boss of the Flea Plus spot in Ozzie's Fort'''
    # loc_id = 0xB7
    boss_obj = 0x9
    # first_x, first_y = 0x270, 0x250

    # show spot is right at the end of obj 0xB, arb 0
    set_generic_one_spot_boss(
        ct_rom, boss, loc_id, boss_obj,
        lambda scr: scr.get_function_start(0x9, 1),
        lambda scr: get_first_coord_cmd_pos(scr, boss_obj, 0)
    )


def set_ozzies_fort_super_slash_spot_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.OZZIES_FORT_SUPER_SLASH):
    '''Sets the boss of the Super Slash spot in Ozzie's Fort'''
    # loc_id = 0xB8

    boss_obj = 0x9
    # first_x, first_y = 0x270, 0x250

    # show spot is right at the end of obj 0xB, arb 0
    # This one is different since we're adding at the start of a function.
    # Need to double check that the routines are setting start/end correctly
    set_generic_one_spot_boss(
        ct_rom, boss, loc_id, boss_obj,
        lambda scr: scr.get_function_start(0x9, 1),
        lambda scr: get_first_coord_cmd_pos(scr, boss_obj, 0)
    )


def set_kings_trial_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.KINGS_TRIAL_NEW):
    '''Sets the boss of the Yakra XIII spot the Prismshard Quest'''
    # Yakra XIII is in 0xC1 now.
    boss_obj = 0xB

    # first_x, first_y = 0x40, 0x100

    boss_ids = [part.enemy_id for part in boss.parts]
    if EnemyID.GUARDIAN_BIT in boss_ids:
        boss.parts[1].displacement = (-0x08, -0x3A)
        boss.parts[2].displacement = (-0x08, 0x30)
    elif EnemyID.MOTHERBRAIN in boss_ids:
        boss.reorder_horiz(left=True)

    # show spot is right at the end of obj 0xB, arb 0
    set_generic_one_spot_boss(
        ct_rom, boss, loc_id, boss_obj,
        lambda scr: scr.get_function_end(0xB, 3)-1,
        lambda scr: get_first_coord_cmd_pos(scr, boss_obj, 0)
    )


def set_giants_claw_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.GIANTS_CLAW_TYRANO):
    '''Sets the boss of the Giant's claw.'''
    boss_ids = [part.enemy_id for part in boss.parts]
    if EnemyID.RUST_TYRANO in boss_ids:
        return

    # loc_id = LocID.GIANTS_CLAW_TYRANO
    script = ct_rom.script_manager.get_script(loc_id)

    # Copying the existing command from when Tyrano dies.
    copy_tiles_cmd = EC.copy_tiles(0, 0, 7, 9, 4, 0x22,
                                   copy_l1=True,
                                   copy_l2=True,
                                   copy_props=True,
                                   unk_0x10=True,
                                   unk_0x20=True)

    # Yes, the tiles will be copied again when the Tyrano dies.  If that's
    # a problem we'll remove the other calls.

    pos = script.get_object_start(0)
    script.insert_commands(copy_tiles_cmd.to_bytearray(), pos)

    # You need to do the copy in obj0, func1 (activate) too.  This is the
    # function that gets called after returning from a menu.

    # Change to a wait for vblank version
    copy_tiles_cmd.command = 0xE4
    func = EF()
    func.add(copy_tiles_cmd)
    script.set_function(0, 1, func)

    # First part is in object 0x9, function 0 (init)
    boss_obj = 0x9
    # first_x, first_y = 0x80, 0x27F

    # Objects can start out shown, no real need for show_pos_fn
    set_generic_one_spot_boss_script(
        script, boss, boss_obj,
        lambda s: s.get_function_start(0, 0) + 1,
        lambda s: get_first_coord_cmd_pos(s, boss_obj, 0),
        is_shown=True
    )
# end set giant's claw boss


def set_tyrano_lair_midboss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.TYRANO_LAIR_NIZBEL):
    '''Sets the boss of the Nizbel II spot in the Tyrano Lair.'''
    # 0x130 is the Nizbel II's map - Tyrano Lair Nizbel's Room
    # loc_id = 0x130
    boss_obj = 0x8
    # first_x = 0x70
    # first_y = 0xD0

    if boss.parts[0].enemy_id == EnemyID.R_SERIES:
        script = ct_rom.script_manager.get_script(loc_id)
        anim_pos = script.find_exact_command(
            EC.generic_command(0xAA, 0x07),
            script.get_function_start(8, 0)
        )
        script.data[anim_pos+1] = 1

    set_generic_one_spot_boss(
        ct_rom, boss, loc_id, boss_obj,
        lambda s: s.get_function_end(8, 3) - 1,
        lambda s: get_last_coord_cmd_pos(s, boss_obj, 3))
# end set_tyrano_lair_midboss


# TODO: See if Mud Imp works here with the extra objects
def set_zeal_palace_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.ZEAL_PALACE_THRONE_NIGHT):
    '''Sets the boss of the Golem spot in Zeal Palace.'''
    # 0x14E is the Golem's map - Zeal Palace's Throneroom (Night)
    # Note this is different from vanilla, where it's 0x14C
    # loc_id = 0x14E
    script = ct_rom.script_manager.get_script(loc_id)

    # So much easier to just manually set the coordinates than parse
    # the script for them.  This is after the golem comes down.
    # first_x = 0x170
    # first_y = 0x90

    # First, let's delete some objects to avoid sprite limits.
    #   - Object F: Schala
    #   - Object E: Queen Zeal
    #   - Object 10: Magus Prophet

    # reverse order to not screw things up
    # removing seems to mess up the color of the beam above the portal.
    # I think it's the colormath commands needing palettes loaded?
    # For now, see if just leaving the junk in is ok.
    # del_objs = [0x10, 0xF, 0xE]

    # for obj in del_objs:
    #     script.remove_object(obj)

    # After deletion, the boss object is 0xA (unmoved)
    boss_obj = 0xA

    def show_pos_fn(script: ctevent.Event) -> int:
        # Right after the golem comes down to its final position.  The marker
        # is a play anim 5 command 'AA 05'
        pos = script.find_exact_command(EC.generic_one_arg(0xAA, 0x5),
                                        script.get_function_start(0xA, 3))

        return pos

    set_generic_one_spot_boss_script(
        script, boss, boss_obj,
        show_pos_fn,
        lambda s: get_first_coord_cmd_pos(s, boss_obj, 3)
    )


def set_epoch_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.REBORN_EPOCH):
    '''Sets the boss of the Dalton Plus spot on the Epoch'''
    # loc_id = LocID.REBORN_EPOCH
    boss_obj = 0xA
    # first_x, first_y = 0x80, 0x1A8

    set_generic_one_spot_boss(
        ct_rom, boss, loc_id, boss_obj,
        None,
        lambda scr: get_first_coord_cmd_pos(scr, boss_obj, 0),
        is_shown=True)


# Twin spot is unique.  Put it after the one spot assignments
# TODO: Check on this again if we ever allow multi-part bosses here.
def set_twin_golem_spot(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.OCEAN_PALACE_TWIN_GOLEM):
    '''Sets the boss of the Twin Golem spot in the Ocean Palace.'''
    # This one is unique because it actually depends on the size of the boss.
    # One spot bosses will be duplicated and others will just appear as-is.

    # 0x19E is the Twin Golems' map - Ocean Palace Regal Antechamber
    # loc_id = 0x19E
    script = ct_rom.script_manager.get_script(loc_id)

    if len(boss.parts) == 1:
        # Now, it should be that single target bosses get copied into
        # EnemyID.TWIN_BOSS.
        return

    # Somewhat center the multi_spot boss
    # 1) Change the move command to have an x-coord of 0x80 + displacement
    # Only twin golem has a displacement on its first part though.
    move_cmd = EC.generic_two_arg(0x96, 0x6, 0xE)
    pos = script.find_exact_command(move_cmd,
                                    script.get_function_start(0xA, 3))

    first_x = 0x88
    first_y = 0xF0

    # Move command is given in tile coords, so >> 4
    new_x = (first_x - 0x8 + boss.parts[0].displacement[0]) >> 4
    new_y = (first_y - 0x10 + boss.parts[0].displacement[1]) >> 4
    script.data[pos+1] = new_x

    # 2) Change the following set coords command to the dest of the move
    coord_cmd = EC.set_object_coordinates_tile(new_x, new_y)
    pos += len(move_cmd)
    script.data[pos:pos+len(coord_cmd)] = coord_cmd.to_bytearray()

    # Now proceed with a normal multi-spot assignment
    boss_objs = [0xA, 0xB]

    # overwrite the boss objs
    for i in range(0, 2):
        part = boss.parts[i]
        set_object_boss(script, boss_objs[i], part.enemy_id, part.slot)

        new_x = first_x + part.displacement[0]
        new_y = first_y + part.displacement[1]

        # first object's coordinates don't matter.  Second is set in arb0
        if i != 0:
            set_object_coordinates(script, boss_objs[i], new_x, new_y,
                                   True, 3)

    # Add as many new ones as needed.  Slight modification of one spot stuff

    show = EF()
    for i in range(2, len(boss.parts)):
        new_obj = append_boss_object(script, boss, i, first_x, first_y,
                                     False)
        show.add(EC.set_object_drawing_status(new_obj, True))

    # Show after part 2 shows up.
    show_pos = script.get_function_end(0xB, 4) - 1
    script.insert_commands(show.get_bytearray(), show_pos)


# Now do multi-part spots.  All of them are very similar but have their own
# quirks which make generalization annoying.  Best to waste keystrokes and
# duplicate code.
def set_zenan_bridge_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.ZENAN_BRIDGE_BOSS):
    '''Sets the boss of Zenan Bridge.'''
    # 0x87 is Zombor's map - Zenan Bridge (Middle Ages)
    # Except to avoid sprite bugs we changed it
    # loc_id = LocID.ZENAN_BRIDGE_BOSS
    script = ct_rom.script_manager.get_script(loc_id)

    num_parts = len(boss.parts)

    if num_parts == 1:
        # Use object 0xB (Zombor's Head, 0xB4) for the boss because it has
        # sound effects in it.  But we'll change the coordinates so that the
        # boss will be on the ground

        # Zombor has an attract battle scene.  So we skip over the conditionals
        pos = script.get_function_start(0xB, 0)
        found_boss = False
        found_coord = False

        # Note: These are tile coordinates, not suitable for anything but the
        #       one spot assignment.
        first_x, first_y = 0xE8, 0x90
        first_id, first_slot = boss.parts[0].enemy_id, boss.parts[0].slot

        while pos < script.get_function_end(0xB, 0):
            cmd = eventcommand.get_command(script.data, pos)

            # print(cmd)
            if cmd.command in EC.fwd_jump_commands:
                pos += (cmd.args[-1] - 1)
            elif cmd.command == 0x83:
                found_boss = True
                cmd.args[0] = first_id
                cmd.args[1] = first_slot
                script.data[pos:pos+len(cmd)] = cmd.to_bytearray()
            elif cmd.command == 0x8B:
                found_coord = True

                cmd = EC.set_object_coordinates_auto(first_x, first_y)
                script.insert_commands(cmd.to_bytearray(), pos)
                script.delete_commands(pos+len(cmd), 1)

            pos += len(cmd)

        if not found_boss or not found_coord:
            raise ValueError(f"Error: found boss({found_boss}), " +
                             f"found coord({found_coord})")

        # Delete the other Zombor object (0xC) to save memory.  It might be
        # OK to leave it in, set it to the one-spot boss, and delete all
        # references as we do below.
        script.remove_object(0xC)
    # end 1 part

    # multi-part assignment

    # Determine whether coordinates will need to be set by pixels or not.
    # Maybe just always force pixels for multi-spot
    pos = get_last_coord_cmd_pos(script, 0xB, 0)
    coord_cmd = eventcommand.get_command(script.data, pos)
    first_x, first_y = coord_cmd.get_pixel_coordinates()
    # print(f'{first_x:04X}, {first_y:04X}')

    force_pixel_coords = are_pixel_coords_forced(first_x, first_y, boss)

    boss_ids = [part.enemy_id for part in boss.parts]
    if num_parts > 1:
        if (
                EnemyID.GUARDIAN_BIT in boss_ids or
                EnemyID.MOTHERBRAIN in boss_ids
        ):
            boss.reorder_horiz(left=False)

        # object to overwrite with new boss ids and coords
        reused_objs = [0xB, 0xC]

        for i in [0, 1]:
            new_x = first_x + boss.parts[i].displacement[0]
            new_y = first_y + boss.parts[i].displacement[1]

            new_id = boss.parts[i].enemy_id
            new_slot = boss.parts[i].slot

            set_object_boss(script, reused_objs[i], new_id, new_slot)
            set_object_coordinates(script, reused_objs[i], new_x, new_y,
                                   force_pixel_coords=force_pixel_coords)

        show_cmds = bytearray()
        for i in range(2, len(boss.parts)):
            new_obj = append_boss_object(
                script, boss, i, first_x, first_y,
                force_pixel_coords=force_pixel_coords
            )
            show = EC.set_object_drawing_status(new_obj, True)
            show_cmds.extend(show.to_bytearray())

        # Suitable time for them to appear is right after the first two parts'
        # entrance.  The very end of obj C, activate (1), before the return
        ins_pos = script.get_function_end(0xC, 1) - 1
        script.insert_commands(show_cmds, ins_pos)
    # end multi-part


def set_death_peak_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.DEATH_PEAK_GUARDIAN_SPAWN):
    '''Sets the boss in the final Lavos Spawn spot on Death Peak.'''
    # 0x1EF is the Lavos Spawn's map - Death Peak Guardian Spawn
    # loc_id = 0x1EF
    script = ct_rom.script_manager.get_script(loc_id)

    # The shell is important since it needs to stick around after battle.
    # It is in object 9, and the head is in object 0xA
    boss_objs = [0x9, 0xA]

    num_used = min(len(boss.parts), 2)

    first_x, first_y = 0x78, 0xD0

    for i in range(num_used):
        part = boss.parts[i]
        boss_id = part.enemy_id
        boss_slot = part.slot

        new_x = first_x + part.displacement[0]
        new_y = first_y + part.displacement[1]
        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        set_object_coordinates(script, boss_objs[i], new_x, new_y,
                               force_pixel_coords=False)

    # Remove unused boss objects from the original script.
    # Will do nothing unless there are fewer boss ids provided than there
    # are original boss objects
    for i in range(len(boss.parts), len(boss_objs)):
        script.remove_object(boss_objs[i])

    # For every object exceeding the count in this map, make a new object.
    # For this particular map, we're going to copy the object except for
    # the enemy load/coords
    calls = bytearray()

    for i in range(len(boss_objs), len(boss.parts)):
        obj_id = script.append_copy_object(0xA)

        new_x = first_x + boss.parts[i].displacement[0]
        new_y = first_y + boss.parts[i].displacement[1]

        part = boss.parts[i]
        set_object_boss(script, obj_id, part.enemy_id, part.slot)
        set_object_coordinates(script, obj_id, new_x, new_y)

        call = EC.call_obj_function(obj_id, 3, 3, FS.CONT)
        calls.extend(call.to_bytearray())

    # Insertion point is right before the first Move Party command (0xD9)
    pos, _ = script.find_command([0xD9],
                                 script.get_function_start(8, 1),
                                 script.get_function_end(8, 1))

    script.insert_commands(calls, pos)


def set_giga_mutant_spot_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.BLACK_OMEN_GIGA_MUTANT):
    '''Sets the boss of the Giga Mutant spot in the Black Omen.'''
    # 0x143 is the Giga Mutant's map - Black Omen 63F Divine Guardian
    # loc_id = 0x143
    script = ct_rom.script_manager.get_script(loc_id)

    boss_objs = [0xE, 0xF]

    num_used = min(len(boss.parts), 2)
    first_x, first_y = 0x278, 0x1A0

    # mutant coords are weird.  The coordinates are the bottom of the mutant's
    # bottom part.  We need to shift up so non-mutants aren't on the party.
    # Golems also float above their coordinate location.
    if boss.parts[0].enemy_id not in [EnemyID.GIGA_MUTANT_HEAD,
                                      EnemyID.GIGA_MUTANT_BOTTOM,
                                      EnemyID.TERRA_MUTANT_HEAD,
                                      EnemyID.TERRA_MUTANT_BOTTOM,
                                      EnemyID.MEGA_MUTANT_HEAD,
                                      EnemyID.MEGA_MUTANT_BOTTOM,
                                      EnemyID.GOLEM, EnemyID.GOLEM_BOSS]:
        first_y -= 0x20

    # overwrite as many boss objects as possible
    for i in range(num_used):
        boss_id = boss.parts[i].enemy_id
        boss_slot = boss.parts[i].slot

        new_x = first_x + boss.parts[i].displacement[0]
        new_y = first_y + boss.parts[i].displacement[1]

        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        set_object_coordinates(script, boss_objs[i], new_x, new_y,
                               force_pixel_coords=True)

    # Remove unused boss objects.
    for i in range(len(boss.parts), len(boss_objs)):
        script.remove_object(boss_objs[i])

    # Add more boss objects if needed
    calls = bytearray()
    for i in range(len(boss_objs), len(boss.parts)):
        obj_id = script.append_copy_object(boss_objs[1])

        new_x = first_x + boss.parts[i].displacement[0]
        new_y = first_y + boss.parts[i].displacement[1]

        set_object_boss(script, obj_id, boss.parts[i].enemy_id,
                        boss.parts[i].slot)
        set_object_coordinates(script, obj_id, new_x, new_y,
                               force_pixel_coords=True)

        # mimic call of other objects
        call = EC.call_obj_function(obj_id, 3, 3, FS.CONT)
        calls.extend(call.to_bytearray())

    # Insertion point is right after call_obj_function(0xE, touch, 3, cont)
    ins_cmd = EC.call_obj_function(0xE, 2, 3, FS.CONT)
    # print(f"{ins_cmd.command:02X}" + str(ins_cmd))

    pos = script.find_exact_command(ins_cmd,
                                    script.get_function_start(0xA, 1),
                                    script.get_function_end(0xA, 1))

    # shift to after the found command
    pos += len(ins_cmd)

    script.insert_commands(calls, pos)

    # This script is organized as a bunch of call(...., cont) with a terminal
    # call(...., halt).  We may have deleted the halting one, so just make sure
    # the last call is a halt
    script.data[pos + len(calls) - len(ins_cmd)] = 0x4  # Call w/ halt


def set_terra_mutant_spot_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.BLACK_OMEN_TERRA_MUTANT):
    '''Sets the boss of the Terra Mutant spot in the Black Omen'''
    # 0x145 is the Terra Mutant's map - Black Omen 98F Astral Guardian
    # loc_id = 0x145
    script = ct_rom.script_manager.get_script(loc_id)

    boss_objs = [0xF, 0x10]

    num_used = min(len(boss.parts), 2)
    # first_x, first_y = 0x70, 0x80
    first_x, first_y = 0x78, 0x90  # pixel version
    force_pixel_coords = are_pixel_coords_forced(first_x, first_y,
                                                 boss)

    # mutant coords are weird.  The coordinates are the bottom of the mutant's
    # bottom part.  We need to shift up so non-mutants aren't on the party.
    # Golems also float above their coordinate location.
    if boss.parts[0].enemy_id not in [EnemyID.GIGA_MUTANT_HEAD,
                                      EnemyID.GIGA_MUTANT_BOTTOM,
                                      EnemyID.TERRA_MUTANT_HEAD,
                                      EnemyID.TERRA_MUTANT_BOTTOM,
                                      EnemyID.MEGA_MUTANT_HEAD,
                                      EnemyID.MEGA_MUTANT_BOTTOM,
                                      EnemyID.GOLEM, EnemyID.GOLEM_BOSS]:
        first_y -= 0x20

    for i in range(num_used):
        boss_id = boss.parts[i].enemy_id
        boss_slot = boss.parts[i].slot

        new_x = first_x + boss.parts[i].displacement[0]
        new_y = first_y + boss.parts[i].displacement[1]

        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        set_object_coordinates(script, boss_objs[i], new_x, new_y,
                               force_pixel_coords=force_pixel_coords)

    # Remove unused boss objects.
    for i in range(len(boss.parts), len(boss_objs)):
        script.remove_object(boss_objs[i])

    # Add more boss objects if needed
    calls = bytearray()
    for i in range(len(boss_objs), len(boss.parts)):
        obj_id = script.append_copy_object(boss_objs[1])

        new_x = first_x + boss.parts[i].displacement[0]
        new_y = first_y + boss.parts[i].displacement[1]

        set_object_boss(script, obj_id, boss.parts[i].enemy_id,
                        boss.parts[i].slot)
        set_object_coordinates(script, obj_id, new_x, new_y,
                               force_pixel_coords=force_pixel_coords)

        # mimic call of other objects
        call = EC.call_obj_function(obj_id, 3, 1, FS.SYNC)
        calls.extend(call.to_bytearray())

    # Insertion point is right after call_obj_function(0xF, arb0, 1, sync)
    ins_cmd = EC.call_obj_function(0xF, 3, 1, FS.SYNC)

    pos = script.find_exact_command(ins_cmd,
                                    script.get_function_start(8, 1))
    pos += len(ins_cmd)

    script.insert_commands(calls, pos)


def set_elder_spawn_spot_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.BLACK_OMEN_ELDER_SPAWN):
    '''Sets the boss of the Elder Spawn spot in the Black Omen.'''
    # 0x60 is the Elder Spawn's map - Black Omen 98F Astral Progeny
    # loc_id = 0x60
    script = ct_rom.script_manager.get_script(loc_id)

    boss_objs = [0x8, 0x9]

    num_used = min(len(boss.parts), 2)
    first_x, first_y = 0x170, 0xB2

    # overwrite as many boss objects as possible
    for i in range(num_used):
        boss_id = boss.parts[i].enemy_id
        boss_slot = boss.parts[i].slot

        new_x = first_x + boss.parts[i].displacement[0]
        new_y = first_y + boss.parts[i].displacement[1]

        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        # The coordinate setting is in activate for whatever reason.
        set_object_coordinates(script, boss_objs[i], new_x, new_y, True, 1,
                               force_pixel_coords=True)

    # Remove unused boss objects.
    for i in range(len(boss.parts), len(boss_objs)):
        script.remove_object(boss_objs[i])

    # Add more boss objects if needed
    calls = bytearray()
    for i in range(len(boss_objs), len(boss.parts)):
        obj_id = script.append_copy_object(boss_objs[1])

        new_x = first_x + boss.parts[i].displacement[0]
        new_y = first_y + boss.parts[i].displacement[1]

        set_object_boss(script, obj_id, boss.parts[i].enemy_id,
                        boss.parts[i].slot)
        # The coordinate setting is in activate for whatever reason.
        set_object_coordinates(script, obj_id, new_x, new_y, True,
                               fn_id=1, force_pixel_coords=True)

        # mimic call of other objects
        call = EC.call_obj_function(obj_id, 2, 6, FS.CONT)
        calls.extend(call.to_bytearray())

    # Insertion point is right before call_obj_function(0x8, touch, 6, cont)
    ins_cmd = EC.call_obj_function(0x8, 2, 6, FS.CONT)

    pos = script.find_exact_command(ins_cmd,
                                    script.get_function_start(0, 0))
    pos += len(ins_cmd)

    script.insert_commands(calls, pos)


def set_sun_palace_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.SUN_PALACE):
    '''Sets the boss of the Sun Palace.'''
    # 0xFB is Son of Sun's map - Sun Palace
    # loc_id = 0xFB
    script = ct_rom.script_manager.get_script(loc_id)

    # Eyeball in 0xB and rest are flames. 0x10 is hidden in rando.
    # Really, 0x10 should just be removed from the start.
    script.remove_object(0x10)

    pos, _ = script.find_command([0x96],
                                 script.get_function_start(0x0B, 4))

    script.data[pos+2] = 0x1F
    pos += 3
    cmd = EC.set_object_coordinates(0x100, 0x1FF, False)

    script.delete_commands(pos, 1)
    script.insert_commands(cmd.to_bytearray(), pos)

    boss_objs = [0xB, 0xC, 0xD, 0xE, 0xF]
    num_used = min(len(boss.parts), len(boss_objs))

    # After the ambush
    # first_x, first_y = 0x100, 0x1B0
    first_x, first_y = 0x108, 0x1C0  # pixel versions
    force_pixel_coords = are_pixel_coords_forced(first_x, first_y,
                                                 boss)

    # overwrite as many boss objects as possible
    for i in range(num_used):
        boss_id = boss.parts[i].enemy_id
        boss_slot = boss.parts[i].slot

        new_x = first_x + boss.parts[i].displacement[0]
        new_y = first_y + boss.parts[i].displacement[1]

        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        set_object_coordinates(script, boss_objs[i], new_x, new_y, True,
                               force_pixel_coords=force_pixel_coords)

        if i == 0:
            # SoS is weird about the first part moving before the rest are
            # visible.  So the rest will pop in relative to these coords
            first_x, first_y = 0x100, 0x1FF

    # Remove unused boss objects.  In reverse order of course.
    for i in range(len(boss_objs), len(boss.parts), -1):
        script.remove_object(boss_objs[i-1])

    # Add more boss objects if needed.  This will never happen for vanilla
    # Son of Sun, but maybe if scaling adds flames?

    calls = bytearray()
    for i in range(len(boss_objs), len(boss.parts)):
        obj_id = script.append_copy_object(boss_objs[1])

        new_x = first_x + boss.parts[i].displacement[0]
        new_y = first_y + boss.parts[i].displacement[1]

        set_object_boss(script, obj_id,
                        boss.parts[i].enemy_id, boss.parts[i].slot)
        # The coordinate setting is in init
        set_object_coordinates(script, obj_id, new_x, new_y, True,
                               force_pixel_coords=force_pixel_coords)

        # mimic call of other objects
        call = EF()
        if i == len(boss.parts)-1:
            call.add(EC.call_obj_function(obj_id, 1, 1, FS.SYNC))
        else:
            call.add(EC.call_obj_function(obj_id, 1, 1, FS.HALT))

        call.add(EC.generic_one_arg(0xAD, 0x01))
        calls.extend(call.get_bytearray())

    # Insertion point is before the pause before Animate 0x1.
    ins_cmd = EC.generic_one_arg(0xAA, 0x01)

    # In the eyeball's (0xB) arb 1
    pos = script.find_exact_command(ins_cmd,
                                    script.get_function_start(0xB, 4))
    pos += len(ins_cmd)

    script.insert_commands(calls, pos)

    # Remove bad animation commands.  Do this after the assignment because
    # an animation command is used as a hook position.
    boss_ids = {part.enemy_id for part in boss.parts}
    bad_ids = [EnemyID.MOTHERBRAIN, ]
    if set(bad_ids).intersection(boss_ids):
        pos = script.find_exact_command(
            EC.generic_command(0xB7, 7, 3),
            script.get_function_start(0xB, 3)
        )

        script.delete_commands(pos, 2)  # Two animation commands


def set_desert_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.SUNKEN_DESERT_DEVOURER):
    '''Sets the boss of the Sunken Desert.'''
    # 0xA1 is Retinite's map - Sunken Desert Devourer
    # loc_id = 0xA1
    script = ct_rom.script_manager.get_script(loc_id)

    boss_objs = [0xE, 0xF, 0x10]

    # Extra copies of retinite bottom for the vanilla random location
    # There are some blank objects that can be removed, but will not do so.
    del_objs = [0x12, 0x11]
    for obj in del_objs:
        script.remove_object(obj)

    num_used = min(len(boss.parts), 3)
    first_x, first_y = 0x120, 0xC9

    # overwrite as many boss objects as possible
    for i in range(num_used):
        boss_id = boss.parts[i].enemy_id
        boss_slot = boss.parts[i].slot

        new_x = first_x + boss.parts[i].displacement[0]
        new_y = first_y + boss.parts[i].displacement[1]

        set_object_boss(script, boss_objs[i], boss_id, boss_slot)
        # The coordinate setting is in arb0 for whatever reason.
        set_object_coordinates(script, boss_objs[i], new_x, new_y, True, 3,
                               force_pixel_coords=True)

    # Remove unused boss objects.  In reverse order of course.
    for i in range(len(boss_objs), len(boss.parts), -1):
        script.remove_object(boss_objs[i-1])

    # Add more boss objects if needed.
    calls = bytearray()

    for i in range(len(boss_objs), len(boss.parts)):
        obj_id = script.append_copy_object(boss_objs[1])

        new_x = first_x + boss.parts[i].displacement[0]
        new_y = first_y + boss.parts[i].displacement[1]

        set_object_boss(script, obj_id, boss.parts[i].enemy_id,
                        boss.parts[i].slot)
        # The coordinate setting is in arb0
        set_object_coordinates(script, obj_id, new_x, new_y, True,
                               fn_id=4, force_pixel_coords=True)

        # mimic call of other objects
        call = EC.call_obj_function(obj_id, 4, 0, FS.SYNC)

        calls.extend(call.to_bytearray())

    # Insertion point is before the pause before Calling obj 0xE, arb 1
    ins_cmd = EC.call_obj_function(0xE, 4, 2, FS.HALT)

    # In the eyeball's (0xB) arb 1
    pos = script.find_exact_command(ins_cmd,
                                    script.get_function_start(0x2, 0))

    pos -= len(ins_cmd)

    script.insert_commands(calls, pos)


def set_mt_woe_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.MT_WOE_SUMMIT):
    '''Sets the boss of Mt. Woe.'''
    boss_ids = [part.enemy_id for part in boss.parts]
    if EnemyID.GIGA_GAIA_HEAD in boss_ids:
        return

    # loc_id = LocID.MT_WOE_SUMMIT
    script = ct_rom.script_manager.get_script(loc_id)

    # Copy blank tiles over GG's body
    pos = script.get_object_start(0)
    copytiles = EC.copy_tiles(2, 1, 0xD, 9, 0x2, 0x11,
                              copy_l1=True, copy_l2=True, copy_l3=True,
                              copy_props=True, wait_vblank=False)
    script.insert_commands(copytiles.to_bytearray(), pos)

    # Copy on return from menu too.
    copytiles_vblank = copytiles.copy()
    copytiles_vblank.command = 0xE4
    pos = script.get_function_start(0, 1)
    script.insert_commands(copytiles_vblank.to_bytearray(), pos)

    # delete the loading of melchior
    pos = script.get_function_start(8, 0)
    script.delete_commands(pos, 1)

    boss_objs = [0x0A, 0x0B, 0x0C]

    first_x, first_y = 0x80, 0x158  # will force pixel coords

    if len(boss_objs) > len(boss.parts):
        # Remove unused objects
        for i in range(len(boss_objs), len(boss.parts), -1):
            script.remove_object(boss_objs[i-1])
            del boss_objs[i-1]
    elif len(boss.parts) > len(boss_objs):
        # Add new copies of a GG Hand object
        for i in range(len(boss_objs), len(boss.parts)):
            obj_id = script.append_copy_object(boss_objs[1])
            boss_objs.append(obj_id)

    for ind, obj in enumerate(boss_objs):
        new_x = first_x + boss.parts[ind].displacement[0]
        new_y = first_y + boss.parts[ind].displacement[1]

        boss_id = boss.parts[ind].enemy_id
        boss_slot = boss.parts[ind].slot

        set_object_boss(script, obj, boss_id, boss_slot)
        set_object_coordinates(script, obj,
                               new_x, new_y, force_pixel_coords=True)

    # Mt. Woe starts with everything visible so there's no need for anything
    # extra inserted.


# This is line-for-line almost identical to the woe one... may be time to
# abstract some of this out.
def set_geno_dome_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.GENO_DOME_MAINFRAME):
    '''Sets the boss of the Geno Dome in Mother Brain's spot.'''
    boss_ids = [part.enemy_id for part in boss.parts]
    if EnemyID.MOTHERBRAIN in boss_ids:
        return

    # loc_id = LocID.GENO_DOME_MAINFRAME
    script = ct_rom.script_manager.get_script(loc_id)

    # There appears to be an unused display object in 0x23.  It has to go
    # to avoid sprite bugs.
    script.remove_object(0x23)

    # One screen has a function to make the screens shift colors.
    # Get rid of it.
    func = script.get_function(0x21, 1)
    script.set_function(0x22, 1, func)

    # Weird commands that make mother brain's colors shift.
    # Setting 0x7E2A21 to  2 or 0.  Both are command 0x4A.
    pos = script.get_function_start(0x1E, 0)
    pos = script.find_exact_command(EC.assign_val_to_mem(2, 0x7E2A21, 1), pos)
    script.delete_commands(pos, 1)
    pos = script.find_exact_command(EC.assign_val_to_mem(0, 0x7E2A21, 1), pos)
    script.delete_commands(pos, 1)

    boss_objs = [0x1F, 0x20, 0x21, 0x22]

    first_x, first_y = 0xA0, 0x6F  # pixel coords, force pixels

    ins_cmds = EF()
    if len(boss_objs) > len(boss.parts):
        # Remove unused objects
        for i in range(len(boss_objs), len(boss.parts), -1):
            script.remove_object(boss_objs[i-1])
            del boss_objs[i-1]
    elif len(boss.parts) > len(boss_objs):
        # Add new copies of a display object
        ins_cmds = EF()
        for i in range(len(boss_objs), len(boss.parts)):
            obj_id = script.append_copy_object(boss_objs[1])
            boss_objs.append(obj_id)

            # record the command that needs to be called to display the
            # new object.  Just call its activate function in this case.
            ins_cmds.add(EC.call_obj_function(obj_id, 1, 1, FS.CONT))

    boss_arb0 = (
        EF()
        .add(EC.set_own_drawing_status(True))
        .add(EC.vector_move(0xC0, 30, False))
        .add(EC.return_cmd())
    )

    for ind, obj in enumerate(boss_objs):
        new_x = first_x + boss.parts[ind].displacement[0]
        new_y = first_y + boss.parts[ind].displacement[1]

        boss_id = boss.parts[ind].enemy_id
        boss_slot = boss.parts[ind].slot

        set_object_boss(script, obj, boss_id, boss_slot)
        set_object_coordinates(script, obj,
                               new_x, new_y, force_pixel_coords=True)

        script.set_function(obj, 3, boss_arb0)

    start = script.get_function_start(0x1E, 0)
    end = script.get_function_end(0x1E, 0)
    ins_pos_cmd = EC.call_obj_function(0x1F, 1, 1, FS.CONT)
    ins_pos = script.find_exact_command(ins_pos_cmd, start, end)

    ins_pos += len(ins_pos_cmd)

    script.insert_commands(ins_cmds.get_bytearray(), ins_pos)


def set_arris_dome_boss(
        ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.ARRIS_DOME_GUARDIAN_CHAMBER):
    '''Sets the boss of the Arris Dome.'''
    if EnemyID.GUARDIAN in [part.enemy_id for part in boss.parts]:
        return

    # loc_id = LocID.ARRIS_DOME_GUARDIAN_CHAMBER
    script = ct_rom.script_manager.get_script(loc_id)

    # Remove the guardian's body because Guardian is not here.
    copy_tiles = EC.copy_tiles(3, 0x11, 0xC, 0x1C,
                               3, 2,
                               copy_l1=True,
                               copy_l3=True,
                               copy_props=True,
                               unk_0x10=True,
                               unk_0x20=True,
                               wait_vblank=False)

    pos: typing.Optional[int]
    pos = script.get_function_start(0, 1)
    script.insert_commands(copy_tiles.to_bytearray(), pos)

    # copy the vblank waiting version to obj0 func 1 for post-menu
    copy_tiles_vblank = EC.copy_tiles(3, 0x11, 0xC, 0x1C,
                                      3, 2,
                                      copy_l1=True,
                                      copy_l3=True,
                                      copy_props=True,
                                      unk_0x10=True,
                                      unk_0x20=True,
                                      wait_vblank=True)

    pos = script.get_function_start(0, 0)
    script.insert_commands(copy_tiles_vblank.to_bytearray(), pos)
    # End guardian body removal

    # We manually get the first x,y because we have to adjust it to make
    # the bosses fall in the right spot.
    first_x, first_y = 0x80, 0xB8
    # first_x, first_y = 0x80, 0xC8

    boss_objs = [0xB, 0xC, 0xD]

    # Remove an unneeded move cmd from the arb0.  The bits float down from
    # the ceiling, but we don't need that.
    script.delete_command_from_function([0x96], 0xC, 3)
    script.delete_command_from_function([0x96], 0xD, 3)

    # Remove the hide command from startup
    script.delete_command_from_function([0x91], 0xB, 0)
    script.delete_command_from_function([0x91], 0xC, 0)
    script.delete_command_from_function([0x91], 0xD, 0)

    # Remove old calls to bit arb0s.  We will recreate these once we have the
    # right list of objects.
    call = EC.call_obj_function(0xC, 3, 3, FS.CONT)
    start = script.get_function_start(9, 1)
    end = script.get_function_end(9, 1)
    pos = script.find_exact_command(call, start, end)

    script.delete_commands(pos, 2)

    if len(boss_objs) > len(boss.parts):
        # Remove unused objects
        for i in range(len(boss_objs), len(boss.parts), -1):
            script.remove_object(boss_objs[i-1])
            del boss_objs[i-1]
    elif len(boss.parts) > len(boss_objs):
        # Add new copies of a bit object (that we cleaned up above)
        for i in range(len(boss_objs), len(boss.parts)):
            obj_id = script.append_copy_object(boss_objs[1])
            boss_objs.append(obj_id)

    for ind, obj in enumerate(boss_objs):
        new_x = first_x + boss.parts[ind].displacement[0]
        new_y = first_y + boss.parts[ind].displacement[1]

        boss_id = boss.parts[ind].enemy_id
        boss_slot = boss.parts[ind].slot

        set_object_boss(script, obj, boss_id, boss_slot)
        set_object_coordinates(script, obj,
                               new_x, new_y,
                               force_pixel_coords=True)

    # add calls to arb0s for all but first object.  This makes them visible
    # and sets collisions correctly.
    new_calls = EF()
    for ind in range(1, len(boss_objs)):
        # The last function halts, so all of them are finished before
        # proceeding to the battle.
        if ind == len(boss_objs) - 1:
            sync = FS.HALT
        else:
            sync = FS.CONT

        new_calls.add(EC.call_obj_function(boss_objs[ind], 3, 3, sync))

    start = script.get_function_start(9, 1)
    end = script.get_function_end(9, 1)
    pos, _ = script.find_command([0xD8], start, end)  # Battle

    script.insert_commands(new_calls.get_bytearray(), pos)


def set_prison_catwalks_boss(
        ct_rom: ctrom.CTRom,
        boss: rotypes.BossScheme,
        loc_id: ctenums.LocID = ctenums.LocID.PRISON_CATWALKS):
    '''Sets the boss of the Dragon Tank's Spot.'''
    # loc_id = ctenums.LocID.PRISON_CATWALKS
    script = ct_rom.script_manager.get_script(loc_id)

    # Unsure what these are doing here.  Looks like experimentation.
    script.remove_object(0x17)
    script.remove_object(0x16)

    # I'm not sure why, but adding a spritepriority command in the tank body
    # startup will fix the layer issues.  This command is not present in the
    # vanilla script (except attract mode), so I'm not sure what's up.
    pos: typing.Optional[int]
    pos = get_last_coord_cmd_pos(script, 0xE, 0)
    script.insert_commands(EC.generic_command(0x8E, 0x84).to_bytearray(), pos)

    boss_ids = [part.enemy_id for part in boss.parts]
    if ctenums.EnemyID.DRAGON_TANK in boss_ids:
        return

    # body, head, grinder
    boss_objs = [0xD, 0xE, 0xF]

    pos = get_last_coord_cmd_pos(script, 0xD, 0)
    coord_cmd = eventcommand.get_command(script.data, pos)
    first_x, first_y = coord_cmd.get_pixel_coordinates()
    force_pixel_coords = are_pixel_coords_forced(first_x, first_y, boss)

    EID = ctenums.EnemyID

    if EID.RETINITE_EYE in boss_ids:
        first_y -= 0x28
    elif EID.MOTHERBRAIN in boss_ids:
        first_y -= 0x28
        first_x -= 0x20

    # Since bosses may move, add a move back to the explosion point
    # Do this before the object order gets all messed up.
    func = (
        EF()
        .add(EC.generic_command(0x96, 0x9, 0x9))
        .add(EC.return_cmd())
    )
    script.set_function(0xE, 6, func)

    pos, cmd = script.find_command([0xD8])

    script.insert_commands(
        EC.call_obj_function(0xE, 6, 6, FS.HALT).to_bytearray(),
        pos+len(cmd)
    )

    # Set up all of the boss objects -- make own function?
    if len(boss.parts) == 1:
        # Keep static object E
        script.remove_object(0xF)
        script.remove_object(0xD)
        boss_objs = [0xD]
    elif len(boss_objs) > len(boss.parts):
        boss.make_part_first(1)
        # Remove unused objects
        for i in range(len(boss_objs), len(boss.parts), -1):
            script.remove_object(boss_objs[i-1])
            del boss_objs[i-1]
    elif len(boss.parts) > len(boss_objs):
        # Add copies of the grinder
        boss.make_part_first(1)
        for i in range(len(boss_objs), len(boss.parts)):
            obj_id = script.append_copy_object(boss_objs[-1])
            boss_objs.append(obj_id)

    # replace tile-based move commands with a vectormove because there is no
    # pixel-based move command.
    new_arb0 = (
        EF()
        .add(EC.set_own_drawing_status(True))
        .add(EC.vector_move(0, 0x50, False))
        .add(EC.return_cmd())
    )

    call_cmds = EF()

    for ind, obj in enumerate(boss_objs):
        new_x = first_x + boss.parts[ind].displacement[0]
        new_y = first_y + boss.parts[ind].displacement[1]

        set_object_boss(script, obj, boss.parts[ind].enemy_id,
                        boss.parts[ind].slot)
        set_object_coordinates(script, obj, new_x, new_y,
                               force_pixel_coords=force_pixel_coords)
        script.set_function(obj, 3, new_arb0)

        if ind == len(boss_objs) - 1:
            call_cmds.add(EC.call_obj_function(obj, 3, 6, FS.HALT))
        else:
            call_cmds.add(EC.call_obj_function(obj, 3, 6, FS.CONT))

    # The only remaining thing is to redo a block of callobjfuncs
    pos = script.find_exact_command(EC.call_obj_function(0xD, 3, 6, FS.CONT))

    while script.data[pos] in (2, 3, 4):  # call cmds
        script.delete_commands(pos, 1)

    script.insert_commands(call_cmds.get_bytearray(), pos)


def set_factory_boss(ct_rom: ctrom.CTRom, boss: rotypes.BossScheme,
                     loc_id: ctenums.LocID = ctenums.LocID(0xE6),
                     is_vanilla: bool = False):
    '''Sets the boss of the R-Series spot.'''
    script = ct_rom.script_manager.get_script(loc_id)

    if not is_vanilla:
        script.remove_object(0xF)
        script.remove_object(0xE)
        boss_objs = [0xA, 0xB, 0xC, 0xD]
    else:
        boss_objs = [0xA, 0xB, 0xC, 0xD, 0xE, 0xF]

    pos: typing.Optional[int]
    pos = get_first_coord_cmd_pos(script, 0xA, 0)

    coord_cmd = eventcommand.get_command(script.data, pos)
    first_x, first_y = coord_cmd.get_pixel_coordinates()
    force_pixel_coords = are_pixel_coords_forced(first_x, first_y, boss)

    if len(boss_objs) > len(boss.parts):
        for i in range(len(boss_objs), len(boss.parts), -1):
            script.remove_object(boss_objs[i-1])
            del boss_objs[i-1]
    elif len(boss.parts) > len(boss_objs):
        # Add copies of an R-series
        for i in range(len(boss_objs), len(boss.parts)):
            obj_id = script.append_copy_object(boss_objs[-1])
            boss_objs.append(obj_id)

    boss_arb0 = (
        EF()
        .add(EC.set_own_drawing_status(True))
        .add(EC.vector_move(90, 0x10, False))
        .add(EC.return_cmd())
    )

    call_cmds = EF()
    for ind, obj in enumerate(boss_objs):
        new_x = first_x + boss.parts[ind].displacement[0]
        new_y = first_y + boss.parts[ind].displacement[1]
        boss_id = boss.parts[ind].enemy_id
        boss_slot = boss.parts[ind].slot

        # R-Series loads are locked behind if flag
        set_object_boss(script, obj, boss_id, boss_slot,
                        ignore_jumps=False)
        set_object_coordinates(script, obj, new_x, new_y,
                               ignore_jumps=False,
                               force_pixel_coords=force_pixel_coords)

        script.set_function(obj, 3, boss_arb0)

        if ind == len(boss_objs)-1:
            call_cmds.add(EC.call_obj_function(obj, 3, 3, FS.HALT))
        else:
            call_cmds.add(EC.call_obj_function(obj, 3, 3, FS.CONT))

    pos = script.find_exact_command(
        EC.call_obj_function(0xA, 3, 3, FS.CONT),
        start_pos=script.get_object_start(1)
    )

    # call cmds but stop with the obj2 call
    while script.data[pos] in (2, 3, 4) and script.data[pos+1] != 4:
        script.delete_commands(pos, 1)

    # I think there's a bug where a prior command to reduce song volume to 0
    # over some time period does not finish before the song is changed and
    # the volume is restored.  This only seems to happen when there are fewer
    # boss objects so the intro animation is faster.  We'll add a brief pause
    # to make sure that the timing works out.
    call_cmds.add(EC.pause(0.25))

    script.insert_commands(call_cmds.get_bytearray(), pos)
