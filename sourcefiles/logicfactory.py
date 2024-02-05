import typing
from typing import List, Optional, Type
from math import ceil

import ctenums
from logictypes import BaselineLocation, Location, LocationGroup,\
    LinkedLocation, Game
from treasures import treasuredata as td

from ctenums import TreasureID as TID, CharID as Characters, ItemID, \
    RecruitID
import randosettings as rset
import randoconfig as cfg


class ImpossibleGameConfigException(Exception):
    pass

#
# The LogicFactory is used by the logic writer to get a GameConfig
# object for the flags that the user selected.  The returned GameConfig
# object holds a list of all LocationGroups, KeyItems, and a configured
# Game object.  These are used by the logic writer to handle key item
# placement.
#
# TODO: There is some duplication in locations between the different GameConfig
#       objects.  Optimally the locations would be defined once and referenced
#       by the GameConfigs that cared about them.
#
# UPDATE: There is still some duplication in creating locations across game
#         modes, but the Locations are all referencing the ctenums.TreasureID
#         enum.  This is probably good enough.
#

#
# The GameConfig class holds the locations and key items associated with a
# game type.
#
class GameConfig:
    def __init__(self,
                 settings: rset.Settings,
                 config: cfg.RandoConfig):
        self.keyItemList: list[ItemID] = []
        self.locationGroups: list[LocationGroup] = []
        self.settings = settings
        self.config = config
        self.game: Game
        self.initLocations()
        self.initKeyItems()
        self.resolveExtraKeyItems()
        self.initGame()

    #
    # Subclasses will override this method to
    # initialize LocationGroups for their specific mode.
    #
    def initLocations(self):
        raise NotImplementedError()


    #
    # Subclasses will override this method to
    # handle the case that more key items than spots exist
    #
    def resolveExtraKeyItems(self):
        raise NotImplementedError()


    #
    # Subclasses will override this method to
    # initialize key items for their specific mode.
    #
    def initKeyItems(self):
        raise NotImplementedError()

    #
    # Subclasses will override this method to
    # configure a game object for their specific mode.
    #
    def initGame(self):
        raise NotImplementedError()

    #
    # Update the key item list based on the current state of the game.
    # Example: Chronosanity removes key item bias after some items are placed
    #
    # return: A potentially modified list of key items (e.g. weights)
    #
    def updateKeyItems(self, keyItemList):
        # Since most modes do not bias anything, I'm setting the default
        # to do nothing.  Sublcasses will override.
        return keyItemList

    #
    # Get the LocationGroups associated with this game mode.
    #
    # return: A list of LocationGroup objects for this mode
    #
    def getLocations(self):
        return self.locationGroups

    #
    # Get the LocationGroup with the given name.
    #
    # return: The LocationGroup object with the given name
    #
    def getLocationGroup(self, name: str) -> Optional[LocationGroup]:
        try:
            return next(x for x in self.locationGroups
                        if x.name == name)
        except StopIteration:
            return None

    #
    # Get the list of key items associated with this game mode.
    #
    # return: A list of KeyItem objects for this mode
    #
    def getKeyItemList(self):
        return self.keyItemList

    #
    # Get the Game object associated with this mode.
    #
    # return: A configured Game object for this mode
    #
    def getGame(self) -> Game:
        return self.game

    #
    # Remove all LocationGroups with the given names.
    #
    # param: names - a name or iterable of names of LocationGroups to remove
    #
    def removeLocationGroups(
            self,
            names: typing.Union[str, typing.Iterable[str]]):

        if isinstance(names, str):
            names = [names]

        removed_inds = (self.locationGroups.index(x)
                        for x in self.locationGroups
                        if x.name in names)

        for ind in sorted(removed_inds, reverse=True):
            del(self.locationGroups[ind])
# end GameLogic class


