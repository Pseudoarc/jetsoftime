# This file contains classes dealing with how ctenums.TreasureID items are
# classified by tier (class TreasureLocTier) and how ctenums.ItemID items are
# classified by tier (class ItemTier).

# There are --many-- global lists defined here, but they are all given _names
# to avoid accidental import with an import * command.  Users of this file
# should use the get_ methods to access the data within those lists.

from __future__ import annotations

from typing import Tuple
import random

from ctenums import TreasureID as TID, StrIntEnum, ItemID

import randosettings as rset


# Note that all of the one-off treasure spots like jerky, taban, and trades
# do not have a TreasureLocTier.
class TreasureLocTier(StrIntEnum):
    LOW = 0
    LOW_MID = 1
    MID = 2
    MID_HIGH = 3
    HIGH_AWESOME = 4
    SEALED = 5


class ItemTier(StrIntEnum):
    LOW_GEAR = 0
    LOW_CONSUMABLE = 1
    PASSABLE_GEAR = 2
    PASSABLE_CONSUMABLE = 3
    MID_GEAR = 4
    MID_CONSUMABLE = 5
    GOOD_GEAR = 6
    GOOD_CONSUMABLE = 7
    HIGH_GEAR = 8
    HIGH_CONSUMABLE = 9
    AWESOME_GEAR = 10
    AWESOME_CONSUMABLE = 11
    SEALED_TREASURE = 12
    TABAN_HELM = 13
    TABAN_WEAPON = 14
    TRADE_RANGED = 15
    TRADE_ACCESSORY = 16
    TRADE_TAB = 17
    TRADE_MELEE = 18
    TRADE_ARMOR = 19
    TRADE_HELM = 20
    JERKY_REWARD = 21


# Mark this is something other people shouldn't touch.  Give the function
# get_treasure_tier_locations(tier) as a public interface for it.
_treasure_loc_tier_list: list[list[TID]] = [[] for i in list(TreasureLocTier)]

_treasure_loc_tier_list[TreasureLocTier.LOW] = [
    TID.TRUCE_MAYOR_1F, TID.TRUCE_MAYOR_2F, TID.KINGS_ROOM_1000,
    TID.QUEENS_ROOM_1000, TID.FOREST_RUINS, TID.PORRE_MAYOR_2F,
    TID.TRUCE_CANYON_1, TID.TRUCE_CANYON_2, TID.KINGS_ROOM_600,
    TID.QUEENS_ROOM_600, TID.ROYAL_KITCHEN, TID.CURSED_WOODS_1,
    TID.CURSED_WOODS_2, TID.FROGS_BURROW_RIGHT, TID.FIONAS_HOUSE_1,
    TID.FIONAS_HOUSE_2, TID.QUEENS_TOWER_600, TID.KINGS_TOWER_600,
    TID.KINGS_TOWER_1000, TID.QUEENS_TOWER_1000, TID.GUARDIA_COURT_TOWER,
]

_treasure_loc_tier_list[TreasureLocTier.LOW_MID] = [
    TID.HECKRAN_CAVE_SIDETRACK, TID.HECKRAN_CAVE_ENTRANCE,
    TID.HECKRAN_CAVE_1, TID.HECKRAN_CAVE_2, TID.GUARDIA_JAIL_FRITZ,
    TID.MANORIA_CATHEDRAL_1, TID.MANORIA_CATHEDRAL_2, TID.MANORIA_CATHEDRAL_3,
    TID.MANORIA_INTERIOR_1, TID.MANORIA_INTERIOR_2, TID.MANORIA_INTERIOR_4,
    TID.DENADORO_MTS_SCREEN2_1, TID.DENADORO_MTS_SCREEN2_2,
    TID.DENADORO_MTS_SCREEN2_3, TID.DENADORO_MTS_FINAL_1,
    TID.DENADORO_MTS_FINAL_2, TID.DENADORO_MTS_FINAL_3,
    TID.DENADORO_MTS_WATERFALL_TOP_3, TID.DENADORO_MTS_WATERFALL_TOP_4,
    TID.DENADORO_MTS_WATERFALL_TOP_5, TID.DENADORO_MTS_ENTRANCE_1,
    TID.DENADORO_MTS_ENTRANCE_2, TID.DENADORO_MTS_SCREEN3_1,
    TID.DENADORO_MTS_SCREEN3_2, TID.DENADORO_MTS_SCREEN3_3,
    TID.DENADORO_MTS_SCREEN3_4, TID.DENADORO_MTS_AMBUSH,
    TID.DENADORO_MTS_SAVE_PT, TID.YAKRAS_ROOM,
    TID.MANORIA_SHRINE_SIDEROOM_1, TID.MANORIA_SHRINE_SIDEROOM_2,
    TID.MANORIA_BROMIDE_1, TID.MANORIA_BROMIDE_2,
    TID.MANORIA_BROMIDE_3, TID.MANORIA_SHRINE_MAGUS_1,
    TID.MANORIA_SHRINE_MAGUS_2,
]

