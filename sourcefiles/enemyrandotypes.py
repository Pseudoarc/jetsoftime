'''
This module contains enumerations for bosses and boss spots and some functions
describing the default relationship between them.
'''

from __future__ import annotations

import copy
import enum
import typing
import random
import ctrom

from ctenums import EnemyID, MobID, LocID

def enemy_type_rando( ct_rom: ctrom.CTRom,):
    excluded_mobs = [EnemyID.PANEL, EnemyID.LASER_GUARD, EnemyID.NU, EnemyID.NU_2]
    enemy_loc_dict = {}
    enemy_pool = {}
    for location in LocID:
        pos = 0
        enemy_loc_dict[location] = []

        while True:
            script = ct_rom.script_manager.get_script(location)
            pos,cmd = script.find_command_opt([0x83],pos)
            
            if pos == None:
                break

            cmd_start = pos
            cmd_end = cmd_start + len(cmd)
            enemy_id = EnemyID(cmd.args[0])
            enemy_index = cmd.args[1]
            pos = cmd_end
            header_enemies = [EnemyID.HENCH_PURPLE,EnemyID.TERRASAUR,EnemyID.KILWALA,EnemyID.REPTITE_PURPLE,
                              EnemyID.OMICRONE,EnemyID.MARTELLO,EnemyID.REPTITE_GREEN]
            if enemy_id not in list(MobID) or enemy_id in excluded_mobs or ( enemy_id in header_enemies and cmd_start < 1100):
                    continue
            
            enemy_data = [cmd, cmd_start, cmd_end, enemy_id, enemy_index]                                   
            enemy_loc_dict[location].append(enemy_data)
            enemy_pool = {enemy_id, *enemy_pool}

        if not enemy_loc_dict[location]:
            del  enemy_loc_dict[location]


    enemy_pool_random = list(enemy_pool)
    random.shuffle(enemy_pool_random)
    enemy_assignments = {enemy:assignment for enemy, assignment in zip(enemy_pool, enemy_pool_random)}

    for location, enemy_data in enemy_loc_dict.items():
        script = ct_rom.script_manager.get_script(location)
        for cmd, cmd_start, cmd_end, enemy_id, enemy_index in enemy_data:
            cmd.args[0] = enemy_assignments[enemy_id]
            script.data[cmd_start:cmd_end] = cmd.to_bytearray()