from __future__ import annotations
import argparse
import copy

from pathlib import Path
from typing import Any, Dict, Generator, Optional, Protocol, List, Tuple, Type

import cli.adapters as adp
import ctoptions
import ctstrings
import objectivehints as obhint
import randosettings as rset
from cli.constants import FLAG_ENTRY_DICT
from randosettings import Difficulty
from randosettings import GameFlags as GF, CosmeticFlags as CF, ROFlags as RO


# https://stackoverflow.com/questions/3853722/
# how-to-insert-newlines-on-argparse-help-text
class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


def args_to_settings(args: argparse.Namespace) -> rset.Settings:
    '''Convert result of argparse to settings object.'''
    ret_set = rset.Settings()
    if 'seed' in args:
        ret_set.seed = args.seed
    ret_set.game_mode = adp.GameModeAdapter.to_setting(args)
    ret_set.gameflags = adp.GameFlagsAdapter.to_setting(args)
    ret_set.initial_flags = copy.deepcopy(ret_set.gameflags)
    ret_set.item_difficulty = adp.ItemDifficultyAdapter.to_setting(args)
    ret_set.enemy_difficulty = adp.EnemyDifficultyAdapter.to_setting(args)
    ret_set.techorder = adp.TechOrderAdapter.to_setting(args)
    ret_set.shopprices = adp.ShopPricesAdapter.to_setting(args)
    ret_set.mystery_settings = adp.MysterySettingsAdapter.to_setting(args)
    ret_set.cosmetic_flags = adp.CosmeticFlagsAdapter.to_setting(args)
    ret_set.ctoptions = adp.CTOptsAdapter.to_setting(args)
    ret_set.char_settings = adp.CharSettingsAdapter.to_setting(args)
    ret_set.tab_settings = adp.TabSettingsAdapter.to_setting(args)
    ret_set.ro_settings = adp.BossRandoSettingsAdapter.to_setting(args)
    ret_set.bucket_settings = adp.BucketSettingsAdapter.to_setting(args)
    return ret_set


class Argument:
    '''Container for argparse argument for use with ArgumentGroup classes.

    Sets most arguments to use argparse.SUPPRESS default, meaning unless explicitly
    passed on CLI, will not end up in argparse.Namespace. Code within SettingsAdapter
    checks for this, and when suppressed, does not override the default values
    assigned when randosettings.Settings is initialized. This prevents needing to
    double set default values in this file and elsewhere and prevents such regressions.
    '''

    name: Tuple[str, ...]
    options: Dict[str, Any]

    def __init__(self, *name: str, **options):
        if not options.get('required') and 'default' not in options:
            options['default'] = argparse.SUPPRESS
        self.name = name
        self.options = options


class ArgumentGroup(Protocol):
    '''Protocol for building argparse argument groups and attaching to parser.'''

    # argument group title and description
    _title: str
    _desc: Optional[str] = None

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        '''Yield arguments from group.'''
        raise NotImplementedError(f"Missing .arguments definition for '{cls}'.")

    @classmethod
    def add_to_parser(cls, parser: argparse.ArgumentParser) -> argparse._ArgumentGroup:
        '''Create argument group, add all arguments to it, and attach to parser.'''
        group = parser.add_argument_group(cls._title, description=cls._desc)
        for arg in cls.arguments():
            group.add_argument(*arg.name, **arg.options)
        return group


class FlagsArgumentGroup(ArgumentGroup):
    '''Implemention of ArgumentGroup for arguments related to Flag options.'''

    # list of flags which should have an argument created (one per flag)
    _flags: List[adp.SettingsFlags]

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        for flag in cls._flags:
            flag_entry = FLAG_ENTRY_DICT[flag]
            name = [flag_entry.name]
            if flag_entry.short_name is not None:
                name.append(flag_entry.short_name)
            yield Argument(*name, help=flag_entry.help_text, action='store_true')