_treasure_loc_tier_list[TreasureLocTier.MID] = [
    TID.GUARDIA_JAIL_FRITZ_STORAGE, TID.GUARDIA_JAIL_CELL,
    TID.GUARDIA_JAIL_OMNICRONE_1, TID.GUARDIA_JAIL_OMNICRONE_2,
    TID.GUARDIA_JAIL_OMNICRONE_3, TID.GUARDIA_JAIL_HOLE_1,
    TID.GUARDIA_JAIL_HOLE_2, TID.GUARDIA_JAIL_OUTER_WALL,
    TID.GUARDIA_JAIL_OMNICRONE_4,  # TID.GIANTS_CLAW_KINO_CELL,
    TID.GIANTS_CLAW_TRAPS, TID.MANORIA_INTERIOR_3,
    TID.DENADORO_MTS_WATERFALL_TOP_1, TID.DENADORO_MTS_WATERFALL_TOP_2,
    TID.SUNKEN_DESERT_B1_NW, TID.SUNKEN_DESERT_B1_NE,
    TID.SUNKEN_DESERT_B1_SE, TID.SUNKEN_DESERT_B1_SW,
    TID.SUNKEN_DESERT_B2_NW, TID.SUNKEN_DESERT_B2_N,
    TID.SUNKEN_DESERT_B2_W,  TID.SUNKEN_DESERT_B2_SW,
    TID.SUNKEN_DESERT_B2_SE, TID.SUNKEN_DESERT_B2_E,
    TID.SUNKEN_DESERT_B2_CENTER, TID.OZZIES_FORT_GUILLOTINES_1,
    TID.OZZIES_FORT_GUILLOTINES_2, TID.OZZIES_FORT_GUILLOTINES_3,
    TID.OZZIES_FORT_GUILLOTINES_4, TID.OZZIES_FORT_FINAL_1,
    TID.OZZIES_FORT_FINAL_2, TID.GIANTS_CLAW_CAVES_1,
    TID.GIANTS_CLAW_CAVES_2, TID.GIANTS_CLAW_CAVES_3,
    TID.GIANTS_CLAW_CAVES_4, TID.GIANTS_CLAW_CAVES_5,
    TID.MYSTIC_MT_STREAM, TID.FOREST_MAZE_1,
    TID.FOREST_MAZE_2, TID.FOREST_MAZE_3, TID.FOREST_MAZE_4,
    TID.FOREST_MAZE_5, TID.FOREST_MAZE_6, TID.FOREST_MAZE_7,
    TID.FOREST_MAZE_8, TID.FOREST_MAZE_9,
    TID.REPTITE_LAIR_REPTITES_1, TID.REPTITE_LAIR_REPTITES_2,
    TID.DACTYL_NEST_1, TID.DACTYL_NEST_2, TID.DACTYL_NEST_3,
    TID.GIANTS_CLAW_THRONE_1, TID.GIANTS_CLAW_THRONE_2,
    TID.TYRANO_LAIR_KINO_CELL, TID.ARRIS_DOME_FOOD_STORE,
    TID.PRISON_TOWER_1000,
]

