from __future__ import annotations
import random
from collections import UserList
from enum import Flag, IntEnum, auto
from dataclasses import dataclass, field, fields
from typing import Any, Callable, Dict, Iterable, List, Union, Mapping, Optional, Sequence, Tuple, Type, TypeVar

import bossrandotypes as rotypes
import ctoptions

JSONPrimitive = Optional[Union[int, float, bool, str]]
JSONType = Union[JSONPrimitive, Mapping[str, "JSONType"], Sequence["JSONType"]]
SIE = TypeVar('SIE', bound='StrIntEnum')


class StrIntEnum(IntEnum):

    def __str__(self):
        x = self.__repr__().split('.')[1].split(':')[0].lower().capitalize()
        x = x.replace('_', ' ')
        return x

    @classmethod
    def default(cls):
        raise NotImplementedError(f"No .default implemented for {cls}")

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

    @classmethod
    def default(_):
        return GameMode.STANDARD


class Difficulty(StrIntEnum):
    EASY = 0
    NORMAL = 1
    HARD = 2

    @classmethod
    def default(_):
        return Difficulty.NORMAL


class TechOrder(StrIntEnum):
    NORMAL = 0
    FULL_RANDOM = 1
    BALANCED_RANDOM = 2

    @classmethod
    def default(_):
        return TechOrder.FULL_RANDOM


class ShopPrices(StrIntEnum):
    NORMAL = 0
    MOSTLY_RANDOM = 1
    FULLY_RANDOM = 2
    FREE = 3

    @classmethod
    def default(_):
        return ShopPrices.NORMAL


class SerializableFlag(Flag):
    def __add__(self, other: Flag):
        return self | other

    def __sub__(self, other: Flag):
        return self & ~other

    def to_jot_json(self) -> List[str]:
        return [str(flag) for flag in type(self) if flag in self]


class GameFlags(SerializableFlag):
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


# Dictionary for what flags force what other flags off.
# Note that this is NOT symmetric.  For example Lost Worlds will force
# Boss Scaling off, but not vice versa because it's annoying to have to
# click off every minor flag to select a major flag like a game mode.
class ForcedFlags:
    _GF = GameFlags
    _GM = GameMode

    forced_off: Dict[Union[GameFlags, GameMode], GameFlags] = {
        _GF.CHRONOSANITY: _GF.BOSS_SCALE,
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
        _GM.VANILLA_RANDO: _GF.BOSS_SCALE,
    }

    # Similar dictionary for forcing flags on
    forced_on: Dict[Union[GameFlags, GameMode], GameFlags] = {
        _GF.ROCKSANITY: _GF.UNLOCKED_SKYGATES,
        _GF.DUPLICATE_CHARS: _GF.CHAR_RANDO,
        _GF.DUPLICATE_TECHS: (_GF.CHAR_RANDO | _GF.DUPLICATE_CHARS),
        _GM.LOST_WORLDS: _GF.UNLOCKED_MAGIC,
        _GM.ICE_AGE: _GF.UNLOCKED_MAGIC,
        _GM.LEGACY_OF_CYRUS: _GF.UNLOCKED_MAGIC,
    }


    @classmethod
    def get_forced_off(cls, flag: Union[GameFlags, GameMode]) -> GameFlags:
        return cls.forced_off.get(flag, GameFlags(0))

    @classmethod
    def get_forced_on(cls, flag: Union[GameFlags, GameMode]) -> GameFlags:
        return cls.forced_on.get(flag, GameFlags(0))

    @classmethod
    def to_jot_json(cls) -> Dict[str, Any]:
        return {
            'forced_off': {str(k): v for k, v in cls.forced_off.items()},
            'forced_on': {str(k): v for k, v in cls.forced_on.items()},
        }


class CosmeticFlags(SerializableFlag):
    ZENAN_ALT_MUSIC = auto()
    DEATH_PEAK_ALT_MUSIC = auto()
    QUIET_MODE = auto()
    REDUCE_FLASH = auto()
    AUTORUN = auto()


class TabRandoScheme(StrIntEnum):
    UNIFORM = 0
    BINOMIAL = 1

    @classmethod
    def default(_):
        return TabRandoScheme.UNIFORM


@dataclass
class TabSettings:
    scheme: TabRandoScheme = TabRandoScheme.default()
    binom_success: float = 0.5  # Only used by binom if set
    power_min: int = 2
    power_max: int = 4
    magic_min: int = 1
    magic_max: int = 3
    speed_min: int = 1
    speed_max: int = 1

    def to_jot_json(self) -> Dict[str, JSONPrimitive]:
        data = {field.name: getattr(self, field.name) for field in fields(self)}
        data['scheme'] = str(self.scheme)
        return data


