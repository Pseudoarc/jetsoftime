from __future__ import annotations
from enum import Enum, auto
import typing
from typing import Optional

from common.random import RNGType
import enemystats
from common.random import RNGType
from ctenums import ItemID, EnemyID

import randoconfig as cfg
import randosettings as rset

from treasures import treasuredata as td

# We do not want to be reconstructing these lists every time that
# get_distributions is called.  They are _named to avoid importing with
# an import *.

# It is possible that we can link directly to the identically named lists
# in treasuredata, but for safety we're going to copy them.
_low_gear = td.get_item_list(td.ItemTier.LOW_GEAR)
_low_cons = td.get_item_list(td.ItemTier.LOW_CONSUMABLE)
_pass_gear = td.get_item_list(td.ItemTier.PASSABLE_GEAR)
_pass_cons = td.get_item_list(td.ItemTier.PASSABLE_CONSUMABLE)
_mid_gear = td.get_item_list(td.ItemTier.MID_GEAR)
_mid_cons = td.get_item_list(td.ItemTier.MID_CONSUMABLE)
_good_gear = td.get_item_list(td.ItemTier.GOOD_GEAR)
_good_cons = td.get_item_list(td.ItemTier.GOOD_CONSUMABLE)
_high_gear = td.get_item_list(td.ItemTier.HIGH_GEAR)
_high_cons = td.get_item_list(td.ItemTier.HIGH_CONSUMABLE)
_awe_gear = td.get_item_list(td.ItemTier.AWESOME_GEAR)
_awe_cons = td.get_item_list(td.ItemTier.AWESOME_CONSUMABLE)


class RewardGroup(Enum):
    COMMON_ENEMY = auto()
    UNCOMMON_ENEMY = auto()
    RARE_ENEMY = auto()
    RAREST_ENEMY = auto()
    EARLY_BOSS = auto()
    MIDGAME_BOSS = auto()
    LATE_BOSS = auto()


