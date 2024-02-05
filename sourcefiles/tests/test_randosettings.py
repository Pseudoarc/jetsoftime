import pytest
import randosettings as rset

from bossrandotypes import BossID
from randosettings import GameFlags as _GF
from randosettings import GameMode as _GM


ALL_KI_FLAGS: rset.GameFlags = _GF.RESTORE_JOHNNY_RACE | _GF.RESTORE_TOOLS | _GF.EPOCH_FAIL | _GF.ROCKSANITY
MOST_SPOT_FLAGS: rset.GameFlags = _GF.ADD_BEKKLER_SPOT | _GF.ADD_CYRUS_SPOT | _GF.ADD_OZZIE_SPOT | _GF.ADD_RACELOG_SPOT

# FIXTURES ###################################################################


@pytest.fixture(scope='function')
def settings():
    return rset.Settings()


# TESTS ###################################################################


@pytest.mark.parametrize(
    'mode, spot_flags, expected_flags',
    [
        # need +2 spots for all flags
        (_GM.STANDARD, _GF.ADD_BEKKLER_SPOT | _GF.ADD_RACELOG_SPOT, ALL_KI_FLAGS),
        # no Epoch Fail / Ribbon for LW, nor other spots, so all get removed
        (_GM.LOST_WORLDS, MOST_SPOT_FLAGS | _GF.VANILLA_ROBO_RIBBON, _GF(0)),
        # 2 extras from IA, -1 no black omen, +1 spot
        (_GM.ICE_AGE, _GF.ADD_OZZIE_SPOT, ALL_KI_FLAGS),
        # no Johnny Race or Restore Tools for LoC, don't need extra spots
        (_GM.LEGACY_OF_CYRUS, _GF(0), _GF.EPOCH_FAIL | _GF.ROCKSANITY),
        (_GM.VANILLA_RANDO, _GF.ADD_CYRUS_SPOT | _GF.ADD_OZZIE_SPOT, ALL_KI_FLAGS),
        # chronosanity should not need any extra spots nor add/remove flags
        (_GM.STANDARD, _GF.CHRONOSANITY, ALL_KI_FLAGS),
    ],
    ids=('std+2', 'lw', 'ia+1', 'loc', 'vr+2', 'std+cr'),
)
def test_fix_flag_conflicts_adequate_spots(mode, spot_flags, expected_flags, settings):
    '''Check no unexpected flags added/removed when adequate spots.

    This test also partially covers _forced_off_dict being applied in fix_flag_conflicts by
    asserting that incompatible flags for the game mode are disabled.
    '''
    # turn on all the extra KI flags (some will be forced off based on mode)
    ki_flags = ALL_KI_FLAGS
    unexpected_flags = ki_flags - expected_flags

    settings.game_mode = mode
    settings.gameflags |= ki_flags | spot_flags

    settings.fix_flag_conflicts()

    assert _GF.VANILLA_ROBO_RIBBON not in settings.gameflags, 'Unexpected vanilla robo ribbon'

    # make sure incompatible flags get removed, but all other KI spots remain
    if mode == _GM.LOST_WORLDS:
        assert not settings.gameflags, 'Extra flags for Lost Worlds'
    else:
        assert expected_flags & settings.gameflags, 'Missing expected flags'
    assert not unexpected_flags & settings.gameflags, 'Unexpected incompatible flags'


@pytest.mark.parametrize(
    'mode, spot_flags, added, removed',
    [
        # no spots added, add ribbon and remove Epoch Fail
        (_GM.STANDARD, _GF(0), _GF.VANILLA_ROBO_RIBBON, _GF.EPOCH_FAIL),
        # added one spot, just ribbon
        (_GM.STANDARD, _GF.ADD_CYRUS_SPOT, _GF.VANILLA_ROBO_RIBBON, _GF(0)),
        # added one spot, removed black omen, add ribbon and remove Epoch Fail
        (_GM.STANDARD, _GF.ADD_OZZIE_SPOT | _GF.REMOVE_BLACK_OMEN_SPOT, _GF.VANILLA_ROBO_RIBBON, _GF.EPOCH_FAIL),
        # +2 IA, -1 no black omen, adds ribbon and but keeps Epoch Fail
        (_GM.ICE_AGE, _GF(0), _GF.VANILLA_ROBO_RIBBON, _GF(0)),
    ],
    ids=('std', 'std+1', 'std+1-1', 'ia'),
)
def test_fix_flag_conflicts_few_spots(mode, spot_flags, added, removed, settings):
    '''Check expected flags added/removed when not enough spots.'''
    # turn on all the extra KI flags (some will be forced off due to lacking spots)
    ki_flags = ALL_KI_FLAGS

    settings.game_mode = mode
    settings.gameflags |= ki_flags | spot_flags

    settings.fix_flag_conflicts()

    assert added & settings.gameflags, 'Missing expected additional flags'
    assert not removed & settings.gameflags, 'Unexpected additional flags'


