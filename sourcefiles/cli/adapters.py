from __future__ import annotations
import argparse
import functools
import operator

from typing import Any, Dict, Generator, List, Mapping, Optional, Protocol, Union, Tuple, Type

import ctoptions
import randosettings as rset

from cli.constants import FLAG_ENTRY_DICT, FlagEntry
from randosettings import Difficulty, ShopPrices, TechOrder
from randosettings import GameMode as GM, GameFlags as GF

SettingsFlags = Union[rset.GameFlags, rset.CosmeticFlags, rset.ROFlags]
GameArgumentType = Union[rset.GameMode, Difficulty, ShopPrices, TechOrder]


class SettingsAdapter(Protocol):
    '''Protocol to adapt CLI arguments to Settings object attributes.

    These classes are used to provide a consistent interface for converting CLI argparse arguments
    into attributes for a randosettings.Settings object (.to_setting classmethod). Some adapters
    set a single value (e.g. GameModeAdapter) while others build and set complex nested objects
    (e.g. MysterySettingsAdapter).
    '''

    # mapping of argument (per argparse.Namespace) mapped to values related to Settings attribute
    _adapter: Mapping[str, Any] = {}
    _cls: Type[Any]

    @classmethod
    def get(cls, arg: str) -> Any:
        '''Get attribute values associated with specified argparse argument.'''
        key = arg.lstrip('-').replace('-', '_')
        return cls._adapter[key]

    @classmethod
    def to_setting(cls, args: argparse.Namespace):
        raise NotImplementedError


class ArgumentAdapter(SettingsAdapter):
    '''Adapter for converting single CLI arg directly into a setting.'''

    _adapter: Mapping[str, GameArgumentType] = {}
    _arg: str
    _cls: Type[GameArgumentType]

    @classmethod
    def to_setting(cls, args: argparse.Namespace):
        '''Get coerced setting from args or default.'''
        if cls._arg in args:
            choice = getattr(args, cls._arg)
            return cls._adapter[choice.lower()]
        return cls._cls.default()


class GameModeAdapter(ArgumentAdapter):
    _adapter: Dict[str, rset.GameMode] = {
        'std': GM.STANDARD,
        'lw': GM.LOST_WORLDS,
        'loc': GM.LEGACY_OF_CYRUS,
        'ia': GM.ICE_AGE,
        'van': GM.VANILLA_RANDO,
    }
    _arg = 'mode'
    _cls = rset.GameMode


class EnemyDifficultyAdapter(ArgumentAdapter):
    _adapter: Dict[str, Difficulty] = {
        'normal': Difficulty.NORMAL,
        'hard': Difficulty.HARD,
    }
    _arg = 'enemy_difficulty'
    _cls = Difficulty


class ItemDifficultyAdapter(ArgumentAdapter):
    _adapter: Dict[str, Difficulty] = {
        'easy': Difficulty.EASY,
        'normal': Difficulty.NORMAL,
        'hard': Difficulty.HARD,
    }
    _arg = 'item_difficulty'
    _cls = Difficulty


class TechOrderAdapter(ArgumentAdapter):
    _adapter: Dict[str, TechOrder] = {
        'normal': TechOrder.NORMAL,
        'balanced': TechOrder.BALANCED_RANDOM,
        'random': TechOrder.FULL_RANDOM,
    }
    _arg = 'tech_order'
    _cls = TechOrder


class ShopPricesAdapter(ArgumentAdapter):
    _adapter: Dict[str, ShopPrices] = {
        'normal': ShopPrices.NORMAL,
        'random': ShopPrices.FULLY_RANDOM,
        'mostrandom': ShopPrices.MOSTLY_RANDOM,
        'free': ShopPrices.FREE,
    }
    _arg = 'shop_prices'
    _cls = ShopPrices


class FlagsAdapter(SettingsAdapter):
    '''Adapter for converting arguments into a Flag.'''

    _cls: Type[SettingsFlags]

    @classmethod
    def to_setting(cls, args: argparse.Namespace, init: Optional[SettingsFlags] = None):
        if init is None:
            init = cls._cls(0)
        flags = (
            flag
            for (flag, entry) in FLAG_ENTRY_DICT.items()
            if isinstance(flag, cls._cls) and getattr(args, cls._flag_to_arg(entry), None) is True
        )
        return functools.reduce(operator.or_, flags, init)

    @staticmethod
    def _flag_to_arg(entry: FlagEntry) -> str:
        return entry.name.lstrip('-').replace('-', '_')