# The existing item distribution all works as follows:
#   1) Choose a drop from some distribution
#   2) Either use the drop as the charm or choose a charm from another dist
#   3) Eliminate the drop with some probability
# This gives rise to three parameters: drop_dist, charm_dist, and drop_rate.
# Treasure assignment then works as follows:
#   1) Get a drop from drop_dist
#   2) if charm_dist is None, charm=drop else get charm from charm_dist
#   3) Set drop to 0 (ItemID.NONE) with probability 1-drop_rate
# So get_distributions returns drop_dist, charm_dist, drop_rate
def get_distributions(
        enemy_group: RewardGroup,
        difficulty: rset.Difficulty
) -> typing.Tuple[td.TreasureDist, Optional[td.TreasureDist], float]:

    if enemy_group == RewardGroup.COMMON_ENEMY:
        if difficulty in (rset.Difficulty.NORMAL, rset.Difficulty.EASY):
            drop_dist = td.TreasureDist(
                (2, _pass_gear + _low_gear),
                (8, _low_cons + _pass_cons),
            )
            charm_dist = None
            drop_rate = 0.5
        elif difficulty == rset.Difficulty.HARD:
            drop_dist = td.TreasureDist((1, [ItemID.NONE]))
            charm_dist = drop_dist
            drop_rate = 0
        else:
            raise ValueError(f"Invalid Difficulty: {difficulty}")
    elif enemy_group == RewardGroup.UNCOMMON_ENEMY:
        if difficulty in (rset.Difficulty.NORMAL, rset.Difficulty.EASY):
            drop_dist = td.TreasureDist(
                (2, _mid_gear+_good_gear),
                (8, _mid_cons+_good_cons)
            )

            charm_dist = None
            drop_rate = 0.4
        elif difficulty == rset.Difficulty.HARD:
            drop_dist = td.TreasureDist((1, [ItemID.NONE]))
            charm_dist = td.TreasureDist(
                (1, _mid_cons+_good_cons)
            )
            drop_rate = 0
        else:
            exit()
    elif enemy_group == RewardGroup.RARE_ENEMY:
        if difficulty in (rset.Difficulty.NORMAL, rset.Difficulty.EASY):
            drop_dist = td.TreasureDist(
                (2, _mid_gear + _good_gear + _high_gear),
                (8, _mid_cons + _good_cons + _high_cons)
            )
            charm_dist = None
            drop_rate = 0.4
        elif difficulty == rset.Difficulty.HARD:
            drop_dist = td.TreasureDist(
                (1, _pass_cons + _mid_cons + _good_cons)
            )
            charm_dist = td.TreasureDist(
                (1, _mid_gear + _good_gear)
            )
            drop_rate = 1.0
        else:
            exit()
    elif enemy_group == RewardGroup.RAREST_ENEMY:
        if difficulty in (rset.Difficulty.NORMAL, rset.Difficulty.EASY):
            drop_dist = td.TreasureDist(
                (1, _high_gear + _awe_gear),
                (9, _high_cons + _awe_cons)
            )
            charm_dist = None
            drop_rate = 0.3
        elif difficulty == rset.Difficulty.HARD:
            drop_dist = td.TreasureDist(
                (2, _mid_gear + _good_gear + _high_gear + _awe_gear),
                (8, _mid_cons + _good_cons + _high_cons + _awe_cons)
            )
            charm_dist = drop_dist
            drop_rate = 0.3
        else:
            exit()
    elif enemy_group == RewardGroup.EARLY_BOSS:
        if difficulty in (rset.Difficulty.NORMAL, rset.Difficulty.EASY):
            drop_dist = td.TreasureDist(
                (15, _awe_gear),
                (60, _good_gear + _high_gear),
                (225, _mid_gear),
                (100, _mid_cons + _high_cons + _good_cons + _awe_cons)
            )
            charm_dist = td.TreasureDist(
                (5, _awe_gear),
                (20, _good_gear + _high_gear),
                (75, _mid_gear)
            )
            drop_rate = 1.0
        elif difficulty == rset.Difficulty.HARD:
            drop_dist = td.TreasureDist(
                (5, _awe_gear),
                (20, _good_gear + _high_gear),
                (75, _mid_gear),
                (100, _mid_cons + _high_cons + _good_cons + _awe_cons)
            )
            charm_dist = td.TreasureDist(
                (5, _awe_gear),
                (20, _good_gear + _high_gear),
                (75, _mid_gear)
            )
            drop_rate = 0.5
        else:
            exit()
    elif enemy_group == RewardGroup.MIDGAME_BOSS:
        if difficulty in (rset.Difficulty.NORMAL, rset.Difficulty.EASY):
            drop_dist = td.TreasureDist(
                (15, _awe_gear),
                (60, _good_gear + _high_gear),
                (225, _good_gear),
                (100, _mid_cons + _high_cons + _good_cons + _awe_cons)
            )
            charm_dist = td.TreasureDist(
                (5, _awe_gear),
                (20, _good_gear + _high_gear),
                (75, _good_gear)
            )
            drop_rate = 1.0
        elif difficulty == rset.Difficulty.HARD:
            drop_dist = td.TreasureDist(
                (5, _awe_gear),
                (20, _good_gear + _high_gear),
                (75, _good_gear),
                (100, _mid_cons + _high_cons + _good_cons + _awe_cons)
            )
            charm_dist = td.TreasureDist(
                (5, _awe_gear),
                (20, _good_gear + _high_gear),
                (75, _good_gear)
            )
            drop_rate = 1.0
        else:
            raise ValueError(f"Invalid Difficulty {difficulty}.")
    elif enemy_group == RewardGroup.LATE_BOSS:
        if difficulty in (rset.Difficulty.NORMAL, rset.Difficulty.EASY):
            drop_dist = td.TreasureDist(
                (15, _awe_gear),
                (285, _good_gear + _high_gear),
                (100, _mid_cons + _good_cons + _high_cons + _awe_cons)
            )
            charm_dist = td.TreasureDist(
                (5, _awe_gear),
                (95, _good_gear + _high_gear)
            )
            drop_rate = 1.0
        elif difficulty == rset.Difficulty.HARD:
            drop_dist = td.TreasureDist(
                (10, _awe_gear),
                (190, _good_gear + _high_gear),
                (100, _mid_cons + _good_cons + _high_cons + _awe_cons)
            )
            charm_dist = td.TreasureDist(
                (5, _awe_gear),
                (95, _good_gear + _high_gear)
            )
            drop_rate = 1.0
        else:
            raise ValueError(f"Invalid Difficulty {difficulty}.")

    return drop_dist, charm_dist, drop_rate