#
# This class represents the game configuration for a
# standard Chronosanity game.
#
class ChronosanityGameConfig(GameConfig):
    def __init__(self, settings: rset.Settings,
                 config: cfg.RandoConfig):
        self.charLocations = config.char_assign_dict
        self.earlyPendant = rset.GameFlags.FAST_PENDANT in settings.gameflags
        self.lockedChars = rset.GameFlags.LOCKED_CHARS in settings.gameflags
        GameConfig.__init__(self, settings, config)
        apply_epoch_fail(self)

    def initLocations(self):
        # Dark Ages
        # Mount Woe does not go away in the randomizer, so it
        # is being considered for key item drops.
        darkagesLocations = \
            LocationGroup("Darkages", 30,
                          lambda game: game.canAccessMtWoe())
        (
            darkagesLocations
            .addLocation(Location(TID.MT_WOE_1ST_SCREEN))
            .addLocation(Location(TID.MT_WOE_2ND_SCREEN_1))
            .addLocation(Location(TID.MT_WOE_2ND_SCREEN_2))
            .addLocation(Location(TID.MT_WOE_2ND_SCREEN_3))
            .addLocation(Location(TID.MT_WOE_2ND_SCREEN_4))
            .addLocation(Location(TID.MT_WOE_2ND_SCREEN_5))
            .addLocation(Location(TID.MT_WOE_3RD_SCREEN_1))
            .addLocation(Location(TID.MT_WOE_3RD_SCREEN_2))
            .addLocation(Location(TID.MT_WOE_3RD_SCREEN_3))
            .addLocation(Location(TID.MT_WOE_3RD_SCREEN_4))
            .addLocation(Location(TID.MT_WOE_3RD_SCREEN_5))
            .addLocation(Location(TID.MT_WOE_FINAL_1))
            .addLocation(Location(TID.MT_WOE_FINAL_2))
            .addLocation(Location(TID.MT_WOE_KEY))
        )

        # Fiona Shrine (Key Item only)
        fionaShrineLocations = \
            LocationGroup("Fionashrine", 2,
                          lambda game: game.canAccessFionasShrine())
        (
            fionaShrineLocations
            .addLocation(Location(TID.FIONA_KEY))
        )

        # Future
        futureOpenLocations = \
            LocationGroup("FutureOpen", 20,
                          lambda game: game.canAccessFuture())
        (
            futureOpenLocations
            # Chests
            .addLocation(Location(TID.ARRIS_DOME_RATS))
            .addLocation(Location(TID.ARRIS_DOME_FOOD_STORE))
            # KeyItems
            .addLocation(Location(TID.ARRIS_DOME_DOAN_KEY))
            .addLocation(Location(TID.SUN_PALACE_KEY))
        )

        futureSewersLocations = \
            LocationGroup("FutureSewers", 9,
                          lambda game: game.canAccessFuture())
        (
            futureSewersLocations
            .addLocation(Location(TID.SEWERS_1))
            .addLocation(Location(TID.SEWERS_2))
            .addLocation(Location(TID.SEWERS_3))
        )

        futureLabLocations = \
            LocationGroup("FutureLabs", 15,
                          lambda game: game.canAccessFuture())
        (
            futureLabLocations
            .addLocation(Location(TID.LAB_16_1))
            .addLocation(Location(TID.LAB_16_2))
            .addLocation(Location(TID.LAB_16_3))
            .addLocation(Location(TID.LAB_16_4))
            .addLocation(Location(TID.LAB_32_1))
            # 1000AD, opened after trial - putting it here to dilute the
            # lab pool a bit.
            .addLocation(Location(TID.PRISON_TOWER_1000))
            # Race log chest is not included.
            # .addLocation(Location(TID.LAB_32_RACE_LOG))
        )

        genoDomeLocations = \
            LocationGroup("GenoDome", 33, lambda game: game.canAccessFuture())
        (
            genoDomeLocations
            .addLocation(Location(TID.GENO_DOME_1F_1))
            .addLocation(Location(TID.GENO_DOME_1F_2))
            .addLocation(Location(TID.GENO_DOME_1F_3))
            .addLocation(Location(TID.GENO_DOME_1F_4))
            .addLocation(Location(TID.GENO_DOME_ROOM_1))
            .addLocation(Location(TID.GENO_DOME_ROOM_2))
            .addLocation(Location(TID.GENO_DOME_PROTO4_1))
            .addLocation(Location(TID.GENO_DOME_PROTO4_2))
            .addLocation(Location(TID.GENO_DOME_2F_1))
            .addLocation(Location(TID.GENO_DOME_2F_2))
            .addLocation(Location(TID.GENO_DOME_2F_3))
            .addLocation(Location(TID.GENO_DOME_2F_4))
            .addLocation(Location(TID.GENO_DOME_KEY))
        )

        # Changing this from access future to access proto because of Vanilla
        # mode/extended keys.
        factoryLocations = \
            LocationGroup("Factory", 30, lambda game: game.canAccessProtoDome())
        (
            factoryLocations
            .addLocation(Location(TID.FACTORY_LEFT_AUX_CONSOLE))
            .addLocation(Location(TID.FACTORY_LEFT_SECURITY_RIGHT))
            .addLocation(Location(TID.FACTORY_LEFT_SECURITY_LEFT))
            .addLocation(Location(TID.FACTORY_RUINS_GENERATOR))
            .addLocation(Location(TID.FACTORY_RIGHT_DATA_CORE_1))
            .addLocation(Location(TID.FACTORY_RIGHT_DATA_CORE_2))
            .addLocation(Location(TID.FACTORY_RIGHT_FLOOR_TOP))
            .addLocation(Location(TID.FACTORY_RIGHT_FLOOR_LEFT))
            .addLocation(Location(TID.FACTORY_RIGHT_FLOOR_BOTTOM))
            .addLocation(Location(TID.FACTORY_RIGHT_FLOOR_SECRET))
            .addLocation(Location(TID.FACTORY_RIGHT_CRANE_LOWER))
            .addLocation(Location(TID.FACTORY_RIGHT_CRANE_UPPER))
            .addLocation(Location(TID.FACTORY_RIGHT_INFO_ARCHIVE))
            # .addLocation(Location(TID.FACTORY_ROBOT_STORAGE))
            # Inaccessible chest
        )

        # GiantsClawLocations
        giantsClawLocations = \
            LocationGroup("Giantsclaw", 30,
                          lambda game: game.canAccessGiantsClaw())
        (
            giantsClawLocations
            # .addLocation(Location(TID.GIANTS_CLAW_KINO_CELL))
            .addLocation(Location(TID.GIANTS_CLAW_TRAPS))
            .addLocation(Location(TID.GIANTS_CLAW_CAVES_1))
            .addLocation(Location(TID.GIANTS_CLAW_CAVES_2))
            .addLocation(Location(TID.GIANTS_CLAW_CAVES_3))
            .addLocation(Location(TID.GIANTS_CLAW_CAVES_4))
            # .addLocation(Location(TID.GIANTS_CLAW_ROCK))
            .addLocation(Location(TID.GIANTS_CLAW_CAVES_5))
            .addLocation(Location(TID.GIANTS_CLAW_KEY))
        )

        # Northern Ruins
        northernRuinsLocations = \
            LocationGroup("NorthernRuins", 8,
                          lambda game: (game.canAccessRuins()))
        (
            northernRuinsLocations
            .addLocation(Location(TID.NORTHERN_RUINS_BASEMENT_600))
            .addLocation(Location(TID.NORTHERN_RUINS_ANTECHAMBER_LEFT_600))
            .addLocation(Location(TID.NORTHERN_RUINS_ANTECHAMBER_LEFT_1000))
            .addLocation(Location(TID.NORTHERN_RUINS_BACK_LEFT_SEALED_600))
            .addLocation(Location(TID.NORTHERN_RUINS_BACK_LEFT_SEALED_1000))
            .addLocation(Location(TID.NORTHERN_RUINS_BACK_RIGHT_SEALED_600))
            .addLocation(Location(TID.NORTHERN_RUINS_BACK_RIGHT_SEALED_1000))
            .addLocation(Location(TID.NORTHERN_RUINS_ANTECHAMBER_SEALED_600))
            .addLocation(Location(TID.NORTHERN_RUINS_ANTECHAMBER_SEALED_1000))
        )

        northernRuinsFrogLocked = \
            LocationGroup(
                "NorthernRuinsFrogLocked", 1,
                lambda game: (game.canAccessRuins()
                              and game.hasCharacter(Characters.FROG))
            )
        (
            northernRuinsFrogLocked
            .addLocation(Location(TID.NORTHERN_RUINS_BASEMENT_1000))
        )

        # Guardia Treasury
        guardiaTreasuryLocations = \
            LocationGroup("GuardiaTreasury", 30,
                          lambda game: game.hasKeyItem(ctenums.ItemID.PRISMSHARD))
        (
            guardiaTreasuryLocations
            .addLocation(Location(TID.GUARDIA_BASEMENT_1))
            .addLocation(Location(TID.GUARDIA_BASEMENT_2))
            .addLocation(Location(TID.GUARDIA_BASEMENT_3))
            .addLocation(Location(TID.GUARDIA_TREASURY_1))
            .addLocation(Location(TID.GUARDIA_TREASURY_2))
            .addLocation(Location(TID.GUARDIA_TREASURY_3))
        )

        guardiaTreasuryKeyLocations = \
            LocationGroup("KingsTrialKey", 6,
                          lambda game: game.canAccessKingsTrial())

        # Ozzie's Fort locations
        # Ozzie's fort is a high level location.
        # For the first four chests, don't consider these locations until the
        # player has either the pendant or gate key.
        # As of 3.1.1, the back two chests are lumped in with the front four.
        earlyOzziesFortLocations = LocationGroup(
            "Ozzie's Fort", 12,
            lambda game: (game.canAccessFuture() or game.canAccessPrehistory())
        )
        (
            earlyOzziesFortLocations
            .addLocation(Location(TID.OZZIES_FORT_GUILLOTINES_1))
            .addLocation(Location(TID.OZZIES_FORT_GUILLOTINES_2))
            .addLocation(Location(TID.OZZIES_FORT_GUILLOTINES_3))
            .addLocation(Location(TID.OZZIES_FORT_GUILLOTINES_4))
            .addLocation(Location(TID.OZZIES_FORT_FINAL_1))
            .addLocation(Location(TID.OZZIES_FORT_FINAL_2))
        )

        # Open locations always available with no access requirements
        # Open locations are split into multiple groups so that weighting
        # can be applied separately to individual areas.
        openLocations = LocationGroup(
            "Open", 10,
            lambda game: True,
            lambda weight: int(weight * 0.2)
        )
        (
            openLocations
            .addLocation(Location(TID.TRUCE_MAYOR_1F))
            .addLocation(Location(TID.TRUCE_MAYOR_2F))
            .addLocation(Location(TID.FOREST_RUINS))
            .addLocation(Location(TID.PORRE_MAYOR_2F))
            .addLocation(Location(TID.TRUCE_CANYON_1))
            .addLocation(Location(TID.TRUCE_CANYON_2))
            .addLocation(Location(TID.FIONAS_HOUSE_1))
            .addLocation(Location(TID.FIONAS_HOUSE_2))
            .addLocation(Location(TID.CURSED_WOODS_1))
            .addLocation(Location(TID.CURSED_WOODS_2))
            .addLocation(Location(TID.FROGS_BURROW_RIGHT))
        )

        openKeys = LocationGroup("OpenKeys", 5, lambda game: True)
        (
            openKeys
            .addLocation(Location(TID.ZENAN_BRIDGE_KEY))
            .addLocation(Location(TID.SNAIL_STOP_KEY))
            .addLocation(Location(TID.LAZY_CARPENTER))
        )

        heckranLocations = LocationGroup("Heckran", 4, lambda game: True)
        (
            heckranLocations
            .addLocation(Location(TID.HECKRAN_CAVE_SIDETRACK))
            .addLocation(Location(TID.HECKRAN_CAVE_ENTRANCE))
            .addLocation(Location(TID.HECKRAN_CAVE_1))
            .addLocation(Location(TID.HECKRAN_CAVE_2))
            .addLocation(Location(TID.TABAN_KEY))
        )

        guardiaCastleLocations = LocationGroup(
            "GuardiaCastle", 3, lambda game: True
        )
        (
            guardiaCastleLocations
            .addLocation(Location(TID.KINGS_ROOM_1000))
            .addLocation(Location(TID.QUEENS_ROOM_1000))
            .addLocation(Location(TID.KINGS_ROOM_600))
            .addLocation(Location(TID.QUEENS_ROOM_600))
            .addLocation(Location(TID.ROYAL_KITCHEN))
            .addLocation(Location(TID.QUEENS_TOWER_600))
            .addLocation(Location(TID.KINGS_TOWER_600))
            .addLocation(Location(TID.KINGS_TOWER_1000))
            .addLocation(Location(TID.QUEENS_TOWER_1000))
            .addLocation(Location(TID.GUARDIA_COURT_TOWER))
        )

        cathedralLocations = LocationGroup(
            "CathedralLocations", 6, lambda game: True
        )
        (
            cathedralLocations
            .addLocation(Location(TID.MANORIA_CATHEDRAL_1))
            .addLocation(Location(TID.MANORIA_CATHEDRAL_2))
            .addLocation(Location(TID.MANORIA_CATHEDRAL_3))
            .addLocation(Location(TID.MANORIA_INTERIOR_1))
            .addLocation(Location(TID.MANORIA_INTERIOR_2))
            .addLocation(Location(TID.MANORIA_INTERIOR_3))
            .addLocation(Location(TID.MANORIA_INTERIOR_4))
            .addLocation(Location(TID.MANORIA_SHRINE_SIDEROOM_1))
            .addLocation(Location(TID.MANORIA_SHRINE_SIDEROOM_2))
            .addLocation(Location(TID.MANORIA_BROMIDE_1))
            .addLocation(Location(TID.MANORIA_BROMIDE_2))
            .addLocation(Location(TID.MANORIA_BROMIDE_3))
            .addLocation(Location(TID.MANORIA_SHRINE_MAGUS_1))
            .addLocation(Location(TID.MANORIA_SHRINE_MAGUS_2))
            .addLocation(Location(TID.YAKRAS_ROOM))
        )

        denadoroLocations = LocationGroup(
            "DenadoroLocations", 6, lambda game: True
        )
        (
            denadoroLocations
            .addLocation(Location(TID.DENADORO_MTS_SCREEN2_1))
            .addLocation(Location(TID.DENADORO_MTS_SCREEN2_2))
            .addLocation(Location(TID.DENADORO_MTS_SCREEN2_3))
            .addLocation(Location(TID.DENADORO_MTS_FINAL_1))
            .addLocation(Location(TID.DENADORO_MTS_FINAL_2))
            .addLocation(Location(TID.DENADORO_MTS_FINAL_3))
            .addLocation(Location(TID.DENADORO_MTS_WATERFALL_TOP_1))
            .addLocation(Location(TID.DENADORO_MTS_WATERFALL_TOP_2))
            .addLocation(Location(TID.DENADORO_MTS_WATERFALL_TOP_3))
            .addLocation(Location(TID.DENADORO_MTS_WATERFALL_TOP_4))
            .addLocation(Location(TID.DENADORO_MTS_WATERFALL_TOP_5))
            .addLocation(Location(TID.DENADORO_MTS_ENTRANCE_1))
            .addLocation(Location(TID.DENADORO_MTS_ENTRANCE_2))
            .addLocation(Location(TID.DENADORO_MTS_SCREEN3_1))
            .addLocation(Location(TID.DENADORO_MTS_SCREEN3_2))
            .addLocation(Location(TID.DENADORO_MTS_SCREEN3_3))
            .addLocation(Location(TID.DENADORO_MTS_SCREEN3_4))
            .addLocation(Location(TID.DENADORO_MTS_AMBUSH))
            .addLocation(Location(TID.DENADORO_MTS_SAVE_PT))
            .addLocation(Location(TID.DENADORO_MTS_KEY))
        )

        # Sealed locations
        sealedLocations = LocationGroup(
            "SealedLocations", 20,
            lambda game: game.canAccessSealedChests(),
            lambda weight: int(weight * 0.3)
        )
        (
            sealedLocations
            # Sealed Doors
            .addLocation(Location(TID.BANGOR_DOME_SEAL_1))
            .addLocation(Location(TID.BANGOR_DOME_SEAL_2))
            .addLocation(Location(TID.BANGOR_DOME_SEAL_3))
            .addLocation(Location(TID.TRANN_DOME_SEAL_1))
            .addLocation(Location(TID.TRANN_DOME_SEAL_2))
            .addLocation(Location(TID.ARRIS_DOME_SEAL_1))
            .addLocation(Location(TID.ARRIS_DOME_SEAL_2))
            .addLocation(Location(TID.ARRIS_DOME_SEAL_3))
            .addLocation(Location(TID.ARRIS_DOME_SEAL_4))
            # Sealed chests
            .addLocation(Location(TID.TRUCE_INN_SEALED_600))
            .addLocation(Location(TID.PORRE_ELDER_SEALED_1))
            .addLocation(Location(TID.PORRE_ELDER_SEALED_2))
            .addLocation(Location(TID.GUARDIA_CASTLE_SEALED_600))
            .addLocation(Location(TID.GUARDIA_FOREST_SEALED_600))
            .addLocation(Location(TID.TRUCE_INN_SEALED_1000))
            .addLocation(Location(TID.PORRE_MAYOR_SEALED_1))
            .addLocation(Location(TID.PORRE_MAYOR_SEALED_2))
            .addLocation(Location(TID.GUARDIA_FOREST_SEALED_1000))
            .addLocation(Location(TID.GUARDIA_CASTLE_SEALED_1000))
            .addLocation(Location(TID.HECKRAN_SEALED_1))
            .addLocation(Location(TID.HECKRAN_SEALED_2))
            # Since the blue pyramid only lets you get one of the two chests,
            # set the key item to be in both of them.
            .addLocation(
                LinkedLocation(Location(TID.PYRAMID_LEFT),
                               Location(TID.PYRAMID_RIGHT))
            )
        )

        # Sealed chest in the magic cave.
        # Requires both powered up pendant and Magus' Castle access
        magicCaveLocations = LocationGroup(
            "Magic Cave", 4,
            lambda game: (game.canAccessSealedChests() and
                          game.canAccessMagusCastle())
        )
        (
            magicCaveLocations
            .addLocation(Location(TID.MAGIC_CAVE_SEALED))
        )

        # Prehistory
        prehistoryForestMazeLocations = LocationGroup(
            "PrehistoryForestMaze", 18, lambda game: game.canAccessPrehistory()
        )
        (
            prehistoryForestMazeLocations
            .addLocation(Location(TID.MYSTIC_MT_STREAM))
            .addLocation(Location(TID.FOREST_MAZE_1))
            .addLocation(Location(TID.FOREST_MAZE_2))
            .addLocation(Location(TID.FOREST_MAZE_3))
            .addLocation(Location(TID.FOREST_MAZE_4))
            .addLocation(Location(TID.FOREST_MAZE_5))
            .addLocation(Location(TID.FOREST_MAZE_6))
            .addLocation(Location(TID.FOREST_MAZE_7))
            .addLocation(Location(TID.FOREST_MAZE_8))
            .addLocation(Location(TID.FOREST_MAZE_9))
        )

        prehistoryReptiteLocations = LocationGroup(
            "PrehistoryReptite", 27, lambda game: game.canAccessPrehistory()
        )
        (
            prehistoryReptiteLocations
            .addLocation(Location(TID.REPTITE_LAIR_REPTITES_1))
            .addLocation(Location(TID.REPTITE_LAIR_REPTITES_2))
            .addLocation(Location(TID.REPTITE_LAIR_KEY))
        )

        # Dactyl Nest already has a character, so give it a relatively low
        # weight compared to the other prehistory locations.
        prehistoryDactylNest = LocationGroup(
            "PrehistoryDactylNest", 6,
            lambda game: game.canAccessPrehistory()
        )
        (
            prehistoryDactylNest
            .addLocation(Location(TID.DACTYL_NEST_1))
            .addLocation(Location(TID.DACTYL_NEST_2))
            .addLocation(Location(TID.DACTYL_NEST_3))
        )

        # MelchiorRefinements
        melchiorsRefinementslocations = LocationGroup(
            "MelchiorRefinements", 15,
            lambda game: game.canAccessMelchiorsRefinements()
        )
        (
            melchiorsRefinementslocations
            .addLocation(Location(TID.MELCHIOR_KEY))
        )

        # Frog's Burrow
        frogsBurrowLocation = LocationGroup(
            "FrogsBurrowLocation", 9,
            lambda game: game.canAccessBurrowItem()
        )
        (
            frogsBurrowLocation
            .addLocation(Location(TID.FROGS_BURROW_LEFT))
        )

        # Prehistory
        self.locationGroups.append(prehistoryForestMazeLocations)
        self.locationGroups.append(prehistoryReptiteLocations)
        self.locationGroups.append(prehistoryDactylNest)

        # Dark Ages
        self.locationGroups.append(darkagesLocations)

        # 600/1000AD
        self.locationGroups.append(fionaShrineLocations)
        self.locationGroups.append(giantsClawLocations)
        self.locationGroups.append(northernRuinsLocations)
        self.locationGroups.append(northernRuinsFrogLocked)
        self.locationGroups.append(guardiaTreasuryLocations)
        self.locationGroups.append(guardiaTreasuryKeyLocations)
        self.locationGroups.append(openLocations)
        self.locationGroups.append(openKeys)
        self.locationGroups.append(heckranLocations)
        self.locationGroups.append(cathedralLocations)
        self.locationGroups.append(guardiaCastleLocations)
        self.locationGroups.append(denadoroLocations)
        self.locationGroups.append(magicCaveLocations)
        self.locationGroups.append(melchiorsRefinementslocations)
        self.locationGroups.append(frogsBurrowLocation)
        self.locationGroups.append(earlyOzziesFortLocations)

        # Future
        self.locationGroups.append(futureOpenLocations)
        self.locationGroups.append(futureLabLocations)
        self.locationGroups.append(futureSewersLocations)
        self.locationGroups.append(genoDomeLocations)
        self.locationGroups.append(factoryLocations)

        # Sealed Locations (chests and doors)
        self.locationGroups.append(sealedLocations)

        flags = self.settings.gameflags
        GF = rset.GameFlags

        if GF.ADD_SUNKEEP_SPOT in flags:
            sunstoneKey = LocationGroup(
                "Sun Keep 2300", 1,
                lambda game: (
                    game.hasKeyItem(ItemID.GATE_KEY) and
                    game.hasKeyItem(ItemID.PENDANT) and
                    game.hasKeyItem(ItemID.MOON_STONE)
                )
            )

            sunstoneKey.addLocation(Location(TID.SUN_KEEP_2300))
            self.locationGroups.append(sunstoneKey)

        if GF.ADD_BEKKLER_SPOT in flags:
            bekklerKey = LocationGroup(
                "BekklersLab", 2,
                lambda game: game.hasKeyItem(ItemID.C_TRIGGER))
            bekklerKey.addLocation(Location(TID.BEKKLER_KEY))

            self.locationGroups.append(bekklerKey)

        if GF.ADD_CYRUS_SPOT in flags:
            northernRuinsLocations = self.getLocationGroup('NorthernRuins')
            northernRuinsLocations.accessRule = _canAccessNorthernRuinsVR

            northernRuinsFrog = self.getLocationGroup(
                'NorthernRuinsFrogLocked')
            northernRuinsFrog.addLocation(Location(TID.CYRUS_GRAVE_KEY))
            northernRuinsFrog.accessRule = _canAccessCyrusGraveVR

        if GF.ADD_OZZIE_SPOT in flags:
            ozziesFort = self.getLocationGroup("Ozzie's Fort")
            ozziesFort.locations.append(Location(TID.OZZIES_FORT_KEY))
            self.locationGroups.append(ozziesFort)

        if GF.ADD_RACELOG_SPOT in flags:
            lab32Key = LocationGroup(
                "RaceLog Chest", 2,
                lambda game: (
                    game.hasKeyItem(ItemID.PENDANT) and
                    game.hasKeyItem(ItemID.BIKE_KEY)
                )
            )
            lab32Key.addLocation(Location(TID.LAB_32_RACE_LOG))
            self.locationGroups.append(lab32Key)

        if GF.SPLIT_ARRIS_DOME in flags:
            future = self.getLocationGroup("FutureOpen")
            future.removeLocationTIDs(TID.ARRIS_DOME_DOAN_KEY)
            future.addLocation(Location(TID.ARRIS_DOME_FOOD_LOCKER_KEY))

            doanKey = LocationGroup("DoanSeed", 1, _canAccessDoanKeyVR)
            doanKey.addLocation(Location(TID.ARRIS_DOME_DOAN_KEY))
            self.locationGroups.append(doanKey)

        if GF.VANILLA_DESERT in flags:
            fiona_shrine = self.getLocationGroup('Fionashrine')
            fiona_shrine.accessRule = _canAccessFionasShrineVR

        if GF.ROCKSANITY in flags:
            self.initLocationsRocksanity()

    def initLocationsRocksanity(self):
        # add rock to existing Denadoro locations
        denadoro = self.getLocationGroup('DenadoroLocations')
        denadoro.weight += 1
        denadoro.addLocation(Location(TID.DENADORO_ROCK))

        # add rock to existing Giants Claw locations
        giantsclaw = self.getLocationGroup('Giantsclaw')
        giantsclaw.weight += 3
        giantsclaw.addLocation(Location(TID.GIANTS_CLAW_ROCK))

        # laruba
        larubaRock = LocationGroup(
            "Laruba Rock", 5, lambda game: game.canAccessPrehistory()
        )
        larubaRock.addLocation(Location(TID.LARUBA_ROCK))

        # kajar
        kajarRock = LocationGroup(
            "Kajar Rock", 5, lambda game: game.canAccessMtWoe()
        )
        kajarRock.addLocation(Location(TID.KAJAR_ROCK))

        self.locationGroups.extend([larubaRock, kajarRock])

        if _couldAccessBlackOmen(self):
            # black omen rock set up to prevent putting go-mode items there
            blackOmenRock = LocationGroup(
                "Black Omen Rock", 1, lambda game: (
                    game.canAccessBlackOmen() and
                    game.canAccessMagusCastle() and
                    game.canAccessTyranoLair()
                )
            )
            blackOmenRock.addLocation(Location(TID.BLACK_OMEN_TERRA_ROCK))
            self.locationGroups.append(blackOmenRock)


    def initKeyItems(self):
        # NOTE:
        # The initial list of key items contains multiples of most of the key
        # items, and not in equal number.  The pendant and gate key are more
        # heavily weighted so that they appear earlier in the run, opening up
        # more potential checks. The ruby knife, dreamstone, clone, and
        # trigger only appear once to reduce the frequency of extremely early
        # go mode from open checks. The hilt and blade show up 2-3 times each,
        # also to reduce early go mode through Magus' Castle to a reasonable
        # number.

        # Seed the list with 5 copies of each item
        # keyItemList = [key for key in (KeyItems)]
        keyItemList = [
            ItemID.GATE_KEY, ItemID.DREAMSTONE, ItemID.RUBY_KNIFE,
            ItemID.PENDANT, ItemID.C_TRIGGER, ItemID.CLONE,
            ItemID.BENT_HILT, ItemID.BENT_SWORD, ItemID.MASAMUNE_2,
            ItemID.HERO_MEDAL, ItemID.ROBORIBBON, ItemID.PRISMSHARD,
            ItemID.TOMAS_POP, ItemID.MOON_STONE, ItemID.JERKY
        ]

        if rset.GameFlags.EPOCH_FAIL in self.settings.gameflags:
            keyItemList.append(ItemID.JETSOFTIME)

        if rset.GameFlags.ADD_SUNKEEP_SPOT in self.settings.gameflags:
            keyItemList.append(ItemID.SUN_STONE)

        if rset.GameFlags.RESTORE_TOOLS in self.settings.gameflags:
            keyItemList.append(ItemID.TOOLS)

        if rset.GameFlags.RESTORE_JOHNNY_RACE in self.settings.gameflags:
            keyItemList.append(ItemID.BIKE_KEY)

        if rset.GameFlags.SPLIT_ARRIS_DOME in self.settings.gameflags:
            keyItemList.append(ItemID.SEED)

        if rset.GameFlags.VANILLA_ROBO_RIBBON in self.settings.gameflags:
            keyItemList.remove(ItemID.ROBORIBBON)

        # keyItemList ends up with 5 of each key item except for
        # lateProgression items
        lateProgression = [ItemID.RUBY_KNIFE, ItemID.DREAMSTONE,
                           ItemID.CLONE, ItemID.C_TRIGGER]
        keyItemList = [x for x in keyItemList if x not in lateProgression]
        keyItemList = 5*keyItemList
        keyItemList.extend(lateProgression)

        # remove some copies of the hilt/blade to reduce early go mode through
        # Magus' Castle
        keyItemList.remove(ItemID.BENT_HILT)
        keyItemList.remove(ItemID.BENT_HILT)
        keyItemList.remove(ItemID.BENT_SWORD)
        keyItemList.remove(ItemID.BENT_SWORD)
        keyItemList.remove(ItemID.BENT_SWORD)

        # Add additional copies of the pendant and gate key
        keyItemList.extend([ItemID.GATE_KEY, ItemID.GATE_KEY, ItemID.GATE_KEY,
                            ItemID.PENDANT, ItemID.PENDANT, ItemID.PENDANT])

        # Add all 5 rocks if Rocksanity used with all Chronosanity modes
        if rset.GameFlags.ROCKSANITY in self.settings.gameflags:
            keyItemList.extend([
                ItemID.BLACK_ROCK, ItemID.BLUE_ROCK, ItemID.GOLD_ROCK,
                ItemID.SILVERROCK, ItemID.WHITE_ROCK
            ])

        self.keyItemList = keyItemList
    # end initKeyItems

    def initGame(self):
        self.game = Game(self.settings, self.config)

    # The ChronoSanityGameConfig wants to remove key item bias after 10 key
    # items are placed.  This just means remove duplicates from the list.
    def updateKeyItems(self, keyItemList):

        if self.game.getKeyItemCount() == 10:
            newList = []
            for key in keyItemList:
                if key not in newList:
                    newList.append(key)
            return newList
        else:
            return keyItemList

    # Chronosanity always has enough spots for items.
    def resolveExtraKeyItems(self):
        pass