class BasicFlagsAG(FlagsArgumentGroup):
    _title = 'Basic Flags'
    _flags = [
        GF.FIX_GLITCH,
        GF.BOSS_SCALE,
        GF.ZEAL_END,
        GF.FAST_PENDANT,
        GF.LOCKED_CHARS,
        GF.UNLOCKED_MAGIC,
        GF.CHRONOSANITY,
        GF.TAB_TREASURES,
        GF.BOSS_RANDO,
        GF.CHAR_RANDO,
        GF.MYSTERY,
        GF.HEALING_ITEM_RANDO,
        GF.GEAR_RANDO,
        GF.EPOCH_FAIL,
        GF.ELEMENT_RANDO
    ]


class BossRandoFlagsAG(FlagsArgumentGroup):
    _title = 'Boss Rando Flags'
    _desc = 'These options are only valid when --boss-randomization [-ro] is set'
    _flags = [RO.BOSS_SPOT_HP, RO.PRESERVE_PARTS]


class QoLFlagsAG(FlagsArgumentGroup):
    _title = 'QoL Flags'
    _flags = [GF.FAST_TABS, GF.VISIBLE_HEALTH, GF.BOSS_SIGHTSCOPE, GF.FREE_MENU_GLITCH]


class ExtraFlagsAG(FlagsArgumentGroup):
    _title = 'Extra Flags'
    _flags = [GF.STARTERS_SUFFICIENT, GF.USE_ANTILIFE, GF.TACKLE_EFFECTS_ON, GF.BUCKET_LIST, GF.TECH_DAMAGE_RANDO]


class LogicKIFlagsAG(FlagsArgumentGroup):
    _title = 'Logic Tweak Flags that add a KI'
    _flags = [GF.RESTORE_JOHNNY_RACE, GF.RESTORE_TOOLS]


class LogicSpotFlagsAG(FlagsArgumentGroup):
    _title = 'Logic Tweak Flags that add/remove a KI Spot'
    _flags = [
        GF.ADD_BEKKLER_SPOT,
        GF.ADD_OZZIE_SPOT,
        GF.ADD_RACELOG_SPOT,
        GF.ADD_CYRUS_SPOT,
        GF.VANILLA_ROBO_RIBBON,
        GF.REMOVE_BLACK_OMEN_SPOT,
    ]


class LogicNeutralFlagsAG(FlagsArgumentGroup):
    _title = 'Logic Flags that are KI/KI Spot Neutral'
    _flags = [GF.UNLOCKED_SKYGATES, GF.ADD_SUNKEEP_SPOT, GF.SPLIT_ARRIS_DOME, GF.VANILLA_DESERT, GF.ROCKSANITY]


class CosmeticsFlagsAG(FlagsArgumentGroup):
    _title = 'Cosmetic Flags'
    _desc = 'Have no effect on randomization.'
    _flags = [CF.AUTORUN, CF.DEATH_PEAK_ALT_MUSIC, CF.ZENAN_ALT_MUSIC, CF.QUIET_MODE, CF.REDUCE_FLASH]


class BucketListAG(ArgumentGroup):
    _title = '--bucket-list [-k] options'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        bset = rset.BucketSettings()
        yield Argument(
            '--bucket-objective-count',
            help=f"Number of objectives to use. [{bset.num_objectives}]",
            type=int,
        )
        yield Argument(
            '--bucket-objective-needed-count',
            help=f"Number of objectives needed to meet goal. [{bset.num_objectives_needed}]",
            type=int,
        )
        yield Argument(
            '--bucket-objectives-win',
            help=f"Objectives win game instead of unlocking bucket. [{bset.objectives_win}]",
            action='store_true',
        )
        yield Argument(
            '--bucket-disable-other-go',
            help=f"The only way to win is through the bucket. [{bset.disable_other_go_modes}]",
            action='store_true',
        )
        for obj in range(1, 9):
            yield Argument(f"--bucket-objective{obj}", f"-obj{obj}", type=cls._check_bucket_objective)

    @staticmethod
    def _check_bucket_objective(hint: str) -> str:
        valid, msg = obhint.is_hint_valid(hint)
        if not valid:
            raise argparse.ArgumentTypeError(f"Invalid bucket objective: '{msg}'")
        return hint