_common_enemies = [
    EnemyID.BELLBIRD, EnemyID.BLUE_IMP, EnemyID.GREEN_IMP, EnemyID.ROLY,
    EnemyID.POLY, EnemyID.ROLYPOLY, EnemyID.ROLY_RIDER, EnemyID.BLUE_EAGLET,
    EnemyID.AVIAN_CHAOS, EnemyID.IMP_ACE, EnemyID.GNASHER, EnemyID.NAGA_ETTE,
    EnemyID.OCTOBLUSH, EnemyID.FREE_LANCER, EnemyID.JINN_BOTTLE,
    EnemyID.TEMPURITE, EnemyID.DIABLOS, EnemyID.HENCH_BLUE, EnemyID.MAD_BAT,
    EnemyID.CRATER, EnemyID.HETAKE, EnemyID.SHADOW, EnemyID.GOBLIN,
    EnemyID.CAVE_BAT, EnemyID.OGAN, EnemyID.BEETLE, EnemyID.GATO,
]

_uncommon_enemies = [
    EnemyID.REPTITE_GREEN, EnemyID.KILWALA, EnemyID.KRAWLIE,
    EnemyID.HENCH_PURPLE, EnemyID.GOLD_EAGLET, EnemyID.RED_EAGLET,
    EnemyID.GNAWER, EnemyID.OCTOPOD, EnemyID.FLY_TRAP, EnemyID.MEAT_EATER,
    EnemyID.KRAKKER, EnemyID.EGDER, EnemyID.DECEDENT, EnemyID.MACABRE,
    EnemyID.GUARD, EnemyID.SENTRY, EnemyID.OUTLAW, EnemyID.REPTITE_PURPLE,
    EnemyID.BLUE_SHIELD, EnemyID.YODU_DE, EnemyID.EVILWEEVIL,
    EnemyID.GRIMALKIN, EnemyID.T_POLE, EnemyID.VAMP,
    EnemyID.BUGGER, EnemyID.DEBUGGER, EnemyID.SORCERER, EnemyID.CRATER,
    EnemyID.VOLCANO, EnemyID.SHITAKE, EnemyID.SHIST, EnemyID.NEREID,
    EnemyID.MOHAVOR, EnemyID.ACID, EnemyID.ALKALINE,
    EnemyID.WINGED_APE, EnemyID.MEGASAUR, EnemyID.OMNICRONE,
    EnemyID.BEAST, EnemyID.AVIAN_REX, EnemyID.RAT, EnemyID.GREMLIN,
    EnemyID.RUNNER, EnemyID.PROTO_2, EnemyID.PROTO_3, EnemyID.BUG,
    EnemyID.MASA, EnemyID.MUNE, EnemyID.MUTANT, EnemyID.DECEDENT_II,
    EnemyID.SPEKKIO_FROG, EnemyID.SPEKKIO_KILWALA, EnemyID.HEXAPOD,
    EnemyID.ROLY_BOMBER, EnemyID.FAKE_FLEA
]