# end ChronosanityGameConfig class

#
# This class represents the game configuration for a
# Lost Worlds Chronosanity game.
#


class ChronosanityLostWorldsGameConfig(GameConfig):
    def __init__(self, settings: rset.Settings, config: cfg.RandoConfig):
        self.charLocations = config.char_assign_dict
        GameConfig.__init__(self, settings, config)

    def initGame(self):
        self.game = Game(self.settings, self.config)
        # Test to make sure the settings have LW/CR set?

    def initKeyItems(self):
        # Since almost all checks are available from the start, no weighting is
        # being applied to the Lost Worlds key items
        self.keyItemList = [ItemID.C_TRIGGER, ItemID.CLONE, ItemID.PENDANT,
                            ItemID.DREAMSTONE, ItemID.RUBY_KNIFE]

    def resolveExtraKeyItems(self):
        pass

    def initLocations(self):

        # Prehistory
        prehistoryForestMazeLocations = \
            LocationGroup("PrehistoryForestMaze", 10, lambda game: True)
        (
            prehistoryForestMazeLocations
            .addLocation(Location(TID.MYSTIC_MT_STREAM))
            .addLocation(Location(TID.FOREST_MAZE_1))
            .addLocation(Location(TID.FOREST_MAZE_2))
            .addLocation(Location(TID.FOREST_MAZE_3))
            .addLocation(Location(TID.FOREST_MAZE_4))
            .addLocation(Location(TID.FOREST_MAZE_5))
            .addLocation(Location(TID.FOREST_MAZE_6))
            .addLocation(Location(TID.FOREST_MAZE_7))
            .addLocation(Location(TID.FOREST_MAZE_8))
            .addLocation(Location(TID.FOREST_MAZE_9))
        )

        prehistoryReptiteLocations = \
            LocationGroup("PrehistoryReptite", 10, lambda game: True)
        (
            prehistoryReptiteLocations
            .addLocation(Location(TID.REPTITE_LAIR_REPTITES_1))
            .addLocation(Location(TID.REPTITE_LAIR_REPTITES_2))
            .addLocation(Location(TID.REPTITE_LAIR_KEY))
        )

        # Dactyl Nest already has a character, so give it a relatively low
        # weight compared to the other prehistory locations.
        prehistoryDactylNest = \
            LocationGroup("PrehistoryDactylNest", 6, lambda game: True)
        (
            prehistoryDactylNest
            .addLocation(Location(TID.DACTYL_NEST_1))
            .addLocation(Location(TID.DACTYL_NEST_2))
            .addLocation(Location(TID.DACTYL_NEST_3))
        )

        # Dark Ages
        # Mount Woe does not go away in the randomizer, so it
        # is being considered for key item drops.
        darkagesLocations = \
            LocationGroup("Darkages", 10, lambda game: True)
        (
            darkagesLocations
            .addLocation(Location(TID.MT_WOE_1ST_SCREEN))
            .addLocation(Location(TID.MT_WOE_2ND_SCREEN_1))
            .addLocation(Location(TID.MT_WOE_2ND_SCREEN_2))
            .addLocation(Location(TID.MT_WOE_2ND_SCREEN_3))
            .addLocation(Location(TID.MT_WOE_2ND_SCREEN_4))
            .addLocation(Location(TID.MT_WOE_2ND_SCREEN_5))
            .addLocation(Location(TID.MT_WOE_3RD_SCREEN_1))
            .addLocation(Location(TID.MT_WOE_3RD_SCREEN_2))
            .addLocation(Location(TID.MT_WOE_3RD_SCREEN_3))
            .addLocation(Location(TID.MT_WOE_3RD_SCREEN_4))
            .addLocation(Location(TID.MT_WOE_3RD_SCREEN_5))
            .addLocation(Location(TID.MT_WOE_FINAL_1))
            .addLocation(Location(TID.MT_WOE_FINAL_2))
            .addLocation(Location(TID.MT_WOE_KEY))
        )

        # Future
        futureOpenLocations = \
            LocationGroup("FutureOpen", 10, lambda game: True)
        (
            futureOpenLocations
            # Chests
            .addLocation(Location(TID.ARRIS_DOME_RATS))
            .addLocation(Location(TID.ARRIS_DOME_FOOD_STORE))
            # KeyItems
            .addLocation(Location(TID.ARRIS_DOME_DOAN_KEY))
            .addLocation(Location(TID.SUN_PALACE_KEY))
        )

        futureSewersLocations = \
            LocationGroup("FutureSewers", 8, lambda game: True)
        (
            futureSewersLocations
            .addLocation(Location(TID.SEWERS_1))
            .addLocation(Location(TID.SEWERS_2))
            .addLocation(Location(TID.SEWERS_3))
        )

        futureLabLocations = \
            LocationGroup("FutureLabs", 10, lambda game: True)
        (
            futureLabLocations
            .addLocation(Location(TID.LAB_16_1))
            .addLocation(Location(TID.LAB_16_2))
            .addLocation(Location(TID.LAB_16_3))
            .addLocation(Location(TID.LAB_16_4))
            .addLocation(Location(TID.LAB_32_1))
            # Race log chest is not included.
            # .addLocation(Location(TID.LAB_32_RACE_LOG))
        )

        genoDomeLocations = \
            LocationGroup("GenoDome", 10, lambda game: True)
        (
            genoDomeLocations
            .addLocation(Location(TID.GENO_DOME_1F_1))
            .addLocation(Location(TID.GENO_DOME_1F_2))
            .addLocation(Location(TID.GENO_DOME_1F_3))
            .addLocation(Location(TID.GENO_DOME_1F_4))
            .addLocation(Location(TID.GENO_DOME_ROOM_1))
            .addLocation(Location(TID.GENO_DOME_ROOM_2))
            .addLocation(Location(TID.GENO_DOME_PROTO4_1))
            .addLocation(Location(TID.GENO_DOME_PROTO4_2))
            .addLocation(Location(TID.GENO_DOME_2F_1))
            .addLocation(Location(TID.GENO_DOME_2F_2))
            .addLocation(Location(TID.GENO_DOME_2F_3))
            .addLocation(Location(TID.GENO_DOME_2F_4))
            .addLocation(Location(TID.GENO_DOME_KEY))
        )

        factoryLocations = \
            LocationGroup("Factory", 10, lambda game: True)
        (
            factoryLocations
            .addLocation(Location(TID.FACTORY_LEFT_AUX_CONSOLE))
            .addLocation(Location(TID.FACTORY_LEFT_SECURITY_RIGHT))
            .addLocation(Location(TID.FACTORY_LEFT_SECURITY_LEFT))
            .addLocation(Location(TID.FACTORY_RUINS_GENERATOR))
            .addLocation(Location(TID.FACTORY_RIGHT_DATA_CORE_1))
            .addLocation(Location(TID.FACTORY_RIGHT_DATA_CORE_2))
            .addLocation(Location(TID.FACTORY_RIGHT_FLOOR_TOP))
            .addLocation(Location(TID.FACTORY_RIGHT_FLOOR_LEFT))
            .addLocation(Location(TID.FACTORY_RIGHT_FLOOR_BOTTOM))
            .addLocation(Location(TID.FACTORY_RIGHT_FLOOR_SECRET))
            .addLocation(Location(TID.FACTORY_RIGHT_CRANE_LOWER))
            .addLocation(Location(TID.FACTORY_RIGHT_CRANE_UPPER))
            .addLocation(Location(TID.FACTORY_RIGHT_INFO_ARCHIVE))
            # .addLocation(Location(TID.FACTORY_ROBOT_STORAGE))
            # Inaccessible chest
        )

        # Sealed locations
        sealedLocations = \
            LocationGroup("SealedLocations", 10,
                          lambda game: game.canAccessSealedChests())
        (
            sealedLocations
            # Sealed Doors
            .addLocation(Location(TID.BANGOR_DOME_SEAL_1))
            .addLocation(Location(TID.BANGOR_DOME_SEAL_2))
            .addLocation(Location(TID.BANGOR_DOME_SEAL_3))
            .addLocation(Location(TID.TRANN_DOME_SEAL_1))
            .addLocation(Location(TID.TRANN_DOME_SEAL_2))
            .addLocation(Location(TID.ARRIS_DOME_SEAL_1))
            .addLocation(Location(TID.ARRIS_DOME_SEAL_2))
            .addLocation(Location(TID.ARRIS_DOME_SEAL_3))
            .addLocation(Location(TID.ARRIS_DOME_SEAL_4))
        )

        # 65 Million BC
        self.locationGroups.append(prehistoryForestMazeLocations)
        self.locationGroups.append(prehistoryReptiteLocations)
        self.locationGroups.append(prehistoryDactylNest)

        # 12000 BC
        self.locationGroups.append(darkagesLocations)

        # 2300 AD
        self.locationGroups.append(futureOpenLocations)
        self.locationGroups.append(futureLabLocations)
        self.locationGroups.append(futureSewersLocations)
        self.locationGroups.append(genoDomeLocations)
        self.locationGroups.append(factoryLocations)

        # Sealed Locations (chests and doors)
        self.locationGroups.append(sealedLocations)

