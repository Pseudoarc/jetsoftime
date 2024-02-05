'''
Module for turning text expressions into objective choices.
'''
from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Tuple

import bossrandotypes as rotypes
import objectivetypes
from characters import pcrecruit
from common import distribution
import ctenums

import randosettings as rset


class InvalidNameException(Exception):
    pass


class WeightException(Exception):
    pass

# Mapping of objective hint aliases mapped to objective hint strings
# NOTE: this is ordered (python>=3.5) with more common random categories at the top
_objective_hint_aliases: Dict[str, str] = {
    'Random': '65:quest_gated, 30:boss_nogo, 15:recruit_gated',
    'Random Gated Quest': 'quest_gated',
    'Random Hard Quest': 'quest_late',
    'Random Go Mode Quest': 'quest_go',
    'Random Gated Character Recruit': 'recruit_gated',
    'Random Boss (Includes Go Mode Dungeons)': 'boss_any',
    'Random Boss from Go Mode Dungeon': 'boss_go',
    'Random Boss (No Go Mode Dungeons)': 'boss_nogo',
    'Recruit 3 Characters (Total 5)': 'recruit_3',
    'Recruit 4 Characters (Total 6)': 'recruit_4',
    'Recruit 5 Characters (Total 7)': 'recruit_5',
    'Collect 10 of 20 Fragments': 'collect_10_fragments_20',
    'Collect 10 of 30 Fragments': 'collect_10_fragments_30',
    'Collect 3 Rocks': 'collect_3_rocks',
    'Collect 4 Rocks': 'collect_4_rocks',
    'Collect 5 Rocks': 'collect_5_rocks',
    'Forge the Masamune': 'quest_forge',
    'Charge the Moonstone': 'quest_moonstone',
    'Trade the Jerky Away': 'quest_jerky',
    'Defeat the Arris Dome Boss': 'quest_arris',
    "Visit Cyrus's Grave with Frog": 'quest_cyrus',
    "Defeat the Boss of Death's Peak": 'quest_deathpeak',
    'Defeat the Boss of Denadoro Mountains': 'quest_denadoro',
    'Gain Epoch Flight': 'quest_epoch',
    'Defeat the Boss of the Factory Ruins': 'quest_factory',
    'Defeat the Boss of the Geno Dome': 'quest_geno',
    "Defeat the Boss of the Giant's Claw": 'quest_claw',
    "Defeat the Boss of Heckran's Cave": 'quest_heckran',
    "Defeat the Boss of the King's Trial": 'quest_shard',
    'Defeat the Boss of Manoria Cathedral': 'quest_cathedral',
    'Defeat the Boss of Mount Woe': 'quest_woe',
    'Defeat the Boss of the Pendant Trial': 'quest_pendant',
    'Defeat the Boss of the Reptite Lair': 'quest_reptite',
    'Defeat the Boss of the Sun Palace': 'quest_sunpalace',
    'Defeat the Boss of the Sunken Desert': 'quest_desert',
    'Defeat the Boss in the Zeal Throneroom': 'quest_zealthrone',
    'Defeat the Boss of Zenan Bridge': 'quest_zenan',
    'Defeat the Black Tyrano': 'quest_blacktyrano',
    'Defeat the Tyrano Lair Midboss': 'quest_tyranomid',
    "Defeat the Boss in Flea's Spot": 'quest_flea',
    "Defeat the Boss in Slash's Spot": 'quest_slash',
    "Defeat Magus in Magus's Castle": 'quest_magus',
    'Defeat the Boss in the GigaMutant Spot': 'quest_omengiga',
    'Defeat the Boss in the TerraMutant Spot': 'quest_omenterra',
    'Defeat the Boss in the ElderSpawn Spot': 'quest_omenelder',
    'Defeat the Boss in the Twin Golem Spot': 'quest_twinboss',
    'Beat Johnny in a Race': 'quest_johnny',
    'Bet on a Fair Race and Win': 'quest_fairrace',
    'Play the Fair Drinking Game': 'quest_soda',
    'Defeat AtroposXR': 'boss_atropos',
    'Defeat DaltonPlus': 'boss_dalton',
    'Defeat DragonTank': 'boss_dragontank',
    'Defeat ElderSpawn': 'boss_elderspawn',
    'Defeat Flea': 'boss_flea',
    'Defeat Flea Plus': 'boss_fleaplus',
    'Defeat Giga Gaia': 'boss_gigagaia',
    'Defeat GigaMutant': 'boss_gigamutant',
    'Defeat Golem': 'boss_golem',
    'Defeat Golem Boss': 'boss_golemboss',
    'Defeat Guardian': 'boss_guardian',
    'Defeat Heckran': 'boss_heckran',
    'Defeat LavosSpawn': 'boss_lavosspawn',
    'Defeat Magus (North Cape)': 'boss_magusnc',
    'Defeat Masamune': 'boss_masamune',
    'Defeat Mother Brain': 'boss_motherbrain',
    'Defeat Mud Imp': 'boss_mudimp',
    'Defeat Nizbel': 'boss_nizbel',
    'Defeat Nizbel II': 'boss_nizbel2',
    'Defeat R-Series': 'boss_rseries',
    'Defeat Retinite': 'boss_retinite',
    'Defeat RustTyrano': 'boss_rusttyrano',
    'Defeat Slash': 'boss_slash',
    'Defeat Son of Sun': 'boss_sonofsun',
    'Defeat Super Slash': 'boss_superslash',
    'Defeat TerraMutant': 'boss_terramutant',
    # Skip twinboss b/c it's in quests
    'Defeat Yakra': 'boss_yakra',
    'Defeat Yakra XIII': 'boss_yakraxiii',
    'Defeat Zombor': 'boss_zombor'
}


