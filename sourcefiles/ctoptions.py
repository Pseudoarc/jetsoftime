'''
Module for preconfiguring in-game options at compile time
'''
from typing import TYPE_CHECKING, Dict, Optional

import byteops
from ctenums import ActionMap, InputMap
from ctrom import CTRom
from ctevent import FSWriteType

if TYPE_CHECKING:
    import randosettings as rset

class ControllerBinds:
    '''
    Class to provide utilities to control button binds.
    
    CT uses bitmasks stored in a known order to implement button mapping.
    The action is controlled by the index in the array.
    The button to which the action is bound is controlled by the value of the indexed byte
    
    During vblank (and inside an NMI), the functions at 0x0284EC (rearranger) and 0x028545 (translator)
    rearrange the raw data from the SNES's joypad registers such that all buttons are on the low byte and all
    d-pad input is on the high byte, and additional addresses are written according to the user's bindings.
    These addresses are referenced depending on what the game needs to check for, actions or specific buttons,
    and whether the game needs to check for a held button, a pressed button that requires releasing before
    accepting more input, or how long the user has pressed the button.
    
    The Start button is never allowed to be rebound. All eight actions will still need to be mapped, thus
    one button will always trigger two actions (or conversely, two actions will always have the same button bound to them)
    
    CT uses four copies of the button mapping in RAM at any one time:
        The in-use copy, used by 0x028585 and therefore everywhere that respects user binds; 0x7E2993
        
        The persistent user copy, saved from RAM to SRAM when the user saves the game; 0x7E0408
        
        A cache of the persistent user copy, exists when user is editing binds ; 0x7E9890
        
        User proposed copy, edited when user is rebinding and checked against the cached copy
        to prevent undesired lack of actions being bound to a button. ; 0x7E0f00
        
    Strategy:
        Save a copy of vanilla binds in freespace
        Repoint function to copy vanilla or custom binds to new vanilla binds location
        Overwrite vanilla binds storage offset with custom binds
        
    Produces effects:
        Vanilla binds accessible at runtime via disabling Custom Control Pad.
        Load screen respects user binds.
        Runtime user binds are editable and saved to SRAM when game is saved.
        Runtime user binds can be reset to generation time user binds.
    '''

    BUTTONS_OFFSET = 0x02FCA9
    BUTTONS_LENGTH = 8

    def __init__(self, data: Optional[bytearray] = None):

        self.mappings = self.get_vanilla()
        
        if data is None:
            return

        self.update_from_bytes(data[-8:])

    @staticmethod
    def get_vanilla():

        ret = {
            ActionMap.CONFIRM: InputMap.A_BUTTON,
            ActionMap.CANCEL: InputMap.B_BUTTON,
            ActionMap.MENU: InputMap.X_BUTTON,
            ActionMap.DASH: InputMap.B_BUTTON,
            ActionMap.MAP: InputMap.SELECT_BUTTON,
            ActionMap.WARP: InputMap.Y_BUTTON,
            ActionMap.PG_UP: InputMap.R_SHOULDER,
            ActionMap.PG_DN: InputMap.L_SHOULDER
        }
        
        return ret
    
    @staticmethod
    def is_valid_mappings(binds: dict) -> bool:
        '''
        Checks provided dictionary for invalid settings.
        Rationale: Avoid unrecoverable states in game (trapped in a menu, unable to separate binds)

        Criteria:
            Cancel and Dash are mirrored, as vanilla.
            All buttons are assigned to at least one action.

        Params:
            binds: Dict. See get_vanilla() for expected structure.
                Unexpected keys are filtered out and therefore ignored.
                
        Return: False if criteria are not met. True otherwise.
        '''

        try:
            check = {x: binds[x] for x in ActionMap}
        except KeyError:
            return False

        assigned = [y for x, y in check.items()]
           
        # All buttons are assigned to at least one action.
        for x in InputMap:
            if ( 1 <= assigned.count(x) <= 2 ):
                continue

            return False
            
        # Cancel and Dash are not the same.
        if check[ActionMap.CANCEL] != check[ActionMap.DASH]:
            return False
        
        return True
        
    @classmethod
    def from_rom(cls, ctrom: CTRom, offset: int = BUTTONS_OFFSET):
        rom = ctrom.rom_data
        
        rom.seek(offset)
        data = rom.read(cls.BUTTONS_LENGTH)

        return cls(bytearray(data))


    def to_bytearray(self, data = None):
        '''
        Return bytearray in order CT expects it in, suitable for writing back to CTRom
        Optionally, accept an iterable of ints to write in its stead. Order of input not checked.
        '''
        ret = bytearray(8)

        if data is None:
            data = [self.mappings[x] for x in ActionMap]
        
        for idx, button in enumerate(data):
            ret[idx] = button
                
        return ret

    def update_from_bytes(self, byte_data: bytearray):
        '''
        Updates button bindings in place given bytearray; bytearray assumed to be ordered in the same way as out
        
        '''
        if not (8 <= len(byte_data) <= 11):
            return

        byte_data = byte_data[-8:]

        for idx, byte in zip(ActionMap, byte_data):
            for input_id in InputMap:
                if byte == input_id:
                    self.mappings[idx] = input_id
                    break
    
    def reset_to_vanilla(self):
        '''
        Restore vanilla settings, in place.
        '''
        self.mappings = self.get_vanilla()

    def write_routine_offsets(self, ctrom: CTRom):
        '''
        Repoint routine to control default/custom user binds to point to saved copy of vanilla binds
        
        Strategy:
            Save a copy of vanilla binds in freespace
            Repoint function to copy vanilla or custom binds to 0x7E2993 to read vanilla binds from freespace offset
            Overwrite vanilla binds storage offset with custom binds
            
        Combined with forcing Custom Control Pad to True if binds are different, produces the effect:
            New games start with custom binds. Loaded save games with previous runtime modifications are not affected.
            Load screen respects custom binds.
            User is capable of rebinding controls in game, resetting to generation time binds, or swapping back to vanilla.
        '''
        
        rom = ctrom.rom_data
        space_man = rom.space_manager

        binds = self.to_bytearray(self.get_vanilla().values())

        start = space_man.get_free_addr(len(binds))
        rom_start = byteops.to_rom_ptr(start)
        
        rom_start_addr = byteops.to_little_endian(rom_start & 0x00FFFF, 2)
        rom_start_bank = (rom_start >> 16).to_bytes(1, 'little')
        
        #source addr (LDX)
        rom.seek(0x02C558 + 1)
        rom.write(rom_start_addr)
        
        #source bank (MVN)
        rom.seek(0x02C561 + 2)
        rom.write(rom_start_bank)

        rom.seek(start)
        rom.write(binds, FSWriteType.MARK_USED)

    def __str__(self):
        ret = ''
            
        ret += f'Confirm: {self.mappings[ActionMap.CONFIRM]}' + '\n'
        ret += f'Cancel: {self.mappings[ActionMap.CANCEL]}' + '\n'
        ret += f'Menu: {self.mappings[ActionMap.MENU]}' + '\n'
        ret += f'Dash: {self.mappings[ActionMap.DASH]}' + '\n'
        ret += f'Map: {self.mappings[ActionMap.MAP]}' + '\n'
        ret += f'Warp: {self.mappings[ActionMap.WARP]}' + '\n'
        ret += f'Pg Dn: {self.mappings[ActionMap.PG_DN]}' + '\n'
        ret += f'Pg Up: {self.mappings[ActionMap.PG_UP]}'
        
        return ret

    def __iter__(self):
        return iter(self.mappings.items())


