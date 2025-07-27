'''
The Chrono Trigger: Jets of Time Randomizer
'''
from __future__ import annotations

import random
import pickle
import sys
import json
import textwrap
import typing

from pathlib import Path
from typing import Optional, Union

import cli.arguments as arguments
import charassign
import eventfunction

from base import chesttext, basepatch

import enemystats
import itemdata
import itemrando
from characters import pcrecruit, ctpcstats
from maps import mapmangler
from treasures import treasurewriter, treasuretypes
from shops import shopwriter
import logicwriters as logicwriter
import bossrandoevent as bossrando
import bossrandotypes as rotypes
import bossscaler
import tabchange as tabwriter
import fastmagic
import fastpendant
import charrando
import roboribbon
import techrandomizer
import elementrando
import qolhacks
import cosmetichacks
import iceage
import legacyofcyrus
import mystery
from vanillarando import vanillarando
import epochfail
import flashreduce
import seedhash
import prismshard
import scriptshortener
import bucketlist
import techdescs
import techdamagerando

import byteops
import ctenums
import ctevent
import eventcommand
from ctrom import CTRom
import ctstrings
import enemyrewards


# from freespace import FSWriteType
import randoconfig as cfg
import randosettings as rset

from jotjson import JOTJSONEncoder


class GenerationFailedException(Exception):
    '''Exception to raise when generating the randomized rom fails.'''


class NoSettingsException(GenerationFailedException):
    '''Raise when trying to generate a config or rom with no settings.'''


class NoConfigException(GenerationFailedException):
    '''Raise when trying to generate a rom with no config set.'''