# This is inconsistent with 3.1 because its categories had some overlaps
# with lower tiers.  These have been removed.
_treasure_loc_tier_list[TreasureLocTier.MID_HIGH] = [
    TID.GUARDIA_BASEMENT_1, TID.GUARDIA_BASEMENT_2, TID.GUARDIA_BASEMENT_3,
    TID.MAGUS_CASTLE_RIGHT_HALL, TID.MAGUS_CASTLE_GUILLOTINE_1,
    TID.MAGUS_CASTLE_GUILLOTINE_2, TID.MAGUS_CASTLE_SLASH_ROOM_1,
    TID.MAGUS_CASTLE_SLASH_ROOM_2, TID.MAGUS_CASTLE_STATUE_HALL,
    TID.MAGUS_CASTLE_FOUR_KIDS, TID.MAGUS_CASTLE_OZZIE_1,
    TID.MAGUS_CASTLE_OZZIE_2, TID.MAGUS_CASTLE_ENEMY_ELEVATOR,
    TID.BANGOR_DOME_SEAL_1, TID.BANGOR_DOME_SEAL_2, TID.BANGOR_DOME_SEAL_3,
    TID.TRANN_DOME_SEAL_1, TID.TRANN_DOME_SEAL_2,
    TID.LAB_16_1, TID.LAB_16_2, TID.LAB_16_3, TID.LAB_16_4,
    TID.ARRIS_DOME_RATS, TID.LAB_32_1,
    TID.FACTORY_LEFT_AUX_CONSOLE, TID.FACTORY_LEFT_SECURITY_RIGHT,
    TID.FACTORY_LEFT_SECURITY_LEFT, TID.FACTORY_RIGHT_FLOOR_TOP,
    TID.FACTORY_RIGHT_FLOOR_LEFT, TID.FACTORY_RIGHT_FLOOR_BOTTOM,
    TID.FACTORY_RIGHT_FLOOR_SECRET, TID.FACTORY_RIGHT_CRANE_LOWER,
    TID.FACTORY_RIGHT_CRANE_UPPER, TID.FACTORY_RIGHT_INFO_ARCHIVE,
    TID.FACTORY_RUINS_GENERATOR, TID.SEWERS_1,
    TID.SEWERS_2, TID.SEWERS_3, TID.DEATH_PEAK_SOUTH_FACE_KRAKKER,
    TID.DEATH_PEAK_SOUTH_FACE_SPAWN_SAVE, TID.DEATH_PEAK_SOUTH_FACE_SUMMIT,
    TID.DEATH_PEAK_FIELD, TID.GENO_DOME_1F_1,
    TID.GENO_DOME_1F_2, TID.GENO_DOME_1F_3, TID.GENO_DOME_1F_4,
    TID.GENO_DOME_ROOM_1, TID.GENO_DOME_ROOM_2, TID.GENO_DOME_PROTO4_1,
    # TID.GENO_DOME_PROTO4_2,
    TID.FACTORY_RIGHT_DATA_CORE_1,
    TID.FACTORY_RIGHT_DATA_CORE_2, TID.DEATH_PEAK_KRAKKER_PARADE,
    TID.DEATH_PEAK_CAVES_LEFT, TID.DEATH_PEAK_CAVES_CENTER,
    TID.DEATH_PEAK_CAVES_RIGHT, # TID.GENO_DOME_2F_1,
    TID.GENO_DOME_2F_2, TID.GENO_DOME_2F_3, TID.GENO_DOME_2F_4,
    TID.TYRANO_LAIR_TRAPDOOR, TID.TYRANO_LAIR_MAZE_1,
    TID.TYRANO_LAIR_MAZE_2, TID.TYRANO_LAIR_MAZE_3,
    TID.TYRANO_LAIR_MAZE_4, TID.OCEAN_PALACE_MAIN_S,
    TID.OCEAN_PALACE_MAIN_N, TID.OCEAN_PALACE_E_ROOM,
    TID.OCEAN_PALACE_W_ROOM, TID.OCEAN_PALACE_SWITCH_NW,
    TID.OCEAN_PALACE_SWITCH_SW, TID.OCEAN_PALACE_SWITCH_NE,
    TID.GUARDIA_TREASURY_1, TID.GUARDIA_TREASURY_2, TID.GUARDIA_TREASURY_3,
    TID.MAGUS_CASTLE_LEFT_HALL, TID.MAGUS_CASTLE_UNSKIPPABLES,
    TID.MAGUS_CASTLE_PIT_E, TID.MAGUS_CASTLE_PIT_NE, TID.MAGUS_CASTLE_PIT_NW,
    TID.MAGUS_CASTLE_PIT_W,
    # Woe monstly moved mid-high
    TID.MT_WOE_2ND_SCREEN_1, TID.MT_WOE_2ND_SCREEN_2,
    TID.MT_WOE_2ND_SCREEN_3, # TID.MT_WOE_2ND_SCREEN_4,
    TID.MT_WOE_2ND_SCREEN_5, # TID.MT_WOE_3RD_SCREEN_1,
    TID.MT_WOE_3RD_SCREEN_2, TID.MT_WOE_3RD_SCREEN_3,
    TID.MT_WOE_3RD_SCREEN_4, TID.MT_WOE_3RD_SCREEN_5,
    TID.MT_WOE_1ST_SCREEN, TID.MT_WOE_FINAL_1,
    TID.MT_WOE_FINAL_2,
    # FACTORY_RUINS_UNUSED: 0xE7
]

_treasure_loc_tier_list[TreasureLocTier.HIGH_AWESOME] = [
    TID.ARRIS_DOME_SEAL_1, TID.ARRIS_DOME_SEAL_2,
    TID.ARRIS_DOME_SEAL_3, TID.ARRIS_DOME_SEAL_4,
    TID.REPTITE_LAIR_SECRET_B2_NE_RIGHT, TID.REPTITE_LAIR_SECRET_B1_SW,
    TID.REPTITE_LAIR_SECRET_B1_NE, TID.REPTITE_LAIR_SECRET_B1_SE,
    TID.REPTITE_LAIR_SECRET_B2_SE_RIGHT,
    TID.REPTITE_LAIR_SECRET_B2_NE_OR_SE_LEFT,
    TID.REPTITE_LAIR_SECRET_B2_SW, TID.BLACK_OMEN_AUX_COMMAND_MID,
    TID.BLACK_OMEN_AUX_COMMAND_NE, TID.BLACK_OMEN_GRAND_HALL,
    TID.BLACK_OMEN_NU_HALL_NW, TID.BLACK_OMEN_NU_HALL_W,
    TID.BLACK_OMEN_NU_HALL_SW, TID.BLACK_OMEN_NU_HALL_NE,
    TID.BLACK_OMEN_NU_HALL_E, TID.BLACK_OMEN_NU_HALL_SE,
    TID.BLACK_OMEN_ROYAL_PATH, TID.BLACK_OMEN_RUMINATOR_PARADE,
    TID.BLACK_OMEN_EYEBALL_HALL, TID.BLACK_OMEN_TUBSTER_FLY,
    TID.BLACK_OMEN_MARTELLO, TID.BLACK_OMEN_ALIEN_SW,
    TID.BLACK_OMEN_ALIEN_NE, TID.BLACK_OMEN_ALIEN_NW,
    TID.BLACK_OMEN_TERRA_W, TID.BLACK_OMEN_TERRA_NE,
    TID.OCEAN_PALACE_SWITCH_SECRET,
    TID.OCEAN_PALACE_FINAL,
    # A Few Woe Chests
    TID.MT_WOE_2ND_SCREEN_4, TID.MT_WOE_3RD_SCREEN_1,
    # A Few Geno Chests
    TID.GENO_DOME_PROTO4_2, TID.GENO_DOME_2F_1,

]