_rare_enemies = [
    EnemyID.TERRASAUR, EnemyID.MARTELLO, EnemyID.PANEL, EnemyID.STONE_IMP,
    EnemyID.BANTAM_IMP, EnemyID.RUMINATOR, EnemyID.MAN_EATER, EnemyID.DEFUNCT,
    EnemyID.DECEASED, EnemyID.REAPER, EnemyID.JUGGLER, EnemyID.RETINITE_EYE,
    EnemyID.MAGE, EnemyID.INCOGNITO, EnemyID.PEEPINGDOOM, EnemyID.BOSS_ORB,
    EnemyID.GARGOYLE, EnemyID.SCOUTER, EnemyID.FLYCLOPS, EnemyID.DEBUGGEST,
    EnemyID.JINN, EnemyID.BARGHEST, EnemyID.PAHOEHOE, EnemyID.ALKALINE,
    EnemyID.THRASHER, EnemyID.LASHER, EnemyID.FLUNKY, EnemyID.GROUPIE,
    EnemyID.CAVE_APE, EnemyID.LIZARDACTYL, EnemyID.BLOB, EnemyID.ALIEN,
    EnemyID.PROTO_4, EnemyID.GOON, EnemyID.SYNCHRITE, EnemyID.METAL_MUTE,
    EnemyID.GIGASAUR, EnemyID.FOSSIL_APE, EnemyID.CYBOT, EnemyID.TUBSTER,
    EnemyID.RED_SCOUT, EnemyID.BLUE_SCOUT, EnemyID.LASER_GUARD,
    EnemyID.SPEKKIO_OGRE, EnemyID.SPEKKIO_OMNICRONE, EnemyID.SPEKKIO_MASA_MUNE,
    EnemyID.SPEKKIO_NU, EnemyID.OZZIE_MAGUS_CHAINS,
]

_rarest_enemies = [
    EnemyID.NU, EnemyID.DEPARTED, EnemyID.SIDE_KICK, EnemyID.RUBBLE,
    EnemyID.NU_2,
]

_early_bosses = [
    EnemyID.YAKRA, EnemyID.MASA, EnemyID.MUNE, EnemyID.MASA_MUNE,
    EnemyID.OZZIE_ZENAN, EnemyID.OZZIE_FORT, EnemyID.HECKRAN,
    EnemyID.ZOMBOR_BOTTOM, EnemyID.ZOMBOR_TOP, EnemyID.SUPER_SLASH,
    EnemyID.FLEA_PLUS, EnemyID.ATROPOS_XR, EnemyID.GOLEM_BOSS,
]

_midgame_bosses = [
    EnemyID.RETINITE_EYE, EnemyID.DRAGON_TANK, EnemyID.GRINDER, EnemyID.NIZBEL,
    EnemyID.NIZBEL_II, EnemyID.SLASH_SWORD, EnemyID.FLEA, EnemyID.TANK_HEAD,
    EnemyID.RETINITE_BOTTOM, EnemyID.RETINITE_TOP, EnemyID.DISPLAY,
    EnemyID.RUST_TYRANO, EnemyID.MOTHERBRAIN, EnemyID.YAKRA_XIII,
    EnemyID.LAVOS_2_HEAD, EnemyID.LAVOS_2_LEFT, EnemyID.LAVOS_2_RIGHT,
    EnemyID.LAVOS_3_CORE, EnemyID.GUARDIAN_BIT, EnemyID.GUARDIAN,
    EnemyID.LAVOS_SPAWN_SHELL, EnemyID.LAVOS_SPAWN_HEAD,
    EnemyID.LAVOS_OCEAN_PALACE, EnemyID.LAVOS_3_LEFT, EnemyID.LAVOS_3_RIGHT,
    EnemyID.SON_OF_SUN_EYE, EnemyID.SON_OF_SUN_FLAME, EnemyID.R_SERIES,
]

_late_bosses = [
    EnemyID.MAMMON_M, EnemyID.ZEAL, EnemyID.TWIN_BOSS, EnemyID.GOLEM,
    EnemyID.AZALA, EnemyID.ELDER_SPAWN_HEAD, EnemyID.ELDER_SPAWN_SHELL,
    EnemyID.ZEAL_2_CENTER, EnemyID.ZEAL_2_LEFT, EnemyID.ZEAL_2_RIGHT,
    EnemyID.GIGA_MUTANT_HEAD, EnemyID.GIGA_MUTANT_BOTTOM,
    EnemyID.TERRA_MUTANT_HEAD, EnemyID.TERRA_MUTANT_BOTTOM,
    EnemyID.FLEA_PLUS_TRIO, EnemyID.SUPER_SLASH_TRIO, EnemyID.GREAT_OZZIE,
    EnemyID.BLACKTYRANO, EnemyID.GIGA_GAIA_HEAD, EnemyID.GIGA_GAIA_LEFT,
    EnemyID.GIGA_GAIA_RIGHT, EnemyID.MAGUS, EnemyID.DALTON_PLUS,
    EnemyID.MEGA_MUTANT_BOTTOM, EnemyID.MEGA_MUTANT_HEAD
]

