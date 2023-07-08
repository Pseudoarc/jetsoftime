from __future__ import annotations
from enum import Flag, IntEnum, auto
from dataclasses import dataclass, field
from typing import Callable, Union, Optional, Tuple, Type, TypeVar

import bossrandotypes as rotypes
import ctoptions

SIE = TypeVar('SIE', bound='StrIntEnum')


class StrIntEnum(IntEnum):

    def __str__(self):
        x = self.__repr__().split('.')[1].split(':')[0].lower().capitalize()
        x = x.replace('_', ' ')
        return x

    @classmethod
    def str_dict(cls: Type[SIE]) -> dict[SIE, str]:
        enum_list: list[SIE] = list(cls)
        return dict((x, str(x)) for x in enum_list)

    @classmethod
    def inv_str_dict(
            cls: Type[SIE],
            formatter: Callable[[str], str] = lambda x: x) -> dict[str, SIE]:
        enum_list: list[SIE] = list(cls)
        return dict((formatter(str(x)), x) for x in enum_list)


class GameMode(StrIntEnum):
    STANDARD = auto()
    LOST_WORLDS = auto()
    ICE_AGE = auto()
    LEGACY_OF_CYRUS = auto()
    VANILLA_RANDO = auto()


class Difficulty(StrIntEnum):
    EASY = 0
    NORMAL = 1
    HARD = 2


class TechOrder(StrIntEnum):
    NORMAL = 0
    FULL_RANDOM = 1
    BALANCED_RANDOM = 2


class ShopPrices(StrIntEnum):
    NORMAL = 0
    MOSTLY_RANDOM = 1
    FULLY_RANDOM = 2
    FREE = 3


class GameFlags(Flag):
    FIX_GLITCH = auto()
    BOSS_SCALE = auto()
    ZEAL_END = auto()
    FAST_PENDANT = auto()
    LOCKED_CHARS = auto()
    UNLOCKED_MAGIC = auto()
    CHRONOSANITY = auto()
    ROCKSANITY = auto()
    TAB_TREASURES = auto()  # Maybe needs to be part of treasure page?
    BOSS_RANDO = auto()
    CHAR_RANDO = auto()
    DUPLICATE_CHARS = auto()
    DUPLICATE_TECHS = auto()
    VISIBLE_HEALTH = auto()
    FAST_TABS = auto()
    BUCKET_LIST = auto()
    MYSTERY = auto()
    BOSS_SIGHTSCOPE = auto()
    USE_ANTILIFE = auto()
    TACKLE_EFFECTS_ON = auto()
    HEALING_ITEM_RANDO = auto()
    FREE_MENU_GLITCH = auto()
    GEAR_RANDO = auto()
    STARTERS_SUFFICIENT = auto()
    EPOCH_FAIL = auto()
    BOSS_SPOT_HP = auto()
    # Logic Tweak flags from VanillaRando mode
    UNLOCKED_SKYGATES = auto()
    ADD_SUNKEEP_SPOT = auto()
    ADD_BEKKLER_SPOT = auto()
    ADD_CYRUS_SPOT = auto()
    RESTORE_TOOLS = auto()
    ADD_OZZIE_SPOT = auto()
    RESTORE_JOHNNY_RACE = auto()
    ADD_RACELOG_SPOT = auto()
    SPLIT_ARRIS_DOME = auto()
    VANILLA_ROBO_RIBBON = auto()
    VANILLA_DESERT = auto()
    REMOVE_BLACK_OMEN_SPOT = auto()
    # No longer Logic Tweak Flags
    TECH_DAMAGE_RANDO = auto()
    ELEMENT_RANDO = auto()

    def __add__(self, other: GameFlags):
        return self | other

    def __sub__(self, other: GameFlags):
        return self & ~other