# end ChronosanityLostWorldsGameConfig class


def apply_epoch_fail(game_config: GameConfig):
    '''
    Split and/or add flight requirements to group.  Add JoT to KI list.
    '''
    settings = game_config.settings

    if settings.game_mode not in (rset.GameMode.STANDARD,
                                  rset.GameMode.LEGACY_OF_CYRUS,
                                  rset.GameMode.ICE_AGE,
                                  rset.GameMode.VANILLA_RANDO):
        return

    if rset.GameFlags.EPOCH_FAIL not in settings.gameflags:
        return

    flight_tids = [
        # Sun Palace
        TID.SUN_PALACE_KEY,
        # Geno Dome
        TID.GENO_DOME_1F_1, TID.GENO_DOME_1F_2, TID.GENO_DOME_1F_3,
        TID.GENO_DOME_1F_4, TID.GENO_DOME_2F_1, TID.GENO_DOME_2F_2,
        TID.GENO_DOME_2F_3, TID.GENO_DOME_2F_4, TID.GENO_DOME_KEY,
        TID.GENO_DOME_PROTO4_1, TID.GENO_DOME_PROTO4_2,
        TID.GENO_DOME_ROOM_1, TID.GENO_DOME_ROOM_2,
        # Giant's Claw
        TID.GIANTS_CLAW_CAVES_1, TID.GIANTS_CLAW_CAVES_2,
        TID.GIANTS_CLAW_CAVES_3, TID.GIANTS_CLAW_CAVES_4,
        TID.GIANTS_CLAW_CAVES_5, TID.GIANTS_CLAW_KEY,
        TID.GIANTS_CLAW_TRAPS, # TID.GIANTS_CLAW_KINO_CELL,
        TID.GIANTS_CLAW_THRONE_1, TID.GIANTS_CLAW_THRONE_2,
        # Northern Ruins
        TID.NORTHERN_RUINS_ANTECHAMBER_LEFT_1000,
        TID.NORTHERN_RUINS_ANTECHAMBER_LEFT_600,
        TID.NORTHERN_RUINS_ANTECHAMBER_SEALED_1000,
        TID.NORTHERN_RUINS_ANTECHAMBER_SEALED_600,
        TID.NORTHERN_RUINS_BACK_LEFT_SEALED_1000,
        TID.NORTHERN_RUINS_BACK_LEFT_SEALED_600,
        TID.NORTHERN_RUINS_BACK_RIGHT_SEALED_1000,
        TID.NORTHERN_RUINS_BACK_RIGHT_SEALED_600,
        TID.NORTHERN_RUINS_BASEMENT_1000, TID.NORTHERN_RUINS_BASEMENT_600,
        TID.CYRUS_GRAVE_KEY,
        # Ozzie's Fort
        TID.OZZIES_FORT_FINAL_1, TID.OZZIES_FORT_FINAL_2,
        TID.OZZIES_FORT_GUILLOTINES_1, TID.OZZIES_FORT_GUILLOTINES_2,
        TID.OZZIES_FORT_GUILLOTINES_3, TID.OZZIES_FORT_GUILLOTINES_4,
        TID.OZZIES_FORT_KEY,
        # OpenKeys
        TID.LAZY_CARPENTER,
        # MelchiorRefinements
        TID.MELCHIOR_KEY
    ]

    # When the Sun Keep spot is in, the Sun Keep needs flight but Melchior
    # no longer requires flight.
    if rset.GameFlags.ADD_SUNKEEP_SPOT in settings.gameflags:
        flight_tids.append(TID.SUN_KEEP_2300)
        flight_tids.remove(TID.MELCHIOR_KEY)

    if rset.GameFlags.ROCKSANITY in settings.gameflags:
        flight_tids.append(TID.GIANTS_CLAW_ROCK)

    def add_flight(func):

        def ret_func(game: Game):
            settings = game.settings
            if rset.GameFlags.UNLOCKED_SKYGATES in settings.gameflags:
                return (func(game) and game.hasKeyItem(ItemID.JETSOFTIME) and
                        game.canAccessEndOfTime())
            return func(game) and game.hasKeyItem(ItemID.JETSOFTIME)

        return ret_func

    new_groups = []
    for group in game_config.locationGroups:
        # print(f'{group.getName()}, weight={group.getWeight()}')
        flight_locs = []
        grounded_locs = []
        for location in group.locations:
            # print(f'{location.getName()}')
            if isinstance(location, LinkedLocation):
                tid = location.location1.treasure_id
            else:
                tid = location.treasure_id

            if tid in flight_tids:
                # print('Adding to flight_locs')
                flight_locs.append(location)
            else:
                # print('Adding to grounded_locs')
                grounded_locs.append(location)

        if flight_locs:
            if grounded_locs:
                orig_weight = group.weight
                weight_per_loc = orig_weight / len(group.locations)
                for loc in flight_locs:
                    group.removeLocation(loc)

                new_name = group.getName() + '_flight'
                new_weight = ceil(weight_per_loc * len(flight_locs))
                new_rule = add_flight(group.accessRule)
                new_group = LocationGroup(new_name, new_weight, new_rule)
                # print(f'Splitting {group.getName()}, weight={new_weight}')
                for flight_loc in flight_locs:
                    # print(f'\tAdding {flight_loc.getName()} to {new_name}')
                    new_group.addLocation(flight_loc)
                new_groups.append(new_group)
            else:
                # print(f'Adding flight to {group.getName()}')
                group.accessRule = add_flight(group.accessRule)

    game_config.locationGroups.extend(new_groups)

