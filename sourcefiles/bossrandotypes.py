'''
This module contains enumerations for bosses and boss spots and some functions
describing the default relationship between them.
'''

from __future__ import annotations

import copy
import enum
import typing

import ctenums


class BossSpotID(enum.Enum):
    '''Enum for Boss Spots.'''
    MANORIA_CATHERDAL = enum.auto()
    HECKRAN_CAVE = enum.auto()
    DENADORO_MTS = enum.auto()
    ZENAN_BRIDGE = enum.auto()
    REPTITE_LAIR = enum.auto()
    MAGUS_CASTLE_FLEA = enum.auto()
    MAGUS_CASTLE_SLASH = enum.auto()
    GIANTS_CLAW = enum.auto()
    TYRANO_LAIR_NIZBEL = enum.auto()
    ZEAL_PALACE = enum.auto()
    DEATH_PEAK = enum.auto()
    BLACK_OMEN_GIGA_MUTANT = enum.auto()
    BLACK_OMEN_TERRA_MUTANT = enum.auto()
    BLACK_OMEN_ELDER_SPAWN = enum.auto()
    KINGS_TRIAL = enum.auto()
    OZZIES_FORT_FLEA_PLUS = enum.auto()
    OZZIES_FORT_SUPER_SLASH = enum.auto()
    SUN_PALACE = enum.auto()
    SUNKEN_DESERT = enum.auto()
    OCEAN_PALACE_TWIN_GOLEM = enum.auto()
    GENO_DOME = enum.auto()
    MT_WOE = enum.auto()
    ARRIS_DOME = enum.auto()
    FACTORY_RUINS = enum.auto()
    PRISON_CATWALKS = enum.auto()
    EPOCH_REBORN = enum.auto()

    def __str__(self):
        return _boss_spot_names[self]


_boss_spot_names: dict[BossSpotID, str] = {
    BossSpotID.MANORIA_CATHERDAL: 'Cathedral',
    BossSpotID.HECKRAN_CAVE: 'Heckran\'s Cave',
    BossSpotID.DENADORO_MTS: 'Denadoro Mountains',
    BossSpotID.ZENAN_BRIDGE: 'Zenan Bridge',
    BossSpotID.REPTITE_LAIR: 'Reptite Lair',
    BossSpotID.MAGUS_CASTLE_FLEA: 'Magus Castle Flea',
    BossSpotID.MAGUS_CASTLE_SLASH: 'Magus Castle Slash',
    BossSpotID.GIANTS_CLAW: 'Giant\'s Claw',
    BossSpotID.TYRANO_LAIR_NIZBEL: 'Tyrano Lair Midboss',
    BossSpotID.ZEAL_PALACE: 'Zeal Palace Throneroom',
    BossSpotID.DEATH_PEAK: 'Death Peak',
    BossSpotID.BLACK_OMEN_GIGA_MUTANT: 'Black Omen Giga Mutant',
    BossSpotID.BLACK_OMEN_TERRA_MUTANT: 'Black Omen Terra Mutant',
    BossSpotID.BLACK_OMEN_ELDER_SPAWN: 'Black Omen Elder Spawn',
    BossSpotID.KINGS_TRIAL: 'King\'s Trial',
    BossSpotID.OZZIES_FORT_FLEA_PLUS: 'Ozzie\'s Fort Flea Plus',
    BossSpotID.OZZIES_FORT_SUPER_SLASH: 'Ozzie\'s Fort Super Slash',
    BossSpotID.SUN_PALACE: 'Sun Palace',
    BossSpotID.SUNKEN_DESERT: 'Sunken Desert',
    BossSpotID.OCEAN_PALACE_TWIN_GOLEM: 'Ocean Palace Twin Boss',
    BossSpotID.GENO_DOME: 'Geno Dome',
    BossSpotID.MT_WOE: 'Mt. Woe',
    BossSpotID.ARRIS_DOME: 'Arris Dome',
    BossSpotID.FACTORY_RUINS: 'Factory',
    BossSpotID.PRISON_CATWALKS: 'Prison Catwalks',
    BossSpotID.EPOCH_REBORN: 'Epoch Reborn'
}


