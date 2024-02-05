import ctenums
import ctrom

import eventcommand
import randoconfig as cfg

from eventcommand import EventCommand as EC, FuncSync as FS, Operation as OP
from eventfunction import EventFunction as EF


def _build_pc_npc_startup_function(
        pc_id: ctenums.CharID,
        recruited_flag_addr: int, recruited_flag_bit: int,
        pc_npc_startup: EF
        ) -> EF:
    '''
    Builds a startup function that loads an npc-copy of a pc when the given
    flag is not set.  If the flag is set mid-script, then the object gets 
    marked as controllable.
    '''
    ret_fn = (
        EF()
        .add_if_else(
            EC.if_mem_op_value(recruited_flag_addr,
                               OP.BITWISE_AND_NONZERO,
                               recruited_flag_bit, 1, 0),
            EF().add(EC.load_pc_in_party(pc_id)),
            pc_npc_startup
        )
        .add(EC.return_cmd())
        .set_label('loop')
        .add_if_else(
            EC.if_mem_op_value(recruited_flag_addr,
                               OP.BITWISE_AND_NONZERO,
                               recruited_flag_bit, 1, 0),
            EF(),
            EF().jump_to_label(EC.jump_back(0), 'loop')
        )
        .add(EC.set_controllable_infinite())
        .add(EC.end_cmd())
    )

    return ret_fn


def _build_recruit_function(pc_id: ctenums.CharID,
                            recruited_flag_addr: int,
                            recruited_flag_bit: int,
                            pc2_index_addr: int):

    two_pc_recruit = (
        EF()
        .add(EC.party_follow())
        .add(EC.set_explore_mode(False))
        .add(EC.generic_command(0x95, 0))  # Follow PC00 once
        .add(EC.add_pc_to_active(pc_id))
        .add(EC.load_pc_in_party(pc_id))
        .add(EC.set_bit(recruited_flag_addr, recruited_flag_bit))
        .add(EC.name_pc(int(pc_id)))
    )

    three_pc_recruit = (
        EF()
        .add(EC.generic_command(0x95, 0))  # Follow PC00 once
        .add(EC.name_pc(pc_id))
        .add(EC.add_pc_to_reserve(pc_id))
        .add(EC.load_pc_in_party(pc_id))
        .add(EC.set_bit(recruited_flag_addr, recruited_flag_bit))
        .add(EC.set_explore_mode(True))
        .add(EC.switch_pcs())
    )

    ret_fn = (
        EF()
        .add_if_else(
            EC.if_mem_op_value(pc2_index_addr,
                               OP.EQUALS, 0x80, 1, 0),
            two_pc_recruit,
            three_pc_recruit
        )
        .add(EC.set_explore_mode(True))
        .add(EC.return_cmd())
    )

    return ret_fn


