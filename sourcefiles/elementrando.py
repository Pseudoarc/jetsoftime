from __future__ import annotations

import charrando as dc

import ctenums

import randoconfig as cfg
import randosettings as rset

def write_config(settings: rset.Settings, config: cfg.RandoConfig, rand):
    if rset.GameFlags.ELEMENT_RANDO in settings.gameflags:
        #elems = [ctenums.Element.LIGHTNING, ctenums.Element.SHADOW, ctenums.Element.ICE, ctenums.Element.FIRE]
        #doubled_elem = rand.choice(elems)
        #elems = elems + doubled_elem

        #rand.shuffle(elems) # we'll just use the order for now. crono marle lucca (skip robo) frog (skip ayla) magus
        # static right now
        elems = [ctenums.Element.SHADOW, ctenums.Element.FIRE, ctenums.Element.SHADOW, ctenums.Element.LIGHTNING, ctenums.Element.ICE]

        config.tech_db = shuffle_techdb(config.tech_db, elems)

def setelem(tech, elem: ctenums.Element):
    tech['control'][3] &= 0x0F
    if elem == ctenums.Element.LIGHTNING:
        tech['control'][3] |= 0x80
    elif elem == ctenums.Element.SHADOW:
        tech['control'][3] |= 0x40
    elif elem == ctenums.Element.ICE:
        tech['control'][3] |= 0x20
    elif elem == ctenums.Element.FIRE:
        tech['control'][3] |= 0x10
    return tech

_name_replaces = {
    ctenums.TechID.SLASH: {
        ctenums.Element.SHADOW: 'DarkSlash',
        ctenums.Element.FIRE: '',
        ctenums.Element.ICE: ''
    },
    ctenums.TechID.LIGHTNING: {
        ctenums.Element.SHADOW: 'DarkBolt',
        ctenums.Element.FIRE: '',
        ctenums.Element.ICE: ''
    },
    ctenums.TechID.LIGHTNING_2: {
        ctenums.Element.SHADOW: 'DarkBolt II',
        ctenums.Element.FIRE: '',
        ctenums.Element.ICE: ''
    },
    ctenums.TechID.LUMINAIRE: {
        ctenums.Element.SHADOW: 'Darkinaire',
        ctenums.Element.FIRE: '',
        ctenums.Element.ICE: ''
    },

    ctenums.TechID.ICE: {
        ctenums.Element.SHADOW: '',
        ctenums.Element.FIRE: 'Fire',
        ctenums.Element.LIGHTNING: ''
    },
    ctenums.TechID.ICE_2: {
        ctenums.Element.SHADOW: '',
        ctenums.Element.FIRE: 'Fire II',
        ctenums.Element.LIGHTNING: ''
    },

    ctenums.TechID.FLAME_TOSS: {
        ctenums.Element.SHADOW: 'Dark Toss',
        ctenums.Element.ICE: '',
        ctenums.Element.LIGHTNING: ''
    },
    ctenums.TechID.FIRE: {
        ctenums.Element.SHADOW: 'Dark Fire',
        ctenums.Element.ICE: '',
        ctenums.Element.LIGHTNING: ''
    },
    ctenums.TechID.NAPALM: {
        ctenums.Element.SHADOW: 'Dark Bomb',
        ctenums.Element.ICE: '',
        ctenums.Element.LIGHTNING: ''
    },
    ctenums.TechID.FIRE_2: {
        ctenums.Element.SHADOW: 'Dark Mist',
        ctenums.Element.ICE: '',
        ctenums.Element.LIGHTNING: ''
    },
    ctenums.TechID.MEGABOMB: {
        ctenums.Element.SHADOW: 'OmegaBomb',
        ctenums.Element.ICE: '',
        ctenums.Element.LIGHTNING: ''
    },
    ctenums.TechID.FLARE: {
        ctenums.Element.SHADOW: 'DarkMatter',
        ctenums.Element.ICE: '',
        ctenums.Element.LIGHTNING: ''
    },

    ctenums.TechID.WATER: {
        ctenums.Element.SHADOW: '',
        ctenums.Element.FIRE: '',
        ctenums.Element.LIGHTNING: 'Lightning'
    },
    ctenums.TechID.WATER_2: {
        ctenums.Element.SHADOW: '',
        ctenums.Element.FIRE: '',
        ctenums.Element.LIGHTNING: 'LghtningII'
    },

    ctenums.TechID.DARK_BOMB: {
        ctenums.Element.FIRE: '',
        ctenums.Element.ICE: 'WaterBomb',
        ctenums.Element.LIGHTNING: ''
    },
    ctenums.TechID.DARK_MIST: {
        ctenums.Element.FIRE: '',
        ctenums.Element.ICE: 'Ice II',
        ctenums.Element.LIGHTNING: ''
    },
    ctenums.TechID.DARK_MATTER: {
        ctenums.Element.FIRE: '',
        ctenums.Element.ICE: 'Hecks Mist',
        ctenums.Element.LIGHTNING: ''
    },

    ctenums.TechID.ICE_2_M: {
        ctenums.Element.SHADOW: 'Dark Mist'
    },
    ctenums.TechID.FIRE_2_M: {
        ctenums.Element.SHADOW: 'Dark Mist'
    },
    ctenums.TechID.LIGHTNING_2_M: {
        ctenums.Element.SHADOW: 'Dark Mist'
    }
}