class BossID(enum.Enum):
    '''Enum for bosses.'''
    ATROPOS_XR = enum.auto()
    DALTON_PLUS = enum.auto()
    ELDER_SPAWN = enum.auto()
    FLEA = enum.auto()
    FLEA_PLUS = enum.auto()
    GIGA_MUTANT = enum.auto()
    GOLEM = enum.auto()
    GOLEM_BOSS = enum.auto()
    HECKRAN = enum.auto()
    LAVOS_SPAWN = enum.auto()
    MAMMON_M = enum.auto()
    MAGUS_NORTH_CAPE = enum.auto()
    MASA_MUNE = enum.auto()
    MEGA_MUTANT = enum.auto()
    MUD_IMP = enum.auto()
    NIZBEL = enum.auto()
    NIZBEL_2 = enum.auto()
    RETINITE = enum.auto()
    R_SERIES = enum.auto()
    RUST_TYRANO = enum.auto()
    SLASH_SWORD = enum.auto()
    SUPER_SLASH = enum.auto()
    SON_OF_SUN = enum.auto()
    TERRA_MUTANT = enum.auto()
    TWIN_BOSS = enum.auto()
    YAKRA = enum.auto()
    YAKRA_XIII = enum.auto()
    ZOMBOR = enum.auto()

    MOTHER_BRAIN = enum.auto()
    DRAGON_TANK = enum.auto()
    GIGA_GAIA = enum.auto()
    GUARDIAN = enum.auto()

    # Midbosses
    MAGUS = enum.auto()
    BLACK_TYRANO = enum.auto()

    # End Bosses
    LAVOS_SHELL = enum.auto()
    INNER_LAVOS = enum.auto()
    LAVOS_CORE = enum.auto()
    ZEAL = enum.auto()
    ZEAL_2 = enum.auto()

    def __str__(self):
        if self == BossID.MAGUS_NORTH_CAPE:
            return 'Magus (North Cape)'
        if self == BossID.YAKRA_XIII:
            return 'Yakra XIII'
        if self == BossID.NIZBEL_2:
            return 'Nizbel II'

        out = self.__repr__().split('.')[1].split(':')[0].lower().title()
        out = out.replace('_', ' ')
        return out


def get_assignable_bosses() -> list[BossID]:
    '''
    Returns a list of bosses that boss rando can assign to.
    '''
    boss_list = [
        BossID.ATROPOS_XR, BossID.DALTON_PLUS, BossID.FLEA, BossID.FLEA_PLUS,
        BossID.GOLEM, BossID.GOLEM_BOSS, BossID.HECKRAN,
        BossID.MAGUS_NORTH_CAPE, BossID.MASA_MUNE, BossID.NIZBEL,
        BossID.NIZBEL_2, BossID.RUST_TYRANO, BossID.SLASH_SWORD,
        BossID.SUPER_SLASH, BossID.YAKRA, BossID.YAKRA_XIII,
        BossID.ZOMBOR, BossID.LAVOS_SPAWN, BossID.ELDER_SPAWN,
        BossID.MEGA_MUTANT, BossID.GIGA_MUTANT, BossID.TERRA_MUTANT,
        BossID.RETINITE, BossID.SON_OF_SUN, BossID.MOTHER_BRAIN,
        BossID.GUARDIAN, BossID.GIGA_GAIA, BossID.MUD_IMP, BossID.R_SERIES,
        BossID.DRAGON_TANK
    ]

    return boss_list


def get_one_part_bosses():
    '''
    Return a list of one-part BossIDs which are eligible for boss rando.
    Helper for legacy boss placement
    '''
    return [
        BossID.ATROPOS_XR, BossID.DALTON_PLUS, BossID.FLEA, BossID.FLEA_PLUS,
        BossID.GOLEM, BossID.GOLEM_BOSS, BossID.HECKRAN,
        BossID.MAGUS_NORTH_CAPE, BossID.MASA_MUNE, BossID.NIZBEL,
        BossID.NIZBEL_2, BossID.RUST_TYRANO, BossID.SLASH_SWORD,
        BossID.SUPER_SLASH, BossID.YAKRA, BossID.YAKRA_XIII
    ]


def get_one_part_boss_spots():
    '''
    Return a list of one-part BossSpotIDs which are eilgible for boss rando.
    Helper for legacy boss placement
    '''
    BSID = BossSpotID
    return [
        BSID.DENADORO_MTS, BSID.EPOCH_REBORN, BSID.GIANTS_CLAW,
        BSID.HECKRAN_CAVE, BSID.KINGS_TRIAL, BSID.MAGUS_CASTLE_FLEA,
        BSID.MAGUS_CASTLE_SLASH, BSID.MANORIA_CATHERDAL,
        BSID.OZZIES_FORT_FLEA_PLUS, BSID.OZZIES_FORT_SUPER_SLASH,
        BSID.REPTITE_LAIR, BSID.TYRANO_LAIR_NIZBEL, BSID.ZEAL_PALACE
    ]