def assign_pc_to_manoria(ct_rom: ctrom.CTRom,
                         char_id: ctenums.CharID):
    '''
    Set the recruitable character in Manoria.
    '''
    script = ct_rom.script_manager.get_script(ctenums.LocID.MANORIA_SANCTUARY)

    if char_id == ctenums.CharID.FROG:
        pc_obj_id = 4
    elif char_id == ctenums.CharID.ROBO:
        pc_obj_id = 5
    else:
        pc_obj_id = char_id + 1

    pc_npc_startup = (
        EF()
        .add(EC.load_pc_always(char_id))
        .add(eventcommand.get_command(b'\x8B\x0B\x00'))  # coords
        .add(EC.script_speed(4))
        .add(EC.generic_zero_arg(0x1D))  # Facing
        .add(eventcommand.get_command(b'\x8E\x33'))  # draw priority
        .add(EC.set_own_drawing_status(False))
    )

    startup = _build_pc_npc_startup_function(
        char_id, 0x7F0100, 0x01, pc_npc_startup
    )
    script.set_function(pc_obj_id, 0, startup)

    # A call is made to obj 1 before the battle.  Replace with a call to PC1.
    # Note: This actually causes a bug if not fixed because calling out will
    #       hang if Crono is not in the party.  This leaves the object's
    #       priority set and can cause other calls to fail.
    pos = script.find_exact_command(EC.call_obj_function(1, 4, 3, FS.CONT))
    script.delete_commands(pos, 1)
    script.insert_commands(
        EF()
        .add(EC.call_pc_function(1, 4, 3, FS.CONT)).get_bytearray(),
        pos
    )

    # Grab the part of the script that does the animation before the char is
    # named.
    start = script.get_function_start(0x19, 3)
    end, _ = script.find_command([0xD2], start)

    recruit_anim_before = EF.from_bytearray(script.data[start:end])

    # Now get the part after the naming
    start = script.find_exact_command(EC.generic_command(0xE8, 0x6E), end)
    end = script.find_exact_command(EC.generic_command(0x87, 0x01), start)
    end += 2

    recruit_anim_after = EF.from_bytearray(script.data[start:end])

    two_pc_recruit = (
        EF()
        .add(EC.party_follow())
        .add(EC.set_explore_mode(False))
        .add(EC.generic_command(0x95, 0))  # Follow PC00 once
        .add(EC.add_pc_to_active(char_id))
        .add(EC.load_pc_in_party(char_id))
        .add(EC.set_bit(0x7F0100, 0x01))
        .add(EC.set_explore_mode(True))
        # .add(EC.name_pc(pc_id))
    )

    three_pc_recruit = (
        EF()
        .add(EC.generic_command(0x95, 0))  # Follow PC00 once
        .add(EC.party_follow())
        .add(EC.add_pc_to_reserve(char_id))
        .add(EC.load_pc_in_party(char_id))
        .add(EC.set_bit(0x7F0100, 0x01))
        .add(EC.switch_pcs())
    )

    recruit_func = (
        EF()
        .append(recruit_anim_before)
        .add(EC.name_pc(char_id))
        .append(recruit_anim_after)
        .add_if_else(
            EC.if_mem_op_value(0x7F021C, OP.EQUALS, 0x80, 1, 0),
            two_pc_recruit,
            three_pc_recruit
        )
        .add(EC.return_cmd())
    )
    script.set_function(pc_obj_id, 3+0xA, recruit_func)

    hook_cmd = EC.call_obj_function(0x19, 3, 3, FS.HALT)
    repl_cmd = EC.call_obj_function(pc_obj_id, 3+0xA, 3, FS.HALT)

    hook_pos = script.find_exact_command(hook_cmd,
                                         script.get_object_start(0xF))
    script.insert_commands(repl_cmd.to_bytearray(), hook_pos)
    hook_pos += len(repl_cmd)
    script.delete_commands(hook_pos, 1)

    script.remove_object(0x19)