# Dictionary for what flags force what other flags off.
# Note that this is NOT symmetric.  For example Lost Worlds will force
# Boss Scaling off, but not vice versa because it's annoying to have to
# click off every minor flag to select a major flag like a game mode.
_GF = GameFlags
_GM = GameMode
_forced_off_dict: dict[Union[_GF, _GM], _GF] = {
    _GF.FIX_GLITCH: _GF(0),
    _GF.BOSS_SCALE: _GF(0),
    _GF.ZEAL_END: _GF(0),
    _GF.FAST_PENDANT: _GF(0),
    _GF.LOCKED_CHARS: _GF(0),
    _GF.UNLOCKED_MAGIC: _GF(0),
    _GF.CHRONOSANITY: _GF.BOSS_SCALE,
    _GF.ROCKSANITY: _GF(0),
    _GF.TAB_TREASURES: _GF(0),
    _GF.BOSS_RANDO: _GF(0),
    _GF.CHAR_RANDO: _GF(0),
    _GF.DUPLICATE_CHARS: _GF(0),
    _GF.DUPLICATE_TECHS: _GF(0),
    _GF.VISIBLE_HEALTH: _GF(0),
    _GF.FAST_TABS: _GF(0),
    _GF.BUCKET_LIST: _GF(0),
    _GF.MYSTERY: _GF(0),
    _GF.GEAR_RANDO: _GF(0),
    _GF.HEALING_ITEM_RANDO: _GF(0),
    _GF.EPOCH_FAIL: _GF(0),
    _GM.STANDARD: _GF(0),
    _GM.LOST_WORLDS: (
        _GF.BOSS_SCALE | _GF.BUCKET_LIST | _GF.EPOCH_FAIL |
        _GF.ADD_BEKKLER_SPOT | _GF.ADD_CYRUS_SPOT | _GF.ADD_OZZIE_SPOT |
        _GF.ADD_RACELOG_SPOT | _GF.ADD_SUNKEEP_SPOT | _GF.RESTORE_JOHNNY_RACE |
        _GF.SPLIT_ARRIS_DOME | _GF.RESTORE_TOOLS | _GF.UNLOCKED_SKYGATES |
        _GF.VANILLA_DESERT | _GF.VANILLA_ROBO_RIBBON | _GF.ROCKSANITY |
        _GF.REMOVE_BLACK_OMEN_SPOT
    ),
    _GM.ICE_AGE: (
        _GF.ZEAL_END |
        _GF.BOSS_SCALE | _GF.BUCKET_LIST |
        _GF.ADD_BEKKLER_SPOT
    ),
    _GM.LEGACY_OF_CYRUS: (
        _GF.ZEAL_END |
        _GF.BUCKET_LIST | _GF.BOSS_SCALE |
        _GF.ADD_OZZIE_SPOT | _GF.ADD_SUNKEEP_SPOT | _GF.RESTORE_TOOLS |
        _GF.RESTORE_JOHNNY_RACE | _GF.SPLIT_ARRIS_DOME | _GF.ADD_RACELOG_SPOT |
        _GF.ADD_BEKKLER_SPOT
    ),
    _GM.VANILLA_RANDO: (
        _GF.BOSS_SCALE
    )
}


# Similar dictionary for forcing flags on
_forced_on_dict = {
    _GF.FIX_GLITCH: _GF(0),
    _GF.BOSS_SCALE: _GF(0),
    _GF.ZEAL_END: _GF(0),
    _GF.FAST_PENDANT: _GF(0),
    _GF.LOCKED_CHARS: _GF(0),
    _GF.UNLOCKED_MAGIC: _GF(0),
    _GF.CHRONOSANITY: _GF(0),
    _GF.ROCKSANITY: _GF.UNLOCKED_SKYGATES,
    _GF.TAB_TREASURES: _GF(0),
    _GF.BOSS_RANDO: _GF(0),
    _GF.CHAR_RANDO: _GF(0),
    _GF.DUPLICATE_CHARS: _GF.CHAR_RANDO,
    _GF.DUPLICATE_TECHS: (_GF.CHAR_RANDO | _GF.DUPLICATE_CHARS),
    _GF.VISIBLE_HEALTH: _GF(0),
    _GF.FAST_TABS: _GF(0),
    _GF.BUCKET_LIST: _GF(0),
    _GF.MYSTERY: _GF(0),
    _GF.GEAR_RANDO: _GF(0),
    _GF.HEALING_ITEM_RANDO: _GF(0),
    _GF.EPOCH_FAIL: _GF(0),
    _GM.STANDARD: _GF(0),
    _GM.LOST_WORLDS: _GF.UNLOCKED_MAGIC,
    _GM.ICE_AGE: _GF.UNLOCKED_MAGIC,
    _GM.LEGACY_OF_CYRUS: _GF.UNLOCKED_MAGIC,
    _GM.VANILLA_RANDO: _GF(0)
}


