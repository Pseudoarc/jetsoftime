from __future__ import annotations

import random as rand

import ctenums
import logictypes
from treasures import treasuredata as td
import randoconfig as cfg
import randosettings as rset
import vanillarando.vrtreasure as vrtreasure


TID = ctenums.TreasureID
ItemID = ctenums.ItemID


# When LW is selected and Frog/Robo is in the game, add their key item gear
# (robo ribbon, hero medal, grandleon) to the config.  Must be called after
# key items and characters are placed.
def add_lw_key_item_gear(settings: rset.Settings,
                         config: cfg.RandoConfig):

    if settings.game_mode != rset.GameMode.LOST_WORLDS:
        return

    # RecruitID = ctenums.RecruitID
    # lw_char_recruits = [RecruitID.STARTER_1, RecruitID.STARTER_2,
    #                     RecruitID.PROTO_DOME, RecruitID.DACTYL_NEST]
    # lw_chars = [x.held_char
    #             for x in [
    #                 config.char_assign_dict[y] for y in lw_char_recruits
    #             ]]

    # CharID = ctenums.CharID

    # if not (CharID.ROBO in lw_chars or CharID.FROG in lw_chars):
    #     return

    # Get a list of all LW TIDs where the gear can go.  For now we're going
    # to say that those are Chronosanity locations
    
    # TODO: Can we read this from the logic?
    lw_tids = [
        TID.MYSTIC_MT_STREAM, TID.FOREST_MAZE_1, TID.FOREST_MAZE_2,
        TID.FOREST_MAZE_3, TID.FOREST_MAZE_4, TID.FOREST_MAZE_5,
        TID.FOREST_MAZE_6, TID.FOREST_MAZE_7, TID.FOREST_MAZE_8,
        TID.FOREST_MAZE_9, TID.REPTITE_LAIR_REPTITES_1,
        TID.REPTITE_LAIR_REPTITES_2,
        TID.DACTYL_NEST_1, TID.DACTYL_NEST_2, TID.DACTYL_NEST_3,
        TID.MT_WOE_1ST_SCREEN, TID.MT_WOE_2ND_SCREEN_1,
        TID.MT_WOE_2ND_SCREEN_2, TID.MT_WOE_2ND_SCREEN_3,
        TID.MT_WOE_2ND_SCREEN_4, TID.MT_WOE_2ND_SCREEN_5,
        TID.MT_WOE_3RD_SCREEN_1, TID.MT_WOE_3RD_SCREEN_2,
        TID.MT_WOE_3RD_SCREEN_3, TID.MT_WOE_3RD_SCREEN_4,
        TID.MT_WOE_3RD_SCREEN_5, TID.MT_WOE_FINAL_1,
        TID.MT_WOE_FINAL_2, TID.ARRIS_DOME_RATS,
        TID.ARRIS_DOME_FOOD_STORE, TID.SEWERS_1, TID.SEWERS_2,
        TID.SEWERS_3, TID.LAB_16_1, TID.LAB_16_2, TID.LAB_16_3,
        TID.LAB_16_4, TID.LAB_32_1, TID.GENO_DOME_1F_1,
        TID.GENO_DOME_1F_2, TID.GENO_DOME_1F_3, TID.GENO_DOME_1F_4,
        TID.GENO_DOME_ROOM_1, TID.GENO_DOME_ROOM_2, TID.GENO_DOME_PROTO4_1,
        TID.GENO_DOME_PROTO4_2, TID.GENO_DOME_2F_1, TID.GENO_DOME_2F_2,
        TID.GENO_DOME_2F_3, TID.GENO_DOME_2F_4, TID.FACTORY_LEFT_AUX_CONSOLE,
        TID.FACTORY_LEFT_SECURITY_RIGHT, TID.FACTORY_LEFT_SECURITY_LEFT,
        TID.FACTORY_RUINS_GENERATOR, TID.FACTORY_RIGHT_DATA_CORE_1,
        TID.FACTORY_RIGHT_DATA_CORE_2, TID.FACTORY_RIGHT_FLOOR_TOP,
        TID.FACTORY_RIGHT_FLOOR_LEFT, TID.FACTORY_RIGHT_FLOOR_BOTTOM,
        TID.FACTORY_RIGHT_FLOOR_SECRET, TID.FACTORY_RIGHT_CRANE_LOWER,
        TID.FACTORY_RIGHT_CRANE_UPPER, TID.FACTORY_RIGHT_INFO_ARCHIVE,
        TID.BANGOR_DOME_SEAL_1, TID.BANGOR_DOME_SEAL_2,
        TID.BANGOR_DOME_SEAL_3, TID.TRANN_DOME_SEAL_1,
        TID.TRANN_DOME_SEAL_2, TID.ARRIS_DOME_SEAL_1, TID.ARRIS_DOME_SEAL_2,
        TID.ARRIS_DOME_SEAL_3, TID.ARRIS_DOME_SEAL_4
    ]

    lw_key_tids = [
        TID.REPTITE_LAIR_KEY, TID.MT_WOE_KEY, TID.ARRIS_DOME_DOAN_KEY,
        TID.SUN_PALACE_KEY, TID.GENO_DOME_KEY
    ]

    ItemID = ctenums.ItemID
    lw_keys = [
        ItemID.PENDANT, ItemID.RUBY_KNIFE, ItemID.DREAMSTONE,
        ItemID.CLONE, ItemID.C_TRIGGER
    ]

    if rset.GameFlags.CHRONOSANITY in settings.gameflags:
        lw_tids += lw_key_tids

    lw_avail_tids = [x for x in lw_tids
                     if config.treasure_assign_dict[x].reward
                     not in lw_keys]

    # added_treasures = []
    # if CharID.FROG in lw_chars:
    #     added_treasures += [ItemID.HERO_MEDAL, ItemID.MASAMUNE_2]

    # if CharID.ROBO in lw_chars:
    #     added_treasures += [ItemID.ROBORIBBON]

    added_treasures = [ItemID.HERO_MEDAL, ItemID.MASAMUNE_2,
                       ItemID.ROBORIBBON]

    added_tids = rand.sample(lw_avail_tids, len(added_treasures))

    for ind, tid in enumerate(added_tids):
        item = added_treasures[ind]
        config.treasure_assign_dict[tid].reward = item

        # We use Cronosanity's location types in the spoiler log, so we
        # sort of hack some new ones on to have the new items.
        loc = logictypes.Location(tid)
        loc.setKeyItem(item)
        config.key_item_locations.append(loc)