# Sealed chests include some script chests from Northern Ruins
_treasure_loc_tier_list[TreasureLocTier.SEALED] = [
    TID.NORTHERN_RUINS_ANTECHAMBER_LEFT_600,
    TID.NORTHERN_RUINS_ANTECHAMBER_SEALED_600,
    TID.NORTHERN_RUINS_ANTECHAMBER_LEFT_1000,
    TID.NORTHERN_RUINS_ANTECHAMBER_SEALED_1000,
    TID.NORTHERN_RUINS_BACK_LEFT_SEALED_600,
    TID.NORTHERN_RUINS_BACK_LEFT_SEALED_1000,
    TID.NORTHERN_RUINS_BACK_RIGHT_SEALED_600,
    TID.NORTHERN_RUINS_BACK_RIGHT_SEALED_1000,
    TID.NORTHERN_RUINS_BASEMENT_600,
    TID.NORTHERN_RUINS_BASEMENT_1000,
    TID.TRUCE_INN_SEALED_600, TID.TRUCE_INN_SEALED_1000,
    TID.PORRE_ELDER_SEALED_1, TID.PORRE_ELDER_SEALED_2,
    TID.PORRE_MAYOR_SEALED_1, TID.PORRE_MAYOR_SEALED_2,
    TID.GUARDIA_CASTLE_SEALED_600, TID.GUARDIA_CASTLE_SEALED_1000,
    TID.GUARDIA_FOREST_SEALED_600, TID.GUARDIA_FOREST_SEALED_1000,
    TID.HECKRAN_SEALED_1, TID.HECKRAN_SEALED_2,
    TID.PYRAMID_LEFT, TID.PYRAMID_RIGHT,
    TID.MAGIC_CAVE_SEALED,
]


# This is how other modules should get the TreasureIDs in each tier
def get_treasures_in_tier(tier: TreasureLocTier):
    return _treasure_loc_tier_list[tier].copy()


_item_tier_list: dict[ItemTier, list[ItemID]] = {
    tier: [] for tier in list(ItemTier)
}

_item_tier_list[ItemTier.LOW_GEAR] = [
    ItemID.BANDANA, ItemID.DEFENDER, ItemID.MAGICSCARF, ItemID.POWERGLOVE,
    ItemID.RIBBON, ItemID.SIGHTSCOPE, ItemID.IRON_BLADE, ItemID.STEELSABER,
    ItemID.LODE_SWORD, ItemID.BOLT_SWORD,
    ItemID.IRON_BOW, ItemID.LODE_BOW, ItemID.DART_GUN, ItemID.AUTO_GUN,
    ItemID.HAMMER_ARM, ItemID.MIRAGEHAND, ItemID.IRON_SWORD, ItemID.IRON_HELM,
    ItemID.BERET, ItemID.GOLD_HELM, ItemID.KARATE_GI, ItemID.BRONZEMAIL,
    ItemID.MAIDENSUIT, ItemID.IRON_SUIT, ItemID.TITAN_VEST, ItemID.GOLD_SUIT,
]

_item_tier_list[ItemTier.LOW_CONSUMABLE] = [
    ItemID.TONIC, ItemID.MID_TONIC, ItemID.HEAL, ItemID.REVIVE,
    ItemID.SHELTER, ItemID.POWER_MEAL,
]

_item_tier_list[ItemTier.PASSABLE_GEAR] = [
    ItemID.BERSERKER, ItemID.RAGE_BAND, ItemID.HIT_RING, ItemID.MUSCLERING,
    ItemID.POWERSCARF, ItemID.RED_KATANA, ItemID.FLINT_EDGE, ItemID.DARK_SABER,
    ItemID.SERAPHSONG, ItemID.ROBIN_BOW, ItemID.PICOMAGNUM, ItemID.PLASMA_GUN,
    ItemID.STONE_ARM, ItemID.ROCK_HELM, ItemID.CERATOPPER, ItemID.RUBY_VEST,
    ItemID.DARK_MAIL, ItemID.MIST_ROBE, ItemID.MESO_MAIL,
]