def replace_elem(db, techid, elem: ctenums.Element):
    tech = db.get_tech(techid)
    name = _name_replaces.get(techid, {}).get(elem, None)
    if name is not None:
        tech['name'] = dc.get_ct_name(name)
    tech = setelem(tech, elem)
    db.set_tech(tech, techid)

def replace_elems(db, techids, elem: ctenums.Element):
    for techid in techids:
        replace_elem(db, techid, elem)

def shuffle_techdb(orig_db, elems):
    # TODO: double/triple techs
    # crono
    if elems[0] != ctenums.Element.LIGHTNING:
        replace_elems(orig_db,
                [ctenums.TechID.SLASH, ctenums.TechID.LIGHTNING, ctenums.TechID.LIGHTNING_2, ctenums.TechID.LUMINAIRE],
                elems[0])
    # marle
    if elems[1] != ctenums.Element.ICE:
        replace_elems(orig_db,
                [ctenums.TechID.ICE, ctenums.TechID.ICE_2],
                elems[1])
    # lucca
    if elems[2] != ctenums.Element.FIRE:
        replace_elems(orig_db,
                [ctenums.TechID.FLAME_TOSS, ctenums.TechID.FIRE, ctenums.TechID.NAPALM, ctenums.TechID.FIRE_2, ctenums.TechID.MEGABOMB, ctenums.TechID.FLARE],
                elems[2])
    # frog
    if elems[3] != ctenums.Element.ICE:
        replace_elems(orig_db,
                [ctenums.TechID.WATER, ctenums.TechID.WATER_2],
                elems[3])
    # magus
    if elems[4] != ctenums.Element.SHADOW:
        replace_elems(orig_db,
                [ctenums.TechID.DARK_BOMB, ctenums.TechID.DARK_MIST, ctenums.TechID.DARK_MATTER],
                elems[4])

        # replace the lv2 spell for the new element with a weak dark mist
        if elems[4] == ctenums.Element.ICE:
            to_replace_lv2 = ctenums.TechID.ICE_2_M
        elif elems[4] == ctenums.Element.FIRE:
            to_replace_lv2 = ctenums.TechID.FIRE_2_M
        elif elems[4] == ctenums.Element.LIGHTNING:
            to_replace_lv2 = ctenums.TechID.LIGHTNING_2_M
        replace_elem(orig_db, to_replace_lv2, ctenums.Element.SHADOW)

    return orig_db