def get_forced_off(flag: GameFlags) -> GameFlags:
    return _forced_off_dict.get(flag, GameFlags(0))


def get_forced_on(flag: GameFlags) -> GameFlags:
    return _forced_on_dict.get(flag, GameFlags(0))


class CosmeticFlags(Flag):
    ZENAN_ALT_MUSIC = auto()
    DEATH_PEAK_ALT_MUSIC = auto()
    QUIET_MODE = auto()
    REDUCE_FLASH = auto()
    AUTORUN = auto()


class TabRandoScheme(StrIntEnum):
    UNIFORM = 0
    BINOMIAL = 1


@dataclass
class TabSettings:
    scheme: TabRandoScheme = TabRandoScheme.UNIFORM
    binom_success: float = 0.5  # Only used by binom if set
    power_min: int = 2
    power_max: int = 4
    magic_min: int = 1
    magic_max: int = 3
    speed_min: int = 1
    speed_max: int = 1


class ROFlags(Flag):
    '''
    Flags which can be passed to boss rando.
    '''
    PRESERVE_PARTS = auto()
    BOSS_SPOT_HP = auto()


@dataclass
class ROSettings:
    '''
    Full Boss Rando settings allow specification of which bosses/spots are
    in the pool as well as some additional flags.
    '''
    spots: list[rotypes.BossSpotID] = field(default_factory=list)
    bosses: list[rotypes.BossID] = field(default_factory=list)
    flags: ROFlags = ROFlags(0)

    @classmethod
    def from_game_mode(
            cls,
            mode: GameMode,
            boss_list: Optional[list[rotypes.BossID]] = None,
            ro_flags: ROFlags = ROFlags(0)
            ) -> ROSettings:
        '''
        Construct an ROSettings object with correct initial locations given
        the game mode.
        '''
        spots = []
        BS = rotypes.BossSpotID
        if mode == GameMode.LOST_WORLDS:
            spots = [
                BS.ARRIS_DOME, BS.GENO_DOME, BS.SUN_PALACE, BS.MT_WOE,
                BS.REPTITE_LAIR, BS.DEATH_PEAK, BS.ZEAL_PALACE,
                BS.OCEAN_PALACE_TWIN_GOLEM, BS.BLACK_OMEN_GIGA_MUTANT,
                BS.BLACK_OMEN_TERRA_MUTANT, BS.BLACK_OMEN_ELDER_SPAWN
            ]
        elif mode == GameMode.LEGACY_OF_CYRUS:
            removed_spots = [
                BS.ARRIS_DOME, BS.GENO_DOME, BS.SUN_PALACE,
                BS.DEATH_PEAK, BS.BLACK_OMEN_ELDER_SPAWN,
                BS.BLACK_OMEN_GIGA_MUTANT, BS.BLACK_OMEN_ELDER_SPAWN,
                BS.PRISON_CATWALKS, BS.FACTORY_RUINS
            ]
            spots = [
                spot for spot in list(BS)
                if spot not in removed_spots
            ]
        else:  # Std, IA, Vanilla
            spots = list(BS)

        if boss_list is None:
            boss_list = rotypes.get_assignable_bosses()

        return ROSettings(spots, boss_list, ro_flags)


@dataclass
class BucketSettings:
    '''
    Class for settings passed to bucket flag.
    '''
    disable_other_go_modes: bool = False
    objectives_win: bool = False

    # Configuration for number of objectives avail/needed
    num_objectives: int = 5
    num_objectives_needed: int = 4
    hints: list[str] = field(default_factory=list)


