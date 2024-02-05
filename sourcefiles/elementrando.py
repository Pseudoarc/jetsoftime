from __future__ import annotations

from typing import Dict
import re

import byteops
from asm import instructions as inst
from asm.instructions import AddressingMode as AM
from asm import assemble
import ctenums
import ctrom
from freespace import FSWriteType as FSW
from ctenums import Element as El, TechID as T, LocID as L, CharID as C
from techdb import TechDB
import ctstrings

import randoconfig as cfg
import randosettings as rset

def write_config(settings: rset.Settings, config: cfg.RandoConfig, rand):
    if rset.GameFlags.ELEMENT_RANDO in settings.gameflags:
        elems = [El.LIGHTNING, El.SHADOW, El.ICE, El.FIRE]
        doubled_elem = rand.choice(elems)

        roboelems = list(set(elems) - {doubled_elem,})
        elems = elems + [doubled_elem]
            
        # These are just keyed by order:
        # crono marle lucca (skip robo) frog (skip ayla) magus
        # laser spin, area bomb, shock for robo
        rand.shuffle(elems) 
        rand.shuffle(roboelems)

        for i, elem in enumerate(elems):
            real_i = i
            if i == 3:
                real_i = 4
            elif i == 4:
                real_i = 6
            statblock = config.pcstats.pc_stat_dict[C(real_i)].stat_block
            statblock.innate_element_resisted = elem

        config.elems = elems + roboelems
        config.tech_db = shuffle_techdb(config.tech_db, elems, roboelems)


def update_element_placards_on_ctrom(ct_rom: ctrom.CTRom, config: cfg.RandoConfig):
    """
    Update the element graphics on each PC's stats page in the menu to show the randomized element.
    Call this after charrando because its changes need to be overwritten.
    """

    if not config.elems:
        return

    # The relevant code is:
    # $C2/A27C BF C6 A2 C2 LDA $C2A2C6,x[$C2:A2C6]
    # X has the pc-index which needs to be reeassigned

    # These are indices computed from looking at the $C2A6C6 range
    elem_index_dict: dict[ctenums.Element, int] = {
        ctenums.Element.LIGHTNING: 0,
        ctenums.Element.FIRE: 6,
        ctenums.Element.ICE: 4,
        ctenums.Element.SHADOW: 2,
        ctenums.Element.NONELEMENTAL: 8
    }

    char_elem_dict: dict[ctenums.CharID, ctenums.Element] = {
        ctenums.CharID.CRONO: config.elems[0],
        ctenums.CharID.MARLE: config.elems[1],
        ctenums.CharID.LUCCA: config.elems[2],
        ctenums.CharID.FROG: config.elems[3],
        ctenums.CharID.MAGUS: config.elems[4],
        ctenums.CharID.ROBO: ctenums.Element.NONELEMENTAL,
        ctenums.CharID.AYLA: ctenums.Element.NONELEMENTAL
    }

    reassign_dict = {
        pc_id: config.pcstats.get_character_assignment(pc_id)
        for pc_id in ctenums.CharID
    }

    char_index_b = bytes(
        [elem_index_dict[char_elem_dict[reassign_dict[pc_id]]]
         for pc_id in ctenums.CharID]
    )

    # Possibly you can overwrite the $C2A2C6,x range, but we'll just
    # Grab 7 bytes from somewhere else.
    rom = ct_rom.rom_data
    space_man = ct_rom.rom_data.space_manager
    char_index_addr = space_man.get_free_addr(len(char_index_b))

    rom.seek(char_index_addr)
    rom.write(char_index_b, FSW.MARK_USED)

    routine: assemble.ASMList = [
        inst.LDA(byteops.to_rom_ptr(char_index_addr), AM.LNG_X)
    ]
    routine_b = assemble.assemble(routine)

    # fix menu magic type picture

    rom.seek(0x02A27C)
    rom.write(routine_b)  # Replacing 4 bytes for 4 bytes.





def update_ctrom(ct_rom: ctrom.CTRom, config: cfg.RandoConfig):
    update_scripts(ct_rom, config)