def get_two_part_boss_spots():
    '''
    Return a list of two-part BossSpotIDs which are eilgible for boss rando.
    Helper for legacy boss placement.
    '''
    BSID = BossSpotID
    return [
        BSID.BLACK_OMEN_ELDER_SPAWN, BSID.BLACK_OMEN_GIGA_MUTANT,
        BSID.BLACK_OMEN_TERRA_MUTANT, BSID.DEATH_PEAK, BSID.ZENAN_BRIDGE
    ]


def get_two_part_bosses():
    '''
    Return a list of two-part BossIDs which are eilgible for boss rando.
    Helper for legacy boss placement.
    '''
    return [
        BossID.ZOMBOR, BossID.LAVOS_SPAWN, BossID.ELDER_SPAWN,
        BossID.MEGA_MUTANT, BossID.GIGA_MUTANT, BossID.TERRA_MUTANT
    ]


class BossPart():
    '''
    Data class for a single part of a boss: enemy id, slot, and displacement
    from primary part.
    '''
    def __init__(self, enemy_id: ctenums.EnemyID = ctenums.EnemyID.NU,
                 slot: int = 3,
                 displacement: typing.Tuple[int, int] = (0, 0)):
        self.enemy_id = enemy_id
        self.slot = slot
        self.displacement = displacement

    def __str__(self):
        return f'BossPart: enemy_id={self.enemy_id}, slot={self.slot}, ' \
            f'disp={self.displacement}'


class BossScheme:
    '''
    Essentially a list of BossParts with some methods for manipulating
    displacements.
    '''
    def __init__(self, *parts: BossPart):
        self.parts = list(parts)

    def __str__(self):
        out_str = 'Boss Scheme:\n'
        for part in self.parts:
            out_str += '\t' + str(part) + '\n'

        return out_str

    def make_part_first(self, new_first_ind):
        '''
        Makes the part with the given index first.  Relative order of other
        parts is unchanged.
        '''
        self.parts[0], self.parts[new_first_ind] = \
            self.parts[new_first_ind], self.parts[0]

        disp_0 = self.parts[0].displacement
        for part in self.parts:
            cur_disp = part.displacement
            part.displacement = (cur_disp[0] - disp_0[0],
                                 cur_disp[1] - disp_0[1])

    def reorder_horiz(self, left: bool = True):
        '''
        Move the leftmost (if left is True) or rightmost (otherwise) to the
        first spot
        '''

        # expecting a value from enumerate(self.parts)
        def key_fn(val):
            return val[1].displacement[0]

        if left:
            x_extr = min(enumerate(self.parts), key=key_fn)
        else:
            x_extr = max(enumerate(self.parts), key=key_fn)

        extr_ind = x_extr[0]
        self.make_part_first(extr_ind)

    def flip_disps(self):
        '''
        Flip a boss's orientation so that bosses like guardian can fit when
        they are located on the left/right edges of the screen.
        '''

        for part in self.parts:
            part.displacement = (part.displacement[1], part.displacement[0])


