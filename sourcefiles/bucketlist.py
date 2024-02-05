from __future__ import annotations

import dataclasses
import typing

import bossrandotypes as rotypes
from bossrandotypes import BossSpotID as BSID
import bucketfragment

from common import distribution
import ctenums
import ctrom

from eventcommand import EventCommand as EC, Operation as OP, FuncSync as FS
from eventfunction import EventFunction as EF
from maps import locationtypes

import objectivehints as obhint
import objectivetypes as oty
import randoconfig as cfg
import randosettings as rset
import xpscale


class ImpossibleHintException(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class RomFlag:
    address: int = 0
    bit: int = 0


# Many of these are taken from Anguirel's Tracker code.
_boss_spot_flags: dict[BSID, RomFlag] = {
    BSID.ARRIS_DOME: RomFlag(0x7F00EC, 0x01),
    BSID.BLACK_OMEN_ELDER_SPAWN: RomFlag(0x7F01A9, 0x01),
    BSID.BLACK_OMEN_GIGA_MUTANT: RomFlag(0x7F0071, 0x10),
    BSID.BLACK_OMEN_TERRA_MUTANT: RomFlag(0x7F015A, 0x01),
    BSID.DEATH_PEAK: RomFlag(0x7F0064, 0x20),
    # Epoch reborn doesn't have a flag, but it sets 0x7F00D2 = 7 before the
    # cutscene starts.  So we can test any of the 0x07 bits for this one.
    BSID.EPOCH_REBORN: RomFlag(0x7F00D2, 0x2),
    # Actually the flag for activating the power core.
    BSID.FACTORY_RUINS: RomFlag(0x7F0103, 0x40),
    BSID.GENO_DOME: RomFlag(0x7F013B, 0x10),
    BSID.GIANTS_CLAW: RomFlag(0x7F01D2, 0x40),
    BSID.HECKRAN_CAVE: RomFlag(0x7F01A3, 0x08),
    BSID.KINGS_TRIAL: RomFlag(0x7F0050, 0x40),
    BSID.MAGUS_CASTLE_FLEA: RomFlag(0x7F00A3, 0x08),
    BSID.MAGUS_CASTLE_SLASH: RomFlag(0x7F00A3, 0x40),
    BSID.MANORIA_CATHERDAL: RomFlag(0x7F000D, 0x01),
    BSID.MT_WOE: RomFlag(0x7F0100, 0x20),
    BSID.OCEAN_PALACE_TWIN_GOLEM: RomFlag(0x7F0100, 0x80),
    BSID.OZZIES_FORT_FLEA_PLUS: RomFlag(0x7F01A1, 0x04),
    BSID.OZZIES_FORT_SUPER_SLASH: RomFlag(0x7F01A1, 0x08),
    BSID.PRISON_CATWALKS: RomFlag(0x7F0198, 0x08),
    BSID.REPTITE_LAIR: RomFlag(0x7F0105, 0x20),
    BSID.SUN_PALACE: RomFlag(0x7F013A, 0x01),
    BSID.SUNKEN_DESERT: RomFlag(0x7F01AD, 0x04),
    BSID.TYRANO_LAIR_NIZBEL: RomFlag(0x7F00EE, 0x01),
    BSID.ZEAL_PALACE: RomFlag(0x7F0105, 0x80),
    BSID.ZENAN_BRIDGE: RomFlag(0x7F0101, 0x02)
}


_boss_names: dict[rotypes.BossID, str] = {
    rotypes.BossID.ATROPOS_XR: 'AtroposXR',
    rotypes.BossID.DALTON_PLUS: 'DaltonPlus',
    rotypes.BossID.ELDER_SPAWN: 'ElderSpawn',
    rotypes.BossID.FLEA: 'Flea',
    rotypes.BossID.FLEA_PLUS: 'Flea Plus',
    rotypes.BossID.GIGA_MUTANT: 'GigaMutant',
    rotypes.BossID.GOLEM: 'Golem',
    rotypes.BossID.GOLEM_BOSS: 'Golem Boss',
    rotypes.BossID.HECKRAN: 'Heckran',
    rotypes.BossID.LAVOS_SPAWN: 'LavosSpawn',
    rotypes.BossID.MAMMON_M: 'Mammon M',
    rotypes.BossID.MAGUS_NORTH_CAPE: 'Magus (NC)',
    rotypes.BossID.MASA_MUNE: 'Masa&Mune',
    rotypes.BossID.MEGA_MUTANT: 'MegaMutant',
    rotypes.BossID.MUD_IMP: 'Mud Imp',
    rotypes.BossID.NIZBEL: 'Nizbel',
    rotypes.BossID.NIZBEL_2: 'Nizbel II',
    rotypes.BossID.RETINITE: 'Retinite',
    rotypes.BossID.R_SERIES: 'R Series',
    rotypes.BossID.RUST_TYRANO: 'RustTyrano',
    rotypes.BossID.SLASH_SWORD: 'Slash',
    rotypes.BossID.SUPER_SLASH: 'Super Slash',
    rotypes.BossID.SON_OF_SUN: 'Son of Sun',
    rotypes.BossID.TERRA_MUTANT: 'TerraMutant',
    rotypes.BossID.TWIN_BOSS: 'Twin Boss',
    rotypes.BossID.YAKRA: 'Yakra',
    rotypes.BossID.YAKRA_XIII: 'Yakra XIII',
    rotypes.BossID.ZOMBOR: 'Zombor',
    rotypes.BossID.MOTHER_BRAIN: 'Mother Brain',
    rotypes.BossID.DRAGON_TANK: 'Dragon Tank',
    rotypes.BossID.GIGA_GAIA: 'Giga Gaia',
    rotypes.BossID.GUARDIAN: 'Guardian',

    # Midbosses -- Should be unused
    rotypes.BossID.MAGUS: 'Magus',
    rotypes.BossID.BLACK_TYRANO: 'Black Tyrano'
}


def add_objectives_to_config(settings: rset.Settings,
                             config: cfg.RandoConfig):

    if rset.GameFlags.BUCKET_LIST not in settings.gameflags:
        return

    IID = ctenums.ItemID
    objective_pool = [
        IID.UNUSED_1C, IID.UNUSED_1D, IID.UNUSED_1E,
        IID.UNUSED_2A, IID.UNUSED_2B, IID.UNUSED_2C, IID.UNUSED_2D,
        IID.UNUSED_56, IID.UNUSED_57, IID.UNUSED_58, IID.UNUSED_59,
        IID.UNUSED_EA, IID.UNUSED_EB, IID.UNUSED_EC, IID.UNUSED_ED,
        IID.UNUSED_EE, IID.UNUSED_EF, IID.UNUSED_F0, IID.UNUSED_F1
    ]

    # Make the objective count item.
    rem_objs = config.item_db[IID.OBJ_COUNT]
    rem_objs.set_name_from_str('*ObjsRemain')
    rem_objs.set_desc_from_str('Count shows remaining objectives')
    rem_objs.secondary_stats.is_unsellable = True
    rem_objs.secondary_stats.is_key_item = True

    num_objs = settings.bucket_settings.num_objectives
    hints = obhint.normalize_objectives_from_hints(settings.bucket_settings.hints)

    KeyType = typing.Union[oty.QuestID, ctenums.RecruitID,
                           rotypes.BossID, str]

    # Quest Keys
    obj_pool: list[KeyType] = list(oty.QuestID)
    obj_pool.remove(oty.QuestID.DEFEAT_JOHNNY)
    obj_pool.remove(oty.QuestID.WIN_RACE_BET)
    obj_pool.remove(oty.QuestID.GIVE_SEED_TO_DOAN)
    obj_pool.remove(oty.QuestID.GET_ARRIS_FOOD_ITEM)
    obj_pool.remove(oty.QuestID.CLEAR_BLACK_TYRANO)

    # Recruit keys
    obj_pool.extend(list(ctenums.CharID))
    obj_pool.extend([ctenums.RecruitID.CASTLE, ctenums.RecruitID.DACTYL_NEST,
                     ctenums.RecruitID.PROTO_DOME,
                     ctenums.RecruitID.FROGS_BURROW])

    # Boss keys
    avail_bosses = [boss_id for spot_id, boss_id
                    in config.boss_assign_dict.items()]
    obj_pool.extend(avail_bosses)

    # CollectKeys
    obj_pool.extend(['rocks', 'fragments', 'recruits'])

    objectives = []
    used_keys: list[KeyType] = []

    # Pre-set some keys in used_keys to avoid impossible hints
    if not rset.GameFlags.EPOCH_FAIL | rset.GameFlags.UNLOCKED_SKYGATES \
       in settings.gameflags:
        used_keys.append(oty.QuestID.GAIN_EPOCH_FLIGHT)

    if rset.GameFlags.RESTORE_JOHNNY_RACE not in settings.gameflags:
        used_keys.append(oty.QuestID.DEFEAT_JOHNNY)

    default_hint = '50:quest_gated, 30:boss_nogo, 20:recruit_gated'
    for ind in range(len(hints), num_objs):
        hints.append(default_hint)

    for ind in range(num_objs):
        hint = hints[ind]
        if hint == '':
            hint = default_hint
        dist = obhint.parse_hint(hint, settings,
                                 config.boss_assign_dict,
                                 config.char_assign_dict)

        # Remove already-chosen objectives from the distribution
        # If it's empty after cleaning, try the default hint.
        dist = clean_distribution(dist, used_keys)
        if dist.get_total_weight() == 0:
            dist = obhint.parse_hint(default_hint, settings,
                                     config.boss_assign_dict,
                                     config.char_assign_dict)
            dist = clean_distribution(dist, used_keys)

            if dist.get_total_weight() == 0:
                raise ImpossibleHintException

        chosen_key = dist.get_random_item()

        objective = get_obj_from_key(chosen_key, settings, config,
                                     objective_pool[ind])
        objectives.append(objective)

        if isinstance(chosen_key, str):
            chosen_key = chosen_key.split('_')[0]
        used_keys.append(chosen_key)

        if isinstance(chosen_key, ctenums.CharID):
            used_keys.append('recruits')

    for objective in objectives:
        objective.update_item_db(config.item_db)
        if isinstance(objective, oty.CollectNFragmentsObjective):
            bucketfragment.write_fragments_to_config(
                objective.fragments_needed+objective.extra_fragments,
                settings, config
            )

    config.objectives = objectives


def clean_distribution(dist: distribution.Distribution,
                       used_keys: list):
    '''Remove used keys from a distribution.'''
    wo_pairs = dist.get_weight_object_pairs()
    new_wo_pairs = []
    for weight, items in wo_pairs:
        for key in used_keys:
            if key in ('fragments', 'rocks', 'recruits'):
                str_keys = [x for x in items if isinstance(x, str)]
                match_keys = [x for x in str_keys if key in x]
                for key in match_keys:
                    items.remove(key)
            elif key in items:
                items.remove(key)
        if items:
            new_wo_pairs.append((weight, items))

    dist = distribution.Distribution(*new_wo_pairs)
    return dist


def get_obj_from_key(key, settings: rset.Settings,
                     config: cfg.RandoConfig,
                     item_id: ctenums.ItemID):
    if isinstance(key, rotypes.BossID):
        return oty.get_defeat_boss_obj(key, settings,
                                       config.boss_assign_dict, item_id)
    if isinstance(key, oty.QuestID):
        return oty.get_quest_obj(key, settings, item_id)
    if isinstance(key, ctenums.RecruitID):
        return oty.get_recruit_spot_obj(key, settings,
                                        config.char_assign_dict, item_id)
    if isinstance(key, ctenums.CharID):
        return oty.get_recruit_char_obj(key, settings,
                                        config.char_assign_dict, item_id)
    if isinstance(key, str):
        parts = key.split('_')
        if parts[0] == 'rocks':
            num_rocks = int(parts[1])
            return oty.ObtainNRocksObjective(num_rocks, 0x7F003D,
                                             config.treasure_assign_dict, item_id)
        if parts[0] == 'fragments':
            num_fragments = int(parts[1])
            total_fragments = int(parts[2])
            total_fragments = max(num_fragments, total_fragments)

            return oty.CollectNFragmentsObjective(
                num_fragments, total_fragments-num_fragments, item_id
            )
        if parts[0] == 'recruits':
            num_recruits = int(parts[1])
            num_recruits = min(num_recruits, 5)
            num_recruits = max(1, num_recruits)
            return oty.RecruitNCharactersObjective(num_recruits, 0x7F003E,
                                                   item_id)

    raise ValueError('Could not handle: ' + str(key))


def modify_bucket_activation(
        ct_rom: ctrom.CTRom,
        num_objectives_needed: int,
        objective_count_addr: int
        ):
    '''
    Change to bucket to work when the objectives are complete or under the
    usual circumstances.
    '''

    script = ct_rom.script_manager.get_script(
        ctenums.LocID.END_OF_TIME
    )

    bucket_obj_id = 9
    bucket_func_id = 1

    # Function for the normal bucket activation.  Notably, this does not have
    # a trailing return.  So we'll just append the bucket gauntlet function
    # to the end.
    bucket_func = script.get_function(9, 1)

    dec_str = \
        'Warp to bucket boss gauntlet?{line break}'\
        '   Yes{line break}'\
        '   No{null}'
    dec_str_id = script.add_py_string(dec_str)

    # Detect no value on time gauge for apoc
    jump_cmd = EC.if_mem_op_value(0x7F022E, OP.NOT_EQUALS, 0, 1, 0)
    warp_cmd = EC.change_location(0x1A6, 0x8, 0x12, 0, 1)
    warp_cmd.command = 0xDD

    bucket_gauntlet_func = (
        EF()
        # If you already have 1999 access, then forget about this.
        .add_if(jump_cmd, EF().add(EC.return_cmd()))
        .add_if(
            EC.if_mem_op_value(objective_count_addr, OP.LESS_THAN,
                               num_objectives_needed, 1, 0),
            EF().add(EC.return_cmd())
        )
        .add(EC.decision_box(dec_str_id, 1, 2))
        .add_if(
            EC.if_result_equals(1, 0),
            (
                EF()
                .add(EC.assign_val_to_mem(1, 0x7E288B, 2))
                .add(warp_cmd)
                .add(EC.generic_command(0xEB, 0, 0))
                .add(EC.generic_command(0xEB, 0xFF, 0xFF))
                .add(EC.generic_command(0xEA, 0x34))  # song, needed?
                .add(EC.generic_command(0xFF, 0x83))
            )
        )
    )

    bucket_func.append(bucket_gauntlet_func)
    script.set_function(bucket_obj_id, bucket_func_id, bucket_func)

    # Now fix the Zeal2 location
    script = ct_rom.script_manager.get_script(
        ctenums.LocID.BLACK_OMEN_CELESTIAL_GATE
    )

    if_mammon_m_defeated = EC.if_mem_op_value(0x7F01A8, OP.BITWISE_AND_NONZERO,
                                              0x80, 1, 0)
    ins_func = (
        EF()
        .add_if(
            if_mammon_m_defeated,
            EF()
            .set_label('jump')
            .add(EC.jump_forward(1))
        )
    )

    offset = ins_func.labels['jump']

    ins_pos = script.find_exact_command(EC.return_cmd()) + 1
    script.insert_commands(ins_func.get_bytearray(), ins_pos)

    jump_target = script.find_exact_command(if_mammon_m_defeated,
                                            ins_pos+len(ins_func))
    jump_offset = ins_pos + offset + 1
    script.data[jump_offset] = jump_target-jump_offset


def disable_non_bucket_go(ct_rom: ctrom.CTRom):
    '''
    Add blocks/warps out when the last boss in Ocean Palace/Omen are defeated.
    '''

    # Releveant maps are 0x19F Ocean Palace Throne and 0x1C2 Omega Defense

    # Ocean Palace: Have the Nu in the final hallway not move.
    script = ct_rom.script_manager.get_script(
        ctenums.LocID.OCEAN_PALACE_THRONE)

    nu_obj = 0x17
    start = script.get_function_start(nu_obj, 1)
    end = script.get_function_end(nu_obj, 1)

    _, cmd = script.find_command([0xBB], start, end)
    nu_str_ind = cmd.args[-1]

    new_nu_fn = (
        EF()
        .add(EC.generic_command(0x17))  # facing down
        .add(EC.generic_command(0xAA, 1))  # anim 1
        .add(EC.generic_command(0xAA, 5))  # anim 5
        .add(EC.pause(0.25))
        .add(EC.generic_command(0xAC, 0x0F))  # static anim 0xF
        .add(EC.auto_text_box(nu_str_ind))
        .add(EC.generic_command(0xAE))  # reset anim
        .add(EC.return_cmd())
    )

    script.set_function(nu_obj, 1, new_nu_fn)

    # Black Omen:  Stop the central panel from being overwritten.
    # Copy tiles flags are weird, so just copying the command

    loc_id = ctenums.LocID.BLACK_OMEN_OMEGA_DEFENSE
    script = ct_rom.script_manager.get_script(loc_id)

    copy_cmd = EC.generic_command(0xE4, 0, 0x1C, 1, 0x1F, 7, 1, 0x3B)

    pos = script.find_exact_command(copy_cmd)
    script.delete_commands(pos, 1)

    copy_cmd.command = 0xE5  # Switch to vblank version
    pos = script.find_exact_command(copy_cmd, script.get_function_start(8, 1))
    script.delete_commands(pos, 1)

    # Delete the exit from to the throne.
    all_exits = locationtypes.LocExits.from_rom(ct_rom.rom_data)
    loc_exits = all_exits.get_exits(loc_id)

    for ind, loc_exit in enumerate(loc_exits):
        if loc_exit.dest_loc == 0x1C3:
            all_exits.delete_exit(loc_id, ind)
            break

    all_exits.write_to_fsrom(ct_rom.rom_data)


def write_objectives_to_ctrom(
        ct_rom: ctrom.CTRom,
        settings: rset.Settings,
        config: cfg.RandoConfig
        ):

    if rset.GameFlags.BUCKET_LIST not in settings.gameflags:
        return

    bucket_settings = settings.bucket_settings
    modify_bucket_activation(
        ct_rom, bucket_settings.num_objectives_needed, 0x7F003F
    )

    script = ct_rom.script_manager.get_script(ctenums.LocID.LOAD_SCREEN)
    obj_id = script.append_empty_object()

    num_objs = len(config.objectives)
    needed_objs = settings.bucket_settings.num_objectives_needed

    objs = config.objectives
    add_objs_fn = EF()
    for ind in range(needed_objs):
        add_objs_fn.add(EC.add_item(ctenums.ItemID.OBJ_COUNT))

    for obj in objs:
        item_id = obj.item_id
        if item_id is None:
            raise ValueError("No item assigned to objective \'{obj.name}\'")
        add_objs_fn.add(EC.add_item(int(item_id)))

    script.set_function(
        obj_id, 0,
        EF().add(EC.return_cmd()).add(EC.end_cmd())
    )

    script.set_function(obj_id, 1, add_objs_fn)

    pos = script.get_object_start(0)
    while True:
        pos, cmd = script.find_command([0xC8], pos)

        if cmd.args[0] in range(0xC0, 0xC7):
            break
        pos += len(cmd)

    script.insert_commands(
        EC.call_obj_function(obj_id, 1, 5, FS.HALT).to_bytearray(), pos
    )

    script = ct_rom.script_manager.get_script(ctenums.LocID.TELEPOD_EXHIBIT)
    obj_id = script.append_empty_object()

    obj_str = ''
    for ind, obj in enumerate(objs):
        obj_str += f'{ind+1}) {obj.desc}'

        if ind == len(objs)-1:
            obj_str += '{null}'
        elif (ind - 2) % 4 == 0:
            obj_str += '{full break}'
        else:
            obj_str += '{linebreak+0}'

    if num_objs == needed_objs:
        count_str = 'All.{linebreak+0}'
    else:
        count_str = f'{needed_objs} of {num_objs}.{{linebreak+0}}'

    if settings.bucket_settings.objectives_win:
        reward_str = 'Win Game'
    else:
        reward_str = 'Bucket List'

    warning_str = ''
    if settings.bucket_settings.disable_other_go_modes:
        warning_str = 'Other go modes are disabled!{linebreak+0}'
    else:
        warning_str = 'Other go modes are enabled!{linebreak+0}'

    obj_str = f'{reward_str}: Complete {count_str} {obj_str}'
    dec_str = \
        warning_str + \
        'Review Objectives in the Item Menu!{line break}'\
        '   See the list again{line break}'\
        '   Close this message{null}'

    str_id = script.add_py_string(obj_str)
    dec_id = script.add_py_string(dec_str)

    dec_st = 2

    script.set_function(
        obj_id, 0,
        (
            EF()
            .add(EC.return_cmd())
            .add_if(
                EC.if_storyline_counter_lt(0x0C, 0),
                EF()
                # .append(add_objs_fn)
                .set_label('text')
                .add(EC.auto_text_box(str_id))
                .add(EC.decision_box(dec_id, dec_st, dec_st+1, 'auto'))
                .add_if(
                    EC.if_result_equals(dec_st, 0),
                    EF().jump_to_label(EC.jump_back(0), 'text')
                )
            )
            .add(EC.end_cmd())
        )
    )

    objectives = config.objectives
    for objective in objectives:
        objective.add_objective_check_to_ctrom(
            ct_rom, settings.bucket_settings, 0x7F003F)

    xpscale.double_xp(ct_rom, 0x7E287E)

    if bucket_settings.disable_other_go_modes:
        disable_non_bucket_go(ct_rom)