class CharNamesAG(ArgumentGroup):
    _title = 'Character Names'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        for char_name in rset.CharNames.default():
            yield Argument(f"--{char_name.lower()}-name", help=f"[{char_name}]", type=cls._verify_name)

    @staticmethod
    def _verify_name(string: str) -> str:
        if len(string) > 5:
            raise argparse.ArgumentTypeError('Name must have length 5 or less.')
        try:
            ctnamestr = ctstrings.CTNameString.from_string(string, 5)
        except ctstrings.InvalidSymbolException as exc:
            raise argparse.ArgumentTypeError(f"Invalid symbol: '{exc}'")
        return string


class CharRandoAG(ArgumentGroup):
    _title = '-rc Options'
    _desc = 'These options are only valid when --char-rando [-rc] is set'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        yield Argument(
            '--duplicate-characters',
            '-dc',
            help='Allow multiple copies of a character to be present in a seed.',
            action='store_true',
        )
        yield Argument(
            '--duplicate-techs',
            help='Allow duplicate characters to perform dual techs together.',
            action='store_true',
        )
        yield Argument(
            '--crono-choices',
            help='The characters Crono is allowed to be assigned. For example, '
            '--crono-choices "lucca robo" would allow Crono to be assigned to '
            'either Lucca or Robo.  If the list is preceded with "not" '
            '(e.g. not lucca ayla) then all except the listed characters will be '
            'allowed.',
        )
        for name in rset.CharNames.default()[1:-1]:
            yield Argument(f"--{name.lower()}-choices", help='Same as --crono-choices.')


class GameOptionsAG(ArgumentGroup):
    _title = 'Game Options'
    _desc = ''

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        ct_default = ctoptions.CTOpts()

        menu_opts = (
            ('--save-menu-cursor', 'save last used page of X-menu'),
            ('--save-battle-cursor', 'save battle cursor position'),
            ('--save-skill-cursor-off', 'do not save position in skill/item menu'),
            ('--skill-item-info-off', 'do not show skill/item descriptions'),
            ('--consistent-paging', 'page up/down have the same effect in all menus'),
        )

        for name, desc in menu_opts:
            default: Any = bool(getattr(ct_default, adp.CTOptsAdapter.get(name)))
            if name.endswith('-off'):
                default = not default
            desc = f"{desc} [{default}]"
            yield Argument(name, help=desc, action="store_true")

        plus_one_opts = (
            ('--battle-speed', 'default battle speed (lower is faster)'),
            ('--battle-msg-speed', 'default battle message speed (lower is faster)'),
            ('--background', 'default background'),
        )
        for name, desc in plus_one_opts:
            default = int(getattr(ct_default, adp.CTOptsAdapter.get(name))) + 1
            desc = f"{desc} [{default}]"
            yield Argument(name, help=desc, type=int, choices=range(1, 9))

        default = int(getattr(ct_default, adp.CTOptsAdapter.get('battle_gauge_style')))
        desc = f"default atb gauge style [{default}]"
        yield Argument('--battle-gauge-style', help=desc, type=int, choices=range(3))