class GameFlagsAdapter(FlagsAdapter):
    _cls = rset.GameFlags


class CosmeticFlagsAdapter(FlagsAdapter):
    _cls = rset.CosmeticFlags


class CharSettingsAdapter(SettingsAdapter):
    _cls = Type[rset.CharSettings]

    @classmethod
    def to_setting(cls, args: argparse.Namespace) -> rset.CharSettings:
        '''Extract CharSettings from argparse.Namespace.'''
        charset = rset.CharSettings()

        for name in rset.CharNames.default():
            name_arg = f"{name.lower()}_name"
            if name_arg in args:
                charset.names[name] = getattr(args, name_arg)

            choices_arg = f"{name.lower()}_choices"
            if choices_arg in args:
                charset.choices[name] = getattr(args, choices_arg)

        return charset


class BossRandoFlagsAdapter(FlagsAdapter):
    _cls = rset.ROFlags


class BossRandoSettingsAdapter(SettingsAdapter):
    _cls = rset.ROSettings

    @classmethod
    def to_setting(cls, args: argparse.Namespace) -> rset.ROSettings:
        '''Extract ROSettings from argparse.Namespace.'''
        # just flags; spots, bosses are not implmeented options in CLI at this time
        game_mode = GameModeAdapter.to_setting(args)
        roset = rset.ROSettings.from_game_mode(game_mode)
        roset.flags = BossRandoFlagsAdapter.to_setting(args)
        return roset


class BucketSettingsAdapter(SettingsAdapter):
    _adapter: Dict[str, str] = {
        'bucket_disable_other_go': 'disable_other_go_modes',
        'bucket_objectives_win': 'objectives_win',
        'bucket_objective_count': 'num_objectives',
        'bucket_objective_needed_count': 'num_objectives_needed',
    }
    _cls = rset.BucketSettings

    @classmethod
    def to_setting(cls, args: argparse.Namespace) -> rset.BucketSettings:
        '''Extract BucketSettings from argparse.Namespace.'''
        bset = rset.BucketSettings()
        for arg, prop in cls._adapter.items():
            if arg in args:
                setattr(bset, prop, getattr(args, arg))

        # objectives
        objectives = (getattr(args, f"bucket_objective{obj}", None) for obj in range(1, bset.num_objectives + 1))
        hints: List[str] = [hint for hint in objectives if hint is not None]
        if hints:
            bset.hints = hints

        return bset


class TabSettingsAdapter(SettingsAdapter):
    _adapter: Dict[str, str] = {
        'min_power_tab': 'power_min',
        'max_power_tab': 'power_max',
        'min_magic_tab': 'magic_min',
        'max_magic_tab': 'magic_max',
        'min_speed_tab': 'speed_min',
        'max_speed_tab': 'speed_max',
        'tab_scheme': 'scheme',
        'tab_binom_success': 'binom_success',
    }
    _cls = rset.TabSettings

    @classmethod
    def to_setting(cls, args: argparse.Namespace):
        '''Extract TabSettings from argparse.Namespace.'''
        tset = rset.TabSettings()
        for arg, prop in cls._adapter.items():
            if arg in args:
                setattr(tset, prop, getattr(args, arg))

        if 'tab_scheme' in args:
            scheme = getattr(args, 'tab_scheme')
            if scheme == 'binomial':
                setattr(tset, 'scheme', rset.TabRandoScheme.BINOMIAL)
            elif scheme == 'uniform':
                setattr(tset, 'scheme', rset.TabRandoScheme.UNIFORM)
            else:
                raise ValueError(f"Invalid tab scheme: {scheme}")

        return tset


class CTOptsAdapter(SettingsAdapter):
    _adapter: Dict[str, str] = {
        'save_menu_cursor': 'save_menu_cursor',
        'save_battle_cursor': 'save_battle_cursor',
        'save_skill_cursor_off': 'save_tech_cursor',
        'skill_item_info_off': 'skill_item_info',
        'consistent_paging': 'consistent_paging',
        'battle_speed': 'battle_speed',
        'battle_msg_speed': 'battle_msg_speed',
        'battle_gauge_style': 'battle_gauge_style',
        'background': 'menu_background',
    }
    _cls = ctoptions.CTOpts

    @classmethod
    def to_setting(cls, args: argparse.Namespace) -> ctoptions.CTOpts:
        '''Extract CTOpts from argparse.Namespace.'''
        ct_opts = ctoptions.CTOpts()
        inverted_args = ['save_skill_cursor_off', 'skill_item_info_off']
        plus_one_args = ['battle_speed', 'battle_msg_speed', 'background']

        for arg, prop in cls._adapter.items():
            if arg in args:
                if arg in inverted_args:
                    setattr(ct_opts, prop, not getattr(args, arg))
                elif arg in plus_one_args:
                    setattr(ct_opts, prop, getattr(args, arg) - 1)
                else:
                    setattr(ct_opts, prop, getattr(args, arg))
        return ct_opts