class MysterySettings:
    def __init__(self):
        self.game_mode_freqs: dict[GameMode, int] = {
            GameMode.STANDARD: 75,
            GameMode.LOST_WORLDS: 25,
            GameMode.LEGACY_OF_CYRUS: 0,
            GameMode.ICE_AGE: 0,
            GameMode.VANILLA_RANDO: 0
        }
        self.item_difficulty_freqs: dict[Difficulty, int] = {
            Difficulty.EASY: 15,
            Difficulty.NORMAL: 70,
            Difficulty.HARD: 15
        }
        self.enemy_difficulty_freqs: dict[Difficulty, int] = {
            Difficulty.NORMAL: 75,
            Difficulty.HARD: 25
        }
        self.tech_order_freqs: dict[TechOrder, int] = {
            TechOrder.NORMAL: 10,
            TechOrder.BALANCED_RANDOM: 10,
            TechOrder.FULL_RANDOM: 80
        }
        self.shop_price_freqs: dict[ShopPrices, int] = {
            ShopPrices.NORMAL: 70,
            ShopPrices.MOSTLY_RANDOM: 10,
            ShopPrices.FULLY_RANDOM: 10,
            ShopPrices.FREE: 10
        }
        self.flag_prob_dict: dict[GameFlags, float] = {
            GameFlags.TAB_TREASURES: 0.10,
            GameFlags.UNLOCKED_MAGIC: 0.5,
            GameFlags.BUCKET_LIST: 0.15,
            GameFlags.CHRONOSANITY: 0.50,
            GameFlags.BOSS_RANDO: 0.50,
            GameFlags.BOSS_SCALE: 0.10,
            GameFlags.LOCKED_CHARS: 0.25,
            GameFlags.CHAR_RANDO: 0.5,
            GameFlags.DUPLICATE_CHARS: 0.25,
            GameFlags.EPOCH_FAIL: 0.5,
            GameFlags.GEAR_RANDO: 0.25,
            GameFlags.HEALING_ITEM_RANDO: 0.25
        }

    def __str__(self):
        ret_str = ''
        ret_str += str(self.game_mode_freqs) + '\n'
        ret_str += str(self.item_difficulty_freqs) + '\n'
        ret_str += str(self.enemy_difficulty_freqs) + '\n'
        ret_str += str(self.tech_order_freqs) + '\n'
        ret_str += str(self.shop_price_freqs) + '\n'
        ret_str += str(self.flag_prob_dict) + '\n'

        return ret_str


