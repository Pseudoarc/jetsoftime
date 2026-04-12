import ctenums

import randoconfig as cfg
import randosettings as rset
from common.random import RNGType


def randomize_magus(settings: rset.Settings, config:cfg.RandoConfig,
                    rng: RNGType):
    CharID = ctenums.CharID
    EnemyID = ctenums.EnemyID

    # Magus
    magus_char = rng.choice(list(CharID))

    magus_nukes = {
        CharID.CRONO: 0xBB,
        CharID.MARLE: 0x91,
        CharID.LUCCA: 0xA9,
        CharID.ROBO: 0xBB,
        CharID.FROG: 0xA9,
        CharID.AYLA: 0x8E,
        CharID.MAGUS: 0x6B
    }

    base_nuke_id = magus_nukes[magus_char]

    dm = config.enemy_atkdb.get_tech(0x6B)
    new_nuke = config.enemy_atkdb.get_tech(base_nuke_id)
    new_nuke.effect.power = dm.effect.power

    nuke_strs = {
        CharID.CRONO: 'Luminaire / Crono\'s strongest attack!',
        CharID.MARLE: 'Hexagon Mist /Marle\'s strongest attack!',
        CharID.LUCCA: 'Flare / Lucca\'s strongest attack!',
        CharID.ROBO: 'Luminaire /Robo\'s strongest attack!',
        CharID.FROG: 'Hexagon Mist /Frog\'s strongest attack.',
        CharID.AYLA: 'Energy Flare /Ayla\'s strongest attack!',
        CharID.MAGUS: 'Dark Matter / Magus\' strongest attack!',
    }

    new_nuke_id = config.enemy_aidb.unused_techs[-1]
    config.enemy_atkdb.set_tech(new_nuke, new_nuke_id)

    magus_ai = config.enemy_aidb.scripts[EnemyID.MAGUS]
    magus_ai.change_tech_usage(0x6B, new_nuke_id)

    battle_msgs = config.enemy_aidb.battle_msgs
    battle_msgs.set_msg_from_str(0x23, nuke_strs[magus_char])

    config.enemy_dict[EnemyID.MAGUS].name = str(magus_char)


def set_black_tyrano_element(config: cfg.RandoConfig):
    pass 