def assign_pc_to_proto_dome(ct_rom: ctrom.CTRom,
                            pc_id: ctenums.CharID,
                            locked_chars: bool = False):
    '''
    Set the proto dome's recruit to the given pc.
    '''
    script = ct_rom.script_manager.get_script(ctenums.LocID.PROTO_DOME)
    
    # When the recruit is the 3rd pc (lost worlds or psychopaths) there is no
    # reload of the screen/character during recruitment.  So in order to get
    # the pc added correctly, we put the startup function in a loop which
    # waits until the pc is recruited (0x7F00F3 & 0x02)

    pc_npc_obj = 0x18  # object where pc-as-npc is loaded
    pc_obj = 1 + pc_id
    pc_npc_startup = (
        EF()
        .add(EC.load_pc_always(pc_id))
        .add(EC.generic_command(0x8B, 0x38, 0x16))  # coords
        .add(EC.generic_command(0xAA, 0x1D))  # kneeling animation
        .add(EC.generic_command(0x0D, 0x00))  # movement properties
    )

    # Load up the pc as an npc when the recruitment hasn't occurred.
    # Otherwise, do a normal PC load.
    pc_startup = EF()
    (
        pc_startup
        .add_if_else(
            EC.if_mem_op_value(0x7F00F3, OP.BITWISE_AND_NONZERO, 0x02, 1, 0),
            EF().add(EC.load_pc_in_party(pc_id)),
            pc_npc_startup
        )
        .add(EC.return_cmd())
        .set_label('loop')
        .add_if_else(
            EC.if_mem_op_value(0x7F00F3, OP.BITWISE_AND_NONZERO, 0x02, 1, 0),
            EF(),
            EF().jump_to_label(EC.jump_back(0), 'loop')
        )
        .add(EC.set_controllable_infinite())
        .add(EC.end_cmd())
    )
    script.set_function(pc_obj, 0, pc_startup)

    # The PC's activate function needs to do the animation and recruitment
    # if the recruitment hasn't occurred.

    # Just get the spinning/sparks flying animation part
    last_anim_cmd = EC.generic_command(0xAA, 0x1A)
    start = script.get_function_start(pc_npc_obj, 1)
    end = script.find_exact_command(last_anim_cmd, start) + len(last_anim_cmd)
    recruit_anim = EF.from_bytearray(script.data[start:end])

    if locked_chars:
        locked_chars_cmd = EC.if_mem_op_value(
            0x7F0103, OP.BITWISE_AND_NONZERO, 0x40, 1, 0
        )
        string_ind = script.add_py_string(
            "{line break}"
            "No Power.  Complete the Factory.{null}"
        )
        char_lock_func = (
            EF()
            .add_if_else(
                locked_chars_cmd,
                EF(),
                EF().add(EC.auto_text_box(string_ind)).add(EC.return_cmd())
            )
        )
        # do the insertion this way so that the hanging else of
        # char_lock func will point to the recruit anim
        recruit_anim.insert_at_index(char_lock_func, 0)

    two_pc_recruit = (
        EF()
        .add(EC.party_follow())
        .add(EC.set_explore_mode(False))
        .add(EC.generic_command(0x95, 0))  # Follow PC00 once
        .add(EC.add_pc_to_active(pc_id))
        .add(EC.load_pc_in_party(pc_id))
        .add(EC.set_bit(0x7F00F3, 0x02))
        .add(EC.name_pc(pc_id))
    )

    three_pc_recruit = (
        EF()
        .add(EC.generic_command(0x95, 0))  # Follow PC00 once
        .add(EC.name_pc(pc_id))
        .add(EC.add_pc_to_reserve(pc_id))
        .add(EC.load_pc_in_party(pc_id))
        .add(EC.set_bit(0x7F00F3, 0x02))  # hits controllable?
        .add(EC.set_explore_mode(True))
        .add(EC.switch_pcs())
    )

    # Rewrite the actual recruitment part
    recruit_func = EF()
    (
        recruit_func
        .append(recruit_anim)
        .add(EC.generic_command(0x0E, 0x02))
        .add(EC.generic_command(0xAE))
        .add_if_else(
            # 0x7F022E holds the 3rd PC id.  It is 0x80 when there is none
            # If there is no 3rd PC
            EC.if_mem_op_value(0x7F022E, OP.EQUALS, 0x80, 1, 0),
            two_pc_recruit,
            three_pc_recruit
        )
        .add(EC.set_explore_mode(True))
        .add(EC.return_cmd())
    )

    activate_func = (
        EF()
        .add_if_else(
            EC.if_mem_op_value(0x7F00F3, OP.BITWISE_AND_NONZERO, 0x02, 1, 0),
            EF().add(EC.return_cmd()),
            recruit_func
        )
    )

    script.set_function(pc_obj, 1, activate_func)
    script.set_function(pc_obj, 2, EF().add(EC.return_cmd()))
    script.remove_object(pc_npc_obj)


def fix_cursed_recruit_spots(
        config: cfg.RandoConfig,
        ct_rom: ctrom.CTRom,
        locked_chars: bool = False
):
    manoria_char = config.char_assign_dict[ctenums.RecruitID.CATHEDRAL]\
        .held_char
    proto_char = config.char_assign_dict[ctenums.RecruitID.PROTO_DOME]\
        .held_char

    assign_pc_to_manoria(ct_rom, manoria_char)
    assign_pc_to_proto_dome(ct_rom, proto_char, locked_chars)
