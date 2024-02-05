from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional, Union

from randosettings import GameFlags as GF, CosmeticFlags as CF, ROFlags as RO

if TYPE_CHECKING:
    import randosettings as rset

SettingsFlags = Union['rset.GameFlags', 'rset.CosmeticFlags', 'rset.ROFlags']


@dataclass
class FlagEntry:
    name: str = ""
    short_name: Optional[str] = None
    help_text: Optional[str] = None


FLAG_ENTRY_DICT: Dict[SettingsFlags, FlagEntry] = {
    GF.FIX_GLITCH: FlagEntry(
        "--fix-glitch", "-g",
        "disable save anywhere and HP overflow glitches"),
    GF.BOSS_SCALE: FlagEntry(
        "--boss-scale", "-b",
        "scale bosses based on key-item locations"),
    GF.ZEAL_END: FlagEntry(
        "--zeal-end", "-z",
        "allow the game to be won when Zeal is defeated in the "
        "Black Omen"),
    GF.FAST_PENDANT: FlagEntry(
        "--fast-pendant", "-p",
        "the pendant will be charged when 2300 is reached"),
    GF.LOCKED_CHARS: FlagEntry(
        "--locked-chars", "-c",
        "require dreamstone for the dactyl character and factory for "
        "the Proto Dome character"),
    GF.UNLOCKED_MAGIC: FlagEntry(
        "--unlocked-magic", "-m",
        "magic is unlocked from the beginning of the game without "
        "visiting Spekkio"),
    GF.CHRONOSANITY: FlagEntry(
        "--chronosanity", "-cr",
        "key items may be found in treasure chests"),
    GF.ROCKSANITY: FlagEntry(
        "--rocksanity", None,
        "rocks are added as key items and key items may be found "
        "in rock locations"),
    GF.TAB_TREASURES: FlagEntry(
        "--tab-treasures", None,
        "all treasure chests contain tabs"),
    GF.BOSS_RANDO: FlagEntry(
        "--boss-randomization", "-ro",
        "randomize the location of bosses and scale based on location"),
    GF.CHAR_RANDO: FlagEntry(
        "--char-rando", "-rc",
        "randomize character identities and models"), 
    GF.DUPLICATE_CHARS: FlagEntry(
        "--duplicate-characters", "-dc",
        "allow multiple copies of a character to be present in a seed"),
    GF.DUPLICATE_TECHS: FlagEntry(
        "--duplicate-techs", None,
        "allow duplicate characters to perform dual techs together"),
    GF.VISIBLE_HEALTH: FlagEntry(
        "--visible-health", None,
        "the sightscope effect will always be present"),
    GF.FAST_TABS: FlagEntry(
        "--fast-tabs", None,
        "picking up a tab will not pause movement for the fanfare"),
    GF.BUCKET_LIST: FlagEntry(
        "--bucket-list", "-k",
        "allow the End of Time bucket to Lavos to activate when enough "
        "objectives have been completed."),
    GF.TECH_DAMAGE_RANDO: FlagEntry(
        "--tech-damage-rando", None,
        "Randomize the damage dealt by single techs."),
    GF.MYSTERY: FlagEntry(
        "--mystery", None,
        "choose flags randomly according to mystery settings"),
    GF.BOSS_SIGHTSCOPE: FlagEntry(
        "--boss-sightscope", None,
        "allow the sightscope to work on bosses"),
    GF.USE_ANTILIFE: FlagEntry(
        "--use-antilife", None,
        "use Anti-Life instead of Black Hole for Magus"),
    GF.TACKLE_EFFECTS_ON: FlagEntry(
        "--tackle-on-hit-effects", None,
        "allow Robo Tackle to use the on-hit effects of Robo's weapons"),
    GF.HEALING_ITEM_RANDO: FlagEntry(
        "--healing-item-rando", "-he",
        "randomizes effects of healing items"),
    GF.FREE_MENU_GLITCH: FlagEntry(
        "--free-menu-glitch", None,
        "provides a longer window to enter the menu prior to Lavos3 and "
        "Zeal2"),
    GF.GEAR_RANDO: FlagEntry(
        "--gear-rando", "-q",
        "randomizes effects on weapons, armors, and accessories"),
    GF.STARTERS_SUFFICIENT: FlagEntry(
        "--starters-sufficient", None,
        "go mode will be acheivable without recruiting additional "
        "characters"),
    GF.EPOCH_FAIL: FlagEntry(
        "--epoch-fail", "-ef",
        "Epoch flight must be unlocked by bringing the JetsOfTime to "
        "Dalton in the Snail Stop"),
    GF.ELEMENT_RANDO: FlagEntry(
        "--element-randomization", "-er",
        "The elements assigned to each character are randomized, with a "
        "random duplicated element"),
    # Boss Rando flags
    RO.BOSS_SPOT_HP: FlagEntry(
        "--boss-spot-hp", None,
        "boss HP is set to match the vanilla boss HP in each spot"),
    RO.PRESERVE_PARTS: FlagEntry(
        "--legacy-boss-placement", None,
        "use legacy boss placement for boss rando"),
    # Logic Tweak flags from VanillaRando mode
    GF.UNLOCKED_SKYGATES: FlagEntry(
        "--unlocked-skyways", None,
        "Skyways are available as soon as 12kBC is. Normal go mode is still "
        "needed to unlock the Ocean Palace."),
    GF.ADD_SUNKEEP_SPOT: FlagEntry(
        "--add-sunkeep-spot", None,
        "Adds Sun Stone as an independent key item.  Moonstone charges to a "
        "random item"),
    GF.ADD_BEKKLER_SPOT: FlagEntry(
        "--add-bekkler-spot", None,
        "C.Trigger unlocks clone game for a KI"),
    GF.ADD_CYRUS_SPOT: FlagEntry(
        "--add-cyrus-spot", None,
        "Gain a KI from Cyrus's Grave w/ Frog.  No Frog stat boost."),
    GF.RESTORE_TOOLS: FlagEntry(
        "--restore-tools", None,
        "Adds Tools. Tools will fix Norther Ruins."),
    GF.ADD_OZZIE_SPOT: FlagEntry(
        "--add-ozzie-spot", None, "Gain a KI after Ozzie's Fort."),
    GF.RESTORE_JOHNNY_RACE: FlagEntry(
        "--restore-johnny-race", None,
        "Add bike key and Johnny Race. Bike Key is required to cross Lab32."),
    GF.ADD_RACELOG_SPOT: FlagEntry(
        "--add-racelog-spot", None,
        "Gain a KI from the vanilla Race Log chest."),
    GF.REMOVE_BLACK_OMEN_SPOT: FlagEntry(
        "--remove-black-omen-spot", None,
        "Removes Black Omen rock chest being a possible KI."),
    GF.SPLIT_ARRIS_DOME: FlagEntry(
        "--split-arris-dome", None,
        "Get one key item from the dead guy after Guardian.  Get a second "
        "after checking the Arris dome computer and bringing the Seed "
        "(new KI) to Doan."),
    GF.VANILLA_ROBO_RIBBON: FlagEntry(
        "--vanilla-robo-ribbon", None,
        "Gain Robo stat boost from defeating AtroposXR.  If no Atropos in "
        "seed, then gain from Geno Dome."),
    GF.VANILLA_DESERT: FlagEntry(
        "--vanilla-desert", None,
        "The sunken desert only unlocks after talking to the plant lady "
        "in Zeal"),
    # Cosmetic Flags
    CF.AUTORUN: FlagEntry(
        "--autorun", None,
        "Automatically run.  Push run button to walk."
    ),
    CF.DEATH_PEAK_ALT_MUSIC: FlagEntry(
        "--death-peak-alt-music", None,
        "use Singing Mountain track on Death Peak"
    ),
    CF.ZENAN_ALT_MUSIC: FlagEntry(
        "--zenan-alt-music", None,
        "use alt battle theme for Zenan Bridge"
    ),
    CF.QUIET_MODE: FlagEntry(
        "--quiet", None,
        "disable all music (not sound effects)"
    ),
    CF.REDUCE_FLASH: FlagEntry(
        "--reduce-flashes", None,
        "disable most flashing effects"
    )
}