def update_scripts(ct_rom: ctrom.CTRom, config: cfg.RandoConfig):
    if len(config.elems) > 0:
        spekkio_script = ct_rom.script_manager.get_script(L.SPEKKIO)

        for i, barr in enumerate(spekkio_script.strings):
            string = ctstrings.CTString(barr).to_ascii() 
            newstr = None
            if re.search(r'punk hairdo', string) is not None: # Crono
                newstr = re.sub('Lightning', str(config.elems[0]), string)
            elif re.search(r'ponytail', string) is not None: # Marle
                newstr = re.sub('Water', str(config.elems[1]), string)
            elif re.search(r'goofy glasses', string) is not None: # Lucca
                newstr = re.sub('Fire', str(config.elems[2]), string)
            elif re.search(r'biggest toy', string) is not None: # Robo
                newstr = 'SPEKKIO: That\'s the biggest toy I\'ve{line break}ever seen...{line break}Hey, you\'re not alive, are you?!{page break}You\'ve got great strength, however,{line break}since I can\'t measure your inner{line break}character, I can\'t give any magic to{line break}you.{page break}But your various weapons will suffice.{line break}They can inflict many types{line break}of damage.{null}'
            elif re.search(r'a frog', string) is not None: # Frog
                newstr = re.sub('Water', str(config.elems[3]), string)
            elif re.search(r'Sweetheart', string) is not None: # Ayla
                pass # no changes for ayla
            elif re.search(r'marlin', string) is not None: # Magus
                newstr = re.sub('Shadow', str(config.elems[4]), string)

            if newstr is not None:
                spekkio_script.strings[i] = ctstrings.CTString.from_str(newstr)
                spekkio_script.modified_strings = True

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