@pytest.mark.parametrize(
    'flag, required',
    [
        (_GF.ROCKSANITY, _GF.UNLOCKED_SKYGATES),
        (_GF.DUPLICATE_CHARS, _GF.CHAR_RANDO),
    ],
    ids=('rocksanity', 'duplicate-chars'),
)
def test_fix_flag_conflicts_forces_on_required(flag, required, settings):
    '''Check that required flags are forced on when flags that depend on them are used.'''
    assert settings.gameflags == settings.gameflags & required, 'Unexpected required flags'

    settings.gameflags |= flag
    settings.fix_flag_conflicts()

    assert not (required - settings.gameflags), 'Missing required flags'


@pytest.mark.parametrize(
    'mode, incompatible_spots',
    [
        (_GM.LOST_WORLDS, MOST_SPOT_FLAGS | _GF.VANILLA_ROBO_RIBBON),
        (_GM.ICE_AGE, _GF.ADD_BEKKLER_SPOT),
        (_GM.LEGACY_OF_CYRUS, _GF.ADD_BEKKLER_SPOT | _GF.ADD_OZZIE_SPOT | _GF.ADD_RACELOG_SPOT),
    ],
    ids=('lw', 'ia', 'loc'),
)
def test_fix_flag_conflicts_removes_spots(mode, incompatible_spots, settings):
    '''Check incompatible spot flags are removed based on game mode.

    This partially covers _forced_off_dict being applied in fix_flag_conflicts by
    asserting that incompatible spot flags for game mode are disabled.
    '''
    # turn on all spots so can make sure incompatible ones are removed
    spot_flags = MOST_SPOT_FLAGS | _GF.VANILLA_ROBO_RIBBON
    compatible_spots = spot_flags - incompatible_spots

    settings.game_mode = mode
    settings.gameflags |= spot_flags

    settings.fix_flag_conflicts()

    if mode == _GM.LOST_WORLDS:
        assert not settings.gameflags, 'Extra flags for Lost Worlds'
    else:
        assert not incompatible_spots & settings.gameflags, 'Unexpected incompatible spots'
        assert compatible_spots & settings.gameflags, 'Missing compatible spots'


def test_fix_flag_conflicts_unfixable(settings):
    '''Check exception thrown when cannot adjust to have enough spots.'''
    settings.game_mode = _GM.STANDARD
    settings.gameflags |= ALL_KI_FLAGS | _GF.REMOVE_BLACK_OMEN_SPOT
    with pytest.raises(ValueError) as ex:
        settings.fix_flag_conflicts()
    assert 'fix flag conflicts' in str(ex)


@pytest.mark.parametrize('mode', [rset.GameMode.STANDARD, rset.GameMode.LOST_WORLDS], ids=('standard', 'lostworlds'))
def test_ro_settings_bosses(mode):
    '''Check that Boss Rando bosses can be specified in ROSettings.

    Check can specify a partial list of bosses and they are included in ROSettings.
    The boss list is padded out with random other bosses to match number of spots.
    '''
    bosses = [BossID.MAGUS_NORTH_CAPE, BossID.YAKRA_XIII, BossID.NIZBEL_2, BossID.DALTON_PLUS]
    roset = rset.ROSettings.from_game_mode(mode, bosses=bosses)

    assert len(roset.spots) == len(roset.bosses)
    assert bosses == roset.bosses[: len(bosses)], 'ROSettings bosses does not start with expected bosses'


@pytest.mark.parametrize('mode', list(rset.GameMode), ids=[str(mode) for mode in list(rset.GameMode)])
def test_ro_settings_spots(mode):
    '''Check that Boss Rando spots selected from game mode.'''
    roset = rset.ROSettings.from_game_mode(mode)

    assert roset.spots, f'Missing boss rando spots for mode: {mode}'
    assert roset.bosses, f'Missing boss rando bosses for mode: {mode}'


@pytest.mark.parametrize(
    'preset',
    [
        rset.Settings.get_race_presets,
        rset.Settings.get_new_player_presets,
        rset.Settings.get_lost_worlds_presets,
        rset.Settings.get_hard_presets,
        rset.Settings.get_tourney_early_preset,
        rset.Settings.get_tourney_top8_preset,
    ],
    ids=('race', 'new_player', 'lost_worlds', 'hard', 'tourney_early', 'tourney_top8'),
)
def test_settings_from_preset(preset):
    '''Check all presets can be parsed into Settings.'''
    settings = preset()
    assert settings