class Randomizer:
    '''
    Main randomizer class.  Produces a random Chrono Trigger rom given a
    vanilla rom and settings object.

    Basic usage:
        # Obtain ct_vanilla.sfc somehow.  Legally of course.
        with open('ct_vanilla.sfc', 'rb') as infile:
            ct_vanilla = infile.read()

        settings = rset.Settings()  # Lots of options
        out_rom = Randomizer.get_randmomized_rom(ct_vanilla, settings)
        # out_rom has type bytes and can be written out.

    Other usage:
        # Obtain ct_vanilla.sfc and read it into bytes-like ct_vanilla
        rando = Randomizer(ct_vanilla)
        rando.settings = rset.Settings()  # Or whatever other settings.
        rando.set_random_config()
        rando.generate_rom()
        out_rom = rando.get_generated_rom()
    '''
    _pickles_path: Path = Path(__file__).parent / 'pickles'

    def __init__(self, rom: bytes, is_vanilla: bool = True,
                 settings: Optional[rset.Settings] = None,
                 config: Optional[cfg.RandoConfig] = None):
        '''
        Constructor for a Randomizer.

        Args:
            rom : bytes
                A bytes-like object of the input rom.
            is_vanilla: bool = True
                Whether the rom is an unmodified rom.  Both headerless and
                headered roms will be accepted if is_vanilla is True.  Using
                non-vanilla roms is not supported.
            settings: Optional[rset.Settings] = None
                The rset.Settings object to use to generate the
                cfg.Randoconfig. Or, if a config is provided, the settings
                object used to generate it.
            config: Optional[cfg.RandoConfig] = None
                If a cfg.RandoConfig has already been generated, and you wish
                to make a random rom based on that config, it can be provided
                here.  Note, the settings(above) must be the same settings
                (except cosmetic) used to generate the config, or rom
                generation will likely fail.
        '''
        # We want to keep a copy of the base rom around so that we can
        # generate many seeds from it.
        self.base_ctrom = CTRom(rom, ignore_checksum=not is_vanilla)
        self.out_rom: Optional[CTRom] = None
        self.hash_string_bytes: Optional[bytes] = None
        self.has_generated = False

        self.settings = settings
        self.config = config


    # The randomizer will hold onto its last generated rom in self.out_rom
    # The settings and config are made properties so that I can update
    # whether out_rom correctly reflects the settings/config.
    @property
    def settings(self):
        '''
        The randomizer's settings.  Will reset generation if modified.
        '''
        return self._settings

    @settings.setter
    def settings(self, new_settings: rset.Settings):
        self._settings = new_settings
        self.has_generated = False

    @property
    def config(self):
        '''
        The randomizer's cfg.RandoConfig for writing the rom.  Will reset
        generation if modified.
        '''
        return self._config

    @config.setter
    def config(self, new_config: cfg.RandoConfig):
        self._config = new_config
        self.has_generated = False

    def set_random_config(self):
        '''
        Use the Randomizer's settings to generate a random cfg.Randoconfig.
        '''
        if self.settings is None:
            raise NoSettingsException

        random.seed(self.settings.seed)

        if rset.GameFlags.MYSTERY in self.settings.gameflags:
            self.settings = mystery.generate_mystery_settings(self.settings)

        self.settings.fix_flag_conflicts()

        # Some of the config defaults (prices, techdb, enemy stats) are
        # read from the rom.  This routine partially patches a copy of the
        # base rom, gets the data, and builds the base config.
        self.config = Randomizer.get_base_config_from_settings(
            bytearray(self.base_ctrom.rom_data.getvalue()),
            self.settings
        )

        # An alternate approach is to build the base config with the pickles
        # provided.  You just have to make sure to redump any time time that
        # base_patch.ips or hard.ips change.  Demo below.
        '''
        with self._get_pickle_path('default_randoconfig.pickle').open('rb') as infile:
            self.config = pickle.load(infile)

        if self.settings.enemy_difficulty == rset.Difficulty.HARD:
            with self._get_pickle_path('enemy_dict_hard.pickle').open('rb') as infile:
                self.config.enemy_dict = pickle.load(infile)
        '''

        # Character config.  Includes tech randomization and who can equip
        # which items.
        elementrando.write_config(self.settings, self.config, random)
        charrando.write_config(self.settings, self.config)

        techrandomizer.write_tech_order_to_config(self.settings,
                                                  self.config)

        # Tech Damage Rando can add duplicate effect headers for randomized powers.
        # So we have to generate the combo tech descs before randomizing the single tech damage.
        techdescs.update_combo_tech_descs(self.config.tech_db)
        if rset.GameFlags.TECH_DAMAGE_RANDO in self.settings.gameflags:
            techdamagerando.modify_all_single_techs(self.config.tech_db)
        techdescs.update_single_tech_descs(self.config.tech_db)
        techdescs.clean_up_desc_space(self.config.tech_db)

        # Fast Magic.  Should be fine before or after charrando.
        # Safest after.
        fastmagic.write_config(self.settings, self.config)

        # Treasure config.
        treasurewriter.write_treasures_to_config(self.settings, self.config)

        # Enemy rewards
        enemyrewards.write_enemy_rewards_to_config(self.settings, self.config)

        # Key item config.  Important that this goes after treasures because
        # otherwise the treasurewriter can overwrite key items placed by
        # Chronosanity
        logicwriter.commitKeyItems(self.settings, self.config)

        # Now go write LW extra items if need be
        treasurewriter.add_lw_key_item_gear(self.settings, self.config)

        # Shops
        shopwriter.write_shops_to_config(self.settings, self.config)

        # Robo's Ribbon in itemdb
        roboribbon.set_robo_ribbon_in_config(self.config)

        # Item Rando
        # Important this is done after roboribbon or itemrando gets confused
        # over which stat boost is +3 speed
        itemrando.write_item_prices_to_config(self.settings, self.config)
        itemrando.randomize_healing(self.settings, self.config)
        itemrando.randomize_accessories(self.settings, self.config)
        # itemrando.randomize_weapon_armor_stats(self.settings, self.config)
        itemrando.alt_gear_rando(self.settings, self.config)
        self.config.item_db.update_all_descriptions()

        # Boss Rando
        bossrando.write_assignment_to_config(self.settings, self.config)

        # We need the boss rando assignment to determine which bosses need
        # additional bossscaler scaling.  That is accomplished by the above
        # bossrando.write_assignment_to_config.

        # Then, scale based on ranking.
        # This has to come before boss rando scaling  because some boss scaling
        # changes are defined absolutely instead of relatively, so they would
        # just overwrite the boss rando scaling.
        bossscaler.determine_boss_rank(self.settings, self.config)

        # Finally, scale based on new location.
        bossrando.scale_bosses_given_assignment(self.settings, self.config)

        # Black Tyrano/Magus boss randomization
        bossrando.randomize_midbosses(self.settings, self.config)

        # Tabs
        tabwriter.write_tabs_to_config(self.settings, self.config)

        # Bucket
        bucketlist.add_objectives_to_config(self.settings, self.config)

        # Omen elevator
        self.__update_key_item_descs()
        self.__set_omen_elevators_config()

        # Ice age GG buffs if IA flag is present in settings.
        iceage.write_config(self.settings, self.config)

    @classmethod
    def __set_fast_zeal_teleporters(cls, ct_rom: CTRom):
        '''
        Warp straight from the bottom of the mountain to the top.
        '''

        EC = ctevent.EC

        script = ct_rom.script_manager.get_script(
            ctenums.LocID.ZEAL_TELEPORTERS
        )
        bot_loc_cmd = EC.change_location(ctenums.LocID.ZEAL_TELEPORTERS,
                                         0x1F, 0x0E,
                                         3, 1, False)
        new_bot_loc_cmd = EC.change_location(ctenums.LocID.ZEAL_TELEPORTERS,
                                             0x35, 0x0E,
                                             3, 1, False)

        pos = script.find_exact_command(bot_loc_cmd)
        script.data[pos:pos+len(bot_loc_cmd)] = new_bot_loc_cmd.to_bytearray()

        top_loc_cmd = EC.change_location(ctenums.LocID.ZEAL_TELEPORTERS,
                                         0x0A, 0x26,
                                         3, 1, False)
        new_top_loc_cmd = EC.change_location(ctenums.LocID.ZEAL_TELEPORTERS,
                                             0x0A, 0xE,
                                             3, 1, False)

        pos = script.find_exact_command(top_loc_cmd)
        script.data[pos:pos+len(bot_loc_cmd)] = new_top_loc_cmd.to_bytearray()

    @classmethod
    def __set_bike_champions(
            cls, ct_rom: CTRom,
            name_1: str,
            name_2: str,
            name_3: str):
        script = ct_rom.script_manager.get_script(
            ctenums.LocID.ARRIS_DOME_COMMAND)

        _, cmd = script.find_command(
            [0xBB],
            script.get_function_start(9, 1),
            script.get_function_end(9, 1)
        )
        string_id = cmd.args[0]
        lb = '{linebreak+0}'
        new_string = \
            'Bike racing champions: {full break}'\
            f'{name_1}{lb}{name_2}{lb}{name_3}{{null}}'

        new_ctstr = ctstrings.CTString.from_str(new_string)
        new_ctstr.compress()

        script.strings[string_id] = new_ctstr
        script.modified_strings = True

    @classmethod
    def __set_fair_racers(
            cls, ct_rom: CTRom,
            catalack_name: str,
            steel_runner_name: str,
            gi_jogger_name: str,
            green_ambler_name: str
            ):

        script = ct_rom.script_manager.get_script(
            ctenums.LocID.MILLENNIAL_FAIR)

        for ind, ctstr in enumerate(script.strings):
            pystr = ctstrings.CTString.ct_bytes_to_ascii(ctstr)
            pystr = pystr.replace('Catalack', f'{catalack_name} (Ca)')
            pystr = pystr.replace('G. I. Jogger', f'{gi_jogger_name} (GI)')
            pystr = pystr.replace('the Green Ambler',
                                  f'{green_ambler_name} (GA)')
            pystr = pystr.replace('Green Ambler', f'{green_ambler_name} (GA)')
            pystr = pystr.replace('The Steel Runner',
                                  f'{steel_runner_name} (SR)')
            pystr = pystr.replace('Steel Runner',
                                  f'{steel_runner_name} (SR)')

            new_ctstr = ctstrings.CTString.from_str(pystr)
            new_ctstr.compress()
            script.strings[ind] = new_ctstr
            script.modified_strings = True

    @classmethod
    def __clean_lw_loadscreen(cls, ct_rom: CTRom):
        '''
        LW load screen has some extra commands which make a jump command
        have a 255 byte jump.  We need to delete a few of these to make room.
        '''
        script = ct_rom.script_manager.get_script(
            ctenums.LocID.LOAD_SCREEN)

        EC = ctevent.EC
        cmd = EC.assign_val_to_mem(0x7F, 0x7F01E0, 1)
        pos = script.get_object_start(0)
        pos = script.find_exact_command(cmd, pos)
        pos += len(cmd)
        script.delete_commands(pos, 5)

    @classmethod
    def __set_active_wait_song(cls, ct_rom: CTRom, song_id=3):
        '''
        Put a song (corridors of time default) at the active/wait screen.
        '''
        script = ct_rom.script_manager.get_script(
            ctenums.LocID.LOAD_SCREEN)

        pos: Optional[int] = script.get_object_start(0)

        while True:
            pos, cmd = script.find_command([0xC8], pos)
            if cmd.args[0] in range(0xC0, 0xC7):  # name cmd_args
                break

            pos += len(cmd)

        song_cmd = ctevent.EC.generic_one_arg(0xEA, song_id)
        script.insert_commands(song_cmd.to_bytearray(), pos)

    @classmethod
    def __set_fast_magus_castle(cls, ct_rom: CTRom):
        '''
        Do not require the player to visit the Flea and Slash room in castle
        Magus.

        This function sets the flags for visiting the Flea and Slash rooms
        in the telepod exhibit script.  The flags 0x7F00A3 & 0x10/0x20 are
        unused in other events.
        '''
        script = ct_rom.script_manager.get_script(
            ctenums.LocID.TELEPOD_EXHIBIT
        )
        EC = ctevent.EC

        # Just put it at the start of the animation.  No reason to be fancy
        hook_pos = script.get_function_start(0x0E, 4)

        # Slash's Room: Set 0x7F00A3 & 0x10
        # Flea's Room: Set 0x7F00A3 & 0x20
        set_flags_cmd = EC.assign_val_to_mem(0x30, 0x7F00A3, 1)
        script.insert_commands(set_flags_cmd.to_bytearray(), hook_pos)

    @classmethod
    def __add_cat_pet_flag(cls, ct_rom: CTRom, addr: int, bit: int):
        '''
        Uses the bit (addr & bit) to determine whether a player has pet the
        cat in Crono's house.
        '''
        script = ct_rom.script_manager.get_script(
            ctenums.LocID.CRONOS_KITCHEN
        )
        pos = script.get_function_start(0x09, 0x01)

        EC = ctevent.EC
        cmd = EC.set_bit(addr, bit)

        script.insert_commands(cmd.to_bytearray(), pos)

    @classmethod
    def __set_initial_gold(cls, ct_rom: CTRom, gold: int):
        script = ct_rom.script_manager.get_script(ctenums.LocID.LOAD_SCREEN)

        # Cmd 4E (copy) to 0x7E2C53
        cmd_b = bytes.fromhex('4E532C7E0500')
        payload = gold.to_bytes(3, 'little')

        pos = script.data.find(cmd_b)
        pos += len(cmd_b)
        script.data[pos:pos+3] = payload[:]

    def __update_key_item_descs(self):
        config = self.config
        IID = ctenums.ItemID

        item_db = config.item_db
        item_db[IID.GATE_KEY].set_desc_from_str(
            'Unlocks 65m BC (Medina imp closet)'
        )

        item_db[IID.PENDANT].set_desc_from_str(
            'Unlocks future (Castle 1000 Lawyer)'
        )

        item_db[IID.DREAMSTONE].set_desc_from_str(
            'Opens Tyrano Lair (Kino cell switch)'
        )

        item_db[IID.RUBY_KNIFE].set_desc_from_str(
            'Opens Zeal Throneroom'
        )

        item_db[IID.BENT_SWORD].set_desc_from_str(
            'Forge Masa w/ Hilt (Melchior\'s Hut)'
        )

        item_db[IID.BENT_HILT].set_desc_from_str(
            'Forge Masa w/ Blade (Melchior\'s Hut)'
        )

        item_db[IID.PRISMSHARD].set_desc_from_str(
            'Start Shell Trial (King 600 w/ Marle)'
        )

        item_db[IID.TOMAS_POP].set_desc_from_str(
            'Open GiantsClaw (Choras 1000 grave)'
        )

        item_db[IID.CLONE].set_desc_from_str(
            'Go DthPeak (KeeperDome w/ CT)'
        )

        item_db[IID.C_TRIGGER].set_desc_from_str(
            'Go DthPeak (KeeperDome w/ Clone)'
        )

        item_db[IID.JERKY].set_desc_from_str(
            'Unlock Porre Mayor (Porre Elder)'
        )

        item_db[IID.MOON_STONE].set_desc_from_str(
            'Charge in Sun keep for 65,002,300 yrs'
        )

        item_db[IID.SUN_STONE].set_desc_from_str(
            'Give to Melchior after King\'s Trial'
        )

        medal_desc = item_db[IID.HERO_MEDAL].get_desc_as_str()
        medal_desc += ' (Frog\'s Chest)'
        item_db[IID.HERO_MEDAL].set_desc_from_str(medal_desc)

        gameflags = self.settings.gameflags
        GF = rset.GameFlags

        if GF.UNLOCKED_SKYGATES in gameflags:
            item_db[IID.JETSOFTIME].set_desc_from_str(
                'Upgrade Epoch (Blackbird)'
            )
        if GF.ADD_BEKKLER_SPOT in gameflags:
            item_db[IID.C_TRIGGER].set_desc_from_str(
                'Go DthPeak (KeeperDome), Bekkler'
            )
        if GF.RESTORE_TOOLS in gameflags:
            item_db[IID.TOOLS].set_desc_from_str(
                'Repair Ruins (Choras Cafe)'
            )
        else:
            grandleon_desc = item_db[IID.MASAMUNE_2].get_desc_as_str()
            grandleon_desc += ' (Tools)'
            item_db[IID.MASAMUNE_2].set_desc_from_str(grandleon_desc)

        if GF.SPLIT_ARRIS_DOME in gameflags:
            item_db[IID.SEED].set_desc_from_str(
                'Give to Doan after CPU (Arris)'
            )
        if GF.RESTORE_JOHNNY_RACE in gameflags:
            desc = 'Walk Lab32'
            if GF.ADD_RACELOG_SPOT in gameflags:
                desc += ' + RaceLog Box'

            item_db[IID.BIKE_KEY].set_desc_from_str(desc)

    def __accelerate_carpenter_quest(self, ct_rom: CTRom):
        '''
        Just repair the whole ruins on the first visit.
        '''

        script = ct_rom.script_manager.get_script(
            ctenums.LocID.CHORAS_CARPENTER_600
        )

        EC = ctevent.EC
        EF = ctevent.EF

        hook_cmd = EC.set_bit(0x7F019F, 0x2)

        hook_pos = script.find_exact_command(
            hook_cmd,
            script.get_function_start(8, 1)
        ) + len(hook_cmd)

        func = (
            EF()
            .add(EC.set_bit(0x7F019F, 0x04))
            .add(EC.set_bit(0x7F019F, 0x08))
        )
        script.insert_commands(func.get_bytearray(), hook_pos)

    def __fix_northern_ruins_sealed(self, ct_rom: CTRom):
        # In Vanilla 0x7F01A3 & 0x10 is set for 600AD ruins
        #            0x7F01A3 & 0x08 is set for 1000AD ruins

        # In Jets 0x7F01A3 & 0x20 is set for 1000AD ruins
        #         0x7F01A3 & 0x10 is set for 600AD ruins

        # In 0x44 Northern Ruins Antechamber, Object 0x10
        #   Past obtained - 0x7F01A6 & 0x01
        #   Present obtained - 0x7F01A9 & 0x20
        #   Charged - 0x7F01A6 & 0x08  (Freed up)
        # Jets does some different things, but we'll use the vanilla values b/c
        # they seem to not have been repurposed.
        # Note: This frees up 0x7F01A6 & 0x08 for other use.
        # Note to note.  We're using 0x7F01A6 for the cat counter.
        script = ctevent.Event.from_flux(
            './flux/VR_044_Northern_Ruins_Ante.Flux'
        )
        ct_rom.script_manager.set_script(
            script,
            ctenums.LocID.NORTHERN_RUINS_ANTECHAMBER
        )

        # In 0x46 Northern Ruins Back Room, there two chests:
        # 1) Object 0x10
        #      Past obtained - 0x7F01A6 & 0x02
        #      Present obtained - 0x7F01A9 & 0x40
        #      Charged - 0x7F01A6 & 0x10  (Freed up)
        # 1) Object 0x11
        #      Past obtained - 0x7F01A6 & 0x04
        #      Present obtained - 0x7F01A9 & 0x80
        #      Charged - 0x7F01A6 & 0x20  (Freed up)
        script = ctevent.Event.from_flux(
            './flux/VR_046_Northern_Ruins_Back.Flux'
        )
        ct_rom.script_manager.set_script(
            script,
            ctenums.LocID.NORTHERN_RUINS_BACK_ROOM
        )

    def __update_trading_post_string(self, ct_rom: CTRom,
                                     config: cfg.RandoConfig):
        script_man = ct_rom.script_manager

        script = script_man.get_script(ctenums.LocID.IOKA_TRADING_POST)

        # Petal, Fang -> Ranged
        # Petal, Horn -> Accessory
        # Petal, Feather -> Tab
        # Fang, Horn -> Melee
        # Fang, Feather -> Armor
        # Horn, Feather -> Helm

        TID = ctenums.TreasureID
        tp_spots = (TID.TRADING_POST_RANGED_WEAPON,
                    TID.TRADING_POST_ACCESSORY,
                    TID.TRADING_POST_TAB,
                    TID.TRADING_POST_MELEE_WEAPON,
                    TID.TRADING_POST_ARMOR,
                    TID.TRADING_POST_HELM)

        tp_name_dict = {}

        item_db = config.item_db
        CTName = ctstrings.CTNameString
        for treasure_id in tp_spots:
            item_id = config.treasure_assign_dict[treasure_id].reward
            name_b = CTName(item_db[item_id].name[1:])
            name = str(name_b)
            tp_name_dict[treasure_id] = name

        new_str = \
            'Many things for trade!{line break}'\
            f'Petal, Fang: {tp_name_dict[TID.TRADING_POST_RANGED_WEAPON]}'\
            '{line break}'\
            f'Petal, Horn: {tp_name_dict[TID.TRADING_POST_ACCESSORY]}'\
            '{line break}'\
            f'Petal, Feather: {tp_name_dict[TID.TRADING_POST_TAB]}'\
            '{page break}'\
            f'Fang, Horn: {tp_name_dict[TID.TRADING_POST_MELEE_WEAPON]}'\
            '{line break}'\
            f'Fang, Feather: {tp_name_dict[TID.TRADING_POST_ARMOR]}'\
            '{line break}'\
            f'Horn, Feather: {tp_name_dict[TID.TRADING_POST_HELM]}'\
            '{null}'

        new_ct_str = ctstrings.CTString.from_str(new_str)
        new_ct_str.compress()
        script.strings[2] = new_ct_str
        script.modified_strings = True

    def __disable_xmenu_charlocks(self, ct_rom):
        '''Ignore the charlock byte when in the X-menu but not Y-menu.'''

        rom = ct_rom.rom_data
        space_man = rom.space_manager

        rt = bytearray.fromhex(
            'AD 36 0D'     # LDA $0D36  [$7E:0D36]  (will be FF in Y-menu, 0 X)
            '10 04'        # BPL foo
            'A9 00'        # LDA #$00 (no charlock byte)
            '80 04'        # BRA bar
            'AF DF 01 7F'  # LDA $7F01DF[$7F:01DF] (charlock byte) [foo]
            '6B'           # RTL [bar]
        )

        start = space_man.get_free_addr(len(rt))
        rom_start = byteops.to_rom_ptr(start)
        rom_start_b = rom_start.to_bytes(3, 'little')
        jsl = b'\x22' + rom_start_b

        rom.seek(0x02CD55)
        rom.write(jsl)

        mark_used = ctevent.FSWriteType.MARK_USED
        rom.seek(start)
        rom.write(rt, mark_used)

    def __set_omen_elevators_config(self):
        '''Determine which omen elevator encounters a seed gets.'''
        # Ruminators, goons, cybots
        fight_thresh_up = [0xA0, 0x60, 0x80]
        fight_thresh_down = [0x80, 0x60, 0xA0]
        fights_up = [ind for ind, thresh in enumerate(fight_thresh_up)
                     if random.randrange(0, 0x100) < thresh]
        fights_down = [ind for ind, thresh in enumerate(fight_thresh_down)
                       if random.randrange(0, 0x100) < thresh]

        self.config.omen_elevator_fights_up = fights_up
        self.config.omen_elevator_fights_down = fights_down

    def __set_omen_elevator_ctrom(self, ctrom: CTRom,
                                  fights: list[int],
                                  loc_id: ctenums.LocID):
        '''Write an omen elevator encounters to the rom.'''
        script_man = ctrom.script_manager
        script = script_man.get_script(loc_id)

        start = script.get_function_start(0, 0)
        end = script.get_function_end(0, 0)

        # There are three commands (0x7F) that load a random number.
        # These random numbers are then compared to some thresholds to
        # determine whether a fight occurs.
        pos = start
        for i in range(3):
            pos, cmd = script.find_command([0x7F], pos, end)
            offset = cmd.args[0]

            # Get a val to local mem command
            new_cmd = ctevent.EC.get_blank_command(0x4F)
            new_cmd.args[1] = offset

            # If we determined that fight i should occur, store a 0 to the
            # location that would have held the random number.  It will pass
            # any threshold.  Otherwise, assign 0xFF to fail any threshold.
            if i in fights:
                val = 0
            else:
                val = 0xFF

            new_cmd.args[0] = val

            # delete the get random command.  Put in the val-to-mem command.
            script.delete_commands(pos, 1)
            script.insert_commands(new_cmd.to_bytearray(),  pos)

            pos += len(new_cmd)

    def __set_omen_elevators_ctrom(self, ctrom: CTRom,
                                   config: cfg.RandoConfig):
        '''Set both omen elevators'''
        self.__set_omen_elevator_ctrom(
            ctrom, config.omen_elevator_fights_down,
            ctenums.LocID.BLACK_OMEN_ELEVATOR_DOWN
        )

        self.__set_omen_elevator_ctrom(
            ctrom, config.omen_elevator_fights_up,
            ctenums.LocID.BLACK_OMEN_ELEVATOR_UP
        )

    def __lavos_ngplus(self):
        '''Removes a check for dead Mammon Machine on Lavos NG+'''
        script_man = self.out_rom.script_manager
        script = script_man.get_script(ctenums.LocID.TESSERACT)

        start = script.get_function_start(0, 0)
        end = script.get_function_end(0, 0)

        pos, cmd = script.find_command([0x16], start, end)
        if cmd.args[0:3] == [0xA8, 0x80, 0x86]:
            script.delete_commands(pos, 1)
        else:
            raise ctevent.CommandNotFoundException('failed to find mm flag')

    def __free_guardia_forest_600_objs(self):
        """
        Remove Cyrus/Glenn cutscene objects to make room for objective objects.
        """
        loc_id = ctenums.LocID.GUARDIA_FOREST_600
        script = self.out_rom.script_manager.get_script(loc_id)

        for obj_id in range(0xD, 7, -1):
            script.remove_object(obj_id)

    def __try_bromide_fix(self):
        """
        Fix the bromide not being obtainable (despite message) after the boss
        is defeated.
        """
        loc_id = ctenums.LocID.MANORIA_STORAGE
        script = self.out_rom.script_manager.get_script(loc_id)
        EC = eventcommand.EventCommand
        OP = eventcommand.Operation

        pos = script.find_exact_command(
            EC.if_mem_op_value(0x7F0100, OP.BITWISE_AND_NONZERO, 0x02, 1, 0),
            script.get_function_start(8, 1)
        )

        pos += 5  # Get to next command, a goto.

        jump_byte_pos = pos + 1
        flag_set_pos = script.find_exact_command(EC.set_bit(0x7F00FE, 0x02), pos)

        bytes_jumped = flag_set_pos - jump_byte_pos
        script.data[jump_byte_pos] = bytes_jumped

    def __try_sunstone_pickup_fix(self):
        """
        Place the item addition and flag setting prior to the textbox.
        This is done already if ADD_SUNKEEP_SPOT is active.
        """

        if rset.GameFlags.ADD_SUNKEEP_SPOT in self.settings.gameflags:
            return

        loc_id = ctenums.LocID.SUN_KEEP_2300
        script = self.out_rom.script_manager.get_script(loc_id)
        EC = eventcommand.EventCommand
        EF = eventfunction.EventFunction

        pos = script.find_exact_command(EC.set_explore_mode(False),
                                        script.get_function_start(8, 1))
        script.delete_commands(pos, 1)
        set_bit_cmd = EC.set_bit(0x7F013A, 0x40)

        pos, _ = script.find_command([0xBB], pos)
        script.insert_commands(
            EF().add(set_bit_cmd)
            .add(EC.add_item(ctenums.ItemID.SUN_STONE)).get_bytearray(), pos
        )

        pos = script.find_exact_command(set_bit_cmd, pos + len(set_bit_cmd))
        script.delete_commands(pos, 2)

    def __try_manoria_softlock_fix(self):
        """
        Move coordinates of manoria hq fight triggers to avoid double hitting.
        """

        loc_id = ctenums.LocID.MANORIA_HEADQUARTERS
        script = self.out_rom.script_manager.get_script(loc_id)
        EC = eventcommand.EventCommand

        # Trigger objects are in 0x26, 0x27, 0x28.
        # Coordinates in startup are bogus.  They are set in Arb0.

        # Object 0x26 - 0x144, 0x1AC
        # Object 0x27 - 0x178, 0x1AC
        # Object 0x28 - 0x160, 0x198

        # We're going to try to get away with a single trigger (0x27)
        pos = script.get_function_start(0x26, 3)
        new_cmd = EC.set_object_coordinates_pixels(0x144, 0x120)
        script.data[pos: pos + len(new_cmd)] = new_cmd.to_bytearray()

        pos = script.get_function_start(0x28, 3)
        new_cmd = EC.set_object_coordinates_pixels(0x160, 0x120)
        script.data[pos: pos + len(new_cmd)] = new_cmd.to_bytearray()

        # Pixel coords are weird.
        pos = script.get_function_start(0x27, 3)
        new_cmd = EC.set_object_coordinates_pixels(0x160, 0x1AC)
        script.data[pos: pos + len(new_cmd)] = new_cmd.to_bytearray()

    def __try_supervisors_office_recruit_fix(self):
        '''
        Removes a premature ExploreMode On to prevent losing a recruit.
        '''
        loc_id = ctenums.LocID.PRISON_SUPERVISORS_OFFICE
        script = ctevent.Event.from_flux(
            './flux/jot_01D_Prison_Supervisor.Flux'
        )

        self.out_rom.script_manager.set_script(script, loc_id)

    def __try_mystic_mtn_portal_fix(self):
        '''
        Removes touch == activate from dactyl portal.  Maybe this fixes?
        '''
        loc_id = ctenums.LocID.MYSTIC_MTN_PORTAL
        script = self.out_rom.script_manager.get_script(loc_id)

        EF = ctevent.EF
        EC = ctevent.EC

        # Make a function that's just a return
        func = EF()
        func.add(EC.return_cmd())

        # Set the touch (0x02) function of the portal activation obj (0x0A)
        # to just return.
        script.set_function(0x0A, 0x02, func)

    def __try_proto_dome_fix(self):
        '''Removes touch == activate from proto recruit.  Maybe this fixes?'''
        script_man = self.out_rom.script_manager
        script = script_man.get_script(ctenums.LocID.PROTO_DOME)

        EF = ctevent.EF
        EC = ctevent.EC

        # Make a function that's just a return
        func = EF()
        func.add(EC.return_cmd())

        # Set the touch (0x02) function of the recruit obj (0x18) to the
        # return function.
        script.set_function(0x18, 0x02, func)

    def generate_rom(self):
        '''
        Turns settings + config into self.out_rom.
        '''
        if self.settings is None:
            raise NoSettingsException

        if self.config is None:
            raise NoConfigException

        if self.has_generated:
            return

        # With valid config and settings, we can write generate the rom
        self.__write_out_rom()

    # There are no good tools for working with animation scripts.  The
    # change is small, so we're doing it directly
    def __modify_bh_script(self):
        ct_rom = self.out_rom

        # Replace a weird unknown command (bh-specfic) with show damage
        ct_rom.rom_data.seek(0x0E3191)
        ct_rom.rom_data.write(b'\x50')

        # Change the hit effect with dark matter's
        ct_rom.rom_data.seek(0x0E319C)
        ct_rom.rom_data.write(
            bytearray.fromhex(
                '2402' +
                '6900' +
                '2014' +
                '6A' +
                # '36' +
                '00'
            )
        )

    def __write_config_to_out_rom(self):
        '''
        Writes elements of the config to self.out_rom
        '''
        config = self.config
        ctrom = self.out_rom

        # We can always do this, even if not reverting to black hole because
        # antilife just uses life2's script, not black hole's....
        # ...unless we're in vanilla mode.
        if self.settings.game_mode != rset.GameMode.VANILLA_RANDO:
            self.__modify_bh_script()

        # Subtle Bug Alert:
        # AtkDB needs to count the number of attacks when determining whether
        # it needs to reallocate.  To do this, it reads enemy data.  If the
        # new enemy data is written first, it will read the wrong number of
        # attacks and free too much.  So the ai/atks are written first.
        config.enemy_ai_db.write_to_ctrom(ctrom)
        config.enemy_atk_db.write_to_ctrom(ctrom)

        # Write enemies out
        for enemy_id, stats in config.enemy_dict.items():
            stats.write_to_ctrom(ctrom, enemy_id)

        for enemy_id, sprite_data in config.enemy_sprite_dict.items():
            sprite_data.write_to_ctrom(ctrom, enemy_id)

        # Write treasures out -- this includes key items
        # for treasure in config.treasure_assign_dict.values():
        for tid in config.treasure_assign_dict:
            treasure = config.treasure_assign_dict[tid]
            treasure.write_to_ctrom(ctrom)

        # Write shops out
        config.shop_manager.write_to_ctrom(ctrom)

        # Write items out
        config.item_db.write_to_ctrom(ctrom)

        # Write characters out
        # Recruitment spots
        for character in config.char_assign_dict.values():
            character.write_to_ctrom(ctrom)

        charassign.fix_cursed_recruit_spots(
            config, ctrom,
            rset.GameFlags.LOCKED_CHARS in self.settings.gameflags
        )

        # I need to write objectives before bosses are in because otherwise
        # the change in object count change the correct object_ids to hook into.
        bucketlist.write_objectives_to_ctrom(self.out_rom, self.settings,
                                             self.config)

        # Stats
        config.pcstats.write_to_ctrom(ctrom)

        # Write out the rest of the character data (incl. techs)
        charrando.reassign_characters_on_ctrom(ctrom, config)
        elementrando.update_element_placards_on_ctrom(ctrom, config)

        # Write out the bosses
        bossrando.write_bosses_to_ctrom(ctrom, config)

        # tabs
        tabwriter.rewrite_tabs_on_ctrom(ctrom, config)

        # Omen elevator
        self.__set_omen_elevators_ctrom(ctrom, config)

        scriptshortener.shorten_all_scripts(ctrom)
        # Disabling xmenu character locks is only relevant in LoC and IA, but
        # there's no reason not to just do it always.
        self.__disable_xmenu_charlocks(ctrom)

    def __write_out_rom(self):
        '''Given config and settings, write to self.out_rom'''
        self.out_rom = CTRom(self.base_ctrom.rom_data.getvalue(), True)

        initial_vanilla = False
        if CTRom.validate_ct_rom_bytes(self.out_rom.rom_data.getbuffer()):
            initial_vanilla = True
            # It's too hard reclaiming space from basepatch.ips.  Just take
            # one block that I know is OK.
            # basepatch.mark_initial_free_space(self.out_rom)
            self.out_rom.rom_data.space_manager.mark_block(
                (0x027DE4, 0x028000), ctevent.FSWriteType.MARK_FREE
            )

        # TODO:  Consider working some of the always-applied script changes
        #        Into base_patch.ips to improve generation speed.
        self.__apply_basic_patches(self.out_rom, self.settings)
        self.__free_guardia_forest_600_objs()
        self.__apply_settings_patches(self.out_rom, self.settings)


        if initial_vanilla:
            # self.out_rom.rom_data.space_manager.mark_block(
            chesttext.apply_chest_text_hack(
                self.out_rom, self.config.item_db
            )
            self.out_rom.rom_data.space_manager.mark_block(
                (0x027DE4, 0x028000), ctevent.FSWriteType.MARK_USED
            )

        # This makes copies of heckran cave passagesways, king's trial,
        # and now Zenan Bridge so that all bosses can go there.
        # There's no reason not do just do this regardless of whether
        # boss rando is on.
        mapmangler.duplicate_maps_on_ctrom(self.out_rom)
        mapmangler.duplicate_zenan_bridge(self.out_rom,
                                          ctenums.LocID.ZENAN_BRIDGE_BOSS)

        # Script changes which can always be made
        Event = ctevent.Event
        script_manager = self.out_rom.script_manager

        # Three dc flag patches can be added regardless.  No reason not to.

        # 1) Set magic learning at game start depending on character assignment
        #    unless LW...because telepod exhibit now has the LW portal change.

        if self.settings.game_mode != rset.GameMode.LOST_WORLDS:
            telepod_event = Event.from_flux('./flux/cr_telepod_exhibit.flux')

            # 3.1.1 Change:
            # The only relevant script change with 3.1.1 is setting the
            # 0x80 bit of 0x7f0057 for the skyway logic in the Telepod
            # Exhibit script.
            EC = ctevent.EC

            # set flag cmd -- too lazy to make an EC function for this
            cmd = EC.generic_two_arg(0x65, 0x07, 0x57)
            start = telepod_event.get_function_start(0x0E, 0x04)
            end = telepod_event.get_function_end(0x0E, 0x04)

            # Set the flag right before the screen darkens
            pos = telepod_event.find_exact_command(EC.fade_screen(),
                                                   start, end)
            telepod_event.insert_commands(cmd.to_bytearray(), pos)

            script_manager.set_script(telepod_event,
                                      ctenums.LocID.TELEPOD_EXHIBIT)
        else:
            # The LW mode sets the magic-learned bits on the load screen.
            # We will just set them all.
            load_screen_event = script_manager.get_script(
                ctenums.LocID.LOAD_SCREEN
                )

            cmd = ctevent.EC.set_bit(0x7F01E0, 0x01)
            pos = load_screen_event.find_exact_command(cmd)

            new_cmd = ctevent.EC.assign_val_to_mem(0x7F, 0x7F01E0, 1)
            load_screen_event.insert_commands(new_cmd.to_bytearray(),
                                              pos)

        # 2) Allows left chest when medal is on non-Frog Frogs
        burrow_event = Event.from_flux('./flux/cr_burrow.Flux')

        # 3) Start Ruins quest when Grand Leon is on non-Frog Frogs
        choras_cafe_event = Event.from_flux('./flux/cr_choras_cafe.Flux')

        script_manager.set_script(burrow_event,
                                  ctenums.LocID.FROGS_BURROW)
        script_manager.set_script(choras_cafe_event,
                                  ctenums.LocID.CHORAS_CAFE)

        # 4) Fixed trading post script
        tp_event = Event.from_flux('./flux/jot_trading_post.Flux')
        script_manager.set_script(tp_event, ctenums.LocID.IOKA_TRADING_POST)

        # Flag specific script changes:
        #   - Locked characters changes to proto dome and dactyl nest
        #   - Duplicate characters changes to Spekkio when not in LW
        flags = self.settings.gameflags
        mode = self.settings.game_mode
        char_rando = rset.GameFlags.CHAR_RANDO in flags
        locked_chars = rset.GameFlags.LOCKED_CHARS in flags
        lost_worlds = rset.GameMode.LOST_WORLDS == mode
        vanilla = rset.GameMode.VANILLA_RANDO == mode
        epoch_fail = rset.GameFlags.EPOCH_FAIL in flags

        if char_rando and not lost_worlds:
            # Lets Spekkio give magic properly with randomized/duplicate chars
            rc_spekkio_event = Event.from_flux('./flux/charrando-eot.flux')
            script_manager.set_script(rc_spekkio_event,
                                      ctenums.LocID.SPEKKIO)

        if locked_chars:
            # Note: Proto Dome's lock is taken care of in charassign now.
            lc_dactyl_upper_event = \
                Event.from_flux('./flux/lc_dactyl_upper.Flux')
            script_manager.set_script(lc_dactyl_upper_event,
                                      ctenums.LocID.DACTYL_NEST_UPPER)

        # Proto fix, Mystic Mtn fix, and Lavos NG+ are candidates for being
        # rolled into base_patch.ips.

        prismshard.update_prismshard_quest(self.out_rom)

        elementrando.update_ctrom(self.out_rom, self.config)

        if epoch_fail:
            epochfail.apply_epoch_fail(self.out_rom, self.settings)

        if vanilla:
            # Restore geno conveyor, 6 R-series, easier lavos script.
            # Logic changes are all handled by flags now.
            vanillarando.restore_scripts(self.out_rom)

        self.__apply_logic_tweaks_to_ctrom(self.settings, self.config,
                                           self.out_rom)

        if rset.GameFlags.UNLOCKED_MAGIC in self.settings.gameflags:
            fastmagic.add_tracker_hook(self.out_rom)

        if self.settings.game_mode == rset.GameMode.LOST_WORLDS:
            self.__clean_lw_loadscreen(self.out_rom)

        self.__set_active_wait_song(self.out_rom)

        # Don't require visiting Flea/Slash rooms for Magus's Castle
        if self.settings.game_mode != rset.GameMode.LOST_WORLDS:
            # The Telepod script is different in LW.  Just ignore.
            self.__set_fast_magus_castle(self.out_rom)

        self.__set_fast_zeal_teleporters(self.out_rom)

        # Use 0x7F01A6 for the cat counter.
        self.__add_cat_pet_flag(self.out_rom, 0x7F01A6, 0x08)

        # Split the NR "sealed" chests and make the quest a little faster.
        self.__fix_northern_ruins_sealed(self.out_rom)
        self.__accelerate_carpenter_quest(self.out_rom)

        # Update the trading post descriptions
        self.__update_trading_post_string(self.out_rom, self.config)

        # Two potential softlocks caused by (presumably) touch == activate.
        self.__try_proto_dome_fix()
        self.__try_mystic_mtn_portal_fix()

        # One softlock caused by (presumably) race condition on touch triggers
        self.__try_manoria_softlock_fix()

        # Bromide not obtainable after Yakra fix
        self.__try_bromide_fix()

        # Sunstone flag/item is not added until after music change
        self.__try_sunstone_pickup_fix()

        # Potential recruit loss when characters rescue in prison
        self.__try_supervisors_office_recruit_fix()

        # Enable NG+ by defeating Lavos without doing Omen.
        self.__lavos_ngplus()

        # Everything prior was purely based on settings, not the randomization.
        # Now, write the information from the config to the rom.
        self.__write_config_to_out_rom()

        # Fix to giant's claw box
        claw_copy = treasuretypes.ChestTreasureData()
        claw_copy.copy_location = ctenums.LocID.TYRANO_LAIR_ANTECHAMBERS
        claw_copy.write_to_ctrom(self.out_rom, 0x19)

        # Ice Age/LoC script changes need to go after the config is written
        # because the recruit spot works by changing all character recruit
        # commands into the recruit's version.  The code inserted by theen
        # recruit locks would get incorrectly changed by this.
        mode = self.settings.game_mode
        if mode == rset.GameMode.ICE_AGE:
            iceage.set_ice_age_recruit_locks(self.out_rom,
                                             self.config)
            iceage.set_ice_age_dungeon_locks(self.out_rom, self.config)
            iceage.set_ending_after_woe(self.out_rom)
        elif mode == rset.GameMode.LEGACY_OF_CYRUS:
            legacyofcyrus.write_loc_recruit_locks(self.out_rom,
                                                  self.config)
            legacyofcyrus.write_loc_dungeon_locks(self.out_rom)
            legacyofcyrus.set_ending_after_ozzies_fort(self.out_rom)
        elif mode == rset.GameMode.VANILLA_RANDO:
            vanillarando.restore_sos(self.out_rom, self.config)

        # Write and remove all scripts
        self.out_rom.write_all_scripts_to_rom(clear_scripts=True)

        # Put the seed hash on the active/wait screen
        self.hash_string_bytes = seedhash.write_hash_string(self.out_rom)

        # Apply post-randomization changes
        self.__apply_cosmetic_patches(self.out_rom, self.settings)
        self.__set_bike_champions(
            self.out_rom,
            'Xelpher', 'I\'m All N', 'Korenth'
        )
        self.__set_fair_racers(
            self.out_rom,
            catalack_name='Xelpher',
            steel_runner_name='Korenth',
            green_ambler_name='I\'m All N',
            gi_jogger_name='AzureCale',
        )

        # Rewrite any scripts changed by post-randomization
        self.out_rom.write_all_scripts_to_rom()
        self.out_rom.fix_snes_checksum()
        self.has_generated = True

    def get_generated_rom(self) -> bytes:
        if not self.has_generated:
            self.generate_rom()

        if self.out_rom is None:
            raise GenerationFailedException("Failed to generate rom.")
        return self.out_rom.rom_data.getvalue()

    def write_spoiler_log(self, outfile):
        if isinstance(outfile, str):
            with open(outfile, 'w', encoding='utf-8') as real_outfile:
                self.write_spoiler_log(real_outfile)
        else:
            self.write_settings_spoilers(outfile)
            self.write_tab_spoilers(outfile)
            self.write_consumable_spoilers(outfile)
            self.write_objective_spoilers(outfile)
            self.write_key_item_spoilers(outfile)
            self.write_boss_rando_spoilers(outfile)
            self.write_character_spoilers(outfile)
            self.write_boss_stat_spoilers(outfile)
            self.write_treasure_spoilers(outfile)
            self.write_drop_charm_spoilers(outfile)
            self.write_shop_spoilers(outfile)
            self.write_item_stat_spoilers(outfile)

    def write_json_spoiler_log(self, outfile):
        if isinstance(outfile, str):
            with open(outfile, 'w', encoding='utf-8') as real_outfile:
                self.write_json_spoiler_log(real_outfile)
        else:
            json.dump(
                {"configuration": self.config, "settings": self.settings},
                outfile, cls=JOTJSONEncoder, indent=2
            )

    def _summarize_dupes(self):
        CharID = ctenums.CharID

        def summarize_single(choicelist):
            if len(choicelist) < 4:
                return "Only " + \
                    ", ".join([str(CharID(i)) for i in choicelist])
            elif len(choicelist) == 7:
                return "Any"
            else:
                return "No " + \
                    ", ".join([str(CharID(i))
                               for i in (set(range(7)) - set(choicelist))])

        chars = {c: summarize_single(self.settings.char_settings.choices[c])
                 for c in range(len(self.settings.char_settings.choices))}
        rv = ""
        for c in sorted(chars.keys()):
            if chars[c] != "Any":
                rv = rv + "\n\t" + str(CharID(c)) + ": " + chars[c]
        return rv

    def write_settings_spoilers(self, file_object):
        gf = self.settings.gameflags

        def pretty(flags: rset.GameFlags, indent="", width=80) -> str:
            # use textwrap.wraps hyphen-splitting mechanism to split on flags
            text = str(flags).replace("|", "-")
            lines = [
                line.replace("-", "|").rstrip("|")
                for line in textwrap.wrap(
                    text, width=width, break_long_words=False, subsequent_indent=indent
                )
            ]
            return "\n".join(lines)

        if self.hash_string_bytes is not None:
            hashstr = str(ctstrings.CTNameString(self.hash_string_bytes)).replace('*', '{star}')
            file_object.write(f"Seed Hash: {hashstr}\n")
        file_object.write(f"Game Mode: {self.settings.game_mode}\n")
        file_object.write(f"Enemies: {self.settings.enemy_difficulty}\n")
        file_object.write(f"Items: {self.settings.item_difficulty}\n")
        if self.settings.tab_settings != rset.TabSettings():
            tab_set = self.settings.tab_settings
            file_object.write(
                f"Tabs: Power {tab_set.power_min}-{tab_set.power_max}, "
                f"Magic {tab_set.magic_min}-{tab_set.magic_max}, "
                f"Speed {tab_set.speed_min}-{tab_set.speed_max}\n"
            )
        if rset.GameFlags.CHAR_RANDO in gf and \
           self.settings.char_settings.choices != rset.Settings().char_settings.choices:

            dupes = self._summarize_dupes()
            file_object.write(f"Characters: {dupes}\n")
        file_object.write(f"Techs: {self.settings.techorder}\n")
        file_object.write(f"Shops: {self.settings.shopprices}\n")
        pretty_flags = pretty(gf, indent=16*" "+"|")
        file_object.write(f"Flags: {pretty_flags}\n")
        # if settings changed from initial values passed by user, print flags diff
        if self.settings.initial_flags and gf != self.settings.initial_flags:
            diff = "Diff:"
            plus_flags, minus_flags = self.settings.get_flag_diffs()
            if plus_flags:
                plus = pretty(plus_flags, indent="  + |", width=73)
                diff += f"\n  + {plus}"
            if minus_flags:
                minus = pretty(minus_flags, indent=" - |", width=73)
                diff += f"\n  - {minus}"
            file_object.write(textwrap.indent(f"{diff}\n", 7*" "))
        if rset.GameFlags.BOSS_RANDO in self.settings.gameflags and self.settings.ro_settings.flags:
            pretty_ro = pretty(self.settings.ro_settings.flags, indent=23*" "+"|")
            file_object.write(f"RO Flags: {pretty_ro}\n")
        if self.settings.cosmetic_flags:
            pretty_cosmetics = pretty(self.settings.cosmetic_flags, indent=23*" "+"|")
            file_object.write(f"Cosmetic: {pretty_cosmetics}\n")
        file_object.write("\n")

    def write_consumable_spoilers(self, file_object):
        file_object.write("Consumable Properties\n")
        file_object.write("---------------------\n")

        IID = ctenums.ItemID
        consumables = (
            IID.TONIC, IID.MID_TONIC, IID.FULL_TONIC,
            IID.ETHER, IID.MID_ETHER, IID.FULL_ETHER,
            IID.LAPIS, IID.REVIVE
        )

        for item_id in consumables:
            item = self.config.item_db[item_id]
            name = ctstrings.CTNameString(item.name)
            name_str = str(name).ljust(15, ' ')
            desc = ctstrings.CTString(item.desc[:-1])  # Remove {null}
            desc_str = desc.to_ascii()

            file_object.write(name_str+desc_str+'\n')
        file_object.write('\n')

    def write_tab_spoilers(self, file_object):
        file_object.write("Tab Properties\n")
        file_object.write("--------------\n")

        tab_names = [
            'Power Tab',
            'Magic Tab',
            'Speed Tab'
        ]

        tab_magnitudes = [
            self.config.tab_stats.power_tab_amt,
            self.config.tab_stats.magic_tab_amt,
            self.config.tab_stats.speed_tab_amt
        ]

        for name, magnitude in zip(tab_names, tab_magnitudes):
            file_object.write(f'{name}: +{magnitude}\n')

        file_object.write('\n')

    def write_key_item_spoilers(self, file_object):
        file_object.write("Key Item Locations\n")
        file_object.write("------------------\n")

        # We have to use the logicwriter's Location class only because
        # of Chronosanity's linked locations needing to be handled properly.

        width = max(len(x.getName()) for x in self.config.key_item_locations)

        for location in self.config.key_item_locations:
            item_id = location.lookupKeyItem(self.config)
            item_name = self.config.item_db[item_id].get_name_as_str(True)
            file_object.write(str.ljust(f"{location.getName()}", width+8) +
                              item_name + '\n')
        file_object.write('\n')
        file_object.write('Completion by Spheres:\n')
        spheres = logicwriter.get_proof_string_from_settings_config(
            self.settings, self.config
        )
        file_object.write(spheres + '\n')

    def write_character_spoilers(self, file_object):
        pcstats = self.config.pcstats
        char_assign = self.config.char_assign_dict

        file_object.write("Character Locations\n")
        file_object.write("-------------------\n")
        for recruit_spot in char_assign.keys():
            held_char = char_assign[recruit_spot].held_char
            reassign_char = \
                pcstats.get_character_assignment(held_char)
            file_object.write(str.ljust(f"{recruit_spot}", 20) +
                              f"{char_assign[recruit_spot].held_char}"
                              f" reassigned {reassign_char}\n")
        file_object.write('\n')

        file_object.write("Character Stats\n")
        file_object.write("---------------\n")

        CharID = ctenums.CharID
        char_rando = rset.GameFlags.CHAR_RANDO in self.settings.gameflags
        tech_db = self.config.tech_db

        for char_id in range(7):
            pc_id = CharID(char_id)
            file_object.write(f"{CharID(char_id)}:")
            if char_rando:
                file_object.write(
                    f" assigned to {pcstats.get_character_assignment(pc_id)}"
                )
            file_object.write('\n')
            file_object.write(
                pcstats.pc_stat_dict[pc_id].get_spoiler_string(
                    self.config.item_db
                )
            )

            file_object.write('Tech Order:\n')
            for tech_num in range(8):
                tech_id = 1 + 8*char_id + tech_num
                tech = tech_db.get_tech(tech_id)
                name = ctstrings.CTString.ct_bytes_to_techname(tech['name'])
                file_object.write(f"\t{name}\n")
            file_object.write('\n')

    def write_treasure_spoilers(self, file_object):
        # Where should the location groupings go?
        width = max(len(str(x))
                    for x in self.config.treasure_assign_dict.keys())

        file_object.write("Treasure Assignment\n")
        file_object.write("-------------------\n")
        treasure_dict = self.config.treasure_assign_dict
        for treasure in treasure_dict.keys():
            reward = treasure_dict[treasure].reward
            if isinstance(reward, ctenums.ItemID):
                name = self.config.item_db[reward].get_name_as_str(True)
            else:
                name = f'{reward}G'

            file_object.write(str.ljust(str(treasure), width+8) +
                              name + '\n')
        file_object.write('\n')

    def write_shop_spoilers(self, file_object):
        file_object.write("Shop Assigmment\n")
        file_object.write("---------------\n")
        file_object.write(
            self.config.shop_manager.get_spoiler_string(self.config.item_db)
        )
        file_object.write('\n')

    def write_item_stat_spoilers(self, file_object):
        file_object.write("Item Stats\n")
        file_object.write("----------\n")

        # width = max(len(str(x)) for x in list(ctenums.ItemID)) + 8

        item_ids = [x for x in list(ctenums.ItemID)
                    if x in range(1, ctenums.ItemID(0xD0))]

        for item_id in item_ids:
            item = self.config.item_db[item_id]
            name = str(ctstrings.CTNameString(item.name[1:])).ljust(15, ' ')
            desc = ctstrings.CTString(item.desc[:-1]).to_ascii()
            price = str(item.price).rjust(5, ' ') + 'G'

            file_object.write(name + ' ' + price + ' ' + desc + '\n')
        file_object.write('\n')

    def write_boss_rando_spoilers(self, file_object):
        file_object.write("Boss Locations\n")
        file_object.write("--------------\n")

        boss_dict = self.config.boss_assign_dict
        width = max(len(str(x)) for x in boss_dict.keys()) + 8

        for location in boss_dict.keys():
            boss_name = str(boss_dict[location])

            if location == rotypes.BossSpotID.OCEAN_PALACE_TWIN_GOLEM:
                boss_name = 'Twin ' + boss_name

            file_object.write(
                str.ljust(str(location), width) +
                boss_name +
                '\n'
            )

        file_object.write('\n')

    def write_boss_stat_spoilers(self, file_object):

        scale_dict = self.config.boss_rank_dict
        BossID = rotypes.BossID

        file_object.write("Boss Stats\n")
        file_object.write("----------\n")

        endboss_ids = [
            BossID.LAVOS_SHELL, BossID.INNER_LAVOS, BossID.LAVOS_CORE,
            BossID.MAMMON_M, BossID.ZEAL, BossID.ZEAL_2
        ]

        boss_ids = list(self.config.boss_assign_dict.values()) + \
            [BossID.MAGUS, BossID.BLACK_TYRANO] + endboss_ids

        if rotypes.BossSpotID.OCEAN_PALACE_TWIN_GOLEM in \
           self.config.boss_assign_dict:
            boss_ids.append(rotypes.BossID.TWIN_BOSS)

        for boss_id in boss_ids:
            file_object.write(str(boss_id)+':')
            if boss_id in scale_dict.keys():
                file_object.write(
                    f" Key Item scale rank = {scale_dict[boss_id]}"
                )
            if boss_id == BossID.BLACK_TYRANO:
                tyrano_elem = bossrando.get_black_tyrano_element(self.config)
                file_object.write(
                    f" Element is {tyrano_elem}"
                )
            elif boss_id == BossID.RUST_TYRANO:
                tyrano_elem = bossrando.get_rust_tyrano_element(
                    ctenums.EnemyID.RUST_TYRANO, self.config
                )
                file_object.write(
                    f" Element is {tyrano_elem}"
                )
            elif boss_id == BossID.TWIN_BOSS:
                name = self.config.enemy_dict[ctenums.EnemyID.TWIN_BOSS].name
                if name == 'Rust Tyrano':
                    tyrano_elem = bossrando.get_rust_tyrano_element(
                        ctenums.EnemyID.TWIN_BOSS, self.config
                    )
                    file_object.write(
                        f" Element is {tyrano_elem}"
                    )
            # elif boss_id == BossID.MEGA_MUTANT:
            #     part = ctenums.EnemyID.MEGA_MUTANT_BOTTOM
            #     obstacle_id = bossrando.get_obstacle_id(part, self.config)
            #     obstacle = self.config.enemy_atk_db.get_tech(obstacle_id)
            #     obstacle_status = obstacle.effect.status_effect
            #     status_string = ', '.join(str(x) for x in obstacle_status)
            #     file_object.write(f' Obstacle is {status_string}')
            # elif boss_id == BossID.TERRA_MUTANT:
            #     part = ctenums.EnemyID.TERRA_MUTANT_HEAD
            #     obstacle_id = bossrando.get_obstacle_id(part, self.config)
            #     obstacle = self.config.enemy_atk_db.get_tech(obstacle_id)
            #     obstacle_status = obstacle.effect.status_effect
            #     status_string = ', '.join(str(x) for x in obstacle_status)
            #     file_object.write(f' Obstacle is {status_string}')

            file_object.write('\n')

            boss_scheme = self.config.boss_data_dict[boss_id]
            part_ids = [part.enemy_id for part in boss_scheme.parts]
            for part_id in part_ids:
                if len(part_ids) > 1:
                    file_object.write(f"Part: {part_id}\n")
                part = self.config.enemy_dict[part_id]
                part_str = part.get_spoiler_string(self.config.item_db)
                # put the string one tab out
                part_str = '\t' + str.replace(part_str, '\n', '\n\t')
                file_object.write(part_str+'\n')
            file_object.write('\n')

        obstacle = self.config.enemy_atk_db.get_tech(0x58)
        obstacle_status = obstacle.effect.status_effect
        status_string = ', '.join(str(x) for x in obstacle_status)
        file_object.write("Obstacle is {status_string}\n\n")

    def write_drop_charm_spoilers(self, file_object):
        file_object.write("Enemy Drop and Charm\n")
        file_object.write("--------------------\n")

        EnTier = enemyrewards.RewardGroup
        get_enemies = enemyrewards.get_enemy_tier
        tiers = [
            get_enemies(EnTier.COMMON_ENEMY),
            get_enemies(EnTier.UNCOMMON_ENEMY),
            get_enemies(EnTier.RARE_ENEMY),
            get_enemies(EnTier.RAREST_ENEMY),
            (
                get_enemies(EnTier.EARLY_BOSS) +
                get_enemies(EnTier.MIDGAME_BOSS) +
                get_enemies(EnTier.LATE_BOSS)
            )
        ]

        labels = ['Common Enemies',
                  'Uncommon Enemies',
                  'Rare Enemies',
                  'Rarest Enemies',
                  'Bosses']

        ids = [x for tier in tiers for x in tier]
        width = max(len(str(x)) for x in ids) + 8

        item_db = self.config.item_db

        for ind, tier in enumerate(tiers):
            file_object.write(labels[ind] + '\n')
            for enemy_id in tier:
                drop_id = self.config.enemy_dict[enemy_id].drop_item
                drop_str = item_db[drop_id].get_name_as_str(True)
                charm_id = self.config.enemy_dict[enemy_id].charm_item
                charm_str = item_db[charm_id].get_name_as_str(True)
                file_object.write(
                    '\t' +
                    str.ljust(f"{enemy_id}", width) +
                    " Drop: " + drop_str + '\n'
                )
                file_object.write(
                    '\t' +
                    str.ljust("", width) +
                    "Charm: " + charm_str + '\n'
                )

        file_object.write('\n')

    def write_objective_spoilers(self, file_object: typing.TextIO):
        if rset.GameFlags.BUCKET_LIST not in self.settings.gameflags:
            return

        file_object.write("Objectives\n")
        file_object.write("----------\n")

        bset = self.settings.bucket_settings

        reward_str = "unlock the bucket"
        if bset.objectives_win:
            reward_str = "win the game"
            file_object.write(f"Complete {bset.num_objectives_needed} to "
                          f"{reward_str}.\n")

        if bset.disable_other_go_modes:
            file_object.write("Other go modes are DISABLED.\n\n")

        num_objectives = self.settings.bucket_settings.num_objectives
        for ind, objective in enumerate(self.config.objectives):
            if ind >= num_objectives:
                break

            file_object.write(f'Objective {ind+1}: {objective.desc}\n')

        file_object.write('\n')

    @classmethod
    def __apply_logic_tweaks_to_config(cls, settings: rset.Settings,
                                       config: cfg.RandoConfig):
        '''
        Applies logic tweaks to the config.  Assumes that the settings are
        valid (no conflicts w/ game mode)
        '''
        flags = settings.gameflags
        GF = rset.GameFlags

        if GF.ADD_SUNKEEP_SPOT in flags:
            vanillarando.add_sunstone_spot_to_config(config)

        if GF.ADD_BEKKLER_SPOT in flags:
            vanillarando.add_vanilla_clone_check_to_config(config)

        if GF.ADD_CYRUS_SPOT in flags:
            vanillarando.restore_cyrus_grave_check_to_config(config)

        if GF.ADD_OZZIE_SPOT in flags:
            vanillarando.add_check_to_ozzies_fort_in_config(config)

        if GF.SPLIT_ARRIS_DOME in flags:
            vanillarando.add_arris_food_locker_check_to_config(config)

        if GF.ADD_RACELOG_SPOT in flags:
            vanillarando.add_racelog_chest_to_config(config)

    @classmethod
    def __apply_logic_tweaks_to_ctrom(cls, settings: rset.Settings,
                                      config: cfg.RandoConfig,
                                      ct_rom: CTRom):
        '''
        Applies logic tweaks to the scripts.  Assumes that the settings are
        valid (no conflicts w/ game mode)
        '''

        flags = settings.gameflags
        GF = rset.GameFlags

        if GF.UNLOCKED_SKYGATES in flags:
            vanillarando.unlock_skyways(ct_rom)

        if GF.ADD_SUNKEEP_SPOT in flags:
            vanillarando.split_sunstone_quest(ct_rom)

        if GF.ADD_BEKKLER_SPOT in flags:
            vanillarando.add_vanilla_clone_check_scripts(ct_rom)

        if GF.RESTORE_TOOLS in flags:
            vanillarando.restore_tools_to_carpenter_script(ct_rom)

        if GF.ADD_CYRUS_SPOT in flags:
            vanillarando.restore_cyrus_grave_script(ct_rom)

        if GF.ADD_OZZIE_SPOT in flags:
            vanillarando.add_check_to_ozzies_fort_script(ct_rom)

        if GF.RESTORE_JOHNNY_RACE in flags:
            vanillarando.restore_johnny_race(ct_rom)

        if GF.SPLIT_ARRIS_DOME in flags:
            vanillarando.split_arris_dome(ct_rom)

        if GF.VANILLA_DESERT in flags:
            vanillarando.revert_sunken_desert_lock(ct_rom)

        if GF.VANILLA_ROBO_RIBBON in flags:
            vanillarando.restore_ribbon_boost_atropos(
                ct_rom, config.boss_assign_dict
        )

    # Because switching logic is a feature now, we need a settings object.
    # Ugly.  BETA_LOGIC flag is gone now, but keeping it as-is in case of
    # logic changes to test.
    @classmethod
    def __apply_basic_patches(cls, ctrom: CTRom,
                              settings: Optional[rset.Settings] = None):
        '''Apply patches that are always applied to a jets rom.'''
        rom_data = ctrom.rom_data

        if settings is None:
            # Will give non-beta patch.  Outside of normal randomization,
            # where a settings object is provided, this function is only
            # called for dumping a basic config, and this won't change
            # depending on beta or not.
            settings = rset.Settings.get_race_presets()

        # Apply the patches that always are applied for jets
        # base_patch.ips makes sure that we have
        #   - Stats/stat growths for characters for CharManager
        #   - Tech data for TechDB
        #   - Item data (including prices) for shops
        # patch_codebase.txt may not be needed
        rom_data.patch_ips_file('./patches/base_patch.ips')

        # 99.9% sure this patch is redundant now
        rom_data.patch_txt_file('./patches/patch_codebase.txt')

        # I verified that the following convenience patches which are now
        # always applied are disjoint from the glitch fix patches, so it's
        # safe to move them here.
        rom_data.patch_txt_file('./patches/fast_overworld_walk_patch.txt')
        rom_data.patch_txt_file('./patches/faster_epoch_patch.txt')
        rom_data.patch_txt_file('./patches/faster_menu_dpad.txt')

        # Add qwertymodo's MSU-1 patch
        # rom_data.patch_ips_file('./patches/chrono_msu1.ips')

        basepatch.apply_tf_compressed_enemy_gfx_hack(ctrom)

    @classmethod
    def __apply_settings_patches(cls, ctrom: CTRom,
                                 settings: rset.Settings):
        '''
        Apply patches to a vanilla ctrom based on randomizer settings.
        These are patches not handled by writing the config.
        '''

        rom_data = ctrom.rom_data
        flags = settings.gameflags
        mode = settings.game_mode

        if rset.GameFlags.FIX_GLITCH in flags:
            rom_data.patch_txt_file('./patches/save_anywhere_patch.txt')
            rom_data.patch_txt_file('./patches/unequip_patch.txt')
            rom_data.patch_txt_file('./patches/fadeout_patch.txt')
            rom_data.patch_txt_file('./patches/hp_overflow_patch.txt')

        # TODO:  I'd like to do this with .Flux event changes
        if rset.GameFlags.ZEAL_END in flags:
            # rom_data.patch_txt_file('./patches/zeal_end_boss.txt')
            cls.__apply_zeal_end(ctrom)

        # Patching with lost.ips does not give a valid event for
        # mystic mountains.  I could fix the event by applying a flux file,
        # but I'm worried about what might happen when the invalid event is
        # marked free space.  For now we keep with older versions and apply the
        # mysticmtnfix.ips to restore the event.
        if rset.GameMode.LOST_WORLDS == mode:
            rom_data.patch_ips_file('./patches/lost.ips')
            rom_data.patch_ips_file('./patches/mysticmtnfix.ips')

        if rset.GameFlags.FAST_PENDANT in flags:
            if mode in (rset.GameMode.LOST_WORLDS,
                        rset.GameMode.LEGACY_OF_CYRUS):
                # Game modes where there is no pendant trial need to enforce
                # fast pendant by changing scripts.
                fastpendant.apply_fast_pendant_script(ctrom)
            else:
                rom_data.patch_txt_file('./patches/fast_charge_pendant.txt')

        # Big TODO:  Unwrap the hard patch into its component changes.
        #            As far as I can tell it's just enemies and starting GP.
        # The only thing the hard.ips would do is set the initial gold.
        # We already read the enemy data with get_base_config_from_settings().
        if settings.item_difficulty == rset.Difficulty.HARD:
            cls.__set_initial_gold(ctrom, 10000)

        qolhacks.attempt_all_qol_hacks(ctrom, settings)

        if rset.GameFlags.UNLOCKED_MAGIC in flags:
            fastmagic.write_ctrom(ctrom, settings)

    @classmethod
    def __apply_zeal_end(cls, ct_rom: CTRom):
        '''
        Makes the Zeal fight end the game.  We need to add a check to make
        sure that it's not the Zeal fight from the bucket boss gauntlet.
        '''

        script = ct_rom.script_manager.get_script(
            ctenums.LocID.BLACK_OMEN_CELESTIAL_GATE
        )

        obj_id, func_id = 9, 1
        # Finding Zeal's textbox before sending to Lavos
        pos, cmd = script.find_command(
            [0xBB],
            script.get_function_start(obj_id, func_id),
            script.get_function_end(obj_id, func_id)
        )

        EC = ctevent.EC
        EF = ctevent.EF
        OP = eventcommand.Operation

        # I'm just copying the change location command originally used.
        # I don't know what all of the variants do.
        change_loc_command = EC.change_location(0x52, 0, 0, 0, 1)
        change_loc_command.command = 0xDF

        end_func = (
            EF()
            .add(EC.set_storyline_counter(0x75))
            .add(EC.darken(0x0C))
            .add(EC.fade_screen())
            .add_if(
                EC.if_mem_op_value(0x7F01A8, OP.BITWISE_AND_NONZERO, 0x80,
                                   1, 0),
                EF().add(EC.generic_command(0xFF, 0x9F))  # NG+ Mode7
            )
            .add(change_loc_command)
            .add(EC.return_cmd())
        )

        # The current way to encode that we're in the boss gauntlet is to
        # write 0x0001 to the apocalypse spot in 0x7E288B
        func = (
            EF()
            .add(EC.assign_mem_to_mem(0x7E288B, 0x7F0300, 2))
            .add_if(
                EC.if_mem_op_value(0x7F0300, OP.NOT_EQUALS, 1, 2, 0),
                end_func
            )
        )

        script.insert_commands(func.get_bytearray(), pos)

    @classmethod
    def __apply_cosmetic_patches(cls, ctrom: CTRom,
                                 settings: rset.Settings):
        cos_flags = settings.cosmetic_flags

        if rset.CosmeticFlags.QUIET_MODE in cos_flags:
            cosmetichacks.apply_quiet_mode(ctrom, settings)

        if rset.CosmeticFlags.ZENAN_ALT_MUSIC in cos_flags:
            cosmetichacks.zenan_bridge_alt_battle_music(ctrom, settings)

        if rset.CosmeticFlags.DEATH_PEAK_ALT_MUSIC in cos_flags:
            cosmetichacks.death_peak_singing_mountain_music(ctrom, settings)

        cosmetichacks.set_pc_names(
            ctrom, *settings.char_settings.names
        )

        if rset.CosmeticFlags.REDUCE_FLASH in cos_flags:
            flashreduce.apply_all_flash_hacks(ctrom)

        if rset.CosmeticFlags.AUTORUN in cos_flags:
            cosmetichacks.set_auto_run(ctrom)

        settings.ctoptions.write_to_ctrom(ctrom)

    @classmethod
    def dump_default_config(cls, ct_vanilla: bytearray):
        '''Turn vanilla ct rom into default objects for a config.
        Should run whenever a big patch (base_patch.ips, hard.ips) changes.'''
        ct_rom = CTRom(ct_vanilla, ignore_checksum=False)
        cls.__apply_basic_patches(ct_rom)

        RC = cfg.RandoConfig
        config = RC()
        cls.fill_default_config_entries(config)
        config.update_from_ct_rom(ct_rom)

        with Randomizer._get_pickle_path('default_randoconfig.pickle').open('wb') as outfile:
            pickle.dump(config, outfile)

    @classmethod
    def fill_default_config_entries(cls, config: cfg.RandoConfig):
        config.boss_assign_dict = rotypes.get_default_boss_assignment()
        config.treasure_assign_dict = treasuretypes.get_base_treasure_dict()
        config.char_assign_dict = pcrecruit.get_base_recruit_dict()
        config.boss_rank_dict = {}

    @classmethod
    def get_base_config_from_settings(cls,
                                      ct_vanilla: bytearray,
                                      settings: rset.Settings):
        '''Gets an rset.RandoConfig object with the correct initial values.

        RandoConfig members which are read from rom_data after patches:
          - enemy_dict: holds stats depending on hard mode or not
          - shop_manager: This shouldn't be strictly needed, but at present
                          ShopManager objects read the initial shop data from
                          the rom.
          - price_manager: base_patch.ips changes the default prices.
                           Potentially the difficulty patch could too.
          - char_manager: base_patch.ips changes character stat growths and
                          base stats.
          - tech_db: base_patch.ips changes the basic techs (i.e. Antilife)
          - enemy_atk_db: Various enemy techs are changed by base_patch.ips.
          - enemy_ai_db: Various enemy attack scripts are changed by
                         base_patch.ips.
        '''

        # It's a little wasteful copying the rom data to partially patch it
        # to extract the base values for the above.

        # I do have a pickle with a default config and normal/hard enemy dicts
        # which can be used instead if this is an issue.  The problem with
        # using those is the need to update them with every patch.
        van_ct_rom = CTRom(ct_vanilla, True)
        ct_rom = CTRom(ct_vanilla, True)
        Randomizer.__apply_basic_patches(ct_rom)
        config = cfg.RandoConfig()
        cls.fill_default_config_entries(config)

        spots = bossrando.get_assignable_spots(settings.game_mode,
                                               settings.gameflags)
        config.boss_assign_dict = {
            spot: config.boss_assign_dict[spot]
            for spot in spots
        }

        config.boss_data_dict = rotypes.get_boss_data_dict()

        if settings.game_mode == rset.GameMode.VANILLA_RANDO:
            config.update_from_ct_rom(van_ct_rom)
            vanillarando.fix_config(config)

            # Apply the experimental logic tweaks in the config
            # This is new, it used to be automatic in vanilla mode.
            cls.__apply_logic_tweaks_to_config(settings, config)

        else:
            van_config = cfg.RandoConfig()
            van_config.update_from_ct_rom(van_ct_rom)
            config.update_from_ct_rom(ct_rom)

            # base_patch.ips apparently writes marle into the magus spot with
            # custom ai to heal and cast ice2.  It's cool, but we want the
            # vanilla north cape magus.
            magus_id = ctenums.EnemyID.MAGUS_NORTH_CAPE
            magus_nc_sprite = van_config.enemy_sprite_dict[magus_id]
            magus_nc_ai = van_config.enemy_ai_db.scripts[magus_id]
            magus_nc_stats = van_config.enemy_dict[magus_id]

            config.enemy_ai_db.scripts[magus_id] = magus_nc_ai
            config.enemy_sprite_dict[magus_id] = magus_nc_sprite
            config.enemy_dict[magus_id] = magus_nc_stats

            # Apply the experimental logic tweaks in the config
            cls.__apply_logic_tweaks_to_config(settings, config)

            # Get hard versions of config items if needed.
            # We're done with the rom at this point, so it's OK to patch.
            ct_rom.rom_data.patch_ips_file('./patches/hard.ips')
            if settings.enemy_difficulty == rset.Difficulty.HARD:
                config.enemy_dict = \
                    enemystats.get_stat_dict_from_ctrom(ct_rom)

            if settings.item_difficulty == rset.Difficulty.HARD:
                config.item_db = itemdata.ItemDB.from_rom(
                    ct_rom.rom_data.getvalue()
                )

            # Why is Dalton worth so few TP?
            config.enemy_dict[ctenums.EnemyID.DALTON_PLUS].tp = 50

            # Elder Spawn Name
            elder = config.enemy_dict[ctenums.EnemyID.ELDER_SPAWN_SHELL]
            elder.name = 'Elder Spawn'

            # Give Rusty a few more HP, like avg hp of old boss rando
            enemy_id = ctenums.EnemyID.RUST_TYRANO
            rt_stats = config.enemy_dict[enemy_id]

            rt_stats.hp = int(rt_stats.hp * 1.75)

            # Lower the base magic/lvl so that the party is likely to survive
            # the initial nuke.
            rt_stats.magic = int(rt_stats.magic * 0.6)
            rt_stats.level = int(rt_stats.level * 0.6)

            # Fix Falcon Hit to use Spincut as a prerequisite
            tech_db = config.tech_db
            falcon_hit = tech_db.get_tech(ctenums.TechID.FALCON_HIT)
            falcon_hit['lrn_req'][0] = int(ctenums.TechID.SPINCUT)
            tech_db.set_tech(falcon_hit, ctenums.TechID.FALCON_HIT)

            # Fix volt bite damage error.
            tech = tech_db.get_tech(ctenums.TechID.VOLT_BITE)
            # orig: 0x40 - Ignore hit/evd (set for all combo techs)
            # Add 0x20: Something similar for magic attacks?  Set for all similar techs
            # Add 0x01: Control which effects get damage displayed (not precisely known)
            tech['control'][1] = 0x61
            tech_db.set_tech(tech, ctenums.TechID.VOLT_BITE)

            # Change Cure to ReRaise, Speed to 9 for Marle
            cure = tech_db.get_tech(ctenums.TechID.CURE)
            reraise = tech_db.get_tech(ctenums.TechID.LIFE_2_M)
            reraise['gfx'][0] = 0x87
            reraise['gfx'][6] = 0xFF
            reraise['control'][5] = 0x3E
            reraise['name'] = ctstrings.CTNameString.from_string(
                '*Reraise'
            )
            reraise['desc_ptr'] = None
            new_desc = ctstrings.CTString.from_str(
                'Greendream effect on one ally.{null}'
            )
            reraise['desc'] = new_desc
            reraise['target'] = bytearray(cure['target'])
            tech_db.mps[ctenums.TechID.CURE] = 15
            tech_db.set_tech(reraise, ctenums.TechID.CURE)
            tech_db.menu_usable_ids[ctenums.TechID.CURE] = False

            pcstats = config.pcstats
            pcstats.set_current_stat(ctenums.CharID.MARLE,
                                     ctpcstats.PCStat.SPEED,
                                     9)

            pcstats.pc_stat_dict[ctenums.CharID.FROG]\
                   .tp_threshholds.set_threshold(3, 100)

            # Reduce Robo tackle to 24 power (follow +15% rule)
            tackle_id = int(ctenums.TechID.ROBO_TACKLE)
            power_byte = tackle_id*tech_db.effect_size + 9
            tech_db.effects[power_byte] = 24

            # Now, the flag keeps tackle effects on
            # (do nothing vs base_patch.ips)
            # If the flag is not present, reset the on-hit byte.
            if rset.GameFlags.TACKLE_EFFECTS_ON not in settings.gameflags:
                on_hit_byte = tackle_id*tech_db.effect_size + 8
                tech_db.effects[on_hit_byte] = 0

            # Revert antilife to black hole
            if rset.GameFlags.USE_ANTILIFE not in settings.gameflags:
                TechDB = charrando.TechDB
                vanilla_db = TechDB.get_default_db(ct_vanilla)
                black_hole = vanilla_db.get_tech(ctenums.TechID.ANTI_LIFE)

                anti_life = tech_db.get_tech(ctenums.TechID.ANTI_LIFE)
                anti_life['control'][8] = 0x16  # +Atk for down allies
                anti_life['effects'][0][9] = 0x20  # Megabomb power
                al_eff_id = anti_life['control'][5]

                # A note here that set_tech needs the effects to be set
                # correctly.
                # TODO: get_tech needs to be fixed to supply mp values so that
                #   set_tech can work as it ought.  Really fix the whole
                #   techdb.
                byteops.set_record(tech_db.effects, anti_life['effects'][0],
                                   al_eff_id,
                                   tech_db.effect_size)

                black_hole['control'] = anti_life['control']
                tech_db.set_tech(black_hole, ctenums.TechID.ANTI_LIFE)

                tech_db.pc_target[int(ctenums.TechID.ANTI_LIFE)] = 6

            # Make X-Strike use Spincut+Leapslash
            # Also buff 3d-attack and triple raid
            x_strike = tech_db.get_tech(ctenums.TechID.X_STRIKE)
            x_strike['control'][5] = int(ctenums.TechID.SPINCUT)
            x_strike['control'][6] = int(ctenums.TechID.LEAP_SLASH)

            # Crono's techlevel = 4 (spincut)
            # Frog's techlevel = 5 (leapslash)
            x_strike['lrn_req'] = [4, 5, 0xFF]

            x_strike['mmp'][0] = int(ctenums.TechID.SPINCUT)
            x_strike['mmp'][1] = int(ctenums.TechID.LEAP_SLASH)
            tech_db.set_tech(x_strike, ctenums.TechID.X_STRIKE)

            # 3d-atk
            three_d_atk = tech_db.get_tech(ctenums.TechID.THREE_D_ATTACK)
            three_d_atk['control'][6] = int(ctenums.TechID.SPINCUT)
            three_d_atk['control'][7] = int(ctenums.TechID.LEAP_SLASH)

            three_d_atk['mmp'][0] = int(ctenums.TechID.SPINCUT)
            three_d_atk['mmp'][1] = int(ctenums.TechID.LEAP_SLASH)

            three_d_atk['lrn_req'] = [4, 5, 8]
            tech_db.set_tech(three_d_atk, ctenums.TechID.THREE_D_ATTACK)

            # Triple Raid
            triple_raid = tech_db.get_tech(ctenums.TechID.TRIPLE_RAID)
            triple_raid['control'][5] = int(ctenums.TechID.SPINCUT)
            triple_raid['control'][7] = int(ctenums.TechID.LEAP_SLASH)

            triple_raid['mmp'][0] = int(ctenums.TechID.SPINCUT)
            triple_raid['mmp'][2] = int(ctenums.TechID.LEAP_SLASH)

            triple_raid['lrn_req'] = [4, 4, 5]
            tech_db.set_tech(triple_raid, ctenums.TechID.TRIPLE_RAID)

            # Ayla changes
            combo_tripkick_effect_id = 0x3D
            rock_tech_effect_id = int(ctenums.TechID.ROCK_THROW)

            effects = tech_db.effects
            power_byte = 9
            # Triple Kick combo power set to 0x2B=43 to match single
            # tech power
            trip_pwr = combo_tripkick_effect_id*tech_db.effect_size + \
                power_byte
            effects[trip_pwr] = 0x2B

            # Rock throw getting the 15% boost that tripkick got
            # From 0x1E=30 to 0x23=35
            rock_pwr = rock_tech_effect_id*tech_db.effect_size + power_byte
            effects[rock_pwr] = 0x23

        # The following changes can happen regardless of mode.
        if rset.GameFlags.EPOCH_FAIL in settings.gameflags:
            epochfail.update_config(config)

        # Add grandleon lowering magus's mdef
        # Editing AI is ugly right now, so just use raw binary
        magus_ai = config.enemy_ai_db.scripts[ctenums.EnemyID.MAGUS]
        magus_ai_b = magus_ai.get_as_bytearray()
        masa_hit = bytearray.fromhex(
            '18 3D 04 29 FE'
            '0B 3C 14 00 2E FE'
        )

        masa_hit_loc = magus_ai_b.find(masa_hit)
        masa_hit[1] = 0x42  # Change MM (0x3D) to GL (0x42)
        magus_ai_b[masa_hit_loc:masa_hit_loc] = masa_hit
        new_magus_ai = cfg.enemyai.AIScript(magus_ai_b)

        config.enemy_ai_db.scripts[ctenums.EnemyID.MAGUS] = new_magus_ai

        # Allow combo tech confuse to use on-hit effects
        tech_db = config.tech_db
        combo_confuse_id = 0x3C
        on_hit_byte = combo_confuse_id*tech_db.effect_size + 8
        tech_db.effects[on_hit_byte] = 0x80

        if rset.GameFlags.BOSS_SIGHTSCOPE in settings.gameflags:
            qolhacks.enable_boss_sightscope(config)

        return config

    @classmethod
    def get_randmomized_rom(cls,
                            rom: bytearray,
                            settings: rset.Settings) -> bytes:
        '''
        Generate a random rom from the given (maybe not vanilla) rom.
        Uses the seed in settings.seed.
        '''
        rando = Randomizer(rom,
                           is_vanilla=False,
                           settings=settings,
                           config=None)
        rando.set_random_config()
        rando.generate_rom()
        return rando.get_generated_rom()

    @staticmethod
    def _get_pickle_path(filename: Union[str, Path]) -> Path:
        '''Get path to pickle from "pickles" directory in package.'''
        return Randomizer._pickles_path / filename