# TechID: {Element: {'name': 'NewName', 'gfx': {4: 0x63, 5: 0x98 etc.}}}
_replacements: Dict = {
    T.SLASH: {
        El.SHADOW: {'name': 'DarkSlash', 'gfx': {4: 0x25}},
        El.FIRE:   {'name': 'FireSlash', 'gfx': {4: 0x13}},
        El.ICE:    {'name': 'IceSlash', 'gfx': {4: 0x3a}}
    },
    T.LIGHTNING: {
        El.SHADOW: {'name': '*DarkBolt', 'gfx': {4: 0x25, 5: 0x07}},
        El.FIRE: {'name': _common['fire'], 'gfx': {4: 0x13, 5: 0x0A}},
        El.ICE: {'name': _common['ice'], 'gfx': {4: 0x3A, 5: 0x03, 6: 0x2D}}
    },
    T.LIGHTNING_2: {
        El.SHADOW: {'name': '*DarkBolt 2', 'gfx': {4: 0x25, 5: 0x06, 6: 0x2F}},
        El.FIRE: {'name': _common['fire2'], 'gfx': {4: 0x13, 6: 0x1C}},
        El.ICE: {'name': _common['ice2'], 'gfx': {4: 0x3A, 6: 0x32}}
    },
    T.LUMINAIRE: {
        El.SHADOW: {'name': '*Darkinaire', 'gfx': {6: 0x1E}},
        El.FIRE: {'name': '*Flaire', 'gfx': {0: 0x04, 6: 0x0D}},
        El.ICE: {'name': '*Iceinaire', 'gfx': {0: 0x03, 1: 0xFC, 2: 0x00, 3: 0x00, 4: 0x3A, 5: 0x00, 6: 0x17}}
    },

    T.ICE: {
        El.SHADOW: {'name': '*DrkCrystal', 'gfx': {4: 0x25, 6: 0x33}},
        El.FIRE: {'name': _common['fire'], 'gfx': {4: 0x13, 6: 0x15}},
        El.LIGHTNING: {'name': _common['lit'], 'gfx': {4: 0x02, 6: 0x10}}
    },
    T.ICE_2: {
        El.FIRE: {'name': _common['fire2'], 'gfx': {4: 0x13, 6: 0x1c}},
        El.LIGHTNING: {'name': _common['lit2'], 'gfx': {4: 0x03, 6: 0x02}},
        El.SHADOW: {'name': _common['dmist'], 'gfx': {4: 0x25, 6: 0x2F}}
    },

    T.FLAME_TOSS: {
        El.SHADOW: {'name': 'Dark Toss', 'gfx': {4: 0x25}},
        El.ICE: {'name': 'Ice Toss', 'gfx': {4: 0x3A}},
        El.LIGHTNING: {'name': 'LightToss', 'gfx': {4: 0x03}}
    },
    T.FIRE: {
        El.SHADOW: {'name': '*Dark Fire', 'gfx': {4: 0x25}},
        El.ICE: {'name': _common['ice'], 'gfx': {4: 0x3A}},
        El.LIGHTNING: {'name': _common['lit'], 'gfx': {4: 0x03}}
    },
    T.NAPALM: {
        El.SHADOW: {'name': '*Dark Bomb', 'gfx': {4: 0x25, 6: 0x21}},
        El.ICE: {'name': 'WtrBalloon', 'gfx': {4: 0x3A, 6: 0x53}},
        El.LIGHTNING: {'name': 'LghtGrenade', 'gfx': {4: 0x03, 6: 0x2C}}
    },
    T.FIRE_2: {
        El.ICE: {'name':_common['ice2'], 'gfx': {4: 0x3A, 6: 0x57}},
        El.LIGHTNING: {'name': _common['lit2'], 'gfx': {4: 0x03, 6: 0x02}},
        El.SHADOW: {'name': _common['dmist'], 'gfx': {4: 0x25, 6: 0x2F}}
    },
    T.MEGABOMB: {
        El.SHADOW: {'name': 'OmegaBomb', 'gfx': {4: 0x25, 6: 0x06}},
        El.ICE: {'name': 'Ice Bomb', 'gfx': {4: 0x3A, 6: 0x27}},
        El.LIGHTNING: {'name': 'LightBomb', 'gfx': {4: 0x03, 6: 0x29}}
    },
    T.FLARE: {
        El.SHADOW: {'name': '*DarkMatter', 'gfx': {0: 0x16, 4: 0x34, 6: 0x1E}},
        El.ICE: {'name': '*Iceburst', 'gfx': {0: 0x16, 4: 0x3A, 6: 0x32}},
        El.LIGHTNING: {'name': '*Lumiflare', 'gfx': {0: 0x16, 4: 0x03, 6: 0x01}}
    },

    T.WATER: {
        El.SHADOW: {'name': '*DarkSplash', 'gfx': {4: 0x25, 5: 0x25}},
        El.FIRE: {'name': _common['fire'], 'gfx': {4: 0x11, 5: 0x03}},
        El.LIGHTNING: {'name': _common['lit'], 'gfx': {4: 0x03, 5: 0x03}}
    },
    T.WATER_2: {
        El.FIRE: {'name': _common['fire2'], 'gfx': {4: 0x13, 6: 0x1c}},
        El.LIGHTNING: {'name': _common['lit2'], 'gfx': {4: 0x03, 6: 0x02}},
        El.SHADOW: {'name': _common['dmist'], 'gfx': {4: 0x25, 6: 0x2F}}
    },

    T.DARK_BOMB: {
        El.FIRE: {'name': 'Napalm', 'gfx': {6: 0x49}},
        El.ICE: {'name': 'WtrBalloon', 'gfx': {6: 0x53}},
        El.LIGHTNING: {'name': 'LightBomb', 'gfx': {6: 0x2C}}
    },
    T.DARK_MIST: {
        El.ICE: {'name':_common['ice2'], 'gfx': {4: 0x3A, 6: 0x57}},
        El.FIRE: {'name': _common['fire2'], 'gfx': {4: 0x13, 6: 0x1c}},
        El.LIGHTNING: {'name': _common['lit2'], 'gfx': {4: 0x03, 6: 0x02}},
        El.SHADOW: {'name': _common['dmist'], 'gfx': {4: 0x25, 6: 0x2F}}
    },
    T.DARK_MATTER: {
        El.FIRE: {'name': '*Flare', 'gfx': {6: 0x0D}},
        El.ICE: {'name': '*Hex Mist', 'gfx': {0: 0x34, 6: 0x17}},
        El.LIGHTNING: {'name': '*Luminaire', 'gfx': {6: 0x01}}
    },

    T.ICE_2_M: {
        El.ICE: {'name':_common['ice2'], 'gfx': {4: 0x3A, 6: 0x57}},
        El.FIRE: {'name': _common['fire2'], 'gfx': {4: 0x13, 6: 0x1c}},
        El.LIGHTNING: {'name': _common['lit2'], 'gfx': {4: 0x03, 6: 0x02}},
        El.SHADOW: {'name': _common['dmist'], 'gfx': {4: 0x25, 6: 0x2F}}
    },
    T.FIRE_2_M: {
        El.ICE: {'name':_common['ice2'], 'gfx': {4: 0x3A, 6: 0x57}},
        El.FIRE: {'name': _common['fire2'], 'gfx': {4: 0x13, 6: 0x1c}},
        El.LIGHTNING: {'name': _common['lit2'], 'gfx': {4: 0x03, 6: 0x02}},
        El.SHADOW: {'name': _common['dmist'], 'gfx': {4: 0x25, 6: 0x2F}}
    },
    T.LIGHTNING_2_M: {
        El.ICE: {'name':_common['ice2'], 'gfx': {4: 0x3A, 6: 0x57}},
        El.FIRE: {'name': _common['fire2'], 'gfx': {4: 0x13, 6: 0x1c}},
        El.LIGHTNING: {'name': _common['lit2'], 'gfx': {4: 0x03, 6: 0x02}},
        El.SHADOW: {'name': _common['dmist'], 'gfx': {4: 0x25, 6: 0x2F}}
    },

    T.LASER_SPIN: {
        El.ICE: {'name': 'Ice Spin', 'gfx': {6: 0x24}},
        El.FIRE: {'name': 'Fire Spin', 'gfx': {6: 0x4F}},
        El.LIGHTNING: {'name': 'LightSpin', 'gfx': {6: 0x3D}}
    },
    T.AREA_BOMB: {
        El.ICE: {'name': 'Ice Burst', 'gfx': {4: 0x3A}},
        El.LIGHTNING: {'name': 'FlashBomb', 'gfx': {4: 0x03, 6: 0x02}},
        El.SHADOW: {'name': 'DarkBurst', 'gfx': {4: 0x25}}
    },
    T.SHOCK: {
        El.ICE: {'name': 'Freeze', 'gfx': {6: 0x32}},
        El.FIRE: {'name': 'Immolate', 'gfx': {6: 0x62}},
        El.SHADOW: {'name': 'Obscure', 'gfx': {6: 0x64}}
    },

    T.DOUBLE_BOMB: {
        El.SHADOW: {'name': "OmegaDBomb"},
        El.ICE: {'name': "IceWtrBomb"},
        El.LIGHTNING: {'name': "VoltBomb"}
    },

    T.SPIRE: {
        El.SHADOW: {'name': 'DarkSpire'},
        El.ICE: {'name': 'IceSpire'},
        El.FIRE: {'name': 'FlameSpire'}
    },
    T.VOLT_BITE: {
        El.SHADOW: {'name': 'Dark Bite'},
        El.ICE: {'name': 'Ice Bite'},
        El.FIRE: {'name': 'Flame Bite'}
    },
    T.ICE_SWORD: {
        El.SHADOW: {'name': 'Dark Sword'},
        El.ICE: {'name': 'Ice Sword'},
        El.FIRE: {'name': 'Fire Sword'},
        El.LIGHTNING: {'name': 'Light Sword'}
    },
    T.ICE_SWORD_2: {
        El.SHADOW: {'name': 'Dark Sword 2'},
        El.ICE: {'name': 'Ice Sword 2'},
        El.FIRE: {'name': 'Fire Sword 2'},
        El.LIGHTNING: {'name': 'Light Sword 2'}
    },
    T.ICE_TACKLE: {
        El.SHADOW: {'name': 'Dark Tackle'},
        El.ICE: {'name': 'Ice Tackle'},
        El.FIRE: {'name': 'Fire Tackle'},
        El.LIGHTNING: {'name': 'LightTackle'}
    },
    T.ICE_TOSS: {
        El.SHADOW: {'name': 'ShdwToss'},
        El.FIRE: {'name': 'Fire Toss'},
        El.LIGHTNING: {'name': 'Light Toss'}
    },
    T.CUBE_TOSS: {
        El.SHADOW: {'name': 'Dark Toss'},
        El.FIRE: {'name': 'Blaze Toss'},
        El.LIGHTNING: {'name': 'Shock Toss'}
    },
    T.ARC_IMPULSE: {
        El.SHADOW: {'name': 'DarkImpulse'},
        El.FIRE: {'name': 'FireImpulse'},
        El.LIGHTNING: {'name': 'LghtImpulse'}
    },
    T.FIRE_WHIRL: {
        El.SHADOW: {'name': 'ShdwWhirl'},
        El.ICE: {'name': 'Ice Whirl'},
        El.LIGHTNING: {'name': 'Light Whirl'}
    },
    T.FIRE_SWORD: {
        El.SHADOW: {'name': 'Dark Sword'},
        El.ICE: {'name': 'Ice Sword'},
        El.FIRE: {'name': 'Fire Sword'},
        El.LIGHTNING: {'name': 'Light Sword'}
    },
    T.FIRE_SWORD_2: {
        El.SHADOW: {'name': 'Dark Sword 2'},
        El.ICE: {'name': 'Ice Sword 2'},
        El.FIRE: {'name': 'Fire Sword 2'},
        El.LIGHTNING: {'name': 'Light Sword 2'}
    },
    T.FIRE_PUNCH: {
        El.SHADOW: {'name': 'Dark Punch'},
        El.ICE: {'name': 'Ice Punch'},
        El.LIGHTNING: {'name': 'Light Punch'}
    },
    T.FIRE_TACKLE: {
        El.SHADOW: {'name': 'Dark Tackle'},
        El.ICE: {'name': 'Ice Tackle'},
        El.FIRE: {'name': 'Fire Tackle'},
        El.LIGHTNING: {'name': 'LightTackle'}
    },
    T.RED_PIN: {
        El.SHADOW: {'name': 'Dark Pin'},
        El.ICE: {'name': 'Ice Pin'},
        El.LIGHTNING: {'name': 'Light Pin'}
    },
    T.LINE_BOMB: {
        El.SHADOW: {'name': 'Dark Line'},
        El.ICE: {'name': 'Ice Line'},
        El.LIGHTNING: {'name': 'Shock Line'}
    },
    T.FROG_FLARE: {
        El.SHADOW: {'name': 'FrogMatter'},
        El.ICE: {'name': 'Frog Mist'},
        El.LIGHTNING: {'name': 'Froginaire'}
    },
    T.FLAME_KICK: {
        El.SHADOW: {'name': 'Shadow Kick'},
        El.ICE: {'name': 'Ice Kick'},
        El.LIGHTNING: {'name': 'Light Kick'}
    },
    T.BLAZE_TWISTER: {
        El.SHADOW: {'name': 'Dark Whirl'},
        El.ICE: {'name': 'FreezeWhirl'},
        El.LIGHTNING: {'name': 'Shock Whirl'}
    },
    T.BLAZE_KICK: {
        El.SHADOW: {'name': 'Dark Kick'},
        El.ICE: {'name': 'FreezeKick'},
        El.LIGHTNING: {'name': 'Shock Kick'}
    },
    T.FIRE_ZONE: {
        El.SHADOW: {'name': 'Dark Zone'},
        El.ICE: {'name': 'Ice Zone'},
        El.LIGHTNING: {'name': 'Shock Zone'}
    },
    T.SWORD_STREAM: {
        El.SHADOW: {'name': 'Dark Sword'},
        El.FIRE: {'name': 'Sword Flame'},
        El.LIGHTNING: {'name': 'Sword Bolt'}
    },
    T.ROCKET_ROLL: {
        El.ICE: {'name': 'Ice Roll'},
        El.FIRE: {'name': 'Flame Roll'},
        El.LIGHTNING: {'name': 'Light Roll'}
    },
    T.TWISTER: {
        El.ICE: {'name': 'IceTwist'},
        El.FIRE: {'name': 'FlameTwist'},
        El.LIGHTNING: {'name': 'LightTwist'}
    },
    T.SUPER_VOLT: {
        El.SHADOW: {'name': 'ShadowVolt'},
        El.ICE: {'name': 'Ice Volt'},
        El.FIRE: {'name': 'Fire Volt'}
    },
    T.ANTIPODE: {
        El.ICE: {'name': 'Icepode'},
        El.FIRE: {'name': 'Firepode'},
        El.LIGHTNING: {'name': 'Lightpode'}
    },
    T.ANTIPODE_2: {
        El.ICE: {'name': 'Icepode 2'},
        El.FIRE: {'name': 'Firepode 2'},
        El.LIGHTNING: {'name': 'Lightpode 2'}
    },
    T.ANTIPODE_3: {
        El.ICE: {'name': 'Icepode 3'},
        El.FIRE: {'name': 'Firepode 3'},
        El.LIGHTNING: {'name': 'Lightpode 3'}
    },
    T.ICE_WATER: {
        El.SHADOW: {'name': 'Shadow Dark'},
        El.FIRE: {'name': 'Flame Blaze'},
        El.LIGHTNING: {'name': 'Light Shock'}
    },
    T.GLACIER: {
        El.SHADOW: {'name': 'Dark Shadow'},
        El.FIRE: {'name': 'Blaze Flame'},
        El.LIGHTNING: {'name': 'Shock Light'}
    },
    T.FINAL_KICK: {
        El.ICE: {'name': 'GlcierKick'},
        El.FIRE: {'name': 'InfrnoKick'},
        El.LIGHTNING: {'name': 'ThnderKick'}
    },
    T.GATLING_KICK: {
        El.ICE: {'name': 'GlcierKick'},
        El.FIRE: {'name': 'InfrnoKick'},
        El.LIGHTNING: {'name': 'ThnderKick'}
    }
}