_item_tier_list[ItemTier.PASSABLE_CONSUMABLE] = [
    ItemID.MID_TONIC, ItemID.ETHER
]

_item_tier_list[ItemTier.MID_GEAR] = [
    ItemID.THIRD_EYE, ItemID.WALLET, ItemID.SILVERERNG, ItemID.FRENZYBAND,
    ItemID.POWER_RING, ItemID.MAGIC_RING, ItemID.WALL_RING,
    ItemID.AEON_BLADE, ItemID.DEMON_EDGE, ItemID.ALLOYBLADE,
    ItemID.SAGE_BOW, ItemID.DREAM_BOW,
    ItemID.RUBY_GUN, ItemID.DREAM_GUN, ItemID.DOOMFINGER, ItemID.MAGMA_HAND,
    ItemID.MEGATONARM, ItemID.FLASHBLADE, ItemID.PEARL_EDGE, ItemID.HURRICANE,
    ItemID.GLOW_HELM, ItemID.LODE_HELM, ItemID.TABAN_HELM, ItemID.LUMIN_ROBE,
    ItemID.FLASH_MAIL, ItemID.WHITE_VEST, ItemID.BLACK_VEST, ItemID.BLUE_VEST,
    ItemID.RED_VEST, ItemID.TABAN_VEST,
]

_item_tier_list[ItemTier.MID_CONSUMABLE] = [
    ItemID.FULL_TONIC, ItemID.MID_ETHER, ItemID.LAPIS, ItemID.BARRIER,
    ItemID.SHIELD,
]

_item_tier_list[ItemTier.GOOD_GEAR] = [
    ItemID.SPEED_BELT, ItemID.FLEA_VEST, ItemID.MAGIC_SEAL, ItemID.POWER_SEAL,
    ItemID.GOLD_ERNG, ItemID.SILVERSTUD, ItemID.GREENDREAM,
    ItemID.SLASHER, ItemID.STAR_SWORD, ItemID.VEDICBLADE,
    ItemID.COMETARROW, ItemID.SONICARROW,
    ItemID.MEGABLAST, ItemID.GRAEDUS, ItemID.BIG_HAND, ItemID.KAISER_ARM,
    ItemID.RUNE_BLADE, ItemID.DEMON_HIT, ItemID.STARSCYTHE, ItemID.AEON_HELM,
    ItemID.DARK_HELM, ItemID.RBOW_HELM, ItemID.MERMAIDCAP, ItemID.LODE_VEST,
    ItemID.AEON_SUIT, ItemID.WHITE_MAIL, ItemID.BLACK_MAIL, ItemID.BLUE_MAIL,
    ItemID.RED_MAIL,
]

_item_tier_list[ItemTier.GOOD_CONSUMABLE] = [
    ItemID.FULL_TONIC, ItemID.FULL_ETHER, ItemID.HYPERETHER,
]

_item_tier_list[ItemTier.HIGH_GEAR] = [
    ItemID.AMULET, ItemID.DASH_RING, ItemID.GOLD_STUD, ItemID.SUN_SHADES,
    ItemID.KALI_BLADE, ItemID.SLASHER_2, ItemID.VALKERYE,
    ItemID.SIREN, ItemID.SHOCK_WAVE, ItemID.GIGA_ARM, ItemID.TERRA_ARM,
    ItemID.BRAVESWORD, ItemID.DOOMSICKLE, ItemID.GLOOM_HELM, ItemID.SAFE_HELM,
    ItemID.SIGHT_CAP, ItemID.MEMORY_CAP, ItemID.TIME_HAT, ItemID.ZODIACCAPE,
    ItemID.RUBY_ARMOR, ItemID.GLOOM_CAPE,
]

_item_tier_list[ItemTier.HIGH_CONSUMABLE] = [
    ItemID.ELIXIR, ItemID.HYPERETHER, ItemID.POWER_TAB, ItemID.MAGIC_TAB,
    ItemID.SPEED_TAB,
]

_item_tier_list[ItemTier.AWESOME_GEAR] = [
    ItemID.PRISMSPECS, ItemID.SHIVA_EDGE, ItemID.SWALLOW,
    ItemID.RAINBOW, ItemID.WONDERSHOT, ItemID.CRISIS_ARM, ItemID.HASTE_HELM,
    ItemID.PRISM_HELM, ItemID.VIGIL_HAT, ItemID.PRISMDRESS, ItemID.TABAN_SUIT,
    ItemID.MOON_ARMOR, ItemID.NOVA_ARMOR,
]

_item_tier_list[ItemTier.AWESOME_CONSUMABLE] = [
    ItemID.ELIXIR, ItemID.MEGAELIXIR
]