class ROFlags(SerializableFlag):
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
    spots: List[rotypes.BossSpotID] = field(default_factory=list)
    bosses: List[rotypes.BossID] = field(default_factory=list)
    flags: ROFlags = ROFlags(0)

    @staticmethod
    def from_game_mode(
        mode: GameMode, bosses: Optional[List[rotypes.BossID]] = None, flags: ROFlags = ROFlags(0)
    ) -> ROSettings:
        '''Construct an ROSettings object with correct initial locations given the game mode.'''
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

        if not bosses:
            bosses = rotypes.get_assignable_bosses()
        # if bosses specified, and not enough bosses for spots, assure any specified bosses are included,
        # but randomly take enough other assignable bosses to fill all spots
        elif (padding_needed := len(spots) - len(bosses)) > 0:
            assignable = [boss for boss in rotypes.get_assignable_bosses() if boss not in bosses]
            bosses.extend(random.sample(assignable, k=padding_needed))

        return ROSettings(spots, bosses, flags)

    def to_jot_json(self) -> Dict[str, Any]:
        data = {}
        for item in fields(self):
            attr = getattr(self, item.name)
            data[item.name] = [str(x) for x in attr] if isinstance(attr, List) else attr
        return data


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

    def to_jot_json(self) -> Dict[str, JSONType]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


class CharChoices(UserList):
    '''Type-checked list of lists for character choices allowing get/set via string or index.'''

    def __init__(self, choices: Optional[List[Union[str, List[int]]]] = None):
        self.data = [list(range(7)) for _ in range(7)]

        if choices:
            for pc_id, choice in enumerate(choices):
                self[pc_id] = choice

    def __getitem__(self, key):
        '''Lookup items via characer name string or index.'''
        return self.data[CharNames.lookup(key)]

    def __setitem__(self, key, choices):
        '''Set items via character name string or index.

        When choices is a string, parse to determine character choice ints.
        Otherwise, item must be a list of ints, or raise TypeError.
        '''
        index = CharNames.lookup(key)
        if isinstance(choices, str):
            self.data[index] = self._parse_choices(choices)
        elif isinstance(choices, List) and all(isinstance(x, int) for x in choices):
            self.data[index] = choices
        else:
            raise TypeError('Character choices must be either string or list of ints.')

    @staticmethod
    def _parse_choices(choices: str) -> List[int]:
        '''Determine list of character choice ints based on specified string.'''
        selections = choices.lower().split()

        # select all character choices
        if selections[0] == 'all':
            return list(range(7))

        # inverted selection: get all character choices except specified
        if selections[0] == 'not':
            indices = [CharNames.lookup(choice) for choice in selections[1:]]
            return [index for index in range(7) if index not in indices]

        # regular selection: get all character choices specified
        indices = [CharNames.lookup(choice) for choice in selections]
        return [index for index in range(7) if index in indices]

    def to_jot_json(self) -> List[List[int]]:
        def _choices(choices):
            if isinstance(choices, str):
                return choices
            else:
                return [choice for choice in choices]
        return [_choices(character) for character in self.data]


class CharNames(UserList):
    '''Type-checked list of character names allowing get/set via string or index.'''

    def __init__(self, names: Optional[Iterable[str]] = None):
        names = [name for name in names] if names else []
        if not names:
            names = self.default()
        if len(names) != 8:
            raise IndexError('Must specify 8 names if using assignment.')
        if not all(isinstance(name, str) for name in names):
            raise TypeError('All character names must be strings.')
        self.data = names

    def __getitem__(self, key):
        '''Lookup items via characer name string or index.'''
        return self.data[self.lookup(key)]

    def __setitem__(self, key, name):
        '''Set items via character name string or index.'''
        if not isinstance(name, str):
            raise TypeError('Character names must be strings.')
        self.data[self.lookup(key)] = name

    @staticmethod
    def default() -> List[str]:
        '''Default character names.'''
        return ['Crono', 'Marle', 'Lucca', 'Robo', 'Frog', 'Ayla', 'Magus', 'Epoch']

    @staticmethod
    def lookup(key) -> int:
        if isinstance(key, str):
            return CharNames.default().index(key.lower().capitalize())
        return key

    def to_jot_json(self) -> List[str]:
        return [name for name in self.data]


@dataclass
class CharSettings:
    '''Contains settings related to characters.'''
    names: CharNames
    choices: CharChoices

    def __init__(self):
        self.names = CharNames()
        self.choices = CharChoices()

    def to_jot_json(self) -> Dict[str, JSONType]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass
