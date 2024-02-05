'''
Tests for sourcefiles/arguments.py.

This file ends up exercising and covering a lot of settings-related code across arguments.py,
randosettings.py, ctoptions.py, bossrandotypes.py, and more, because it tests from passing CLI args through
the argparse parser to randosettings.args_to_settings creating a Settings object, and makes assertions about
that which cover testing settings for GameMode, GameFlags, CosmeticFlags, item and enemy difficulty,
TechOrder, ShopPrices, character names and settings (CharSettings), BucketSettings and more.
'''
from __future__ import annotations
import pytest

import cli.arguments as arguments
import cli.adapters as adp
import ctoptions
import randosettings as rset

from randosettings import CosmeticFlags as CF, GameFlags as GF, GameMode as GM, ROFlags as RO


@pytest.fixture(scope='session')
def parser():
    return arguments.get_parser()


@pytest.mark.parametrize(
    'cli_args, expected_settings',
    [
        # defaults
        (
            [],
            {
                'game_mode': GM.STANDARD,
                'item_difficulty': rset.Difficulty.NORMAL,
                'enemy_difficulty': rset.Difficulty.NORMAL,
                'techorder': rset.TechOrder.FULL_RANDOM,
                'shopprices': rset.ShopPrices.NORMAL,
                'mystery_settings': rset.MysterySettings(),
                'tab_settings': rset.TabSettings(),
                'char_settings': rset.CharSettings(),
                'bucket_settings': rset.BucketSettings(),
            },
        ),
        # overriding most non-flag settings
        (
            (
                '--mode loc --boss-randomization --char-rando --gear-rando --zenan-alt-music'
                ' --item-difficulty hard --enemy-difficulty hard --tech-order balanced'
                ' --shop-prices free'
            ).split(' '),
            {
                'game_mode': GM.LEGACY_OF_CYRUS,
                'gameflags': GF.BOSS_RANDO | GF.CHAR_RANDO | GF.GEAR_RANDO,
                'cosmetic_flags': CF.ZENAN_ALT_MUSIC,
                'item_difficulty': rset.Difficulty.HARD,
                'enemy_difficulty': rset.Difficulty.HARD,
                'techorder': rset.TechOrder.BALANCED_RANDOM,
                'shopprices': rset.ShopPrices.FREE,
            },
        ),
    ],
    ids=('defaults', 'complex'),
)
def test_args_to_settings(cli_args, expected_settings, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    settings = arguments.args_to_settings(args)

    assert isinstance(settings, rset.Settings), f"Wrong type for settings: {type(settings)}"

    for attr, value in expected_settings.items():
        assert getattr(settings, attr) == value


@pytest.mark.parametrize(
    'cli_args, expected',
    [
        # default
        ([], rset.BucketSettings()),
        # set objectives
        (
            (
                '--bucket-disable-other-go --bucket-objectives-win --bucket-objective-count 4'
                ' --bucket-objective-needed-count 2'
            ).split(' ')
            + [
                '--bucket-objective1=quest_gated',
                '--bucket-objective2=boss_nogo',
                '-obj3=50:quest_gated, 30:boss_nogo, 20:recruit_gated',
                '-obj4=Collect 3 Rocks',
            ],
            rset.BucketSettings(
                disable_other_go_modes=True,
                objectives_win=True,
                num_objectives=4,
                num_objectives_needed=2,
                hints=[
                    'quest_gated',
                    'boss_nogo',
                    '50:quest_gated, 30:boss_nogo, 20:recruit_gated',
                    'Collect 3 Rocks',
                ],
            ),
        ),
    ],
    ids=('default', 'objectives'),
)
def test_bucket_settings(cli_args, expected, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    bset = arguments.args_to_settings(args).bucket_settings

    assert bset == expected


@pytest.mark.parametrize(
    'cli_args, expected_choices',
    [
        # default all characters to all
        (
            [],
            [
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
                [0, 1, 2, 3, 4, 5, 6],
            ],
        ),
        # cover various options for character restriction including specifying characters,
        # specificying "all", defaulting to all, and specifying "not" (can be other characters)
        (
            [
                '--crono-choices=robo magus',
                '--marle-choices=marle lucca ayla',
                '--lucca-choices=crono lucca robo frog ayla',
                '--robo-choices=all',
                '--frog-choices=not magus crono',
                '--ayla-choices=ayla',
            ],
            [
                [3, 6],
                [1, 2, 5],
                [0, 2, 3, 4, 5],
                [0, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5],
                [5],
                [0, 1, 2, 3, 4, 5, 6],
            ],
        ),
    ],
    ids=('default', 'restricted'),
)
def test_char_choices(cli_args, expected_choices, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    settings = arguments.args_to_settings(args)

    assert settings.char_settings.choices == expected_choices


@pytest.mark.parametrize(
    'cli_args, expected_names',
    [
        # default
        ([], ['Crono', 'Marle', 'Lucca', 'Robo', 'Frog', 'Ayla', 'Magus', 'Epoch']),
        # overrides
        (
            '--frog-name Glenn --marle-name Nadia --epoch-name Apoch'.split(' '),
            ['Crono', 'Nadia', 'Lucca', 'Robo', 'Glenn', 'Ayla', 'Magus', 'Apoch'],
        ),
    ],
    ids=('default', 'override'),
)
def test_char_names(cli_args, expected_names, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    settings = arguments.args_to_settings(args)

    assert settings.char_settings.names == expected_names


@pytest.mark.parametrize(
    'cli_args, expected_settings',
    [
        # default
        (
            [],
            {
                'battle_speed': 4,
                'save_menu_cursor': 0,
                'skill_item_info': 1,
                'menu_background': 0,
                'battle_msg_speed': 4,
                'save_battle_cursor': 0,
                'save_tech_cursor': 1,
                'battle_gauge_style': 1,
            },
        ),
        # override all ctoptions
        (
            (
                '--battle-speed=1 --save-menu-cursor --skill-item-info-off --background=3'
                ' --battle-msg-speed 1 --save-battle-cursor --save-skill-cursor-off'
                ' --battle-gauge-style 2'
            ).split(' '),
            {
                'battle_speed': 0,
                'save_menu_cursor': 1,
                'skill_item_info': 0,
                'menu_background': 2,
                'battle_msg_speed': 0,
                'save_battle_cursor': 1,
                'save_tech_cursor': 0,
                'battle_gauge_style': 2,
            },
        ),
    ],
    ids=('default', 'complex'),
)
def test_ctoptions_settings(cli_args, expected_settings, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    ctopts = arguments.args_to_settings(args).ctoptions

    assert isinstance(ctopts, ctoptions.CTOpts), f"Wrong type: {type(ctopts)}"

    for attr, value in expected_settings.items():
        assert getattr(ctopts, attr) == value


@pytest.mark.parametrize(
    'cli_args, cls, init, expected_flags',
    [
        # game flags
        (
            ['--fix-glitch', '--zeal-end', '--fast-pendant'],
            adp.GameFlagsAdapter,
            None,
            GF.FIX_GLITCH | GF.ZEAL_END | GF.FAST_PENDANT,
        ),
        # cosmetic flags
        (['--autorun', '--reduce-flashes'], adp.CosmeticFlagsAdapter, None, CF.AUTORUN | CF.REDUCE_FLASH),
        # starting with initial flags and adding more game flags from CLI args
        (
            ['--chronosanity', '--unlocked-skyways'],
            adp.GameFlagsAdapter,
            GF.FIX_GLITCH | GF.FAST_TABS,
            GF.FIX_GLITCH | GF.FAST_TABS | GF.CHRONOSANITY | GF.UNLOCKED_SKYGATES,
        ),
    ],
    ids=('gameflags', 'cosmetic_flags', 'init'),
)
def test_flags_adapters(cli_args, cls, init, expected_flags, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])

    flags = cls.to_setting(args, init=init)
    expected_type = type(expected_flags)

    assert isinstance(flags, expected_type), f"Flags are not expected type: {expected_type}"
    assert flags == expected_flags, 'Flags do not match expected flags'


@pytest.mark.parametrize(
    'cli_args, expected',
    [
        # default
        ([], rset.ROSettings.from_game_mode(GM.STANDARD)),
        # boss rando
        ('-ro --boss-spot-hp'.split(' '), rset.ROSettings.from_game_mode(GM.STANDARD, flags=RO.BOSS_SPOT_HP)),
        # boss rando LoC
        ('--mode loc -ro'.split(' '), rset.ROSettings.from_game_mode(GM.LEGACY_OF_CYRUS)),
        # boss rando Lost Worlds
        ('--mode lw -ro'.split(' '), rset.ROSettings.from_game_mode(GM.LOST_WORLDS)),
    ],
    ids=('default', 'std', 'loc', 'lw'),
)
def test_ro_settings(cli_args, expected, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    ro_settings = arguments.args_to_settings(args).ro_settings

    assert ro_settings == expected


@pytest.mark.parametrize(
    'cli_args, expected',
    [
        # default
        (
            [],
            rset.MysterySettings(),
        ),
        # override most game_mode_freqs, make sure LW stays at default
        (
            ('--mystery-mode-std=0 --mystery-mode-loc=50 --mystery-mode-ia=20 --mystery-mode-van=5').split(' '),
            rset.MysterySettings().update(
                game_mode_freqs={
                    GM.STANDARD: 0,
                    GM.LEGACY_OF_CYRUS: 50,
                    GM.ICE_AGE: 20,
                    GM.VANILLA_RANDO: 5,
                }
            ),
        ),
        # override item and enemy difficulties, tech orders, shop prices
        (
            (
                '--mystery-item-easy=10 --mystery-item-norm=40 --mystery-item-hard=50'
                ' --mystery-enemy-norm=40 --mystery-enemy-hard=60'
                ' --mystery-tech-norm=0 --mystery-tech-balanced=40 --mystery-tech-rand=60'
                ' --mystery-prices-norm=40 --mystery-prices-mostly-rand=30 --mystery-prices-rand=20'
                ' --mystery-prices-free=10'
            ).split(' '),
            rset.MysterySettings().update(
                item_difficulty_freqs={
                    rset.Difficulty.EASY: 10,
                    rset.Difficulty.NORMAL: 40,
                    rset.Difficulty.HARD: 50,
                },
                enemy_difficulty_freqs={
                    rset.Difficulty.NORMAL: 40,
                    rset.Difficulty.HARD: 60,
                },
                tech_order_freqs={
                    rset.TechOrder.NORMAL: 0,
                    rset.TechOrder.BALANCED_RANDOM: 40,
                    rset.TechOrder.FULL_RANDOM: 60,
                },
                shop_price_freqs={
                    rset.ShopPrices.NORMAL: 40,
                    rset.ShopPrices.MOSTLY_RANDOM: 30,
                    rset.ShopPrices.FULLY_RANDOM: 20,
                    rset.ShopPrices.FREE: 10,
                },
            ),
        ),
        # override flag probs
        (
            (
                '--mystery-flag-bucket-list=0.2 --mystery-flag-boss-scaling=0 --mystery-flag-char-rando=1'
                ' --mystery-flag-gear-rando=0.6'
            ).split(' '),
            rset.MysterySettings().update(
                flag_prob_dict={
                    GF.BUCKET_LIST: 0.2,
                    GF.BOSS_SCALE: 0,
                    GF.CHAR_RANDO: 1.0,
                    GF.GEAR_RANDO: 0.6,
                },
            ),
        ),
    ],
    ids=('default', 'mode', 'complex', 'flag_prob'),
)
def test_mystery_settings(cli_args, expected, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    mystery = arguments.args_to_settings(args).mystery_settings

    assert mystery == expected


@pytest.mark.parametrize(
    'cli_args, expected',
    [
        # default
        (
            [],
            rset.TabSettings(),
        ),
        # override all tabs settings
        (
            (
                '--min-power-tab=3 --max-power-tab=6 --min-magic-tab=2 --max-magic-tab=4'
                ' --max-speed-tab=2 --min-speed-tab=2 --tab-scheme=binomial --tab-binom-success=0.7'
            ).split(' '),
            rset.TabSettings(
                power_min=3,
                power_max=6,
                magic_min=2,
                magic_max=4,
                speed_min=2,
                speed_max=2,
                scheme=rset.TabRandoScheme.BINOMIAL,
                binom_success=0.7,
            ),
        ),
    ],
    ids=('default', 'complex'),
)
def test_tab_settings(cli_args, expected, parser):
    args = parser.parse_args(cli_args + ['-i', 'ct.rom'])
    tabset = arguments.args_to_settings(args).tab_settings

    assert tabset == expected