class MysterySettingsAdapter(SettingsAdapter):
    _adapter: Dict[str, Tuple[str, Any]] = {
        # game_mode_freqs
        'mystery_mode_std': ('game_mode_freqs', GM.STANDARD),
        'mystery_mode_lw': ('game_mode_freqs', GM.LOST_WORLDS),
        'mystery_mode_loc': ('game_mode_freqs', GM.LEGACY_OF_CYRUS),
        'mystery_mode_ia': ('game_mode_freqs', GM.ICE_AGE),
        'mystery_mode_van': ('game_mode_freqs', GM.VANILLA_RANDO),
        #  item_difficulty_freqs
        'mystery_item_easy': ('item_difficulty_freqs', Difficulty.EASY),
        'mystery_item_norm': ('item_difficulty_freqs', Difficulty.NORMAL),
        'mystery_item_hard': ('item_difficulty_freqs', Difficulty.HARD),
        # enemy_difficulty_freqs
        'mystery_enemy_norm': ('enemy_difficulty_freqs', Difficulty.NORMAL),
        'mystery_enemy_hard': ('enemy_difficulty_freqs', Difficulty.HARD),
        # tech_order_freqs
        'mystery_tech_norm': ('tech_order_freqs', TechOrder.NORMAL),
        'mystery_tech_balanced': ('tech_order_freqs', TechOrder.BALANCED_RANDOM),
        'mystery_tech_rand': ('tech_order_freqs', TechOrder.FULL_RANDOM),
        # shop_price_freqs
        'mystery_prices_norm': ('shop_price_freqs', ShopPrices.NORMAL),
        'mystery_prices_mostly_rand': ('shop_price_freqs', ShopPrices.MOSTLY_RANDOM),
        'mystery_prices_rand': ('shop_price_freqs', ShopPrices.FULLY_RANDOM),
        'mystery_prices_free': ('shop_price_freqs', ShopPrices.FREE),
        # flag_prob_dict
        'mystery_flag_tab_treasures': ('flag_prob_dict', GF.TAB_TREASURES),
        'mystery_flag_unlocked_magic': ('flag_prob_dict', GF.UNLOCKED_MAGIC),
        'mystery_flag_bucket_list': ('flag_prob_dict', GF.BUCKET_LIST),
        'mystery_flag_chronosanity': ('flag_prob_dict', GF.CHRONOSANITY),
        'mystery_flag_boss_rando': ('flag_prob_dict', GF.BOSS_RANDO),
        'mystery_flag_boss_scaling': ('flag_prob_dict', GF.BOSS_SCALE),
        'mystery_flag_locked_chars': ('flag_prob_dict', GF.LOCKED_CHARS),
        'mystery_flag_char_rando': ('flag_prob_dict', GF.CHAR_RANDO),
        'mystery_flag_duplicate_chars': ('flag_prob_dict', GF.DUPLICATE_CHARS),
        'mystery_flag_epoch_fail': ('flag_prob_dict', GF.EPOCH_FAIL),
        'mystery_flag_gear_rando': ('flag_prob_dict', GF.GEAR_RANDO),
        'mystery_flag_heal_rando': ('flag_prob_dict', GF.HEALING_ITEM_RANDO),
    }
    _cls = rset.MysterySettings

    @classmethod
    def args(cls, field: str) -> Generator[Tuple[str, Any], None, None]:
        '''Get all CLI arguments and key in field in MysterySettings.'''
        for arg, (item_field, key) in cls._adapter.items():
            if item_field == field:
                yield (arg, key)

    @classmethod
    def to_setting(cls, args: argparse.Namespace) -> rset.MysterySettings:
        '''Get mystery settings from args.

        This creates a MysterySettings object where all explicitly-passed values from the CLI
        override the inherent defaults. Values not explicitly passed are suppressed by
        the parser and will not override the defaults from randosettings.MysterySettings.
        '''
        mset = rset.MysterySettings()
        for arg, (field, key) in cls._adapter.items():
            if arg in args:
                attr = getattr(mset, field)
                attr[key] = getattr(args, arg)
        return mset
