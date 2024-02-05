"""Module to randomize tech damage based on assigned mp."""
import math
import random
from typing import Callable, Dict, Union

import ctstrings
import cttechtypes as ctt
import techdb


def modify_all_single_techs(tech_db: techdb.TechDB):
    """
    Scale every single tech in the tech_db.  Shuffle existing MPs.
    This function relies on vanilla tech names to identify techs that need
    duplicated effects.
    """

    effects: dict[int, ctt.PCTechEffectHeader] = {}
    orig_mps: dict[int, int] = {}
    duplicate_version_dict: dict[int, int] = {}

    control_len, eff_len = 11, 12

    dup_names_effect_dict: dict[str, int] = {
        "Confuse": 0x3C,
        "Triple Kick": 0x3D,
        "Slurp Cut": 0x40
    }

    # Loop through all single techs and collect the damage dealing effect headers
    for tech_id in range(1, 1+7*8):
        tech = tech_db.get_tech(tech_id)
        name_b = tech['name']
        name = str(ctstrings.CTNameString(name_b))

        effect_b = bytearray(tech['effects'][0])
        effect = ctt.PCTechEffectHeader(effect_b)

        good_types = (ctt.EffectType.DAMAGE, ctt.EffectType.MULTIHIT)
        good_formulas = (ctt.DamageFormula.MAGIC, ctt.DamageFormula.PC_AYLA,
                         ctt.DamageFormula.PC_MELEE, ctt.DamageFormula.MISSING_HP)

        if effect.effect_type in good_types:
            formula = effect.damage_formula_id
            if formula in good_formulas:
                effects[tech_id] = effect
                orig_mps[tech_id] = tech_db.mps[tech_id]

                # If the header is one that uses a combo-specific version, add the version
                # to tech_db and record the correspondence of tech_id -> combo effect id
                if name in dup_names_effect_dict:
                    eff_id = dup_names_effect_dict[name]
                    copy_eff = tech_db.effects[eff_id*eff_len:(eff_id+1)*eff_len]
                    tech_db.effects.extend(copy_eff)
                    duplicate_version_dict[tech_id] = len(tech_db.effects)//eff_len - 1
                    tech_db.mps.append(tech_db.mps[tech_id])

    # Shuffle the MP values
    new_mp_vals = list(orig_mps.values())
    random.shuffle(new_mp_vals)
    new_mps = dict(zip(orig_mps.keys(), new_mp_vals))

    # Scale the effects.  Also scale the duplicate if one exists
    for tech_id, effect in effects.items():
        orig_mp = orig_mps[tech_id]
        new_mp = new_mps[tech_id]

        modify_effect_header(effect, orig_mp, new_mp)
        if tech_id in duplicate_version_dict:
            power = effect.power
            copy_ind = duplicate_version_dict[tech_id]
            power_byte = copy_ind*eff_len + 9
            tech_db.effects[power_byte] = power
            tech_db.mps[copy_ind] = new_mp

    # Write the effects back (duplicates already written)
    for tech_id, effect in effects.items():
        st = tech_id*tech_db.effect_size
        end = st + tech_db.effect_size
        tech_db.effects[st:end] = effect
        tech_db.mps[tech_id] = new_mps[tech_id]

    # Loop through all combo techs
    for tech_id in range(1+7*8, tech_db.num_techs):
        tech = tech_db.get_tech(tech_id)

        # Look for techs that need duplication in menu mp list.
        # An alternate strategy would be to build a correspondence
        # (pc_id, combo_tech_effect_id) -> replacement_effect_id and this
        # might be required if we allow further randomization (e.g. charm, life2)
        for duplicate_id in duplicate_version_dict:
            # If found, find the pc-index and replace with the duplicate header.
            if duplicate_id in tech['mmp']:
                repl_id = duplicate_version_dict[duplicate_id]
                repl_pc_id = (duplicate_id-1)//8
                eff_ind = tech['bat_grp'].index(repl_pc_id)
                control_ind = tech_id*control_len + 5 + eff_ind
                # print(f"{tech_db.controls[control_ind]:02X}")
                tech_db.controls[control_ind] = repl_id
                # print(f"{tech_db.controls[control_ind]:02X}")

    # input()

def modify_effect_header(
        effect_header: ctt.PCTechEffectHeader,
        orig_mp: int,
        new_mp: int
):
    """
    Modify the effect header based on its damage formula, original mp and new mp.
    """

    # Sketchy math was performed to come up with these.
    scale_dict: Dict[ctt.DamageFormula, Callable[[int], Union[int, float]]] = {
        ctt.DamageFormula.MAGIC: lambda mp: 1.88*mp+4.34,
        ctt.DamageFormula.PC_MELEE: lambda mp: math.sqrt(55.6*mp + 65.8),
        ctt.DamageFormula.PC_AYLA: lambda mp: math.sqrt(62.6*mp + 134),
        ctt.DamageFormula.MISSING_HP: lambda mp: mp
    }

    formula_type = effect_header.damage_formula_id
    if formula_type not in scale_dict:
        return

    scale_function = scale_dict[formula_type]
    scale_factor = scale_function(new_mp)/scale_function(orig_mp)
    effect_header.power = round(scale_factor*effect_header.power)
