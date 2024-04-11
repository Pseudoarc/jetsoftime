'''
Provides functions to implement Cthulhu Crisis's Legacy of Cyrus mode.
'''
from __future__ import annotations
import functools
import random

import ctenums
import ctevent
import ctrom
import ctstrings
import eventfunction
import eventcommand

import randoconfig as cfg



def get_character_assignment() -> dict[ctenums.RecruitID, ctenums.CharID]:
    '''
    Generates an assignment with neither Magus nor Frog in the future.
    '''
    RID = ctenums.RecruitID
    CharID = ctenums.CharID

    assign_dict = dict()

    avail_chars = list(CharID)
    avail_spots = list(RID)

    # Choose the future character first because it has no restrictions
    future_chars = [
        x for x in avail_chars if x not in (CharID.FROG, CharID.MAGUS)
    ]
    future_char = random.choice(future_chars)

    assign_dict[RID.PROTO_DOME] = future_char

    # Shuffle the remaining characters and assign to the remaining RIDs
    avail_chars.remove(future_char)
    avail_spots.remove(RID.PROTO_DOME)

    random.shuffle(avail_chars)
    remaining_assignments = dict(zip(avail_spots, avail_chars))

    # Add the remaining assignments to the main dict
    assign_dict.update(remaining_assignments)

    return assign_dict


def write_loc_recruit_locks(ct_rom: ctrom.CTRom,
                            config: cfg.RandoConfig):
    '''Force Frog and Magus after recruitment.'''
    CharID = ctenums.CharID
    RID = ctenums.RecruitID

    key_chars = set([CharID.FROG, CharID.MAGUS])
    rids_to_lock = [
        RID.CATHEDRAL, RID.CASTLE, RID.FROGS_BURROW,
        RID.DACTYL_NEST, RID.PROTO_DOME
    ]

    for rid in rids_to_lock:
        insert_recruit_lock(ct_rom, config, rid, key_chars)


def write_loc_dungeon_locks(ct_rom: ctrom.CTRom):
    '''
    Updates dungeon access for Legacy of Cyrus.

    Makes the following changes:
    1) No access to future
    2) Required Frog + Magus + GrandLeon on tools turn-in
    3) Required Frog + Magus + Masamune on Magic Cave cutscene
    4) Required Frog + Magus + Magus's castle on Entering Ozzie's Fort
    '''
    remove_future(ct_rom)
    force_chars_at_carpenter(ct_rom)
    force_ruins_at_magic_cave_exterior(ct_rom)
    force_castle_before_ozzies_fort(ct_rom)
    lock_ocean_palace(ct_rom)


def remove_future(ct_rom: ctrom.CTRom):
    loc_id = ctenums.LocID.GUARDIA_THRONEROOM_1000
    script = ct_rom.script_manager.get_script(loc_id)

    EC = eventcommand.EventCommand
    EF = eventfunction.EventFunction

    new_str_id = script.add_string(
        ctstrings.CTString.from_str(
            'So what if you have the pendant?{line break}'
            'I\'m on my break right now!{null}'
        )
    )

    func = script.get_function(0x13, 1)

    ind = func.find_exact_command(
        EC.if_has_item(int(ctenums.ItemID.PENDANT), 0)
    )
    ins_pos = func.offsets[ind] + len(func.commands[ind])

    end_pos = func.offsets[-1]
    func.set_label('end', end_pos)

    ins_func = EF()
    (
        ins_func
        .add(EC.text_box(new_str_id))
        .jump_to_label(EC.jump_forward(0), 'end')
    )

    func.insert(ins_func, ins_pos)

    script.set_function(0x13, 1, func)


def force_ruins_at_magic_cave_exterior(ct_rom: ctrom.CTRom):

    loc_id = ctenums.LocID.MAGIC_CAVE_EXTERIOR
    script = ct_rom.script_manager.get_script(loc_id)

    obj_id = 0x0
    func_id = 0x0

    EC = eventcommand.EventCommand
    OP = eventcommand.Operation

    EF = eventfunction.EventFunction

    func = script.get_function(obj_id, func_id)

    # find the if sword repaired flag (0x7F0057 & 01)
    if_sword_repaired = EC.if_mem_op_value(
        0x7F0103, OP.BITWISE_AND_NONZERO, 0x02, 1, 0
    )

    ind = func.find_exact_command(if_sword_repaired)
    if_sword_repaired_pos = func.offsets[ind]

    insert_pos = if_sword_repaired_pos + len(if_sword_repaired)
    end_pos = len(func) - len(func.commands[-1])

    func.set_label('end', end_pos)

    if_cyrus_grave = EC.if_mem_op_value(
        0x7F01A3, OP.BITWISE_AND_NONZERO, 0x40, 1, 0
    )

    new_str_ind = script.add_string(
        ctstrings.CTString.from_str(
            '{frog}: We must visit Cyrus\'s grave before{line break}'
            'entering the Fiendlord\'s lair.{null}'
        )
    )

    ins_func = EF()
    (
        ins_func
        .add_if_else(
            if_cyrus_grave,
            EF(),
            (
                EF()
                .add(EC.text_box(new_str_ind))
                .jump_to_label(EC.jump_forward(0), 'end')
            )
        )
    )

    func.insert(ins_func, insert_pos)

    script.set_function(obj_id, func_id, func)


