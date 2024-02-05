# Python libraries
from __future__ import annotations
import random as rand

from typing import List


# jets of time libraries
import logicfactory
import logictypes

import ctenums
import randoconfig as cfg
import randosettings as rset

#
# This script file implements the Chronosanity logic.
# It uses a weighted random distribution to place key items
# based on logical access rules per location.  Any baseline key
# item location that does not get a key item assigned to it will
# be assigned a random treasure.
#

# Script variables
locationGroups: List[logictypes.LocationGroup] = []


#
# Get a list of LocationGroups that are available for key item placement.
#
# param: game - Game object used to determine location access
#
# return: List of all available LocationGroups
#
def getAvailableLocations(game: logictypes.Game) -> List[logictypes.LocationGroup]:
  # Have the game object update what characters are available based on the
  # currently available items and time periods.
  game.updateAvailableCharacters()
  
  # Get a list of all accessible location groups
  accessibleLocationGroups = []
  for locationGroup in locationGroups:
    if locationGroup.canAccess(game):
      if locationGroup.getAvailableLocationCount() > 0:
        accessibleLocationGroups.append(locationGroup)
  
  return accessibleLocationGroups
  
# end getAvailableLocations

#
# Given a list of LocationGroups, get a random location.
#
# param: groups - List of LocationGroups
#
# return: The LocationGroup the Location was chosen from
# return: A Location randomly chosen from the groups list
#
def getRandomLocation(groups):
  # get the max rand value from the combined weightings of the location groups
  # This will be used to help select a location group
  weightTotal = 0
  for group in groups:
    weightTotal = weightTotal + group.getWeight()
  
  # Select a location group
  locationChoice = rand.randint(1, weightTotal)
  counter = 0
  chosenGroup = None
  for group in groups:
    counter = counter + group.getWeight()
    if counter >= locationChoice:
      chosenGroup = group
      break
    
  # Select a random location from the chosen location group.
  location = rand.choice(chosenGroup.getLocations())
  
  return chosenGroup, location
# end getRandomLocation

#
# Given a weighted list of key items, get a shuffled
# version of the list with only a single copy of each item.
#
# param: weightedList - Weighted key item list
#
# return: Shuffled list of key items with duplicates removed
#
def getShuffledKeyItemList(weightedList):
  tempList = weightedList.copy()

  # In the shuffle, higher weighted items have a better chance of appearing
  # before lower weighted items.
  rand.shuffle(tempList)
  
  keyItemList = []
  for keyItem in tempList:
    if not (keyItem in keyItemList):
      keyItemList.append(keyItem)
  
  return keyItemList
# end getShuffledKeyItemList

#
# Randomly place key items.
#
# param: gameConfig A GameConfig object with the configuration information
#                   necessary to place keys for the selected game type
#
# return: A tuple containing:
#             A Boolean indicating whether or not key item placement was successful
#             A list of locations with key items assigned
#
def determineKeyItemPlacement(gameConfig):
  global locationGroups
  locationGroups = gameConfig.getLocations()
  # game = gameConfig.getGame()
  remainingKeyItems = gameConfig.getKeyItemList()
  chosenLocations = []
  return determineKeyItemPlacement_impl(chosenLocations,
                                        remainingKeyItems, gameConfig)
# end place_key_items