#default clamp to 0-1 (boolean)
def bit_prop(index, mask, clamp: int = 1):
    def getter(self):
        return self.get_byte(index, mask)

    def setter(self, val):
        self.set_byte(val, index, clamp, mask)

    return property(getter, setter)

class CTOpts:

    CONFIG_OFFSET = 0x02FCA6
    CONFIG_LENGTH = 3
    
    def __init__(self,  data: Optional[bytearray] = None):
                
        self._data = self.get_vanilla()
        self.controller_binds = ControllerBinds()
        self.consistent_paging = False
        
        if data is None:
            return
        
        self.update_from_bytes(data)
        self.controller_binds.update_from_bytes(data)

        
    @staticmethod
    def get_vanilla():
    
        ret = bytearray([
            0x84, #Battle Speed 4, Stereo Audio, Standard Controls, Save Menu Cursor off, Wait Battle Mode, Skill/Item Info On
            0xa0, #Menu Background 0, Battle Message Speed 4, Save Battle Cursor off, Save Skill/Item Cursor on
            0x01, #Battle Gauge Style 1
        ])
        
        return ret
    
    #Read provided CTRom, get config
    @classmethod
    def from_rom(cls, ctrom: CTRom, offset: int = CONFIG_OFFSET):
        rom = ctrom.rom_data

        rom.seek(offset)
        data = rom.read(cls.CONFIG_LENGTH)
    
        return bytearray(data)

    #write current configuration to provided CTRom
    def write_to_ctrom(self, ctrom: CTRom, offset: int = CONFIG_OFFSET):
        
        self.custom_control_pad = False # update the custom controller option if different from vanilla
        
        out = self.to_bytearray()
        binds = self.controller_binds.to_bytearray()
        
        ctrom.rom_data.seek(offset)
        ctrom.rom_data.write(out + binds)

        if self.menu_background != 0:
            self.set_save_slot_background_hook(ctrom)
        
        if self.custom_control_pad:
            self.controller_binds.write_routine_offsets(ctrom)
            
        if self.consistent_paging:
            self.make_page_up_down_consistent(ctrom)
    
    
    def update_from_bytes(self, data: bytearray):
        self._data[:3] = data[:3]
        
    #Returns all bytes of config, suitable for writing back to CTRom
    def to_bytearray(self):
        return bytearray(self._data)

    def get_byte(self, index, mask: int = 0xFF) -> int:
        '''
        Get the bits specified by mask of the given byte.
        The set bits of mask must be contiguous, else unpredictable behavior.
        '''
        val = self._data[index] & mask
        return val >> byteops.get_minimal_shift(mask)

    def set_byte(self, val: int, index, clamp, mask: int = 0xFF):
        inv_mask = 0xFF - mask
        self._data[index] &= inv_mask
        self._data[index] |= sorted((0, val, clamp))[1] << byteops.get_minimal_shift(mask)
    
    #definitions of properties

    #weird because description in game describes as stereo output, should remain consistent
    #Bit clear == stereo output, bit set == mono output
    @property
    def stereo_audio(self):
        return not(self.get_byte(0, 0x08))
        
    @stereo_audio.setter
    def stereo_audio(self, val):
        self.set_byte(not(val), 0, 1, 0x08)
    
    #Bit clear == standard controls, bit set == custom controls
    @property
    def custom_control_pad(self):
        return self.get_byte(0, 0x10)
        
    @custom_control_pad.setter
    #Force the custom controller on if it deviates from vanilla settings
    def custom_control_pad(self, val):
        if self.controller_binds.to_bytearray() != self.controller_binds.to_bytearray(self.controller_binds.get_vanilla().values()):
            self.set_byte(True, 0, 1, 0x10)
            return

        self.set_byte(val, 0, 1, 0x10)

    #Range, 0-7
    battle_speed = bit_prop(0, 0x07, 7)
   
    #Bit clear == Menu always starts on equipment, bit set == Menu saves position
    save_menu_cursor = bit_prop(0, 0x20)
    
    #Bit clear == battle mode is Wait, bit set == battle mode is Active
    active_battle = bit_prop(0, 0x40)
    
    #Bit clear == in battle, tech and item descriptions are not displayed, bit set == in battle, tech and item descriptions are displayed
    skill_item_info = bit_prop(0, 0x80)

    #Index, 0-7
    menu_background = bit_prop(1, 0x07, 7)
    
    #Range, 0-7
    battle_msg_speed = bit_prop(1, 0x38, 7)
    
    #Bit clear == in battle, cursor always starts on Att. for each PC, bit set == cursor position is saved for each PC
    save_battle_cursor = bit_prop(1, 0x40)

    #Bit clear == tech and inventory cursors are not kept, bit set == tech cursors for each PC, and one for item inventory, are kept
    save_tech_cursor = bit_prop(1, 0x80)

    #Range, 0-2
    battle_gauge_style = bit_prop(2, 0x03, 2)
        
        
    def set_save_slot_background_hook(self, ctrom: CTRom):

        '''
        Add hook to include empty save slots in default menu background.

        The subroutine to clear memory for entering the menu zeroes out the memory region used to store the menu background index of each save slot.
        
        The subroutine to render the save slots on the boot menu and save menus only reads SRAM for save data if the checksum passes.
        
        If the checksum for a save slot fails, the index remains at 0, causing the renderer subroutine to read 00 as the menu background index
        resulting in the default grey background.
        
        Entry condition from 0x02D2A6, save slot render subroutine:
            A and X/Y are 16 bits wide
            X and Y both contain nothing we want to keep
            $79 contains current save slot
            Z and C are clear
        '''
        
        val = self.menu_background
        rom = ctrom.rom_data
        space_man = rom.space_manager

        vanilla = bytearray.fromhex(
            'A5 78'            # LDA $78
            '29 00 03'         # AND #$0300
        )

        rom.seek(0x02D2A6)
        
        hooked = rom.read(5) != vanilla

        #TODO: allow editing of already-extant hooked subroutine; use case: reconfiguring a ROM for which one does not have the settings object and seed / sharelink
        
        if hooked:
            return
        
        bg = bytearray.fromhex(
            'E2 30'            # SEP #$30 ; set A and X/Y to 8 bits; clears high byte of X/Y
            'AD 0C 02'         # LDA $020C ; check if slot has no data, will be 1A if there is no data or invalid data in the save slot
            'C9 1A'            # CMP #$1A ; known value
            'D0 07'            # BNE exit
           f'A9 {val:02x}'     # LDA #${new_value} ; Could do LDA $C2FCA7 and then AND #$07 here, but that consumes runtime clocks for no extra benefit
            'A6 79'            # LDX $79 ; get current save slot from memory, 16 bits wide
            '9D 79 0D'         # STA $0D79, X
            'C2 33'            # REP #$33 [exit]; reset A and X/Y to 16 bits, clear carry and zero flags, same as entry condition
            'A5 78'            # LDA $78
            '29 00 03'         # AND #$0300
            '6B'               # RTL
        )
        
        start = space_man.get_same_bank_free_addrs([len(bg)])
        rom_start = byteops.to_rom_ptr(start[0])
        rom_start_bytes = rom_start.to_bytes(3, 'little')
        jsl = b'\x22' + rom_start_bytes
        
        nop = b'\xEA'
        
        rom.seek(0x02D2A6)
        rom.write(jsl + nop)

        rom.seek(start[0])
        rom.write(bg, FSWriteType.MARK_USED)
        
    def __str__(self):
        
        ret = ''
        ret += f'Battle Speed: {self.battle_speed + 1}' + '\n'
        ret += f'Stereo Audio: {self.stereo_audio}' + '\n'
        ret += f'Custom Controls: {bool(self.custom_control_pad)}' + '\n'
        ret += f'Save Menu Cursor: {bool(self.save_menu_cursor)}' + '\n'
        ret += f'Active Battle: {bool(self.active_battle)}' + '\n'
        ret += f'Skill/Item Info: {bool(self.skill_item_info)}' + '\n'
        ret += f'Menu Background: {self.menu_background + 1}' + '\n'
        ret += f'Battle Message Speed: {self.battle_msg_speed + 1}' + '\n'
        ret += f'Save Battle Cursor: {bool(self.save_battle_cursor)}' + '\n'
        ret += f'Save Skill/Item Cursor: {bool(self.save_tech_cursor)}' + '\n'
        ret += f'Battle Gauge Style: {self.battle_gauge_style}' + '\n'
        ret += f'Consistent Paging: {bool(self.consistent_paging)}'
        
        return ret

    def __eq__(self, other) -> bool:
        return all(getattr(other, key, None) == value for key, value in self)

    def __iter__(self):
        
        ret = {
            'battle_speed': self.battle_speed,
            'stereo_audio': self.stereo_audio,
            'custom_control_pad': self.custom_control_pad,
            'save_menu_cursor': self.save_menu_cursor,
            'active_battle': self.active_battle,
            'skill_item_info': self.skill_item_info,
            'menu_background': self.menu_background,
            'battle_msg_speed': self.battle_msg_speed,
            'save_battle_cursor': self.save_battle_cursor,
            'save_tech_cursor': self.save_tech_cursor,
            'battle_gauge_style': self.battle_gauge_style,
            'consistent_paging': self.consistent_paging
        }

        return iter(ret.items())

    def make_page_up_down_consistent(self, ctrom: CTRom):
        '''
        Modify bit checks to test the opposite bits in inventory scrolls to flip effects of Pg Dn/Up

        Default behavior of Pg Up/Dn is inconsistent. In most scrollable menus (inventory, shops),
        and in the battle inventory menu, (Pg Up / R) scrolls up, and (Pg Dn / L) scrolls down.
        This is in contrast to the actions performing decrement (Pg Dn / L) / increment (Pg Up / R) of 
        character indices during equipment select, or pastwards (Pg Dn / L) / futurewards (Pg Up / R)
        on the Epoch time gauge.
        
        This hurts my brain, so go fix it to make scrolling menus consistent with other uses of Pg Dn and Pg Up.
        
        Trivia: This would result in having to rename ActionMap keys, but ActionMap is as vanilla.
        '''

        rom = ctrom.rom_data
        
        '''
        The menu program does not directly read the input rearrange and translate bytes
        Input collator function 0x02E987 collates Confirm, Cancel, Pg Dn and Pg Up into 0x7E0D1D ,
        for use with BMI and BVS opcodes for efficient checking of the two most common inputs.

        #Used for basically everywhere inside shops, menu (including techs), and inventory.
        '''
        rom.seek(0x0293C9 + 1) # BIT $02
        rom.write(0x01.to_bytes(1, 'little'))

        '''
        Battle inventory scrolling is handled by a different subroutine than menu inventory scrolling.
        It does not collate input like the menu program, and instead isolates bitmasks of translated input
        sourced from $fb and $fc. The function of note 0x01143D controls input during Item menu.
        Overwrite the checks to reverse their effects.
        '''
        rom.seek(0x011477 + 1) # AND #$20
        rom.write(0x10.to_bytes(1, 'little'))
        
        rom.seek(0x011483 + 1) # AND #$10
        rom.write(0x20.to_bytes(1, 'little'))

    def to_jot_json(self) -> Dict[str, 'rset.JSONPrimitive']:
        return {k: v for k, v in self}
        

if __name__ == '__main__':
    pass