def force_chars_at_carpenter(ct_rom: ctrom.CTRom):

    loc_id = ctenums.LocID.CHORAS_CAFE
    script = ct_rom.script_manager.get_script(loc_id)

    # The carpenter is Object 0xF, activate (0x01)
    obj_id = 0xF
    func_id = 0x1

    EF = eventfunction.EventFunction
    EC = eventfunction.EventCommand

    orig_func = script.get_function(obj_id, func_id)

    # The return is actually in the touch function immediately after
    orig_func.set_label('end', len(orig_func))

    error_string = ctstrings.CTString.from_str(
        'Let this man enjoy his drink until we{linebreak+0}'
        'have {frog} and {magus}.{null}'
    )
    error_string_id = script.add_string(error_string)

    new_func = EF()

    for char in (ctenums.CharID.FROG, ctenums.CharID.MAGUS):
        new_func.add_if_else(
            EC.check_active_pc(int(char), 0),
            EF(),
            (
                EF()
                .add(EC.text_box(error_string_id))
                .jump_to_label(EC.jump_forward(0), 'end')
            )
        )

    orig_func.insert(new_func, 0)

    script.set_function(obj_id, func_id, orig_func)


def force_castle_before_ozzies_fort(ct_rom: ctrom.CTRom):

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.OZZIES_FORT_ENTRANCE
    )

    new_str_id = script.add_string(
        ctstrings.CTString.from_str(
            'Ozzie: Muahahahaha!  While {magus}\'s {line break}'
            'castle stands you have no hope of {line break}'
            'defeating me!{null}'
        )
    )

    EC = eventcommand.EventCommand
    EF = eventfunction.EventFunction
    OP = eventcommand.Operation

    # set_met_ozzie_flag = EC.set_bit(0x7F01A1, 0x01)
    unset_met_ozzie_flag = EC.reset_bit(0x7F01A1, 0x01)

    if_defeated_magus = EC.if_mem_op_value(
        0x7F01FF, OP.BITWISE_AND_NONZERO, 0x04, 1, 0
    )

    crystal_anim = EF()
    crystal_anim.add(EC.generic_one_arg(0xAB, 0xA))
    crystal_anim.add(EC.generic_one_arg(0xAA, 0xE))

    # copying the style of the change loc to overworld on death peak
    change_loc = EC.change_location(
        0x1F1, 0x3D*2, 0x1A*2, 1, 0, True
    )
    change_loc.command = 0xE0

    func = script.get_function(0x08, 0x01)

    # copying other ending warps
    warp_ending_cmd = EC.change_location(
        ctenums.LocID.ENDING_SELECTOR, 0, 0, 1, True,
    )
    warp_ending_cmd.command = 0xDF

    ins_func = (
        EF()
        .add(EC.set_storyline_counter(0x99))
        .add(warp_ending_cmd)
    )

    ins_func = EF()
    (
        ins_func
        .add_if_else(
            if_defeated_magus,
            EF(),
            (
                EF()
                .add(unset_met_ozzie_flag)
                .append(crystal_anim)
                .add(EC.text_box(new_str_id, False))
                .add(EC.fade_screen())
                .add(change_loc)
                )
            )
    )

    func.insert(ins_func, 0)
    script.set_function(0x08, 0x01, func)


# The future should be locked, so the omen is locked.
# Now, change the message when Magus is defeated, and prevent opening the
# door in Zeal Palace which leads to the Ocean Palace.
def lock_ocean_palace(ct_rom: ctrom.CTRom):

    loc_id = ctenums.LocID.MAGUS_CASTLE_INNER_SANCTUM
    script = ct_rom.script_manager.get_script(loc_id)

    EC = eventcommand.EventCommand

    # 7F00F4 & 80 == zeal door
    set_zeal_door_flag = EC.set_bit(0x7F00F4, 0x80)

    obj_id = 0x09
    func_id = 0x01
    func = script.get_function(obj_id, func_id)

    # After this, the Zeal door can only be opened with the Ruby Knife, and
    # that shouldn't exist in LoC.
    ind = func.find_exact_command(set_zeal_door_flag)
    func.delete_at_index(ind)

    ind -= 1
    # Now ind points to the textbox command
    str_ind = func.commands[ind].args[-1]

    script.strings[str_ind] = ctstrings.CTString.from_str(
        'The barrier at Ozzie\'s Fort has been{line break}'
        'neutralized!{null}'
    )
    script.modified_strings = True

    script.set_function(obj_id, func_id, func)


