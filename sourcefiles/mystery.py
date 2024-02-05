from __future__ import annotations
import copy
import functools
from typing import Any, Dict, List

import random
import randosettings as rset


def random_weighted_choice_from_dict(choice_dict: Dict[Any, int]):
    '''Make a random choice from dict keys given weights in dict values.'''
    keys, weights = zip(*choice_dict.items())
    return random.choices(keys, weights, k=1)[0]


def generate_mystery_settings(base_settings: rset.Settings) -> rset.Settings:
    '''
    Use the mystery settings in base_settings to generate a new settings
    object with random flags.
    '''
    if rset.GameFlags.MYSTERY not in base_settings.gameflags:
        return base_settings

    GF = rset.GameFlags
    ret_settings = copy.deepcopy(base_settings)

    weighted_choice = random_weighted_choice_from_dict
    ms = base_settings.mystery_settings

    ret_settings.game_mode = weighted_choice(ms.game_mode_freqs)
    ret_settings.item_difficulty = weighted_choice(ms.item_difficulty_freqs)
    ret_settings.enemy_difficulty = weighted_choice(ms.enemy_difficulty_freqs)
    ret_settings.techorder = weighted_choice(ms.tech_order_freqs)
    ret_settings.shopprices = weighted_choice(ms.shop_price_freqs)

    # Order is important in that some flags block off others.
    # Really, once game mode is determined, it's just chronosanity that
    # blocks off boss scaling.
    mystery_flags = list(ms.flag_prob_dict.keys())

    extra_flags: List[rset.GameFlags] = [
        flag for flag in GF
        if flag in base_settings.gameflags and flag not in mystery_flags
    ]

    force_disabled_flags = rset.ForcedFlags.get_forced_off(ret_settings.game_mode)
    force_enabled_flags = rset.ForcedFlags.get_forced_on(ret_settings.game_mode)
    for flag in extra_flags:
        force_disabled_flags |= rset.ForcedFlags.get_forced_off(flag)
        force_enabled_flags |= rset.ForcedFlags.get_forced_on(flag)

    # Check that we don't have any conflicts here.
    assert (force_disabled_flags & force_enabled_flags) == GF(0)

    ret_flags = GF(0)
    for flag in mystery_flags:
        if flag in force_disabled_flags:
            added_flag = GF(0)
        elif flag in force_enabled_flags:
            added_flag = flag
        elif flag in ms.flag_prob_dict:
            prob = ms.flag_prob_dict[flag]
            if random.random() < prob:
                added_flag = flag
            else:
                added_flag = GF(0)
        else:
            raise ValueError('Error: ' + str(flag))

        if added_flag == flag:
            force_disabled_flags |= rset.ForcedFlags.get_forced_off(flag)
            force_enabled_flags |= rset.ForcedFlags.get_forced_on(flag)
            ret_flags |= flag

    # Switching from lits[GF] to just GF
    extra_flags_obj = functools.reduce(
        lambda x, y: x | y,
        extra_flags,
        GF(0)
    )

    # Note that GF.MYSTERY is in extra flags
    ret_flags |= extra_flags_obj
    ret_settings.gameflags = ret_flags

    return ret_settings