class GeneralOptionsAG(ArgumentGroup):
    _title = 'General options'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        diff_default = str(Difficulty.default()).lower()
        yield Argument(
            '--mode',
            choices=['std', 'lw', 'ia', 'loc', 'van'],
            help="R|"
            "the basic game mode\n"
            " std: standard Jets of Time [default]\n"
            "  lw: lost worlds\n"
            "  ia: ice age\n"
            " loc: legacy of cyrus\n"
            " van: vanilla rando",
            type=str.lower,
        )
        yield Argument(
            '--item-difficulty',
            '-idiff',
            help=f"controls quality of treasure, drops, and starting gold [{diff_default}]",
            choices=['easy', 'normal', 'hard'],
            type=str.lower,
        )
        yield Argument(
            '--enemy-difficulty',
            '-ediff',
            help=f"controls strength of enemies and xp/tp rewards [{diff_default}]",
            choices=['normal', 'hard'],
            type=str.lower,
        )
        yield Argument(
            '--tech-order',
            help="R|"
            "controls the order in which characters learn techs\n"
            "  normal - vanilla tech order\n"
            "balanced - random but biased towards better techs later\n"
            "  random - fully random [default]",
            choices=['normal', 'balanced', 'random'],
            type=str.lower,
        )
        yield Argument(
            '--shop-prices',
            help="R|"
            "controls the prices in shops\n"
            "    normal - standard prices [default]\n"
            "    random - fully random prices\n"
            "mostrandom - random except for staple consumables\n"
            "      free - all items cost 1G",
            choices=['normal', 'random', 'mostrandom', 'free'],
            type=str.lower,
        )


class MysterySettingsArgumentGroup(ArgumentGroup):
    '''Implementation of ArgumentGroup for building arguments for mystery options.'''

    # field from randosettings.MysterySettings to build arguments
    _field: str

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        ms_default = rset.MysterySettings()

        for arg, key in adp.MysterySettingsAdapter.args(cls._field):
            flag = f"--{arg.replace('_', '-')}"
            rel_freq = ms_default[cls._field][key]
            desc = "[%d]" % rel_freq
            yield Argument(flag, type=cls._check_non_neg, help=desc)

    @staticmethod
    def _check_non_neg(value) -> int:
        ivalue = int(value)
        if ivalue < 0:
            raise argparse.ArgumentTypeError(f"Invalid negative frequency: {value}")
        return ivalue


class MysteryModeAG(MysterySettingsArgumentGroup):
    _title = 'Mystery Game Mode relative frequency (only with --mystery)'
    _desc = 'Set the relative frequency with which each game mode can appear. These must be non-negative integers.'
    _field = 'game_mode_freqs'


class MysteryItemDiffAG(MysterySettingsArgumentGroup):
    _title = 'Mystery Item Difficulty relative frequency (only with --mystery)'
    _field = 'item_difficulty_freqs'


class MysteryEnemyDiffAG(MysterySettingsArgumentGroup):
    _title = 'Mystery Enemy Difficulty relative frequency (only with --mystery)'
    _field = 'enemy_difficulty_freqs'


class MysteryTechOrderAG(MysterySettingsArgumentGroup):
    _title = 'Mystery Tech Order relative frequency (only with --mystery)'
    _field = 'tech_order_freqs'


class MysteryShopPricesAG(MysterySettingsArgumentGroup):
    _title = 'Mystery Shop Price relative frequency (only with --mystery)'
    _field = 'shop_price_freqs'


class MysteryFlagsAG(ArgumentGroup):
    _title = 'Mystery Flags Probabilities (only with --mystery)'
    _desc = (
        'The chance that a flag will be set in  the mystery settings. '
        'All flags not listed here will be set as they are in the main settings.'
    )

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        ms_default = rset.MysterySettings()

        for arg, key in adp.MysterySettingsAdapter.args('flag_prob_dict'):
            flag = f"--{arg.replace('_', '-')}"
            prob = ms_default['flag_prob_dict'][key]
            desc = "[%0.2f]" % prob
            yield Argument(flag, type=cls._check_prob, help=desc)

    @staticmethod
    def _check_prob(val) -> float:
        fval = float(val)
        if not 0 <= fval <= 1:
            raise argparse.ArgumentTypeError(f"Invalid probability (must be in [0,1]): {fval}")
        return fval