# This is a slightly improved version of the original from iceage.py.
# TODO: Move these generic functions into 'scripttools.py' or something and
#       just call from there.
def insert_recruit_lock(ct_rom: ctrom.CTRom,
                        config: cfg.RandoConfig,
                        recruit_spot: ctenums.RecruitID,
                        required_chars: set[ctenums.CharID]):
    '''
    Forces required characters to be active at the given recruit spot.
    '''

    # The general idea is to do the following
    #   1) Unset any character locks
    #   2) Allow the party shuffle (Y menu)
    #   3) Kick the user back to party shuffle if required characters
    #      are missing
    #   4) Set the character locks
    recruit = config.char_assign_dict[recruit_spot]
    if not isinstance(recruit, cfg.pcrecruit.CharRecruit):
        raise TypeError("Recruit Spot has the wrong type (StarterChar?)")
    loc_id = recruit.loc_id
    script = ct_rom.script_manager.get_script(loc_id)

    chars = list(required_chars)
    char_lock_bytes = functools.reduce(
        lambda a, b: a | b,
        [0x80 >> int(x) for x in chars]
    )

    EC = eventcommand.EventCommand
    EF = eventfunction.EventFunction
    # charlock bytes are in 0x7F01DF
    func = eventfunction.EventFunction()
    func.add(EC.assign_val_to_mem(0x0, 0x7F01DF, 1))
    func.set_label('replace')
    func.add(EC.replace_characters())

    for char in chars:
        char_str = str(char).lower()
        error_string = f"Must include {{{char_str}}}!{{null}}"
        script.strings.append(ctstrings.CTString.from_str(error_string))
        error_string_index = len(script.strings) - 1

        func.add_if(
            EC.check_recruited_pc(int(char), 0),
            (
                EF.if_else(
                    EC.check_active_pc(int(char), 0),
                    EF(),
                    (
                        EF()
                        .add(EC.text_box(error_string_index))
                        .jump_to_label(EC.jump_back(0), 'replace')
                    )
                )
            )
        )
    func.add(EC.assign_val_to_mem(char_lock_bytes, 0x7F01DF, 1))

    switch_pos = script.find_exact_command(EC.replace_characters())
    script.modified_strings = True
    script.insert_commands(func.get_bytearray(), switch_pos)
    script.delete_commands(switch_pos+len(func))

    # for string in script.strings:
    #     print(ctstrings.CTString.ct_bytes_to_ascii(string))


def set_ending_after_ozzies_fort(ct_rom: ctrom.CTRom):
    loc_id = ctenums.LocID.OZZIES_FORT_THRONE_INCOMPETENCE
    script = ct_rom.script_manager.get_script(loc_id)

    EC = eventcommand.EventCommand
    EF = eventfunction.EventFunction

    orig_func = script.get_function(0x08, 2)

    ins_pos = orig_func.offsets[-2]

    # copying other ending warps
    warp_ending_cmd = EC.change_location(
        ctenums.LocID.ENDING_SELECTOR, 0, 0, 1, True,
    )
    warp_ending_cmd.command = 0xDF

    ins_func = (
        EF()
        .add(EC.set_storyline_counter(0x99))
        .add(EC.darken(0x0C))
        .add(EC.fade_screen())
        .add(warp_ending_cmd)
    )

    orig_func.insert(ins_func, ins_pos)

    script.set_function(0x08, 2, orig_func)

    # Default jets messes with some of the locations viewed in the ending
    # 'What the Prophet Seeks.'  Luckily these locations are not able to be
    # accessed in LoC, so we load the vanilla events for these locations.
    orig_op_script = ctevent.Event.from_flux(
        './flux/orig_ocean_palace_entrance.Flux'
    )

    # Twin Golem spot is notable because this could in theory interfere with
    # boss rando.  The location should be locked out in LoC, however.
    orig_tg_script = ctevent.Event.from_flux(
        './flux/orig_twin_golem_spot.Flux'
    )
    end_str_b = orig_tg_script.strings[1]
    end_str = ctstrings.CTString.ct_bytes_to_ascii(end_str_b)
    end_str = end_str.replace('Lavos', 'akuheish')
    new_end_str_b = ctstrings.CTString.from_str(end_str)
    new_end_str_b.compress()
    orig_tg_script.strings[1] = new_end_str_b
    orig_tg_script.modified_strings = True

    ct_rom.script_manager.set_script(
        orig_op_script, ctenums.LocID.OCEAN_PALACE_ENTRANCE
    )

    ct_rom.script_manager.set_script(
        orig_tg_script, ctenums.LocID.OCEAN_PALACE_TWIN_GOLEM
    )