#
# This class represents the game configuration for a
# Normal game.
#
class NormalGameConfig(GameConfig):
    def __init__(self, settings: rset.Settings, config: cfg.RandoConfig):
        self.charLocations = config.char_assign_dict
        self.earlyPendant = rset.GameFlags.FAST_PENDANT in settings.gameflags
        self.lockedChars = rset.GameFlags.LOCKED_CHARS in settings.gameflags
        GameConfig.__init__(self, settings, config)
        apply_epoch_fail(self)

    def initGame(self):
        self.game = Game(self.settings, self.config)

    def initKeyItems(self):
        IID = ItemID
        self.keyItemList = [
            IID.GATE_KEY, IID.DREAMSTONE, IID.RUBY_KNIFE,
            IID.PENDANT, IID.C_TRIGGER, IID.CLONE,
            IID.BENT_HILT, IID.BENT_SWORD, IID.MASAMUNE_2,
            IID.HERO_MEDAL, IID.ROBORIBBON, IID.PRISMSHARD,
            IID.TOMAS_POP, IID.MOON_STONE, IID.JERKY
        ]

        if rset.GameFlags.EPOCH_FAIL in self.settings.gameflags:
            self.keyItemList.append(ItemID.JETSOFTIME)

        if rset.GameFlags.ADD_SUNKEEP_SPOT in self.settings.gameflags:
            self.keyItemList.append(IID.SUN_STONE)

        if rset.GameFlags.RESTORE_TOOLS in self.settings.gameflags:
            self.keyItemList.append(IID.TOOLS)

        if rset.GameFlags.RESTORE_JOHNNY_RACE in self.settings.gameflags:
            self.keyItemList.append(ItemID.BIKE_KEY)

        if rset.GameFlags.SPLIT_ARRIS_DOME in self.settings.gameflags:
            self.keyItemList.append(ItemID.SEED)

        if rset.GameFlags.VANILLA_ROBO_RIBBON in self.settings.gameflags:
            self.keyItemList.remove(ItemID.ROBORIBBON)

        # add all 5 rocks as KI for all 5 rock locations when Rocksanity used
        if rset.GameFlags.ROCKSANITY in self.settings.gameflags:
            self.keyItemList.extend([
                ItemID.BLACK_ROCK, ItemID.BLUE_ROCK, ItemID.GOLD_ROCK,
                ItemID.SILVERROCK, ItemID.WHITE_ROCK
            ])

    def resolveExtraKeyItems(self):
        num_spots = sum(
            len(group.locations) for group in self.locationGroups
        )
        num_keys = len(self.keyItemList)

        if num_spots >= num_keys:
            return

        if ItemID.JERKY in self.keyItemList:
            self.keyItemList.remove(ItemID.JERKY)
            num_keys -= 1

        if num_spots >= num_keys:
            return

        raise ImpossibleGameConfigException

    def initLocations(self):

        # Even though treasurewriter *should* give items to each key item spot
        # we're going to still have them be BaselineLocations so that (1) it
        # makes inheritance easier and (2) it makes them always be listed in
        # the spoiler log.
        mid_dist = td.TreasureDist(
            (1, td.get_item_list(td.ItemTier.MID_GEAR))
        )

        good_dist = td.TreasureDist(
            (1, td.get_item_list(td.ItemTier.GOOD_GEAR))
        )

        high_dist = td.TreasureDist(
            (1, td.get_item_list(td.ItemTier.HIGH_GEAR))
        )

        awesome_dist = td.TreasureDist(
            (1, td.get_item_list(td.ItemTier.AWESOME_GEAR))
        )

        prehistoryLocations = LocationGroup(
            "PrehistoryReptite", 1, lambda game: game.canAccessPrehistory()
        )
        (
            prehistoryLocations
            .addLocation(BaselineLocation(TID.REPTITE_LAIR_KEY, high_dist))
        )

        darkagesLocations = \
            LocationGroup("Darkages", 1, lambda game: game.canAccessMtWoe())
        (
            darkagesLocations
            .addLocation(BaselineLocation(TID.MT_WOE_KEY, awesome_dist))
        )

        openKeys = LocationGroup(
            "OpenKeys", 5, lambda game: True, lambda weight: weight-1
        )
        (
            openKeys
            .addLocation(BaselineLocation(TID.ZENAN_BRIDGE_KEY, good_dist))
            .addLocation(BaselineLocation(TID.SNAIL_STOP_KEY, mid_dist))
            .addLocation(BaselineLocation(TID.LAZY_CARPENTER, mid_dist))
            .addLocation(BaselineLocation(TID.TABAN_KEY, good_dist))
            .addLocation(BaselineLocation(TID.DENADORO_MTS_KEY, good_dist))
        )

        melchiorsRefinementslocations = LocationGroup(
            "MelchiorRefinements", 1,
            lambda game: game.canAccessMelchiorsRefinements()
        )
        (
            melchiorsRefinementslocations
            .addLocation(BaselineLocation(TID.MELCHIOR_KEY, awesome_dist))
        )

        frogsBurrowLocation = LocationGroup(
            "FrogsBurrowLocation", 1, lambda game: game.canAccessBurrowItem()
        )
        (
            frogsBurrowLocation
            .addLocation(BaselineLocation(TID.FROGS_BURROW_LEFT, mid_dist))
        )

        guardiaTreasuryLocations = LocationGroup(
            "GuardiaTreasury", 1, lambda game: game.canAccessKingsTrial()
        )
        (
            guardiaTreasuryLocations
            .addLocation(BaselineLocation(TID.KINGS_TRIAL_KEY, high_dist))
        )

        giantsClawLocations = LocationGroup(
            "Giantsclaw", 1, lambda game: game.canAccessGiantsClaw()
        )
        (
            giantsClawLocations
            .addLocation(BaselineLocation(TID.GIANTS_CLAW_KEY,  high_dist))
        )

        fionaShrineLocations = LocationGroup(
            "Fionashrine", 1, lambda game: game.canAccessFionasShrine()
        )
        (
            fionaShrineLocations
            .addLocation(BaselineLocation(TID.FIONA_KEY, high_dist))
        )

        futureKeys = LocationGroup(
            "FutureOpen", 3, lambda game: game.canAccessFuture(),
            lambda weight: weight-1
        )
        (
            futureKeys
            .addLocation(BaselineLocation(TID.ARRIS_DOME_DOAN_KEY,
                                          high_dist))
            .addLocation(BaselineLocation(TID.SUN_PALACE_KEY, high_dist))
            .addLocation(BaselineLocation(TID.GENO_DOME_KEY, awesome_dist))
        )

        # Prehistory
        self.locationGroups.append(prehistoryLocations)
        # Dark Ages
        self.locationGroups.append(darkagesLocations)
        # 600/1000
        self.locationGroups.append(openKeys)
        self.locationGroups.append(melchiorsRefinementslocations)
        self.locationGroups.append(frogsBurrowLocation)
        self.locationGroups.append(guardiaTreasuryLocations)
        self.locationGroups.append(giantsClawLocations)
        self.locationGroups.append(fionaShrineLocations)
        # 2300
        self.locationGroups.append(futureKeys)

        flags = self.settings.gameflags
        GF = rset.GameFlags

        if GF.ADD_SUNKEEP_SPOT in flags:
            sunstoneKey = LocationGroup(
                "Sun Keep 2300", 1,
                lambda game: (
                    game.canAccessPrehistory() and
                    game.canAccessFuture() and
                    game.hasKeyItem(ItemID.MOON_STONE)
                )
            )
            sunstoneKey.addLocation(BaselineLocation(TID.SUN_KEEP_2300,
                                                     _high_gear_dist))
            self.locationGroups.append(sunstoneKey)

        if GF.ADD_BEKKLER_SPOT in flags:
            bekklerKey = LocationGroup(
                "BekklersLab", 1,
                lambda game: game.hasKeyItem(ItemID.C_TRIGGER)
            )
            bekklerKey.addLocation(
                BaselineLocation(TID.BEKKLER_KEY, _awesome_gear_dist)
            )
            self.locationGroups.append(bekklerKey)

        if GF.ADD_CYRUS_SPOT in flags:
            cyrusKey = LocationGroup(
                "HerosGrave", 1, _canAccessCyrusGraveVR
            )
            cyrusKey.addLocation(
                BaselineLocation(TID.CYRUS_GRAVE_KEY, _awesome_gear_dist)
            )
            self.locationGroups.append(cyrusKey)

        if GF.ADD_OZZIE_SPOT in flags:
            # Logically, Ozzie's fort is gated behind EoT/Woe access, but
            # players can physically enter once they can fly there.
            ozzieKey = LocationGroup("Ozzie's Fort", 1,
                                     lambda game: game.canAccessMtWoe())
            ozzieKey.addLocation(BaselineLocation(TID.OZZIES_FORT_KEY,
                                                  _high_gear_dist))
            self.locationGroups.append(ozzieKey)
        
        if GF.ADD_RACELOG_SPOT in flags:
            lab32Key = LocationGroup(
                "RaceLog Chest", 1, _canAccessRaceLog
            )
            lab32Key.addLocation(BaselineLocation(TID.LAB_32_RACE_LOG,
                                                  _high_gear_dist))
            self.locationGroups.append(lab32Key)

        if GF.SPLIT_ARRIS_DOME in flags:
            future = self.getLocationGroup("FutureOpen")
            future.removeLocationTIDs(TID.ARRIS_DOME_DOAN_KEY)
            future.addLocation(BaselineLocation(TID.ARRIS_DOME_FOOD_LOCKER_KEY,
                                                _high_gear_dist))

            doanKey = LocationGroup("DoanSeed", 1, _canAccessDoanKeyVR)
            doanKey.addLocation(BaselineLocation(TID.ARRIS_DOME_DOAN_KEY,
                                                 _high_gear_dist))
            self.locationGroups.append(doanKey)

        if GF.VANILLA_DESERT in flags:
            fiona_shrine = self.getLocationGroup('Fionashrine')
            fiona_shrine.accessRule = _canAccessFionasShrineVR

        if GF.ROCKSANITY in flags:
            self.initLocationsRocksanity()

    def initLocationsRocksanity(self):
        denadoroRock = LocationGroup(
            "Denadoro Rock", 1, lambda game: True
        )
        denadoroRock.addLocation(Location(TID.DENADORO_ROCK))

        giantsClawRock = LocationGroup(
            "Giantsclaw Rock", 1, lambda game: game.canAccessGiantsClaw()
        )
        giantsClawRock.addLocation(Location(TID.GIANTS_CLAW_ROCK))

        # laruba
        larubaRock = LocationGroup(
            "Laruba Rock", 1, lambda game: game.canAccessPrehistory()
        )
        larubaRock.addLocation(Location(TID.LARUBA_ROCK))

        # kajar
        kajarRock = LocationGroup(
            "Kajar Rock", 1, lambda game: game.canAccessMtWoe()
        )
        kajarRock.addLocation(Location(TID.KAJAR_ROCK))

        self.locationGroups.extend([
            denadoroRock, giantsClawRock, larubaRock, kajarRock
        ])

        if _couldAccessBlackOmen(self):
            # black omen rock set up to prevent putting go-mode items there
            blackOmenRock = LocationGroup(
                    "Black Omen Rock", 1, lambda game: (
                    game.canAccessBlackOmen() and
                    game.canAccessMagusCastle() and
                    game.canAccessTyranoLair()
                )
            )
            blackOmenRock.addLocation(Location(TID.BLACK_OMEN_TERRA_ROCK))
            self.locationGroups.append(blackOmenRock)


