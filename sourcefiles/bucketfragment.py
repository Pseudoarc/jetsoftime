import random

from ctrom import CTRom
import ctenums
import ctevent
import ctstrings
import logicfactory
import logictypes
import randosettings as rset
import randoconfig as cfg
import xpscale


# TODO: there are no references to this function in the codebase
# might be WIP or could be something to remove
def set_bucket_function(ctrom: CTRom, settings: rset.Settings):
    script_man = ctrom.script_manager
    eot_script = script_man.get_script(ctenums.LocID.END_OF_TIME)

    new_eot_script = ctevent.Event.from_flux('./flux/bucket_eot.Flux')

    # TODO: below is only reference to "needed_fragements" in codebase
    # not sure what it should default to but that should be updated in randosettings
    # if this should be used
    num_fragments = getattr(settings.bucket_settings, 'needed_fragments', 0)

    start = new_eot_script.get_function_start(0x09, 1)
    end = new_eot_script.get_function_end(0x09, 1)

    # Find the GetItemAmount command (0xD7) as the new start
    start, _ = new_eot_script.find_command([0xD7], start, end)

    # find the if item_count >= amt
    pos, cmd = new_eot_script.find_command([0x12], start, end)
    new_eot_script.data[pos+2] = num_fragments

    # find the temp = amt
    pos, cmd = new_eot_script.find_command([0x4F], start, end)
    new_eot_script.data[pos+1] = num_fragments

    # find the two textbox commands, and add their strings to the eot script
    pos_text = start
    for i in range(2):
        pos_text, text_cmd = new_eot_script.find_command([0xBB, 0xC1, 0xC2],
                                                         pos_text, end)
        str_ind = text_cmd.args[0]
        new_string = new_eot_script.strings[str_ind]

        eot_script.strings.append(new_string)
        new_string_ind = len(eot_script.strings)-1

        new_eot_script.data[pos_text+1] = new_string_ind

        pos_text += len(text_cmd)

    eot_script.modified_strings = True
    func = new_eot_script.get_function(0x09, 0x01)
    eot_script.set_function(0x09, 0x01, func)

    xpscale.double_xp(ctrom)


def set_fragment_properties(ctrom: CTRom):

    # Let's just set the name to 'Fragment'
    frag_name = ctstrings.CTString.from_str('Fragment', False)

    # first byte is used to put a little icon if needed.  For key items
    # this gets set to FF.
    frag_name = b'\xFF'+frag_name

    item_name_st = 0x0C0B5E
    item_name_len = 0xB

    frag_name_st = item_name_st + ctenums.ItemID.BUCKETFRAG*item_name_len
    ctrom.rom_data.seek(frag_name_st)
    ctrom.rom_data.write(frag_name)


def write_fragments_to_config(
        num_fragments: int,
        settings: rset.Settings,
        config: cfg.RandoConfig,
        ):
    item_db = config.item_db

    # 0xFF is a space instead of an item type icon
    item_db[ctenums.ItemID.BUCKETFRAG].name = \
        ctstrings.CTNameString.from_string(' Fragment', 0xB)

    # Working with Chronosanity locations instead of raw TreasureIDs because
    #   1) We're only putting fragments in Chronosanity locations, and
    #   2) We have to deal with the linked location/pyramid

    # Grab the locations where key items have been placed.
    key_items = config.key_item_locations

    # Make a flags + chronosanity game config to get all assignable locations
    orig_flags = settings.gameflags
    settings.gameflags |= rset.GameFlags.CHRONOSANITY
    game_config = logicfactory.getGameConfig(settings, config)
    settings.gameflags = orig_flags

    loc_groups = game_config.locationGroups

    LocationGroup = logictypes.LocationGroup
    Location = logictypes.Location
    TID = ctenums.TreasureID

    # These locations are not in Chronosanity but they can get fragments
    desertLocations = LocationGroup("Sunken Desert", 0, lambda x: True)
    (
        desertLocations
        .addLocation(Location(TID.SUNKEN_DESERT_B1_NE))
        .addLocation(Location(TID.SUNKEN_DESERT_B1_NW))
        .addLocation(Location(TID.SUNKEN_DESERT_B1_SE))
        .addLocation(Location(TID.SUNKEN_DESERT_B1_SW))
        .addLocation(Location(TID.SUNKEN_DESERT_B2_CENTER))
        .addLocation(Location(TID.SUNKEN_DESERT_B2_E))
        .addLocation(Location(TID.SUNKEN_DESERT_B2_N))
        .addLocation(Location(TID.SUNKEN_DESERT_B2_NW))
        .addLocation(Location(TID.SUNKEN_DESERT_B2_SE))
        .addLocation(Location(TID.SUNKEN_DESERT_B2_SW))
    )

    prisonLocations = LocationGroup("Guardia Prison", 0, lambda x: True)
    (
        prisonLocations
        .addLocation(Location(TID.GUARDIA_JAIL_CELL))
        .addLocation(Location(TID.GUARDIA_JAIL_FRITZ))
        .addLocation(Location(TID.GUARDIA_JAIL_FRITZ_STORAGE))
        .addLocation(Location(TID.GUARDIA_JAIL_HOLE_1))
        .addLocation(Location(TID.GUARDIA_JAIL_HOLE_2))
        .addLocation(Location(TID.GUARDIA_JAIL_OMNICRONE_1))
        .addLocation(Location(TID.GUARDIA_JAIL_OMNICRONE_2))
        .addLocation(Location(TID.GUARDIA_JAIL_OMNICRONE_3))
        .addLocation(Location(TID.GUARDIA_JAIL_OMNICRONE_4))
        .addLocation(Location(TID.GUARDIA_JAIL_OUTER_WALL))
    )

    loc_groups.append(desertLocations)
    loc_groups.append(prisonLocations)

    all_locs = [loc for group in loc_groups for loc in group.locations]

    # This is dangerous, but it should be OK since names are all generated
    # automatically.
    # TODO: write an __eq__ for locations that checks if the underlying
    #       TreasureIDs are equal.  For now, we check getName() equality.
    key_loc_names = [loc.getName() for loc in key_items]

    # for name in key_loc_names:
    #     print(name)

    # print('****')
    avail_locs = [loc for loc in all_locs
                  if loc.getName() not in key_loc_names]

    # for x in avail_locs:
    #     print(x.getName())

    # print('****')
    fragment_locs = random.sample(avail_locs, num_fragments)

    for x in fragment_locs:
        # print(f'Putting fragment in {x.getName()}')
        x.setKeyItem(ctenums.ItemID.BUCKETFRAG)
        x.writeKeyItem(config)