def get_forced_bosses(hint: str) -> list[rotypes.BossID]:
    hint = ''.join(hint.split())
    parts = hint.split(',')

    boss_list = []
    for part in parts:
        if ':' in part:
            part = part.split(':')[1]

        items = part.split('_')
        p_type = items[0]

        if p_type != 'boss':
            continue

        boss_name = items[1]
        try:
            boss = parse_boss_name(boss_name)
            boss_list.append(boss)
        except InvalidNameException:  # 'go', 'nogo', etc
            continue

    return boss_list


def get_objective_hint_aliases() -> OrderedDict[str, str]:
    '''Ordered objective hint aliases mapped to objective strings.'''
    # dicts maintain definition order in python>=3.5 but coerce to ordered
    # for consistency with django web app, and also as means to make a copy
    # instead of passing _objective_hint_aliases as reference
    return OrderedDict(_objective_hint_aliases.items())


def normalize_objectives_from_hints(hints: List[str]) -> List[str]:
    '''Normalize all hints into objectives strings.

    This converts hints specified with a simple objective preset string into
    a parseable objective string. The simple objective presets are an option
    for specifiying objectives in the CLI, TK GUI and web GUI, as an alternative
    to using the native objective hint string format.
    '''
    return [_objective_hint_aliases.get(hint, hint) for hint in hints]


def parse_boss_name(name: str):
    '''
    One day we can go crazy and do some partial string matching.  Today is
    not that day.
    '''
    if name in ('atropos', 'atroposxr'):
        return rotypes.BossID.ATROPOS_XR
    if name in ('dalton', 'daltonplus', 'dalton+'):
        return rotypes.BossID.DALTON_PLUS
    if name in ('dragontank', 'dtank'):
        return rotypes.BossID.DRAGON_TANK
    if name in ('elderspawn', 'elder'):
        return rotypes.BossID.ELDER_SPAWN
    if name == 'flea':
        return rotypes.BossID.FLEA
    if name in ('fleaplus', 'flea+'):
        return rotypes.BossID.FLEA_PLUS
    if name in ('gigagaia', 'gg'):
        return rotypes.BossID.GIGA_GAIA
    if name == 'gigamutant':
        return rotypes.BossID.GIGA_MUTANT
    if name == 'golem':
        return rotypes.BossID.GOLEM
    if name in ('bossgolem', 'golemboss'):
        return rotypes.BossID.GOLEM_BOSS
    if name == 'guardian':
        return rotypes.BossID.GUARDIAN
    if name == 'heckran':
        return rotypes.BossID.HECKRAN
    if name == 'lavosspawn':
        return rotypes.BossID.LAVOS_SPAWN
    if name in ('magusnc', 'ncmagus'):
        return rotypes.BossID.MAGUS_NORTH_CAPE
    if name in ('masamune', 'masa&mune'):
        return rotypes.BossID.MASA_MUNE
    if name == 'megamutant':
        return rotypes.BossID.MEGA_MUTANT
    if name == 'motherbrain':
        return rotypes.BossID.MOTHER_BRAIN
    if name == 'mudimp':
        return rotypes.BossID.MUD_IMP
    if name == 'nizbel':
        return rotypes.BossID.NIZBEL
    if name in ('nizbel2', 'nizbelii'):
        return rotypes.BossID.NIZBEL_2
    if name == 'rseries':
        return rotypes.BossID.R_SERIES
    if name == 'retinite':
        return rotypes.BossID.RETINITE
    if name in ('rusty', 'rusttyrano'):
        return rotypes.BossID.RUST_TYRANO
    if name == 'slash':
        return rotypes.BossID.SLASH_SWORD
    if name in ('sos', 'sonofsun'):
        return rotypes.BossID.SON_OF_SUN
    if name == 'superslash':
        return rotypes.BossID.SUPER_SLASH
    if name == 'terramutant':
        return rotypes.BossID.TERRA_MUTANT
    if name == 'twinboss':
        return rotypes.BossID.TWIN_BOSS
    if name == 'yakra':
        return rotypes.BossID.YAKRA
    if name in ('yakraxiii', 'yakra13'):
        return rotypes.BossID.YAKRA_XIII
    if name == 'zombor':
        return rotypes.BossID.ZOMBOR

    raise InvalidNameException(f"Invalid boss: {name}")