class TabSettingsAG(ArgumentGroup):
    _title = 'Tab Settings'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        tabset = rset.TabSettings()
        yield Argument(
            '--min-power-tab',
            help=f"The minimum value a power tab can increase power by [{tabset.power_min}]",
            type=int,
            choices=range(1, 10),
        )
        yield Argument(
            '--max-power-tab',
            help=f"The maximum value a power tab can increase power by [{tabset.power_max}]",
            type=int,
            choices=range(1, 10),
        )
        yield Argument(
            '--min-magic-tab',
            help=f"The minimum value a magic tab can increase power by [{tabset.magic_min}]",
            type=int,
            choices=range(1, 10),
        )
        yield Argument(
            '--max-magic-tab',
            help=f"The maximum value a magic tab can increase power by [{tabset.magic_max}]",
            type=int,
            choices=range(1, 10),
        )
        yield Argument(
            '--min-speed-tab',
            help=f"The minimum value a speed tab can increase power by [{tabset.speed_min}]",
            type=int,
            choices=range(1, 10),
        )
        yield Argument(
            '--max-speed-tab',
            help=f"The maximum value a speed tab can increase power by [{tabset.speed_max}]",
            type=int,
            choices=range(1, 10),
        )
        scheme = str(tabset.scheme).lower()
        yield Argument(
            '--tab-scheme',
            help=f"Probability distribution scheme for tabs [{scheme}]",
            choices=['uniform', 'binomial'],
        )
        yield Argument(
            '--tab-binom-success',
            help=f"Success probability for tabs (when binomial scheme used) [{tabset.binom_success}]",
            type=float,
        )


class RandomizerCLIOptionsAG(ArgumentGroup):
    '''Options specific to randomizer.py.'''

    _title = 'Generation options'

    @classmethod
    def arguments(cls) -> Generator[Argument, None, None]:
        yield Argument(
            '--input-file',
            '-i',
            required=True,
            help='path to Chrono Trigger (U) rom',
            type=Path,
        )
        yield Argument(
            '--output-path',
            '-o',
            help='path to output directory (default same as input)',
            default=None,
            type=Path,
        )
        yield Argument(
            '--seed',
            help='seed for generation (not website share id)',
        )
        yield Argument(
            '--spoilers',
            help='generate spoilers with the randomized rom.',
            default=None,
            action='store_true',
        )
        yield Argument(
            '--json-spoilers',
            help='generate json spoilers with the randomized rom.',
            default=None,
            action='store_true',
        )


# list of argument groups related to generation of seeds
# (does not include "cosmetics" which are below under "post-generation")
ALL_GENERATION_AG: List[Type[ArgumentGroup]] = [
    GeneralOptionsAG,
    BasicFlagsAG,
    BossRandoFlagsAG,
    CharRandoAG,
    TabSettingsAG,
    QoLFlagsAG,
    ExtraFlagsAG,
    LogicKIFlagsAG,
    LogicSpotFlagsAG,
    LogicNeutralFlagsAG,
    BucketListAG,
    MysteryModeAG,
    MysteryItemDiffAG,
    MysteryEnemyDiffAG,
    MysteryTechOrderAG,
    MysteryShopPricesAG,
    MysteryFlagsAG,
]


# list of argument groups which have to deal with "post-generation" aka "cosmetics"
# (at least as far as web GUI generator is concerned)
ALL_POST_GENERATION_AG: List[Type[ArgumentGroup]] = [
    CosmeticsFlagsAG,
    CharNamesAG,
    GameOptionsAG,
]


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(formatter_class=SmartFormatter)
    groups: List[Type[ArgumentGroup]] = [RandomizerCLIOptionsAG]
    groups.extend(ALL_GENERATION_AG)
    groups.extend(ALL_POST_GENERATION_AG)
    for ag in groups:
        ag.add_to_parser(parser)
    return parser