_BS = BossScheme
_BP = BossPart
_EID = ctenums.EnemyID
_default_schemes: dict[BossID, BossScheme] = {
    BossID.ATROPOS_XR: _BS(_BP(_EID.ATROPOS_XR, 3)),
    BossID.BLACK_TYRANO: _BS(
        _BP(_EID.AZALA, 7),
        _BP(_EID.BLACKTYRANO, 3)  # Not real disp b/c not randomizing
    ),
    BossID.DALTON_PLUS: _BS(_BP(_EID.DALTON_PLUS, 3)),
    BossID.DRAGON_TANK: _BS(
        _BP(_EID.DRAGON_TANK, 3),
        _BP(_EID.TANK_HEAD, 9),
        _BP(_EID.GRINDER, 0xA)
    ),
    BossID.ELDER_SPAWN: _BS(
        _BP(_EID.ELDER_SPAWN_SHELL, 3),
        _BP(_EID.ELDER_SPAWN_HEAD, 9, (-8, 1))
    ),
    BossID.FLEA: _BS(_BP(_EID.FLEA, 7)),
    BossID.FLEA_PLUS: _BS(_BP(_EID.FLEA_PLUS, 7)),
    BossID.GIGA_GAIA: _BS(
        _BP(_EID.GIGA_GAIA_HEAD, 6),
        _BP(_EID.GIGA_GAIA_LEFT, 7, (0x20, 0x20)),
        _BP(_EID.GIGA_GAIA_RIGHT, 9, (-0x20, 0x20))
    ),
    BossID.GIGA_MUTANT: BossScheme(
        BossPart(_EID.GIGA_MUTANT_HEAD, 3),
        BossPart(_EID.GIGA_MUTANT_BOTTOM, 9)
    ),
    BossID.GOLEM: BossScheme(BossPart(_EID.GOLEM, 3)),
    BossID.GOLEM_BOSS: BossScheme(BossPart(_EID.GOLEM_BOSS, 3)),
    BossID.GUARDIAN: BossScheme(
        BossPart(_EID.GUARDIAN, 3),
        BossPart(_EID.GUARDIAN_BIT, 7, (-0x3A, -0x08)),
        BossPart(_EID.GUARDIAN_BIT, 8, (0x40, -0x08))
    ),
    BossID.HECKRAN: BossScheme(BossPart(_EID.HECKRAN, 3),),
    BossID.INNER_LAVOS: BossScheme(
        BossPart(_EID.LAVOS_2_HEAD, 0xA),
        BossPart(_EID.LAVOS_2_LEFT, 6, (-0x32, 0xE)),
        BossPart(_EID.LAVOS_2_RIGHT, 3, (0x32, 0xE))
    ),
    BossID.LAVOS_CORE: BossScheme(  # Fake coords
        BossPart(_EID.LAVOS_3_CORE, 3),
        BossPart(_EID.LAVOS_3_LEFT, 7),
        BossPart(_EID.LAVOS_3_RIGHT, 9)
    ),
    BossID.LAVOS_SHELL: BossScheme(BossPart(_EID.LAVOS_OCEAN_PALACE, 5)),
    BossID.LAVOS_SPAWN: BossScheme(
        BossPart(_EID.LAVOS_SPAWN_SHELL, 3),
        BossPart(_EID.LAVOS_SPAWN_HEAD, 9, (-8, 0))
    ),
    BossID.MAMMON_M: BossScheme(BossPart(_EID.MAMMON_M, 3)),
    BossID.MASA_MUNE: BossScheme(BossPart(_EID.MASA_MUNE, 6)),
    BossID.MEGA_MUTANT: BossScheme(
        BossPart(_EID.MEGA_MUTANT_HEAD, 3),
        BossPart(_EID.MEGA_MUTANT_BOTTOM, 7)
    ),
    BossID.MAGUS: BossScheme(BossPart(_EID.MAGUS, 3)),
    BossID.MAGUS_NORTH_CAPE: BossScheme(BossPart(_EID.MAGUS_NORTH_CAPE, 3)),
    BossID.MOTHER_BRAIN: BossScheme(
        BossPart(_EID.MOTHERBRAIN, 3),
        BossPart(_EID.DISPLAY, 6, (-0x40, -0x0F)),  # (-0x50, -0x1F) Orig
        BossPart(_EID.DISPLAY, 7, (-0x08, -0x1F)),  # (-0x20, -0x2F) Orig
        BossPart(_EID.DISPLAY, 8, (0x38, -0x0F)),  # (-0x40, -0x1F) Orig
    ),
    BossID.MUD_IMP: BossScheme(
        BossPart(_EID.MUD_IMP, 9),
        BossPart(_EID.BLUE_BEAST, 3, (0x30, 0x10)),
        BossPart(_EID.RED_BEAST, 7, (0, 0x20))
    ),
    BossID.NIZBEL: BossScheme(BossPart(_EID.NIZBEL, 3)),
    BossID.NIZBEL_2: BossScheme(BossPart(_EID.NIZBEL_II, 3)),
    BossID.RETINITE: BossScheme(
        BossPart(_EID.RETINITE, 3),
        BossPart(_EID.RETINITE_TOP, 9, (0, -0x8)),
        BossPart(_EID.RETINITE_BOTTOM, 6, (0, 0x28))
    ),
    BossID.R_SERIES: BossScheme(
        # TODO: Fix this from jets values
        BossPart(_EID.R_SERIES, 3),
        BossPart(_EID.R_SERIES, 4, (0, 0x20)),
        BossPart(_EID.R_SERIES, 7, (0x20, 0)),
        BossPart(_EID.R_SERIES, 8, (0x20, 0x20))
    ),
    BossID.RUST_TYRANO: BossScheme(BossPart(_EID.RUST_TYRANO,  3)),
    BossID.SLASH_SWORD: BossScheme(BossPart(_EID.SLASH_SWORD, 3)),
    BossID.SON_OF_SUN: BossScheme(
        BossPart(_EID.SON_OF_SUN_EYE, 3),
        BossPart(_EID.SON_OF_SUN_FLAME, 4, (-0x20, 0)),
        BossPart(_EID.SON_OF_SUN_FLAME, 5, (0x20, 0)),
        BossPart(_EID.SON_OF_SUN_FLAME, 6, (-0x10, 0x10)),
        BossPart(_EID.SON_OF_SUN_FLAME, 7, (0x10, 0x10))
    ),
    BossID.SUPER_SLASH: BossScheme(BossPart(_EID.SUPER_SLASH, 7)),
    BossID.TERRA_MUTANT: BossScheme(
        BossPart(_EID.TERRA_MUTANT_HEAD, 3),
        BossPart(_EID.TERRA_MUTANT_BOTTOM, 9)
    ),
    BossID.TWIN_BOSS: BossScheme(
        BossPart(_EID.TWIN_BOSS, 3, (-0x20, 0)),
        BossPart(_EID.TWIN_BOSS, 6, (0x20, 0))
    ),
    BossID.YAKRA: BossScheme(BossPart(_EID.YAKRA, 3)),
    BossID.YAKRA_XIII: BossScheme(BossPart(_EID.YAKRA_XIII, 3)),
    BossID.ZEAL: BossScheme(BossPart(_EID.ZEAL, 9)),
    BossID.ZEAL_2: BossScheme(
        BossPart(_EID.ZEAL_2_CENTER, 3),
        BossPart(_EID.ZEAL_2_LEFT, 6),  # Fake Coords
        BossPart(_EID.ZEAL_2_RIGHT, 9),  # Fake Coords
    ),
    BossID.ZOMBOR: BossScheme(
        BossPart(_EID.ZOMBOR_TOP, 9),
        BossPart(_EID.ZOMBOR_BOTTOM, 3, (0, 0x20))
    )
}