def parse_quest_name(name: str):
    '''Turn a quest name into a QuestID.'''
    QID = objectivetypes.QuestID

    if name in ('repairmasamune', 'masamune', 'masa', 'forge'):
        return QID.FORGE_MASAMUNE
    if name in ('chargemoon', 'moon', 'moonstone'):
        return QID.CHARGE_MOONSTONE
    if name == "arris":
        return QID.CLEAR_ARRIS_DOME
    if name == 'jerky':
        return QID.GIVE_JERKY_TO_MAYOR
    if name in ('deathpeak', 'death'):
        return QID.CLEAR_DEATH_PEAK
    if name == 'denadoro':
        return QID.CLEAR_DENADORO
    if name in ('epoch', 'flight', 'epochflight'):
        return QID.GAIN_EPOCH_FLIGHT
    if name in ('factory', 'factoryruins'):
        return QID.CLEAR_FACTORY_RUINS
    if name in ('geno', 'genodome'):
        return QID.CLEAR_GENO_DOME
    if name in ('claw', 'giantsclaw'):
        return QID.CLEAR_GIANTS_CLAW
    if name in ('heckran', 'heckranscave', 'heckrancave'):
        return QID.CLEAR_HECKRANS_CAVE
    if name in ('kingstrial', 'shard', 'shardtrial', 'prismshard'):
        return QID.CLEAR_KINGS_TRIAL
    if name in ('cathedral', 'cath', 'manoria'):
        return QID.CLEAR_CATHEDRAL
    if name in ('woe', 'mtwoe'):
        return QID.CLEAR_MT_WOE
    if name in ('ocean', 'oceanpalace'):
        return QID.CLEAR_OCEAN_PALACE
    if name in ('ozzie', 'fort', 'ozziefort', 'ozziesfort'):
        return QID.CLEAR_OZZIES_FORT
    if name in ('pendant', 'pendanttrial'):
        return QID.CLEAR_PENDANT_TRIAL
    if name in ('reptite', 'reptitelair'):
        return QID.CLEAR_REPTITE_LAIR
    if name in ('sunpalace', 'sun'):
        return QID.CLEAR_SUN_PALACE
    if name in ('desert', 'sunkendesert'):
        return QID.CLEAR_SUNKEN_DESERT
    if name in ('zealthrone', 'zealpalace', 'golemspot'):
        return QID.CLEAR_ZEAL_PALACE
    if name in ('zenan', 'bridge', 'zenanbridge'):
        return QID.CLEAR_ZENAN_BRIDGE
    if name in ('tyrano', 'blacktyrano', 'azala'):
        return QID.CLEAR_BLACK_TYRANO
    if name in ('tyranomid', 'nizbel2spot'):
        return QID.CLEAR_TYRANO_MIDBOSS
    if name in ('magus', 'maguscastle'):
        return QID.CLEAR_MAGUS_CASTLE
    if name in ('omengiga', 'gigamutant', 'gigaspot'):
        return QID.CLEAR_OMEN_GIGASPOT
    if name in ('omenterra', 'terramutant', 'terraspot'):
        return QID.CLEAR_OMEN_TERRASPOT
    if name in ('flea', 'magusflea'):
        return QID.CLEAR_MAGUS_FLEA_SPOT
    if name in ('slash', 'magusslash'):
        return QID.CLEAR_MAGUS_SLASH_SPOT
    if name in ('omenelder', 'elderspawn', 'elderspot'):
        return QID.CLEAR_OMEN_ELDERSPOT
    if name in ('twinboss', 'twingolem', 'twinspot'):
        return QID.CLEAR_TWINBOSS_SPOT
    if name in ('cyrus', 'nr', 'northernruins'):
        return QID.VISIT_CYRUS_GRAVE
    if name in ('johnny', 'johnnyrace'):
        return QID.DEFEAT_JOHNNY
    if name in ('fairrace', 'fairbet'):
        return QID.WIN_RACE_BET
    if name in ('soda', 'drink'):
        return QID.DRINK_SODA

    raise InvalidNameException(f"Invalid quest: {name}")