# end NormalGameConfig class

def _couldAccessBlackOmen(gc: GameConfig) -> bool:
    flags = gc.settings.gameflags
    GF = rset.GameFlags

    # configurations which do not have access to Black Omen
    omenless_cfgs: List[Type[GameConfig]] = [
        ChronosanityIceAgeGameConfig,
        ChronosanityLegacyOfCyrusGameConfig,
        IceAgeGameConfig,
        LegacyOfCyrusGameConfig,
    ]
    inaccessible = any(isinstance(gc, cfg) for cfg in omenless_cfgs)

    return not inaccessible and GF.REMOVE_BLACK_OMEN_SPOT not in flags

#
# This class represents the game configuration for a
# Lost Worlds game.
#
class LostWorldsGameConfig(GameConfig):
    def __init__(self, settings: rset.Settings, config: cfg.RandoConfig):
        self.charLocations = config.char_assign_dict
        GameConfig.__init__(self, settings, config)

    def resolveExtraKeyItems(self):
        pass

    def initGame(self):
        self.game = Game(self.settings, self.config)

    def initKeyItems(self):
        self.keyItemList = [ItemID.C_TRIGGER, ItemID.CLONE, ItemID.PENDANT,
                            ItemID.DREAMSTONE, ItemID.RUBY_KNIFE]

    def initLocations(self):
        # Not bothering making these baseline locations
        prehistoryLocations = LocationGroup(
            "PrehistoryReptite", 1, lambda game: game.canAccessPrehistory()
        )
        (
            prehistoryLocations
            .addLocation(Location(TID.REPTITE_LAIR_KEY))
        )

        darkagesLocations = \
            LocationGroup("Darkages", 1, lambda game: game.canAccessMtWoe())
        (
            darkagesLocations
            .addLocation(Location(TID.MT_WOE_KEY))
        )

        futureKeys = LocationGroup(
            "FutureOpen", 3, lambda game: game.canAccessFuture(),
            lambda weight: weight-1
        )
        (
            futureKeys
            .addLocation(Location(TID.ARRIS_DOME_DOAN_KEY))
            .addLocation(Location(TID.SUN_PALACE_KEY))
            .addLocation(Location(TID.GENO_DOME_KEY))
        )

        # Prehistory
        self.locationGroups.append(prehistoryLocations)
        # Dark Ages
        self.locationGroups.append(darkagesLocations)
        # 2300
        self.locationGroups.append(futureKeys)