_enemy_group_dict = dict()

_enemy_group_dict[RewardGroup.COMMON_ENEMY] = _common_enemies
_enemy_group_dict[RewardGroup.UNCOMMON_ENEMY] = _uncommon_enemies
_enemy_group_dict[RewardGroup.RARE_ENEMY] = _rare_enemies
_enemy_group_dict[RewardGroup.RAREST_ENEMY] = _rarest_enemies
_enemy_group_dict[RewardGroup.EARLY_BOSS] = _early_bosses
_enemy_group_dict[RewardGroup.MIDGAME_BOSS] = _midgame_bosses
_enemy_group_dict[RewardGroup.LATE_BOSS] = _late_bosses


# public way to get the list of enemies in a given tier.
# returns a copy to avoid messing with the lists in global scope
def get_enemy_tier(tier: RewardGroup):
    return _enemy_group_dict[tier].copy()


def get_tier_of_enemy(enemy_id: EnemyID):
    tier = (x for x in _enemy_group_dict
            if enemy_id in _enemy_group_dict[x])

    return next(tier)


def set_enemy_charm_drop(stats: enemystats.EnemyStats,
                         reward_group: RewardGroup,
                         difficulty: rset.Difficulty,
                         rng: RNGType):
    drop_dist, charm_dist, drop_rate = \
        get_distributions(reward_group, difficulty)

    drop = drop_dist.get_random_item(rng)
    if charm_dist is None:
        charm = drop
    else:
        charm = charm_dist.get_random_item(rng)

    if rng.random() > drop_rate:
        drop = ItemID.NONE

    stats.drop_item = drop
    stats.charm_item = charm


# This method just alters the cfg.RandoConfig object.
def write_enemy_rewards_to_config(settings: rset.Settings,
                                  config: cfg.RandoConfig,
                                  rng: RNGType):

    for group in list(RewardGroup):
        enemies = _enemy_group_dict[group]
        drop_dist, charm_dist, drop_rate = \
            get_distributions(group, settings.item_difficulty)

        for enemy in enemies:
            drop = drop_dist.get_random_item(rng)
            if charm_dist is None:
                charm = drop
            else:
                charm = charm_dist.get_random_item(rng)

            if rng.random() > drop_rate:
                drop = ItemID.NONE

            config.enemy_dict[enemy].drop_item = drop
            config.enemy_dict[enemy].charm_item = charm

            # print(f"Enemy: {enemy} assigned drop={drop}, charm={charm}")

    # Trading Post: Vanilla
    # Croaker - 2x Fang
    # Amphibite - 2x Horns
    # Rain Frog - 2x Feathers

    # Ion - 2x Feathers
    # Anion - 2x Petals

    # Keep a similar distribution where the frogs are all different and the
    # slimes have one item in common with frogs.
    tp_drops = [ItemID.PETALS_2, ItemID.FANGS_2, ItemID.HORNS_2,
                ItemID.FEATHERS_2]
    tp_enemies = [EnemyID.CROAKER, EnemyID.AMPHIBITE, EnemyID.RAIN_FROG,
                  EnemyID.ION, EnemyID.ANION]

    rng.shuffle(tp_drops)
    tp_drops.append(tp_drops[0])  # Copy a frog drop for the slimes

    for ind, enemy in enumerate(tp_enemies):
        item_id = tp_drops[ind]
        config.enemy_dict[enemy].drop_item = item_id
        config.enemy_dict[enemy].charm_item = item_id