_item_tier_list[ItemTier.SEALED_TREASURE] = [
    ItemID.THIRD_EYE, ItemID.WALLET, ItemID.SILVERERNG, ItemID.FRENZYBAND,
    ItemID.POWER_RING, ItemID.MAGIC_RING, ItemID.WALL_RING, ItemID.FLINT_EDGE,
    ItemID.DARK_SABER, ItemID.AEON_BLADE, ItemID.SAGE_BOW, ItemID.DREAM_BOW,
    ItemID.RUBY_GUN, ItemID.DREAM_GUN, ItemID.DOOMFINGER, ItemID.MAGMA_HAND,
    ItemID.MEGATONARM, ItemID.FLASHBLADE, ItemID.PEARL_EDGE, ItemID.HURRICANE,
    ItemID.GLOW_HELM, ItemID.LODE_HELM, ItemID.TABAN_HELM, ItemID.LUMIN_ROBE,
    ItemID.FLASH_MAIL, ItemID.WHITE_VEST, ItemID.BLACK_VEST, ItemID.BLUE_VEST,
    ItemID.RED_VEST, ItemID.TABAN_VEST, ItemID.AMULET, ItemID.SPEED_BELT,
    ItemID.FLEA_VEST, ItemID.MAGIC_SEAL, ItemID.POWER_SEAL, ItemID.GOLD_ERNG,
    ItemID.SILVERSTUD, ItemID.GREENDREAM, ItemID.DEMON_EDGE, ItemID.ALLOYBLADE,
    ItemID.SLASHER, ItemID.COMETARROW, ItemID.SONICARROW, ItemID.MEGABLAST,
    ItemID.GRAEDUS, ItemID.BIG_HAND, ItemID.KAISER_ARM, ItemID.RUNE_BLADE,
    ItemID.DEMON_HIT, ItemID.STARSCYTHE, ItemID.AEON_HELM, ItemID.DARK_HELM,
    ItemID.RBOW_HELM, ItemID.MERMAIDCAP, ItemID.LODE_VEST, ItemID.AEON_SUIT,
    ItemID.WHITE_MAIL, ItemID.BLACK_MAIL, ItemID.BLUE_MAIL, ItemID.RED_MAIL,
    ItemID.DASH_RING, ItemID.GOLD_STUD, ItemID.SUN_SHADES, ItemID.STAR_SWORD,
    ItemID.VEDICBLADE, ItemID.KALI_BLADE, ItemID.VALKERYE, ItemID.SIREN,
    ItemID.SHOCK_WAVE, ItemID.GIGA_ARM, ItemID.TERRA_ARM, ItemID.BRAVESWORD,
    ItemID.DOOMSICKLE, ItemID.GLOOM_HELM, ItemID.SAFE_HELM, ItemID.SIGHT_CAP,
    ItemID.MEMORY_CAP, ItemID.TIME_HAT, ItemID.ZODIACCAPE, ItemID.RUBY_ARMOR,
    ItemID.GLOOM_CAPE, ItemID.PRISMSPECS, ItemID.SHIVA_EDGE, ItemID.SWALLOW,
    ItemID.SLASHER_2, ItemID.RAINBOW, ItemID.WONDERSHOT, ItemID.CRISIS_ARM,
    ItemID.HASTE_HELM, ItemID.PRISM_HELM, ItemID.VIGIL_HAT, ItemID.PRISMDRESS,
    ItemID.TABAN_SUIT, ItemID.MOON_ARMOR, ItemID.NOVA_ARMOR, ItemID.FULL_TONIC,
    ItemID.MID_ETHER, ItemID.LAPIS, ItemID.BARRIER, ItemID.SHIELD,
    ItemID.FULL_ETHER, ItemID.HYPERETHER, ItemID.ELIXIR, ItemID.MEGAELIXIR,
    ItemID.POWER_TAB, ItemID.MAGIC_TAB, ItemID.SPEED_TAB,
]

# Special Reward Types

# Taban Trades:  Weapon for forged Masamune, Helm for Sun Stone
_item_tier_list[ItemTier.TABAN_HELM] = [
    ItemID.TABAN_HELM, ItemID.TIME_HAT, ItemID.GLOOM_HELM, ItemID.RBOW_HELM,
    ItemID.MERMAIDCAP, ItemID.OZZIEPANTS, ItemID.SAFE_HELM, ItemID.HASTE_HELM,
    ItemID.PRISM_HELM, ItemID.VIGIL_HAT,
]

_item_tier_list[ItemTier.TABAN_WEAPON] = [
    ItemID.VEDICBLADE, ItemID.KALI_BLADE, ItemID.SWALLOW, ItemID.SLASHER_2,
    ItemID.SONICARROW, ItemID.SIREN, ItemID.SHOCK_WAVE, ItemID.KAISER_ARM,
    ItemID.GIGA_ARM, ItemID.RUNE_BLADE, ItemID.BRAVESWORD, ItemID.DEMON_HIT,
    ItemID.STARSCYTHE, ItemID.SHIVA_EDGE, ItemID.RAINBOW, ItemID.VALKERYE,
    ItemID.WONDERSHOT, ItemID.TERRA_ARM, ItemID.CRISIS_ARM, ItemID.DOOMSICKLE,
]