#
# NOTE: Do not call this function directly. This will be called
#       by determineKeyItemPlacement after setting up the parameters
#       needed by this function.
#
# This function will recursively determine key item locations
# such that a seed can be 100% completed.  This uses a weighted random
# approach to placement and will only consider logically accessible locations.
#
# The algorithm for determining locations - For each recursion:
#   If there are no key items remaining, unwind the recursion, otherwise
#     Get a list of logically accessible locations
#     Choose a location randomly (locations are weighted)
#     Get a shuffled list of the remaining key items
#     Loop through the key item list, trying each one in the chosen location
#       Recurse and try the next location/key item
#     
#
# param: chosenLocations - List of locations already chosen for key items
# param: remainingKeyItems - List of key items remaining to be placed
# param: gameConfig - GameConfig object used to determine logic.  In particular
#                     this contains a Game object which determines the logic
#                     while the GameConfig itself has rules for how the keyItem
#                     items may change over time.
# TODO:  Should this pass two parameters? Game and updateKeyItems function?
#        It's weird using the Game member of GameConfig.
#
# return: A tuple containing:
#             A Boolean indicating whether or not key item placement was
#             successful
#
#             A list of locations with key items assigned
#
def determineKeyItemPlacement_impl(chosenLocations,
                                   remainingKeyItems,
                                   gameConfig):
  if len(remainingKeyItems) == 0:
    # We've placed all key items.  This is our breakout condition
    return True, chosenLocations
  else:
    # We still have key items to place.
    availableLocations = getAvailableLocations(gameConfig.getGame())
    if len(availableLocations) == 0:
      # This item configuration is not completable. 
      return False, chosenLocations
    else:
      # Continue placing key items.
      keyItemConfirmed = False
      returnedChosenLocations = None
      
      # Choose a random location
      locationGroup, location = getRandomLocation(availableLocations)
      locationGroup.removeLocation(location)
      locationGroup.decayWeight()
      chosenLocations.append(location)
      
      # Sometimes key item bias is removed after N checks
      gameConfig.updateKeyItems(remainingKeyItems)

      # Use the weighted key item list to get a list of key items
      # that we can loop through and attempt to place.
      localKeyItemList = getShuffledKeyItemList(remainingKeyItems)
      for keyItem in localKeyItemList:
        # Try placing this key item and then recurse
        location.setKeyItem(keyItem)
        gameConfig.getGame().addKeyItem(keyItem)
        
        newKeyItemList = [x for x in remainingKeyItems if x != keyItem]
        # recurse and try to place the next key item.
        keyItemConfirmed, returnedChosenLocations = \
            determineKeyItemPlacement_impl(chosenLocations,
                                           newKeyItemList,
                                           gameConfig)
        
        if keyItemConfirmed:
          # We're unwinding the recursion here, all key items are placed.
          return keyItemConfirmed, returnedChosenLocations
        else:
          gameConfig.getGame().removeKeyItem(keyItem)
      # end keyItem loop
      
      # If we get here, we failed to place an item.  Undo location modifications
      locationGroup.addLocation(location)
      locationGroup.undoWeightDecay()
      chosenLocations.remove(location)
      location.unsetKeyItem()
      
      return False, chosenLocations

# end determineKeyItemPlacement_impl recursive function

#
# Write out the spoiler log.
#
# param: chosenLocations - List of locations containing key items
# param: charLocations - Dictionary of locations to characters
#
def writeSpoilerLog(chosenLocations, charLocations):
  spoilerLog = open("spoiler_log.txt","w+")
  # Write the key item location to the spoiler log
  
  spoilerLog.write("Key ItemLocations:\n")
  for location in chosenLocations:
    spoilerLog.write("  " +
                     location.getName() + ": " +
                     location.getKeyItem().name + "\n")

  # Write the character locations to the spoiler log
  spoilerLog.write("\n\nCharacter Locations:\n")
  for loc, char in charLocations.items():
    character = char.held_char
    spoilerLog.write("  " + str(loc) + ": " + str(character) + "\n")
  spoilerLog.close()


#
# Determine key item placements and write them to the provided ROM file.
# Additionally, a spoiler log is written that lists where the key items and
# characters were placed.
#
# param: settings - randomizer settings including gameflags (rset.Settings)
# param: config - currently determined randomizer output (cfg.RandoConfig)
#
def commitKeyItems(settings: rset.Settings,
                   config: cfg.RandoConfig):

    charLocations = config.char_assign_dict

    # Get a game configuration for the provided flags
    gameConfig = logicfactory.getGameConfig(settings, config)

    # Determine placements for the key items
    success, chosenLocations = determineKeyItemPlacement(gameConfig)

    if not success:
        print("Unable to place key items.")
        return

    # Write key items to the config
    for location in chosenLocations:
        location.writeKeyItem(config)

    additional_locs = []
    # Go through any baseline locations not assigned an item and place a
    # piece of treasure. Treasure quality is based on the location's loot tier.
    for locationGroup in locationGroups:
        for location in locationGroup.getLocations():
            if isinstance(location, logictypes.BaselineLocation) and \
               (location not in chosenLocations):

                # This is a baseline location without a key item.
                # Assign a piece of treasure if it has none.
                if location.getKeyItem() in (None,
                                             ctenums.ItemID.NONE,
                                             ctenums.ItemID.MOP):
                    location.writeRandomItem(config)

                # Always list the BaselineLocations for spoiler purposes
                additional_locs.append(location)

    config.key_item_locations = chosenLocations + additional_locs
    # writeSpoilerLog(chosenLocations, charLocations)


def main():
    pass


if __name__ == '__main__':
    main()
