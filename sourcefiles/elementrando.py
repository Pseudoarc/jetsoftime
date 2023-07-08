from __future__ import annotations

import ctenums
from ctenums import Element as El, TechID as T
from techdb import TechDB
import ctstrings

import randoconfig as cfg
import randosettings as rset

def write_config(settings: rset.Settings, config: cfg.RandoConfig, rand):
    if rset.GameFlags.ELEMENT_RANDO in settings.gameflags:
        #elems = [El.LIGHTNING, El.SHADOW, El.ICE, El.FIRE]
        #doubled_elem = rand.choice(elems)
        #elems = elems + doubled_elem

        #rand.shuffle(elems) # we'll just use the order for now. crono marle lucca (skip robo) frog (skip ayla) magus
        # static right now
        elems = [El.SHADOW, El.FIRE, El.SHADOW, El.LIGHTNING, El.ICE]

        config.tech_db = shuffle_techdb(config.tech_db, elems)

def setelem(tech, elem: El):
    tech['control'][3] &= 0x0F
    if elem == El.LIGHTNING:
        tech['control'][3] |= 0x80
    elif elem == El.SHADOW:
        tech['control'][3] |= 0x40
    elif elem == El.ICE:
        tech['control'][3] |= 0x20
    elif elem == El.FIRE:
        tech['control'][3] |= 0x10
    return tech

_common = {
        'fire': '*Fire',
        'ice': '*Ice',
        'lit': '*Lightning',
        'fire2': '*Fire 2',
        'ice2': '*Ice 2',
        'lit2': '*Lightning2',
        'dmist': '*Dark Mist',
}

_l2 = {
        El.FIRE: _common['fire2'],
        El.ICE: _common['ice2'],
        El.LIGHTNING: _common['lit2'],
        El.SHADOW: _common['dmist']
}

_name_replaces = {
    T.SLASH: {
        El.SHADOW: 'DarkSlash',
        El.FIRE: 'FireSlash',
        El.ICE: 'IceSlash'
    },
    T.LIGHTNING: {
        El.SHADOW: '*DarkBolt',
        El.FIRE: _common['fire'],
        El.ICE: _common['ice']
    },
    T.LIGHTNING_2: {
        El.SHADOW: '*DarkBolt 2',
        El.FIRE: _common['fire2'],
        El.ICE: _common['ice2']
    },
    T.LUMINAIRE: {
        El.SHADOW: '*Darkinaire',
        El.FIRE: '*Flaire',
        El.ICE: '*Iceinaire'
    },

    T.ICE: {
        El.SHADOW: '*DrkCrystal',
        El.FIRE: _common['fire'],
        El.LIGHTNING: _common['lit']
    },
    T.ICE_2: _l2,

    T.FLAME_TOSS: {
        El.SHADOW: 'Dark Toss',
        El.ICE: 'Ice Toss',
        El.LIGHTNING: 'LightToss'
    },
    T.FIRE: {
        El.SHADOW: '*Dark Fire',
        El.ICE: _common['ice'],
        El.LIGHTNING: _common['lit']
    },
    T.NAPALM: {
        El.SHADOW: '*Dark Bomb',
        El.ICE: 'WtrBalloon',
        El.LIGHTNING: 'LghtGrenade'
    },
    T.FIRE_2: _l2,
    T.MEGABOMB: {
        El.SHADOW: 'OmegaBomb',
        El.ICE: 'Ice Bomb',
        El.LIGHTNING: 'LightBomb'
    },
    T.FLARE: {
        El.SHADOW: '*DarkMatter',
        El.ICE: '*Iceburst',
        El.LIGHTNING: '*Lumiflare'
    },

    T.WATER: {
        El.SHADOW: '*DarkSplash',
        El.FIRE: _common['fire'],
        El.LIGHTNING: _common['lit']
    },
    T.WATER_2: _l2,

    T.DARK_BOMB: {
        El.FIRE: 'Napalm',
        El.ICE: 'WtrBalloon',
        El.LIGHTNING: 'LightBomb'
    },
    T.DARK_MIST: _l2,
    T.DARK_MATTER: {
        El.FIRE: '*Red Matter',
        El.ICE: '*Hecks Mist',
        El.LIGHTNING: '*LghtMatter'
    },

    T.ICE_2_M: _l2,
    T.FIRE_2_M: _l2,
    T.LIGHTNING_2_M: _l2,
}

def replace_elem(db, techid, elem: El):
    tech = db.get_tech(techid)
    name = _name_replaces.get(techid, {}).get(elem, None)
    if name is not None:
        tech['name'] = ctstrings.CTNameString.from_string(name, TechDB.name_size)
    tech = setelem(tech, elem)
    db.set_tech(tech, techid)

def replace_elems(db, techids, elem: El):
    for techid in techids:
        replace_elem(db, techid, elem)

def shuffle_techdb(orig_db, elems):
    # TODO: double/triple techs
    # crono
    if elems[0] != El.LIGHTNING:
        replace_elems(orig_db,
                [T.SLASH, T.LIGHTNING, T.LIGHTNING_2, T.LUMINAIRE],
                elems[0])
    # marle
    if elems[1] != El.ICE:
        replace_elems(orig_db,
                [T.ICE, T.ICE_2],
                elems[1])
    # lucca
    if elems[2] != El.FIRE:
        replace_elems(orig_db,
                [T.FLAME_TOSS, T.FIRE, T.NAPALM, T.FIRE_2, T.MEGABOMB, T.FLARE],
                elems[2])
    # frog
    if elems[3] != El.ICE:
        replace_elems(orig_db,
                [T.WATER, T.WATER_2],
                elems[3])
    # magus
    if elems[4] != El.SHADOW:
        replace_elems(orig_db,
                [T.DARK_BOMB, T.DARK_MIST, T.DARK_MATTER],
                elems[4])

        # replace the lv2 spell for the new element with a weak dark mist
        if elems[4] == El.ICE:
            to_replace_lv2 = T.ICE_2_M
        elif elems[4] == El.FIRE:
            to_replace_lv2 = T.FIRE_2_M
        elif elems[4] == El.LIGHTNING:
            to_replace_lv2 = T.LIGHTNING_2_M
        replace_elem(orig_db, to_replace_lv2, El.SHADOW)

    '''
    ice sword/2 -> fire sword/2
    fire whirl -> dark whirl
    fire sword/2 -> dark sword/2
    swordstream -> (lightning)
    spire -> DarkSpire (lol)
    (no marle/lucca changes right now)
    ice water -> (shadow)
    glacier -> (shadow)
    red pin -> black pin
    line bomb -> shadow
    frog flare -> deep frog
    delta force/delta storm -> no change
    arc impulse -> flame arc/photon arc/shadow arc (type from marle)
    '''

    return orig_db