def get_treasure_tier_dict(settings: rset.Settings):

    if settings.game_mode == rset.GameMode.VANILLA_RANDO:
        treasure_tier_dict = vrtreasure.get_vanilla_treasure_tiers()
    else:
        treasure_tier_dict = {
            tier: td.get_treasures_in_tier(tier)
            for tier in td.TreasureLocTier
        }

    # TODO: Instead of implementing complicated easy/normal/hard difficulty,
    #       Let's just handle difficulty by moving boxes up/down in tier
    return treasure_tier_dict


def write_treasures_to_config(settings: rset.Settings,
                              config: cfg.RandoConfig):

    gil = td.get_item_list
    ITier = td.ItemTier

    assign = config.treasure_assign_dict

    treasure_tier_dict = get_treasure_tier_dict(settings)

    # Do standard treasure chests
    for tier in td.TreasureLocTier:
        treasures = treasure_tier_dict[tier]
        dist = td.get_treasure_distribution(settings, tier)

        for treasure in treasures:
            assign[treasure].reward = dist.get_random_item()

    # Now, put treasures in key item spots.  These may get overwritten by
    # the logic.
    mid_gear = gil(ITier.MID_GEAR)
    for treasure_id in (TID.SNAIL_STOP_KEY, TID.LAZY_CARPENTER,
                        TID.FROGS_BURROW_LEFT):
        assign[treasure_id].reward = rand.choice(mid_gear)

    good_gear = gil(ITier.GOOD_GEAR)
    for treasure_id in (TID.TABAN_KEY, TID.ZENAN_BRIDGE_KEY,
                        TID.DENADORO_MTS_KEY):
        assign[treasure_id].reward = rand.choice(good_gear)

    high_gear = gil(ITier.HIGH_GEAR)
    for treasure_id in (TID.REPTITE_LAIR_KEY, TID.GIANTS_CLAW_KEY,
                        TID.ARRIS_DOME_DOAN_KEY, TID.SUN_PALACE_KEY,
                        TID.KINGS_TRIAL_KEY, TID.FIONA_KEY):
        assign[treasure_id].reward = rand.choice(high_gear)

    awesome_gear = gil(ITier.AWESOME_GEAR)
    for treasure_id in (TID.GENO_DOME_KEY, TID.MT_WOE_KEY,
                        TID.MELCHIOR_KEY):
        assign[treasure_id].reward = rand.choice(awesome_gear)

    # Now do special treasures.  These don't have complicated distributions.
    # The distribution is just a random choice from the items associated with
    # the  treasure tier.

    # Build up list of special TIDs and parallel list of the items associated
    # with those spots.
    specials = [
        TID.TABAN_GIFT_HELM, TID.TABAN_GIFT_WEAPON,
        TID.TRADING_POST_ARMOR, TID.TRADING_POST_HELM,
        TID.TRADING_POST_ACCESSORY,
        TID.TRADING_POST_MELEE_WEAPON,
        TID.TRADING_POST_RANGED_WEAPON,
        TID.TRADING_POST_TAB,
        TID.JERKY_GIFT
    ]

    item_lists = [
        gil(ITier.TABAN_HELM), gil(ITier.TABAN_WEAPON),
        gil(ITier.TRADE_ARMOR), gil(ITier.TRADE_HELM),
        gil(ITier.TRADE_ACCESSORY),
        gil(ITier.TRADE_MELEE),
        gil(ITier.TRADE_RANGED),
        gil(ITier.TRADE_TAB),
        gil(ITier.JERKY_REWARD)
    ]

    for ind, tid in enumerate(specials):
        items = item_lists[ind]
        assign[tid].reward = rand.choice(items)

    # finally rocks
    if rset.GameFlags.ROCKSANITY in settings.gameflags:
        # rock locations can be treasures in Rocksanity (e.g. for Chronosanity)
        # use same treasure tier as other KI in same/similar location
        assign[TID.DENADORO_ROCK].reward = rand.choice(good_gear)
        assign[TID.GIANTS_CLAW_ROCK].reward = rand.choice(high_gear)
        assign[TID.LARUBA_ROCK].reward = rand.choice(high_gear)
        assign[TID.KAJAR_ROCK].reward = rand.choice(awesome_gear)
        assign[TID.BLACK_OMEN_TERRA_ROCK].reward = rand.choice(awesome_gear)
    else:
        rock_tids = [TID.DENADORO_ROCK, TID.GIANTS_CLAW_ROCK,
                     TID.LARUBA_ROCK, TID.KAJAR_ROCK, TID.BLACK_OMEN_TERRA_ROCK]

        rocks = [ItemID.GOLD_ROCK, ItemID.BLUE_ROCK,
                 ItemID.SILVERROCK, ItemID.BLACK_ROCK, ItemID.WHITE_ROCK]
        rand.shuffle(rocks)

        for ind, tid in enumerate(rock_tids):
            assign[tid].reward = rocks[ind]