# Ioka trading post rewards
_item_tier_list[ItemTier.TRADE_RANGED] = [
    ItemID.VALKERYE, ItemID.SHOCK_WAVE, ItemID.DOOMSICKLE
]

_item_tier_list[ItemTier.TRADE_ACCESSORY] = [
    ItemID.GOLD_ERNG, ItemID.GOLD_STUD, ItemID.PRISMSPECS, ItemID.AMULET,
    ItemID.DASH_RING
]

_item_tier_list[ItemTier.TRADE_TAB] = [
    ItemID.POWER_TAB, ItemID.MAGIC_TAB, ItemID.SPEED_TAB
]

_item_tier_list[ItemTier.TRADE_MELEE] = [
    ItemID.RAINBOW, ItemID.TERRA_ARM, ItemID.BRAVESWORD,
]

_item_tier_list[ItemTier.TRADE_ARMOR] = [
    ItemID.GLOOM_CAPE, ItemID.TABAN_SUIT, ItemID.ZODIACCAPE,
    ItemID.NOVA_ARMOR, ItemID.MOON_ARMOR, ItemID.PRISMDRESS,
]
_item_tier_list[ItemTier.TRADE_HELM] = [
    ItemID.TABAN_HELM, ItemID.DARK_HELM, ItemID.RBOW_HELM,
    ItemID.MERMAIDCAP, ItemID.SAFE_HELM, ItemID.HASTE_HELM, ItemID.PRISM_HELM,
]

_item_tier_list[ItemTier.JERKY_REWARD] = [
    ItemID.PRISMSPECS, ItemID.SHIVA_EDGE, ItemID.SWALLOW, ItemID.SLASHER_2,
    ItemID.RAINBOW, ItemID.WONDERSHOT, ItemID.CRISIS_ARM, ItemID.HASTE_HELM,
    ItemID.PRISM_HELM, ItemID.VIGIL_HAT, ItemID.PRISMDRESS, ItemID.TABAN_SUIT,
    ItemID.MOON_ARMOR, ItemID.NOVA_ARMOR,
]


# public way to access the treasure tiers.  Eventually this may change so that
# settings/config can be passed in if different settings want to change the
# treasure list like LW adding Frog gear.
def get_item_list(tier: ItemTier):
    return _item_tier_list[tier].copy()


# distribution uses relative frequencies (rf) instead of float probabilities
# for precision.
class TreasureDist:

    def __init__(self, *weight_item_pairs: Tuple[int, list[ItemID]]):
        # print(weight_item_pairs)
        # input()
        self.weight_item_pairs = weight_item_pairs

    def get_random_item(self) -> ItemID:
        target = random.randrange(0, self.__total_weight)

        value = 0
        for x in self.__weight_item_pairs:
            value += x[0]

            if value > target:
                return random.choice(x[1])

        raise ValueError("No selection")

    @property
    def weight_item_pairs(self):
        return self.__weight_item_pairs

    @weight_item_pairs.setter
    def weight_item_pairs(self, new_pairs: list[Tuple[int, list[ItemID]]]):
        self.__weight_item_pairs = new_pairs
        self.__total_weight = sum(x[0] for x in new_pairs)


# Saving keystrokes since we're making another big list
_ITier = ItemTier
_itl = _item_tier_list
_low_gear = _itl[_ITier.LOW_GEAR]
_low_cons = _itl[_ITier.LOW_CONSUMABLE]
_pass_gear = _itl[_ITier.PASSABLE_GEAR]
_pass_cons = _itl[_ITier.PASSABLE_CONSUMABLE]
_mid_gear = _itl[_ITier.MID_GEAR]
_mid_cons = _itl[_ITier.MID_CONSUMABLE]
_good_gear = _itl[_ITier.GOOD_GEAR]
_good_cons = _itl[_ITier.GOOD_CONSUMABLE]
_high_gear = _itl[_ITier.HIGH_GEAR]
_high_cons = _itl[_ITier.HIGH_CONSUMABLE]
_awe_gear = _itl[_ITier.AWESOME_GEAR]
_awe_cons = _itl[_ITier.AWESOME_CONSUMABLE]

# Lookup for treasure distributions that change based on difficulty
LTier = TreasureLocTier

# Set up a dummy lookup table.
#   1st level: Difficulty Easy, Norm, Hard
#   2nd level: low, lowmid, mid, midhigh, highawe tiers
_treas_dists: list[list[TreasureDist]] = [
    [
        TreasureDist((1, [ItemID.MOP]))
        for tier in list(TreasureLocTier)
        if tier in [LTier.LOW, LTier.LOW_MID, LTier.MID, LTier.MID_HIGH,
                    LTier.HIGH_AWESOME]
    ]
    for i in list(rset.Difficulty)
]