def dual_elem(first: El, second: El, clear_enabled=False) -> El:
    if first == second:
        return first
    elif first == El.ICE and second == El.LIGHTNING:
        return El.LIGHTNING
    elif first == El.LIGHTNING and second == El.ICE:
        return El.LIGHTNING
    elif first == El.LIGHTNING and second == El.SHADOW and clear_enabled:
        return El.NONELEMENTAL
    elif first == El.SHADOW and second == El.LIGHTNING and clear_enabled:
        return El.NONELEMENTAL
    else:
        return El.SHADOW

def triple_elem(first: El, second: El, third: El, clear_enabled=False) -> El:
    if first == second == third:
        return first
    elif clear_enabled and first == El.SHADOW and second == El.SHADOW and third == El.LIGHTNING:
        return El.NONELEMENTAL
    elif clear_enabled and first == El.SHADOW and second == El.LIGHTNING and third == El.SHADOW:
        return El.NONELEMENTAL
    elif clear_enabled and first == El.LIGHTNING and second == El.SHADOW and third == El.SHADOW:
        return El.NONELEMENTAL
    elif clear_enabled and first == El.LIGHTNING and second == El.LIGHTNING and third == El.SHADOW:
        return El.NONELEMENTAL
    elif clear_enabled and first == El.LIGHTNING and second == El.SHADOW and third == El.LIGHTNING:
        return El.NONELEMENTAL
    elif clear_enabled and first == El.SHADOW and second == El.LIGHTNING and third == El.LIGHTNING:
        return El.NONELEMENTAL
    else:
        return El.SHADOW

