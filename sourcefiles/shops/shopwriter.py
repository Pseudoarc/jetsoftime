from __future__ import annotations

import math
import random as rand

from common.random import RNGType
from ctenums import ItemID, ShopID
from treasures import treasuredata as td

import randoconfig as cfg
import randosettings as rset


def write_shops_to_config(settings: rset.Settings,
                          config: cfg.RandoConfig,
                          rng: RNGType):

    # Bunch of declarations.  They're here instead of in global scope after
    # the great shelling of November 2021.

    # Get short names for item lists for defining distributions later.
    ITier = td.ItemTier
    # no shop sells low gear
    # low_gear = td.get_item_list(ITier.LOW_GEAR)

    # power meals are not sellable
    low_cons = td.get_item_list(ITier.LOW_CONSUMABLE)
    low_cons.remove(ItemID.POWER_MEAL)

    pass_gear = td.get_item_list(ITier.PASSABLE_GEAR)
    pass_cons = td.get_item_list(ITier.PASSABLE_CONSUMABLE)
    mid_gear = td.get_item_list(ITier.MID_GEAR)
    mid_cons = td.get_item_list(ITier.MID_CONSUMABLE)

    # greendream is not sellable
    good_gear = td.get_item_list(ITier.GOOD_GEAR)
    good_gear.remove(ItemID.GREENDREAM)

    good_cons = td.get_item_list(ITier.GOOD_CONSUMABLE)
    high_gear = td.get_item_list(ITier.HIGH_GEAR)

    # Tabs are not sellable
    high_cons = td.get_item_list(ITier.HIGH_CONSUMABLE)
    for x in [ItemID.POWER_TAB, ItemID.MAGIC_TAB, ItemID.SPEED_TAB]:
        high_cons.remove(x)

    awe_gear = td.get_item_list(ITier.AWESOME_GEAR)
    awe_cons = td.get_item_list(ITier.AWESOME_CONSUMABLE)

    # Regular Shop Setup
    regular_shop_ids = [
        ShopID.TRUCE_MARKET_600, ShopID.ARRIS_DOME, ShopID.DORINO,
        ShopID.PORRE_600, ShopID.PORRE_1000, ShopID.CHORAS_INN_1000,
        ShopID.CHORAS_MARKET_600, ShopID.MILENNIAL_FAIR_ARMOR,
        ShopID.MILLENIAL_FAIR_ITEMS,
    ]

    regular_dist = td.TreasureDist(
        (6, low_cons + pass_cons),
        (4, pass_gear + mid_gear)
    )
    regular_guaranteed: list[ItemID] = []

    # Good Shop Setup.  Fiona and Fritz have lapis guaranteed.
    good_shop_ids = [
        ShopID.MELCHIORS_HUT, ShopID.IOKA_VILLAGE, ShopID.NU_NORMAL_KAJAR,
        ShopID.ENHASA, ShopID.EARTHBOUND_VILLAGE, ShopID.TRANN_DOME,
        ShopID.MEDINA_MARKET,
    ]

    good_lapis_shop_ids = [
        ShopID.FIONAS_SHRINE, ShopID.TRUCE_MARKET_1000,
    ]

    good_dist = td.TreasureDist(
        (5, pass_cons + mid_cons),
        (5, mid_gear + good_gear)
    )
    good_guaranteed: list[ItemID] = []
    good_lapis_guaranteed = [ItemID.LAPIS]

    # Best Shop Setup
    best_shop_ids = [
        ShopID.NU_SPECIAL_KAJAR,
        # ShopID.LAST_VILLAGE_UPDATED,  # This shop is actually unused
        ShopID.NU_BLACK_OMEN,
    ]

    best_dist = td.TreasureDist(
        (5, good_cons + high_cons + awe_cons),
        (5, good_gear + high_gear + awe_gear)
    )
    best_guaranteed = [ItemID.AMULET]

    # Unused Shop Setup
    unused_shop_ids = [
        ShopID.LAST_VILLAGE_UPDATED, ShopID.EMPTY_12, ShopID.EMPTY_14,
    ]

    # Melchior's special shop
    shop_manager = config.shop_manager
    shop_manager.set_shop_items(ShopID.MELCHIOR_FAIR,
                                get_melchior_shop_items())

    # Now write out the regular, good, best shops.
    # Parallel lists for type, dist, and guarantees.  This is a little ugly
    # and maybe each shop should get its own guarantee list instead of by tier.
    shop_types = [regular_shop_ids, good_shop_ids,
                  good_lapis_shop_ids, best_shop_ids]
    shop_dists = [regular_dist, good_dist, good_dist, best_dist]
    shop_guaranteed = [regular_guaranteed, good_guaranteed,
                       good_lapis_guaranteed, best_guaranteed]

    for i in range(len(shop_types)):
        for shop in shop_types[i]:
            guaranteed = shop_guaranteed[i]
            dist = shop_dists[i]
            items = get_shop_items(guaranteed, dist, rng)

            shop_manager.set_shop_items(shop, items)

    for shop in unused_shop_ids:
        shop_manager.set_shop_items(shop, [ItemID.MOP])

    # With the whole shop list in hand, you can do some global guarantees
    # here if desired.  For example, guarantee ethers/midtonics in LW.


def get_melchior_shop_items():

    swords = [ItemID.FLASHBLADE, ItemID.PEARL_EDGE,
              ItemID.RUNE_BLADE, ItemID.DEMON_HIT]
    robo_arms = [ItemID.STONE_ARM, ItemID.DOOMFINGER, ItemID.MAGMA_HAND]
    guns = [ItemID.RUBY_GUN, ItemID.DREAM_GUN, ItemID.MEGABLAST]
    bows = [ItemID.SAGE_BOW, ItemID.DREAM_BOW, ItemID.COMETARROW]
    katanas = [ItemID.FLINT_EDGE, ItemID.DARK_SABER, ItemID.AEON_BLADE]

    item_list = [
        rand.choice(swords),
        rand.choice(robo_arms),
        rand.choice(guns),
        rand.choice(bows),
        rand.choice(katanas),
        ItemID.REVIVE,
        ItemID.SHELTER
    ]

    return item_list


def get_shop_items(guaranteed_items: list[ItemID], item_dist,
                   rng: RNGType):
    shop_items = guaranteed_items[:]

    # potentially shop size should be passed in.  Keep the random isolated.
    item_count = rand.randrange(3, 9) - len(shop_items)

    for item_index in range(item_count):
        item = item_dist.get_random_item(rng)

        # Avoid duplicate items.
        while item in shop_items:
            item = item_dist.get_random_item(rng)

        shop_items.append(item)

    # Typically better items have a higher index.  The big exception is
    # that consumables are at the very top.  That's ok though.
    # TODO: Write a custom sort for ItemIDs
    return sorted(shop_items, reverse=True)


#
# Get a random price from 1-65000.  This function tends to
# bias lower numbers to avoid everything being prohibitively expensive.
#
def getRandomPrice():
    r1 = rand.uniform(0, 1)
    r2 = rand.uniform(0, 1)
    return math.floor(abs(r1 - r2) * 65000 + 1)