def get_default_scheme(boss_id: BossID) -> BossScheme:
    '''
    Associate BossID with a scheme consistent with default JoT.
    '''
    return copy.deepcopy(_default_schemes[boss_id])


def get_boss_data_dict() -> dict[BossID, BossScheme]:
    '''
    Return the default BossScheme for each BossID
    '''
    return copy.deepcopy(_default_schemes)


def get_default_boss_assignment() -> dict[BossSpotID, BossID]:
    '''
    Provides the default assignment of BossSpotID -> BossID.
    '''
    BSID = BossSpotID
    return {
        BSID.ARRIS_DOME: BossID.GUARDIAN,
        BSID.BLACK_OMEN_ELDER_SPAWN: BossID.ELDER_SPAWN,
        BSID.BLACK_OMEN_GIGA_MUTANT: BossID.GIGA_MUTANT,
        BSID.BLACK_OMEN_TERRA_MUTANT: BossID.TERRA_MUTANT,
        BSID.DEATH_PEAK: BossID.LAVOS_SPAWN,
        BSID.DENADORO_MTS: BossID.MASA_MUNE,
        BSID.EPOCH_REBORN: BossID.DALTON_PLUS,
        BSID.FACTORY_RUINS: BossID.R_SERIES,
        BSID.GENO_DOME: BossID.MOTHER_BRAIN,
        BSID.GIANTS_CLAW: BossID.RUST_TYRANO,
        BSID.HECKRAN_CAVE: BossID.HECKRAN,
        BSID.KINGS_TRIAL: BossID.YAKRA_XIII,
        BSID.MAGUS_CASTLE_FLEA: BossID.FLEA,
        BSID.MAGUS_CASTLE_SLASH: BossID.SLASH_SWORD,
        BSID.MANORIA_CATHERDAL: BossID.YAKRA,
        BSID.MT_WOE: BossID.GIGA_GAIA,
        BSID.OCEAN_PALACE_TWIN_GOLEM: BossID.GOLEM,
        BSID.OZZIES_FORT_FLEA_PLUS: BossID.FLEA_PLUS,
        BSID.OZZIES_FORT_SUPER_SLASH: BossID.SUPER_SLASH,
        BSID.PRISON_CATWALKS: BossID.DRAGON_TANK,
        BSID.REPTITE_LAIR: BossID.NIZBEL,
        BSID.SUN_PALACE: BossID.SON_OF_SUN,
        BSID.SUNKEN_DESERT: BossID.RETINITE,
        BSID.TYRANO_LAIR_NIZBEL: BossID.NIZBEL_2,
        BSID.ZEAL_PALACE: BossID.GOLEM,
        BSID.ZENAN_BRIDGE: BossID.ZOMBOR,
    }