def replace_elem(db, techid, elem: El):
    tech = db.get_tech(techid)
    repl = _replacements.get(techid, {}).get(elem, None)
    if repl is not None:
        if 'name' in repl:
            tech['name'] = ctstrings.CTNameString.from_string(repl['name'], TechDB.name_size)
        if 'gfx' in repl:
            for i in range(7):
                if i in repl['gfx']:
                    tech['gfx'][i] = repl['gfx'][i]
    tech = setelem(tech, elem)
    db.set_tech(tech, techid)

def replace_elems(db, techids, elem: El):
    for techid in techids:
        replace_elem(db, techid, elem)

def shuffle_techdb(orig_db, elems, roboelems, clear_enabled=False):
    # crono
    if elems[0] != El.LIGHTNING:
        replace_elems(orig_db,
                [T.SLASH, T.LIGHTNING, T.LIGHTNING_2, T.LUMINAIRE, T.SPIRE, T.VOLT_BITE],
                elems[0])

    # marle
    if elems[1] != El.ICE:
        replace_elems(orig_db,
                [T.ICE, T.ICE_2, T.ICE_SWORD, T.ICE_SWORD_2, T.ICE_TACKLE, T.ICE_TOSS, T.CUBE_TOSS, T.ARC_IMPULSE],
                elems[1])
    # lucca
    if elems[2] != El.FIRE:
        replace_elems(orig_db,
                [T.FLAME_TOSS, T.FIRE, T.NAPALM, T.FIRE_2, T.MEGABOMB, T.FLARE, T.FIRE_WHIRL, T.FIRE_SWORD, T.FIRE_SWORD_2, T.FIRE_PUNCH, T.FIRE_TACKLE, T.RED_PIN, T.LINE_BOMB, T.FROG_FLARE, T.FLAME_KICK, T.BLAZE_TWISTER, T.BLAZE_KICK, T.FIRE_ZONE],
                elems[2])
    # frog
    if elems[3] != El.ICE:
        replace_elems(orig_db,
                [T.WATER, T.WATER_2, T.SWORD_STREAM],
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

    # robo is special, gets a set of 3 elems for Laser Spin, Area Bomb, Shock resp.
    if roboelems[0] != El.SHADOW:
        replace_elems(orig_db, [T.LASER_SPIN, T.ROCKET_ROLL, T.TWISTER], roboelems[0])

    if roboelems[1] != El.FIRE:
        replace_elem(orig_db, T.AREA_BOMB, roboelems[1])

    if roboelems[2] != El.LIGHTNING:
        replace_elem(orig_db, T.SHOCK, roboelems[2])

    # robo duals/triples
    sv_elem = dual_elem(elems[0], roboelems[2], clear_enabled)
    if sv_elem != El.LIGHTNING:
        replace_elem(orig_db, T.SUPER_VOLT, sv_elem)


    db_elem = dual_elem(elems[2], roboelems[1], clear_enabled)
    if db_elem != El.FIRE:
        replace_elem(orig_db, T.DOUBLE_BOMB, db_elem)

    anti_elem = dual_elem(elems[1], elems[2], clear_enabled)
    if anti_elem != El.SHADOW:
        replace_elems(orig_db,
                [T.ANTIPODE, T.ANTIPODE_2, T.ANTIPODE_3],
                anti_elem)

    # marle-frog techs are shadow if their elems differ, otherwise that elem
    mf_elem = dual_elem(elems[1], elems[3], clear_enabled)
    if mf_elem != El.ICE:
        replace_elems(orig_db,
                [T.ICE_WATER, T.GLACIER],
                mf_elem)

    # crono-marle final kick or crono-lucca gatling kick, if types match, become that type
    fk_elem = dual_elem(elems[0], elems[1], clear_enabled)
    if fk_elem != El.SHADOW:
        replace_elem(orig_db, T.FINAL_KICK, fk_elem)

    gk_elem = dual_elem(elems[0], elems[2], clear_enabled)
    if gk_elem != El.SHADOW:
        replace_elem(orig_db, T.GATLING_KICK, gk_elem)

    # these matter only if clear_enabled
    if clear_enabled:
        df_elem = triple_elem(elems[0], elems[1], elems[2], clear_enabled)
        if df_elem != El.SHADOW:
            replace_elem(orig_db, T.DELTA_FORCE, df_elem)

        ds_elem = triple_elem(elems[0], elems[1], elems[3], clear_enabled)
        if ds_elem != El.SHADOW:
            replace_elem(orig_db, T.DELTA_STORM, ds_elem)

        de_elem = triple_elem(elems[1], elems[2], elems[4], clear_enabled)
        if de_elem != El.SHADOW:
            replace_elem(orig_db, T.DARK_ETERNAL, de_elem)

        of_elem = triple_elem(elems[2], elems[4], roboelems[0], clear_enabled)
        if of_elem != El.SHADOW:
            replace_elem(orig_db, T.OMEGA_FLARE, of_elem)

    return orig_db
