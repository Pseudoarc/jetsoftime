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
    excluded_mobs = [EnemyID.PANEL, EnemyID.LASER_GUARD, EnemyID.NU, EnemyID.NU_2,
                     EnemyID.BLUE_SHIELD, EnemyID.YODU_DE, EnemyID.INCOGNITO, EnemyID.PEEPINGDOOM]
    excluded_locations = [LocID.TRUCE_INN_1000,LocID.CRONOS_KITCHEN,LocID.CREDITS_4, LocID.CRONOS_ROOM, # Locations have purple reptite due to Reptite Alt Ending.  Easier to exclude them
                          LocID.CREDITS_4, # End credits has a scouter.  Easier to exclude it
                          LocID.HECKRAN_CAVE_PASSAGEWAYS] # Get color crash here in this location, need to understand why
    enemy_loc_dict = {}
    enemy_pool = {}
    for location in LocID:

        if location in excluded_locations:
            # Exclude some locations.
            # These locations register mobs which aren't real, but also don't have an enemy index >10
            # These locations don't have any mobs in general, easier to exclude them all together
            continue
        
        try:
            script = ct_rom.script_manager.get_script(location)
            pos = script.get_object_start(0)
        except:
            print(location)
            break

        enemy_loc_dict[location] = []
        while True:
            pos,cmd = script.find_command_opt([0x83],pos)
            
            if pos == None:
                break

            cmd_start = pos
            cmd_end = cmd_start + len(cmd)
            enemy_id = EnemyID(cmd.args[0])
            enemy_index = cmd.args[1]
            pos = cmd_end
            if enemy_id not in list(MobID) or enemy_id in excluded_mobs or enemy_index > 10:
                # Only include enemies which are considered mobs
                # Exclude some mobs from getting randomized.  These are ones which are integral to some scenes
                # Also, shields need to be excluded for now since they are two seperate enemies.  Maybe replace them with something else?
                # Any enemy which has an index greater then 10 isn't a real mob
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