def ptr_to_enum(ptr_list):
    # Turn old-style pointer lists into enum lists
    treasuretier = ptr_list
    chestid = set([(x-0x35f404)//4 for x in treasuretier])
    print(' '.join(f"{x:02X}" for x in chestid))

    config = cfg.RandoConfig()
    tdict = config.treasure_assign_dict

    treasureids = [x for x in tdict.keys()
                   if isinstance(tdict[x], cfg.ChestTreasure)
                   and tdict[x].chest_index in chestid]

    used_ids = [tdict[x].chest_index for x in treasureids]
    unused_ids = [x for x in chestid if x not in used_ids]

    # print(' '.join(f"{x:02X}" for x in used_ids))
    print(' '.join(f"{x:02X}" for x in unused_ids))
    input()

    for x in treasureids:
        y = repr(x)
        y = y.split(':')[0].replace('<', '').replace('TreasureID', 'TID')

        print(f"{y},")

    print(len(chestid), len(treasureids))


# Helper function just used when converting from old pointer lists to
# ItemID lists.
def item_num_to_enum(item_list):
    # Turn int list to ItemID list

    enum_list = []

    for x in item_list:
        y = ctenums.ItemID(x)
        enum_list.append(y)

    for x in enum_list:
        y = repr(x).split(':')[0].replace('<', '')
        print(f"{y},")


def find_script_ptrs(ptr_list):

    for ptr in ptr_list:
        chest_index = (ptr-0x35f404)//4
        if 0 > chest_index or chest_index > 0xF8:
            print(f"{ptr:06X}")