# end LostWorldsGameCofig class


class ChronosanityLegacyOfCyrusGameConfig(ChronosanityGameConfig):

    def initKeyItems(self):
        ChronosanityGameConfig.initKeyItems(self)

        unavail_char = \
            self.config.char_assign_dict[RecruitID.PROTO_DOME].held_char

        removed_items = [
            ItemID.C_TRIGGER, ItemID.CLONE, ItemID.RUBY_KNIFE,
            ItemID.MOON_STONE
        ]

        if unavail_char == Characters.MARLE:
            removed_items.append(ItemID.PRISMSHARD)

        # Compared to normal, there's no reason to remove robo's ribbon b/c
        # there are sufficient key item spots.

        # elif unavail_char == Characters.ROBO:
        #     removed_items.append(ItemID.ROBORIBBON)

        if rset.GameFlags.LOCKED_CHARS not in self.settings.gameflags:
            removed_items.append(ItemID.DREAMSTONE)

        for item_id in removed_items:
            while item_id in self.keyItemList:
                self.keyItemList.remove(item_id)

    def initLocations(self):

        ChronosanityGameConfig.initLocations(self)

        # Remove all future groups.  Remove Ozzie's Fort because it is now
        # an endgame area.
        removed_names = [
            'FutureOpen', 'FutureSewers', 'FutureLabs', 'GenoDome',
            'Factory', 'Ozzie\'s Fort', 'MelchiorRefinements'
        ]

        unavail_char = \
            self.config.char_assign_dict[RecruitID.PROTO_DOME].held_char

        # TODO: Consider whether in Cronosanity we allow Prismshard with no
        #       Marle so that the treasury is available.
        if unavail_char == Characters.MARLE:
            removed_names.append('GuardiaTreasury')
            removed_names.append('KingsTrialKey')
        elif unavail_char == Characters.ROBO:
            removed_names.append('Fionashrine')

        self.removeLocationGroups(removed_names)

        sealed_group = self.getLocationGroup('SealedLocations')
        sealed_group.accessRule = lambda game: game.hasKeyItem(ItemID.PENDANT)

        removed_sealed_tids = (
            TID.BANGOR_DOME_SEAL_1, TID.BANGOR_DOME_SEAL_2,
            TID.BANGOR_DOME_SEAL_3, TID.TRANN_DOME_SEAL_1,
            TID.TRANN_DOME_SEAL_2, TID.ARRIS_DOME_SEAL_1,
            TID.ARRIS_DOME_SEAL_2, TID.ARRIS_DOME_SEAL_3,
            TID.ARRIS_DOME_SEAL_4
        )
        sealed_group.removeLocationTIDs(removed_sealed_tids)

        # Only gate key gives Woe access in LoC
        woe_group = self.getLocationGroup('Darkages')
        woe_group.accessRule = lambda game: game.hasKeyItem(ItemID.GATE_KEY)


class LegacyOfCyrusGameConfig(NormalGameConfig):

    def initKeyItems(self):
        NormalGameConfig.initKeyItems(self)

        unavail_char = \
            self.config.char_assign_dict[RecruitID.PROTO_DOME].held_char

        removed_items = [
            ItemID.C_TRIGGER, ItemID.CLONE, ItemID.RUBY_KNIFE,
            ItemID.MOON_STONE
        ]

        if unavail_char == Characters.MARLE:
            removed_items.append(ItemID.PRISMSHARD)
        elif unavail_char == Characters.ROBO:
            removed_items.append(ItemID.ROBORIBBON)

        if rset.GameFlags.LOCKED_CHARS not in self.settings.gameflags:
            removed_items.append(ItemID.DREAMSTONE)

        for item in removed_items:
            if item in self.keyItemList:  # In case something else removed RR
                self.keyItemList.remove(item)

    def initLocations(self):
        # We actually need to mostly redo this whole thing to implement the
        # LoC-specific item distributions.

        good_dist = td.TreasureDist(
            (1, td.get_item_list(td.ItemTier.GOOD_GEAR))
        )

        high_dist = td.TreasureDist(
            (1, td.get_item_list(td.ItemTier.HIGH_GEAR))
        )

        awesome_dist = td.TreasureDist(
            (1, td.get_item_list(td.ItemTier.AWESOME_GEAR))
        )

        unavail_char = \
            self.config.char_assign_dict[RecruitID.PROTO_DOME].held_char

        prehistoryLocations = LocationGroup(
            "PrehistoryReptite", 1, lambda game: game.canAccessPrehistory()
        )
        (
            prehistoryLocations
            .addLocation(BaselineLocation(TID.REPTITE_LAIR_KEY, awesome_dist))
        )
        self.locationGroups.append(prehistoryLocations)

        darkagesLocations = \
            LocationGroup("Darkages", 1, lambda game: game.canAccessMtWoe())
        (
            darkagesLocations
            .addLocation(BaselineLocation(TID.MT_WOE_KEY, awesome_dist))
        )
        self.locationGroups.append(darkagesLocations)

        openKeys = LocationGroup(
            "OpenKeys", 5, lambda game: True, lambda weight: weight-1
        )
        (
            openKeys
            .addLocation(BaselineLocation(TID.ZENAN_BRIDGE_KEY, good_dist))
            .addLocation(BaselineLocation(TID.SNAIL_STOP_KEY, good_dist))
            .addLocation(BaselineLocation(TID.LAZY_CARPENTER, high_dist))
            .addLocation(BaselineLocation(TID.TABAN_KEY, high_dist))
            .addLocation(BaselineLocation(TID.DENADORO_MTS_KEY, high_dist))
        )
        self.locationGroups.append(openKeys)

        frogsBurrowLocation = LocationGroup(
            "FrogsBurrowLocation", 1, lambda game: game.canAccessBurrowItem()
        )
        (
            frogsBurrowLocation
            .addLocation(BaselineLocation(TID.FROGS_BURROW_LEFT, good_dist))
        )
        self.locationGroups.append(frogsBurrowLocation)

        if unavail_char != Characters.MARLE:
            guardiaTreasuryLocations = LocationGroup(
                "GuardiaTreasury", 1, lambda game: game.canAccessKingsTrial()
            )
            (
                guardiaTreasuryLocations
                .addLocation(BaselineLocation(TID.KINGS_TRIAL_KEY,
                                              awesome_dist))
            )
            self.locationGroups.append(guardiaTreasuryLocations)

        giantsClawLocations = LocationGroup(
            "Giantsclaw", 1, lambda game: game.canAccessGiantsClaw()
        )
        (
            giantsClawLocations
            .addLocation(BaselineLocation(TID.GIANTS_CLAW_KEY, awesome_dist))
        )
        self.locationGroups.append(giantsClawLocations)

        if unavail_char != Characters.ROBO:
            fionaShrineLocations = LocationGroup(
                "Fionashrine", 1, lambda game: game.canAccessFionasShrine()
            )
            (
                fionaShrineLocations
                .addLocation(BaselineLocation(TID.FIONA_KEY, awesome_dist))
            )
            self.locationGroups.append(fionaShrineLocations)

        if rset.GameFlags.ROCKSANITY in self.settings.gameflags:
            NormalGameConfig.initLocationsRocksanity(self)