class Settings:

    def __init__(self):

        self.game_mode = GameMode.STANDARD
        self.item_difficulty = Difficulty.NORMAL
        self.enemy_difficulty = Difficulty.NORMAL

        self.techorder = TechOrder.FULL_RANDOM
        self.shopprices = ShopPrices.NORMAL

        self.mystery_settings = MysterySettings()

        self.gameflags = GameFlags(0)
        self.initial_flags = GameFlags(0)
        self.char_choices = [list(range(7)) for j in range(7)]

        self.ro_settings = ROSettings.from_game_mode(self.game_mode)
        self.bucket_settings = BucketSettings()

        self.tab_settings = TabSettings()
        self.cosmetic_flags = CosmeticFlags(0)

        self.ctoptions = ctoptions.CTOpts()

        self.seed = ''

        self.char_names: list[str] = [
            'Crono', 'Marle', 'Lucca', 'Robo', 'Frog', 'Ayla', 'Magus',
            'Epoch'
        ]

    def _jot_json(self):
        return {
            "seed": self.seed,
            "mode": str(self.game_mode),
            "enemy_difficulty": str(self.enemy_difficulty),
            "item_difficulty": str(self.item_difficulty),
            "tech_order": str(self.techorder),
            "shops": str(self.shopprices),
            "flags": self.gameflags,
            "initial_flags": self.initial_flags,
            "cosmetic_flags": self.cosmetic_flags
        }

    @staticmethod
    def get_race_presets():
        ret = Settings()

        ret.item_difficulty = Difficulty.NORMAL
        ret.enemy_difficulty = Difficulty.NORMAL

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.FULL_RANDOM

        ret.gameflags = (GameFlags.FIX_GLITCH |
                         GameFlags.FAST_PENDANT |
                         GameFlags.ZEAL_END)

        ret.seed = ''

        return ret

    @staticmethod
    def get_new_player_presets():
        ret = Settings()

        ret.item_difficulty = Difficulty.EASY
        ret.enemy_difficulty = Difficulty.NORMAL

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.FULL_RANDOM

        ret.gameflags = (GameFlags.FIX_GLITCH |
                         GameFlags.FAST_PENDANT |
                         GameFlags.ZEAL_END |
                         GameFlags.UNLOCKED_MAGIC |
                         GameFlags.VISIBLE_HEALTH |
                         GameFlags.FAST_TABS)

        ret.seed = ''

        return ret

    @staticmethod
    def get_lost_worlds_presets():
        ret = Settings()

        ret.game_mode = GameMode.LOST_WORLDS
        ret.item_difficulty = Difficulty.NORMAL
        ret.enemy_difficulty = Difficulty.NORMAL

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.FULL_RANDOM

        ret.gameflags = (GameFlags.FIX_GLITCH | GameFlags.ZEAL_END)

        ret.seed = ''

        return ret

    @staticmethod
    def get_hard_presets():
        ret = Settings()

        ret.item_difficulty = Difficulty.HARD
        ret.enemy_difficulty = Difficulty.HARD

        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.BALANCED_RANDOM

        ret.gameflags = (GameFlags.FIX_GLITCH |
                         GameFlags.BOSS_SCALE |
                         GameFlags.LOCKED_CHARS)

        ret.seed = ''
        return ret

    @staticmethod
    def get_tourney_early_preset() -> Settings:
        '''
        Settings for tourney up to Ro8.
        '''
        ret = Settings()

        ret.item_difficulty = Difficulty.NORMAL
        ret.enemy_difficulty = Difficulty.NORMAL
        ret.shopprices = ShopPrices.NORMAL
        ret.techorder = TechOrder.FULL_RANDOM

        GF = GameFlags

        ret.gameflags = (
            GF.FIX_GLITCH | GF.ZEAL_END | GF.FAST_PENDANT | GF.BOSS_RANDO |
            GF.BOSS_SPOT_HP | GF.FAST_TABS | GF.FREE_MENU_GLITCH |
            GF.GEAR_RANDO | GF.HEALING_ITEM_RANDO
        )

        return ret

    @staticmethod
    def get_tourney_top8_preset() -> Settings:
        ret = Settings.get_tourney_early_preset()

        ret.item_difficulty = Difficulty.HARD
        ret.gameflags &= ~GameFlags.FREE_MENU_GLITCH

        return ret

    def get_flag_diffs(self) -> Tuple[GameFlags, GameFlags]:
        '''Get diff from initial flags (+, -).'''
        return (self.gameflags - self.initial_flags, self.initial_flags - self.gameflags)

    def fix_flag_conflicts(self):
        '''
        The gui should prevent bad flag choices.  In the event that it somehow
        does not, this method will silently make changes to the flags to fix
        things.

        This intends to prevent logicfactory from raising an ImpossibleGameConfig
        from resolveExtraKeyItems, if possible.
        '''
        mode = self.game_mode
        forced_off = _forced_off_dict[mode]
        self.gameflags &= ~forced_off

        # Duplicate Character implies Character Rando
        if GameFlags.DUPLICATE_CHARS in self.gameflags:
            self.gameflags |= GameFlags.CHAR_RANDO

        # Rocksanity implies Unlocked Skyways
        if GameFlags.ROCKSANITY in self.gameflags:
            self.gameflags |= GameFlags.UNLOCKED_SKYGATES

        # Chronosanity is not compatible with boss scaling.
        if GameFlags.CHRONOSANITY in self.gameflags:
            self.gameflags &= ~GameFlags.BOSS_SCALE

            # there are plenty of spots in chronosanity, so don't need
            # to adjust based on KI/spot flags
            return True

        add_ki_flags = [
            GameFlags.RESTORE_JOHNNY_RACE, GameFlags.RESTORE_TOOLS,
            GameFlags.EPOCH_FAIL
        ]
        added_kis = sum(flag in self.gameflags for flag in add_ki_flags)

        add_spot_flags = [
            GameFlags.ADD_BEKKLER_SPOT, GameFlags.ADD_CYRUS_SPOT,
            GameFlags.ADD_OZZIE_SPOT, GameFlags.ADD_RACELOG_SPOT,
            GameFlags.VANILLA_ROBO_RIBBON
        ]
        added_spots = sum(flag in self.gameflags for flag in add_spot_flags)

        # Rocksanity adds 5 rock KIs, 4-5 spots depending on mode/flags
        if GameFlags.ROCKSANITY in self.gameflags:
            added_kis += 5
            has_black_omen_spot = (
                mode not in [GameMode.LEGACY_OF_CYRUS, GameMode.ICE_AGE] and
                GameFlags.REMOVE_BLACK_OMEN_SPOT not in self.gameflags
            )
            added_spots += 5 if has_black_omen_spot else 4

        # some modes have extra treasure spots (fewer KIs) which can be filled
        if mode == GameMode.ICE_AGE:
            added_spots += 2
        elif mode == GameMode.LEGACY_OF_CYRUS:
            added_spots += 1

        # We need to make changes that the user will not get tripped up by.
        # For example, we don't want to add a spot that they wouldn't know to
        # check.
        # logicfactory handles one extra KI by removing Jerky if necessary.
        while added_kis > added_spots + 1:

            if GameFlags.VANILLA_ROBO_RIBBON not in self.gameflags:
                # Making Robo's Ribbon vanilla is least intrusive.  The player
                # gets to play as they intend but may become puzzled by the
                # stat boost after atropos.
                self.gameflags |= GameFlags.VANILLA_ROBO_RIBBON
                added_spots += 1
            elif GameFlags.EPOCH_FAIL in self.gameflags:
                # Just remove epoch fail and the player will immediately
                # realize something is wrong.
                self.gameflags &= ~GameFlags.EPOCH_FAIL
                added_kis -= 1
            else:
                raise ValueError('Cannot fix flag conflicts')



    def get_flag_string(self):
        # Flag string is based only on main game flags and game mode

        diff_str_dict = {
            Difficulty.EASY: 'e',
            Difficulty.NORMAL: 'n',
            Difficulty.HARD: 'h',
        }

        tech_str_dict = {
            TechOrder.FULL_RANDOM: 'te',
            TechOrder.BALANCED_RANDOM: 'tex',
            TechOrder.NORMAL: ''
        }

        game_mode_dict = {
            GameMode.STANDARD: 'st',
            GameMode.LOST_WORLDS: 'lw',
            GameMode.ICE_AGE: 'ia',
            GameMode.LEGACY_OF_CYRUS: 'loc',
            GameMode.VANILLA_RANDO: 'van'
        }

        flag_str_dict = {
            GameFlags.FIX_GLITCH: 'g',
            GameFlags.BOSS_SCALE: 'b',
            GameFlags.BOSS_RANDO: 'ro',
            GameFlags.ZEAL_END: 'z',
            GameFlags.FAST_PENDANT: 'p',
            GameFlags.LOCKED_CHARS: 'c',
            GameFlags.UNLOCKED_MAGIC: 'm',
            GameFlags.CHRONOSANITY: 'cr',
            GameFlags.TAB_TREASURES: 'tb',
            GameFlags.CHAR_RANDO: 'rc',
            GameFlags.DUPLICATE_CHARS: 'dc',
            GameFlags.HEALING_ITEM_RANDO: 'h',  # h for Healing
            GameFlags.GEAR_RANDO: 'q',  # q for eQuipment (g taken)
            GameFlags.EPOCH_FAIL: 'ef',  # ef for Epoch Fail
            GameFlags.BUCKET_LIST: 'k'  # k for bucKet
        }

        shop_str_dict = {
            ShopPrices.FREE: 'spf',
            ShopPrices.MOSTLY_RANDOM: 'spm',
            ShopPrices.FULLY_RANDOM: 'spr',
            ShopPrices.NORMAL: ''
        }

        if GameFlags.MYSTERY in self.gameflags:
            flag_string = 'mystery'
        else:
            # Now we have difficulty for enemies and items separated, but to
            # match the old flag string, just use enemy difficulty.
            # This won't match for easy, since there's no easy enemy
            # difficulty.
            flag_string = ''
            flag_string += (game_mode_dict[self.game_mode] + '.')
            flag_string += diff_str_dict[self.enemy_difficulty]

            # Add the item difficulty if it differs
            # (old 'e' will end up as 'ne')
            if self.item_difficulty != self.enemy_difficulty:
                flag_string += diff_str_dict[self.item_difficulty]

            # Add a . between mode and difficulty to free up symbols

            flag_symbols = ''
            for flag in flag_str_dict:
                if flag in self.gameflags:
                    flag_symbols += flag_str_dict[flag]

            flag_symbols += tech_str_dict[self.techorder]
            flag_symbols += shop_str_dict[self.shopprices]

            if flag_symbols:
                flag_string += "." + flag_symbols

        return flag_string