_BossDict = Dict[rotypes.BossSpotID, rotypes.BossID]
_RecruitDict = Dict[ctenums.RecruitID, pcrecruit.RecruitSpot]


def get_go_bosses(boss_assign_dict: _BossDict) -> list[rotypes.BossID]:
    BSID = rotypes.BossSpotID
    go_spots = [BSID.BLACK_OMEN_ELDER_SPAWN, BSID.BLACK_OMEN_GIGA_MUTANT,
                BSID.BLACK_OMEN_TERRA_MUTANT, BSID.OCEAN_PALACE_TWIN_GOLEM,
                BSID.ZEAL_PALACE, BSID.DEATH_PEAK, BSID.MAGUS_CASTLE_FLEA,
                BSID.MAGUS_CASTLE_SLASH]

    return [
        boss_id for spot, boss_id in boss_assign_dict.items()
        if spot in go_spots
    ]


def get_objective_keys(obj_str: str, settings: rset.Settings,
                       boss_assign_dict: _BossDict,
                       char_assign_dict: _RecruitDict
                       ) -> list:
    '''
    Turn a part of an objective hint into a list of objective keys.
    '''
    BSID = rotypes.BossSpotID
    BossID = rotypes.BossID

    obj_parts = obj_str.split('_')
    obj_type = obj_parts[0]

    epoch_fail = rset.GameFlags.EPOCH_FAIL in settings.gameflags
    unlocked_skyway = rset.GameFlags.UNLOCKED_SKYGATES in settings.gameflags

    if obj_type == 'boss':
        # At some point, the one-spot BossID was put in the boss_assign_dict
        # instead of BossID.TWIN_BOSS.  We need to undo this here to get the
        # correct keys.
        modified_assign_dict = dict(boss_assign_dict)
        twin_spot = BSID.OCEAN_PALACE_TWIN_GOLEM
        if twin_spot in modified_assign_dict:
            modified_assign_dict[twin_spot] = BossID.TWIN_BOSS

        boss_type = obj_parts[1]
        if boss_type == 'any':
            return list(modified_assign_dict.values())
        if boss_type == 'go':
            return get_go_bosses(modified_assign_dict)
        if boss_type == 'nogo':
            go_bosses = get_go_bosses(modified_assign_dict)
            all_bosses = list(modified_assign_dict.values())
            return [boss_id for boss_id in all_bosses
                    if boss_id not in go_bosses]
        return [parse_boss_name(boss_type)]

    if obj_type == 'quest':
        QID = objectivetypes.QuestID
        quest_type = obj_parts[1]
        if quest_type == 'free':
            return [QID.CLEAR_CATHEDRAL, QID.CLEAR_HECKRANS_CAVE,
                    QID.CLEAR_DENADORO, QID.CLEAR_ZENAN_BRIDGE]
        if quest_type == 'gated':
            gated_quests = [
                QID.CHARGE_MOONSTONE, QID.GIVE_JERKY_TO_MAYOR,
                QID.CLEAR_ARRIS_DOME, QID.GAIN_EPOCH_FLIGHT,
                QID.CLEAR_FACTORY_RUINS, QID.CLEAR_GIANTS_CLAW,
                QID.CLEAR_OZZIES_FORT, QID.CLEAR_TYRANO_MIDBOSS,
                QID.CLEAR_KINGS_TRIAL,
                QID.CLEAR_PENDANT_TRIAL, QID.CLEAR_REPTITE_LAIR,
                QID.CLEAR_SUN_PALACE, QID.CLEAR_SUNKEN_DESERT,
            ]

            # Note that this does not stop someone from naming an impossible
            # quest on purpose.  It just prevents impossible quests from being
            # drawn randomly.
            if epoch_fail:
                gated_quests.remove(QID.GIVE_JERKY_TO_MAYOR)
            if not (epoch_fail and unlocked_skyway):
                gated_quests.remove(QID.GAIN_EPOCH_FLIGHT)

            return gated_quests
        if quest_type == 'late':
            late_quests = [QID.CLEAR_MT_WOE, QID.CLEAR_GENO_DOME,
                           QID.CLEAR_BLACK_TYRANO]
            return late_quests
        if quest_type == 'go':
            go_quests = [QID.CLEAR_ZEAL_PALACE, QID.CLEAR_TWINBOSS_SPOT,
                         QID.CLEAR_DEATH_PEAK,
                         QID.CLEAR_OMEN_GIGASPOT, QID.CLEAR_OMEN_TERRASPOT,
                         QID.CLEAR_OMEN_ELDERSPOT, QID.CLEAR_MAGUS_CASTLE]

            return go_quests
        return [parse_quest_name(quest_type)]

    if obj_type == 'recruit':
        chars = ['crono', 'marle', 'lucca', 'robo', 'frog', 'ayla', 'magus']
        spots = ['castle', 'dactyl', 'proto', 'burrow']
        RID = ctenums.RecruitID
        spot_ids = [RID.CASTLE, RID.DACTYL_NEST, RID.PROTO_DOME,
                    RID.FROGS_BURROW]
        char_choice = obj_parts[1]
        if char_choice == 'any':
            return list(ctenums.CharID)
        if char_choice == 'gated':
            return [
                char_assign_dict[rid].held_char
                for rid in spot_ids
            ]
        if char_choice in chars:
            char_id = ctenums.CharID(chars.index(char_choice))
            return [char_id]
        if char_choice in spots:
            index = spots.index(char_choice)
            return [spot_ids[index]]

        # num_recruits = int(char_choice)
        return ['recruits_' + char_choice]
    if obj_type == 'collect':
        # num_collect = int(obj_parts[1])
        collect_type = obj_parts[2]
        if collect_type == 'rocks':
            return ['_'.join(('rocks', obj_parts[1]))]
        if collect_type == 'fragments':
            # total_fragments = int(obj_parts[3])
            return ['_'.join(('fragments', obj_parts[1], obj_parts[3]))]
        raise InvalidNameException(f"Invalid collect type: {collect_type} ('{obj_str}')")

    raise InvalidNameException(f"Invalid objective type: {obj_type} ('{obj_str}')")