class IceAgeGameConfig(NormalGameConfig):
    def __init__(self, settings: rset.Settings, config: cfg.RandoConfig):
        NormalGameConfig.__init__(self, settings, config)

    def initGame(self):
        NormalGameConfig.initGame(self)

    def initKeyItems(self):
        NormalGameConfig.initKeyItems(self)

        # Remove other go-mode items.  These will be replaced with gear as
        # they would be in Chronosanity modes
        removed_items = [
            ItemID.C_TRIGGER, ItemID.CLONE, ItemID.RUBY_KNIFE
        ]

        for item in removed_items:
            self.keyItemList.remove(item)

    def initLocations(self):
        NormalGameConfig.initLocations(self)

        # The only change needed is that Woe will not be accessible except
        # when dreamstone, ayla, and dactyl char are present.  We keep the
        # group around because a (dud) key item still gets placed there.
        woe_group = next(
            x for x in self.locationGroups if x.name == 'Darkages'
        )

        def has_go_mode(game: Game):
            return (
                game.canAccessDactylCharacter() and
                game.hasCharacter(Characters.AYLA) and
                game.hasKeyItem(ItemID.DREAMSTONE)
            )

        woe_group.accessRule = has_go_mode


class ChronosanityIceAgeGameConfig(ChronosanityGameConfig):

    def initKeyItems(self):
        ChronosanityGameConfig.initKeyItems(self)

        # Remove other go-mode items.  These will be replaced with gear as
        # they would be in Chronosanity modes
        removed_items = [
            ItemID.C_TRIGGER, ItemID.CLONE, ItemID.RUBY_KNIFE
        ]

        for item_id in removed_items:
            while item_id in self.keyItemList:
                self.keyItemList.remove(item_id)

    def initLocations(self):
        ChronosanityGameConfig.initLocations(self)

        # For Chronosanity, just remove the Woe group.
        self.locationGroups.remove(self.getLocationGroup('Darkages'))


# Note: Accessing MtWoe is the same as accessing EoT in current logic.
#       This means you can grind for levels if you really need it.
def _canAccessGiantsClawVR(game: Game):
    return (
        game.hasKeyItem(ItemID.TOMAS_POP) and
        game.canAccessMtWoe()
    )


def _canAccessKingsTrialVR(game: Game):
    return (
        game.hasCharacter(Characters.MARLE) and
        game.hasKeyItem(ItemID.PRISMSHARD) and
        game.canAccessMtWoe()
    )


def _canAccessFionasShrineVR(game: Game):

    flags = game.settings.gameflags
    GF = rset.GameFlags

    if not game.hasCharacter(Characters.ROBO):
        return False

    if GF.UNLOCKED_SKYGATES:
        return game.canAccessMtWoe()
    else:
        return game.canAccessTyranoLair() or game.canAccessMagusCastle()


def _canAccessNorthernRuinsVR(game: Game):
    restore_tools = rset.GameFlags.RESTORE_TOOLS in  game.settings.gameflags
    if restore_tools:
        fix_item = ItemID.TOOLS
    else:
        fix_item = ItemID.MASAMUNE_2

    return game.hasKeyItem(fix_item)


def _canAccessCyrusGraveVR(game: Game):
    return (
        _canAccessNorthernRuinsVR(game) and
        game.hasCharacter(Characters.FROG) and
        game.canAccessMtWoe()
    )

def _canAccessDoanKeyVR(game: Game):
    return game.canAccessFuture() and game.hasKeyItem(ItemID.SEED)


def _canAccessRaceLog(game: Game):
    has_johnny = \
        rset.GameFlags.RESTORE_JOHNNY_RACE in game.settings.gameflags
    return (
        game.hasKeyItem(ItemID.PENDANT) and
        (
            game.hasKeyItem(ItemID.BIKE_KEY) or not has_johnny
        )
    )

_awesome_gear_dist = td.TreasureDist(
    (1, td.get_item_list(td.ItemTier.AWESOME_GEAR))
)

_high_gear_dist = td.TreasureDist(
    (1, td.get_item_list(td.ItemTier.HIGH_GEAR))
)


class VanillaRandoGameConfig(NormalGameConfig):

    def initKeyItems(self):
        NormalGameConfig.initKeyItems(self)

    def initLocations(self):
        NormalGameConfig.initLocations(self)

        # Gate the endgame quests behind EOT (Mt. Woe) access.
        giants_claw = self.getLocationGroup('Giantsclaw')
        giants_claw.accessRule = _canAccessGiantsClawVR

        kings_trial = self.getLocationGroup('GuardiaTreasury')
        kings_trial.accessRule = _canAccessKingsTrialVR

        fiona_shrine = self.getLocationGroup('Fionashrine')
        fiona_shrine.accessRule = _canAccessFionasShrineVR


class ChronosanityVanillaRandoGameConfig(ChronosanityGameConfig):

    def initKeyItems(self):
        ChronosanityGameConfig.initKeyItems(self)

        # This is call done in ChronosanityGameConfig now.
        # for i in range(5):
        #     self.keyItemList.append(ItemID.TOOLS)
        #     self.keyItemList.append(ItemID.SEED)
        #     self.keyItemList.append(ItemID.BIKE_KEY)
        #     self.keyItemList.append(ItemID.SUN_STONE)

        # while ItemID.ROBORIBBON in self.keyItemList:
        #     self.keyItemList.remove(ItemID.ROBORIBBON)

    def initLocations(self):
        ChronosanityGameConfig.initLocations(self)

        # Gate Vanilla endgame dungeons behind Mt. Woe access
        giants_claw = self.getLocationGroup('Giantsclaw')
        giants_claw.accessRule = _canAccessGiantsClawVR

        kings_trial = self.getLocationGroup('KingsTrialKey')
        kings_trial.accessRule = _canAccessKingsTrialVR

        fiona_shrine = self.getLocationGroup('Fionashrine')
        fiona_shrine.accessRule = _canAccessFionasShrineVR


#
# Get a GameConfig object based on randomizer flags.
# The GameConfig object will have have the correct locations,
# initial key items, and game setup for the selected flags.
#
# param: settings - an rset.Settings object containing flag choices
# param: config - a cfg.RandoConfig object containing randomizer assignments
#
# return: A GameConfig object appropriate for the given flag set
#
def getGameConfig(settings: rset.Settings, config: cfg.RandoConfig):
    # Maybe each game mode needs to supply its own logic setup function.
    # Why should this file need to be aware of every possible game mode?

    chronosanity = rset.GameFlags.CHRONOSANITY in settings.gameflags
    standard = rset.GameMode.STANDARD == settings.game_mode
    lostWorlds = rset.GameMode.LOST_WORLDS == settings.game_mode
    iceAge = rset.GameMode.ICE_AGE == settings.game_mode
    legacyofcyrus = rset.GameMode.LEGACY_OF_CYRUS == settings.game_mode
    vanilla = rset.GameMode.VANILLA_RANDO == settings.game_mode

    CfgType: typing.Type[GameConfig]

    if chronosanity:
        if lostWorlds:
            CfgType = ChronosanityLostWorldsGameConfig
        elif legacyofcyrus:
            CfgType = ChronosanityLegacyOfCyrusGameConfig
        elif iceAge:
            CfgType = ChronosanityIceAgeGameConfig
        elif vanilla:
            CfgType = ChronosanityVanillaRandoGameConfig
        elif standard:
            CfgType = ChronosanityGameConfig
        else:
            raise ValueError('Invalid Game Mode')
    else:
        if lostWorlds:
            CfgType = LostWorldsGameConfig
        elif legacyofcyrus:
            CfgType = LegacyOfCyrusGameConfig
        elif iceAge:
            CfgType = IceAgeGameConfig
        elif vanilla:
            CfgType = VanillaRandoGameConfig
        elif standard:
            CfgType = NormalGameConfig
        else:
            raise ValueError('Invalid Game Mode')

    return CfgType(settings, config)
# end getGameConfig