class MysterySettings:
    '''Settings related to generating mystery seeds.'''

    game_mode_freqs: Dict[GameMode, int] = field(default_factory=dict)
    item_difficulty_freqs: Dict[Difficulty, int] = field(default_factory=dict)
    enemy_difficulty_freqs: Dict[Difficulty, int] = field(default_factory=dict)
    tech_order_freqs: Dict[TechOrder, int] = field(default_factory=dict)
    shop_price_freqs: Dict[ShopPrices, int] = field(default_factory=dict)
    flag_prob_dict: Dict[GameFlags, float] = field(default_factory=dict)

    def __init__(self):
        self.game_mode_freqs = {
            GameMode.STANDARD: 75,
            GameMode.LOST_WORLDS: 25,
            GameMode.LEGACY_OF_CYRUS: 0,
            GameMode.ICE_AGE: 0,
            GameMode.VANILLA_RANDO: 0
        }
        self.item_difficulty_freqs = {
            Difficulty.EASY: 15,
            Difficulty.NORMAL: 70,
            Difficulty.HARD: 15
        }
        self.enemy_difficulty_freqs = {
            Difficulty.NORMAL: 75,
            Difficulty.HARD: 25
        }
        self.tech_order_freqs = {
            TechOrder.NORMAL: 10,
            TechOrder.BALANCED_RANDOM: 10,
            TechOrder.FULL_RANDOM: 80
        }
        self.shop_price_freqs = {
            ShopPrices.NORMAL: 70,
            ShopPrices.MOSTLY_RANDOM: 10,
            ShopPrices.FULLY_RANDOM: 10,
            ShopPrices.FREE: 10
        }
        self.flag_prob_dict = {
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

    def to_jot_json(self) -> Dict[str, JSONType]:
        return {
            field.name: {str(k): freq for k, freq in self[field.name].items()}
            for field in fields(self)
        }

    def update(self, **items) -> MysterySettings:
        for attr, updates in items.items():
            self[attr].update(updates)
        return self

    def __getitem__(self, key):
        return getattr(self, key)

    def __str__(self) -> str:
        return '\n'.join(str(self[field.name]) for field in fields(self)) + '\n'


@dataclass
class Settings:
    '''Container for all settings which do not require reading ROM data.'''

    # NOTE: all fields in dataclasses are used to determine object equivalence
    # that is why initial_flags is intentionally missing from fields list, but initialized in __init__
    game_mode: GameMode
    item_difficulty: Difficulty
    enemy_difficulty: Difficulty
    techorder: TechOrder
    shopprices: ShopPrices
    mystery_settings: MysterySettings
    gameflags: GameFlags
    ro_settings: ROSettings
    bucket_settings: BucketSettings
    char_settings: CharSettings
    tab_settings: TabSettings
    cosmetic_flags: CosmeticFlags
    ctoptions: ctoptions.CTOpts
    seed: str

    def __init__(self):

        self.game_mode = GameMode.default()
        self.item_difficulty = Difficulty.default()
        self.enemy_difficulty = Difficulty.default()

        self.techorder = TechOrder.default()
        self.shopprices = ShopPrices.default()

        self.mystery_settings = MysterySettings()

        self.gameflags = GameFlags(0)
        self.initial_flags = GameFlags(0)

        self.ro_settings = ROSettings.from_game_mode(self.game_mode)
        self.bucket_settings = BucketSettings()
        self.char_settings = CharSettings()
        self.tab_settings = TabSettings()
        self.cosmetic_flags = CosmeticFlags(0)

        self.ctoptions = ctoptions.CTOpts()

        self.seed = ''

    def to_jot_json(self) -> Dict[str, Any]:
        return {
            "game_mode": str(self.game_mode),
            "enemy_difficulty": str(self.enemy_difficulty),
            "item_difficulty": str(self.item_difficulty),
            "techorder": str(self.techorder),
            "shopprices": str(self.shopprices),
            "mystery_settings": self.mystery_settings,
            "gameflags": self.gameflags,
            "initial_flags": self.initial_flags,
            "ro_settings": self.ro_settings,
            "bucket_settings": self.bucket_settings,
            "char_settings": self.char_settings,
            "tab_settings": self.tab_settings,
            "cosmetic_flags": self.cosmetic_flags,
            "ctoptions": self.ctoptions,
            "seed": self.seed,
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
            GF.FAST_TABS | GF.FREE_MENU_GLITCH |
            GF.GEAR_RANDO | GF.HEALING_ITEM_RANDO
        )
        ret.ro_settings.flags = ROFlags.BOSS_SPOT_HP

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
        forced_off = ForcedFlags.get_forced_off(mode)
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
                raise ValueError(f"Cannot fix flag conflicts: {added_kis} KIs > {added_spots} spots")


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
            GameFlags.ELEMENT_RANDO: 'er',  # er for Element Rando
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