class RandomizerWriter:
    '''Utility class for writing output/spoilers for Randomizer.'''
    def __init__(self, rando: Randomizer, base_name: Path):
        self.rando = rando

        flag_string = rando.settings.get_flag_string()
        seed = rando.settings.seed
        self.out_string = f"{base_name}.{flag_string}.{seed}"

    def write_output_rom(self, output_path: Path):
        out_name = f"{self.out_string}.sfc"
        self.out_rom = self.rando.get_generated_rom()
        self.full_output_path = output_path / out_name
        self.full_output_path.write_bytes(self.out_rom)

    def write_spoiler_log(self, output_path: Path):
        spoiler_name = f"{self.out_string}.spoilers.txt"
        self.spoiler_path = output_path / spoiler_name
        self.rando.write_spoiler_log(str(self.spoiler_path))

    def write_json_spoiler_log(self, output_path: Path):
        json_spoiler_name = f"{self.out_string}.spoilers.json"
        self.json_spoiler_path = output_path / json_spoiler_name
        self.rando.write_json_spoiler_log(str(self.json_spoiler_path))


def read_names():
    names_path = Path(__file__).parent / 'names.txt'
    with names_path.open('r') as p:
        names = p.readline().split(',')
    return names


def main():
    parser = arguments.get_parser()
    args = parser.parse_args()

    if not args.input_file.exists():
        raise FileNotFoundError("Invalid input file path.")

    if args.output_path is None:
        args.output_path = args.input_file.parent
    if not args.output_path.is_dir():
        raise FileNotFoundError("Invalid output directory.")

    # Make sure the settings are ok before going further and reading the rom.
    settings = arguments.args_to_settings(args)
    if settings.seed is None or settings.seed == "":
        names = read_names()
        settings.seed = "".join(random.choice(names) for i in range(2))

    rom = args.input_file.read_bytes()
    if not CTRom.validate_ct_rom_bytes(rom):
        print(
            'Warning: File provided is not a vanilla CT ROM.  Proceed '
            'anyway?  Randomization is likely to fail. (Y/N)'
        )
        proceed = (input().upper() == 'Y')
        if not proceed:
            sys.exit()

    rando = Randomizer(rom, is_vanilla=False, settings=settings, config=None)
    rando.set_random_config()

    base_name = args.input_file.parts[-1]
    writer = RandomizerWriter(rando, base_name=base_name)
    writer.write_output_rom(args.output_path)
    print(f"output ROM: {writer.full_output_path}")

    if args.spoilers:
        writer.write_spoiler_log(args.output_path)
        print(f"spoilers: {writer.spoiler_path}")

    if args.json_spoilers:
        writer.write_json_spoiler_log(args.output_path)
        print(f"json spoilers: {writer.json_spoiler_path}")


if __name__ == "__main__":
    main()