# Total weight 11
_treas_dists[rset.Difficulty.EASY][TreasureLocTier.LOW] = \
    TreasureDist(
        (5, _pass_cons+_mid_cons),
        (6, _pass_gear+_mid_gear)
    )
# Total weight 110
_treas_dists[rset.Difficulty.EASY][TreasureLocTier.LOW_MID] = \
    TreasureDist(
        (50, _mid_cons+_good_cons),
        (15, _good_gear),
        (45, _mid_gear)
    )
# Total weight 110
_treas_dists[rset.Difficulty.EASY][TreasureLocTier.MID] = \
    TreasureDist(
        (50, _good_cons + _high_cons),
        (3, _awe_gear),
        (12, _high_gear),
        (45, _good_gear)
    )
# Total weight 110
_treas_dists[rset.Difficulty.EASY][TreasureLocTier.MID_HIGH] = \
    TreasureDist(
        (50, _good_cons + _high_cons),
        (3, _awe_gear),
        (12, _high_gear),
        (45, _good_gear)
    )
# Total weight 110
_treas_dists[rset.Difficulty.EASY][TreasureLocTier.HIGH_AWESOME] = \
    TreasureDist(
        (24, _good_cons+_high_cons+_awe_cons),  # 24/40 = 6/10
        (4, _awe_gear),                         #  4/40 = 1/4*4/10
        (12, _high_gear+_good_gear),            # 12/40 = 3/4*4/10
    )
# Total weight 110
_treas_dists[rset.Difficulty.NORMAL][TreasureLocTier.LOW] = \
    TreasureDist(
        (50, _low_cons),
        (60, _low_gear)
    )
# Total weight 110
_treas_dists[rset.Difficulty.NORMAL][TreasureLocTier.LOW_MID] = \
    TreasureDist(
        (50, _low_cons + _pass_cons),
        (15, _mid_gear),
        (45, _pass_gear)
    )
# Total weight 110
_treas_dists[rset.Difficulty.NORMAL][TreasureLocTier.MID] = \
    TreasureDist(
        (50, _pass_cons + _mid_cons),
        (3, _high_gear),
        (12, _good_gear),
        (45, _mid_gear)
    )
# Total weight 110
_treas_dists[rset.Difficulty.NORMAL][TreasureLocTier.MID_HIGH] = \
    TreasureDist(
        (50, _mid_cons + _good_cons),
        (3, _awe_gear),
        (12, _high_gear),
        (45, _good_gear)
    )
# Total weight 1100, could simplify but this is clean enough
_treas_dists[rset.Difficulty.NORMAL][TreasureLocTier.HIGH_AWESOME] = \
    TreasureDist(
        (400, _good_cons + _high_cons + _awe_cons),
        (175, _awe_gear),
        (525, _good_gear + _high_gear)
    )
# Total weight 11
_treas_dists[rset.Difficulty.HARD][TreasureLocTier.LOW] = \
    TreasureDist(
        (5, _low_cons),
        (6, _low_gear)
    )
# Total weight 11
_treas_dists[rset.Difficulty.HARD][TreasureLocTier.LOW_MID] = \
    TreasureDist(
        (5, _low_cons+_pass_cons),
        (6, _pass_gear)
    )
# Total weight 11
_treas_dists[rset.Difficulty.HARD][TreasureLocTier.MID] = \
    TreasureDist(
        (5, _pass_cons + _mid_cons),
        (6, _mid_gear)
    )
# Total weight 11
_treas_dists[rset.Difficulty.HARD][TreasureLocTier.MID_HIGH] = \
    TreasureDist(
        (5, _mid_cons + _good_cons),
        (6, _mid_gear + _good_gear)
    )
# Total weight 1100, could simplify but clean enough
_treas_dists[rset.Difficulty.HARD][TreasureLocTier.HIGH_AWESOME] = \
    TreasureDist(
        (400, _mid_cons + _good_cons + _high_cons + _awe_cons),
        (175, _awe_gear),
        (525, _mid_gear + _good_gear + _high_gear)
    )

_tab_dist = TreasureDist(
    (1, [ItemID.SPEED_TAB]),
    (10, [ItemID.POWER_TAB]),
    (10, [ItemID.MAGIC_TAB])
)

_sealed_dist = TreasureDist(
    (1, _item_tier_list[ItemTier.SEALED_TREASURE])
)


def get_treasure_distribution(settings: rset.Settings,
                              treasure_tier: TreasureLocTier):
    """Get a treasure distribution given the game settings and a tier."""
    difficulty = settings.item_difficulty
    tab_treasures = rset.GameFlags.TAB_TREASURES in settings.gameflags

    if tab_treasures:
        return _tab_dist
    if treasure_tier in [LTier.LOW, LTier.LOW_MID, LTier.MID,
                         LTier.MID_HIGH, LTier.HIGH_AWESOME]:
        return _treas_dists[difficulty][treasure_tier]
    if treasure_tier == LTier.SEALED:
        return _sealed_dist

    raise ValueError(f"{treasure_tier} is not a valid TreasureLocTier")