def is_hint_valid(hint: str) -> Tuple[bool, str]:
    '''
    Determine whether the given objective hint has a valid format.
    Returns a tuple of the validity (bool) and an error message (str).
    '''
    if hint == '':
        return True, ''

    fake_settings = rset.Settings()
    boss_assign_dict = rotypes.get_default_boss_assignment()
    char_assign_dict = pcrecruit.get_base_recruit_dict()

    normalized_hint = normalize_objectives_from_hints([hint])[0]

    try:
        dist = parse_hint(normalized_hint, fake_settings, boss_assign_dict, char_assign_dict)
    except InvalidNameException as exc:
        return (False, str(exc))

    if dist.get_total_weight() == 0:
        return (False, 'Empty Hint')

    return True, ''


def parse_hint(
        hint: str, settings: rset.Settings,
        boss_assign_dict: _BossDict,
        char_assign_dict: _RecruitDict
        ) -> distribution.Distribution:
    '''
    Turn an objective hint into a distribution which generates
    '''
    hint = ''.join(hint.lower().split())  # Remove whitespace
    obj_strs = hint.split(',')

    weight_obj_pairs = []

    has_weight = False
    for obj_str in obj_strs:
        if ':' in obj_str:
            has_weight = True
        elif has_weight:
            raise WeightException('Some but not all categories have weights.')

        if has_weight:
            weight_str, obj_str = obj_str.split(':')
            weight = int(weight_str)
        else:
            weight = 1

        # print(f'******* weight = {weight}')
        obj_keys = get_objective_keys(obj_str, settings,
                                      boss_assign_dict, char_assign_dict)
        # print(obj_keys)
        # print('*******')

        weight_obj_pairs.append((weight, obj_keys))

    return distribution.Distribution(*weight_obj_pairs)
