'''Module to turn a vanilla CT Rom into an open world one...eventually'''
from typing import Optional
from asm import instructions as inst, assemble

import byteops
import ctrom
import freespace
from ctenums import LocID, ItemID
from eventcommand import EventCommand as EC
from eventfunction import EventFunction as EF
from ctevent import FunctionID as FID 


def apply_mauron_enemy_tech_patch(
        ct_rom: ctrom.CTRom,
        # local_ptr_addr: int,
        bank_table_addr: Optional[int] = None
):
    '''
    Apply Mauron's patch to allow enemy tech animation scripts to be in any
    bank.

    param ct_rom:  The CTRom to apply the patch to.
    param bank_table_addr: If not none, the lookup table for the bank table
                           will be placed at this (file) address in the rom.
    '''
    rom = ct_rom.rom_data
    FSW = ctrom.freespace.FSWriteType

    if bank_table_addr is None:
        space_man = ct_rom.rom_data.space_manager
        bank_table_addr = space_man.get_free_addr(0x100)

    bank_table_b = b'\xCD' * 0x100
    rom.seek(bank_table_addr)
    rom.write(bank_table_b, FSW.MARK_USED)

    # This is Mauron's patch which fetches the tech script address using the
    # bank table.  I'm not disassembling it except to show the bank load.
    rt = bytearray.fromhex(
        'A8 0A AA BF F0 61 CD 85 40 BB'
        'BF C6 DD CC'  # LDA $CCDDC6, X loads from the bank table
        '8542E2207BA8AAB7409581C8B7409580C8BBC00400D0F098C221654085407BA8'
        'C2200680901FADB3A0D016A9010099AC5D5A980A0AA8A74099BD5DA54299BF5D7'
        'AE640E640C8C01000D0D57BE220ADB3A0F0099CB3A0A482848080C2'
    )

    # Overwrite the bank location
    bank_table_addr_b = int.to_bytes(
        byteops.to_rom_ptr(bank_table_addr), 3, 'little'
    )
    rt[11:14] = bank_table_addr_b

    rom.seek(0x0146ED)
    rom.write(rt, FSW.NO_MARK)  # Should already be marked used.


def apply_mauron_enemy_attack_patch(
        ct_rom: ctrom.CTRom,
        # local_ptr_addr: int,
        bank_table_addr: Optional[int] = None
):
    '''
    Apply Mauron's patch to allow enemy attack animation scripts to be in any
    bank.

    param ct_rom:  The CTRom to apply the patch to.
    param bank_table_addr: If not none, the lookup table for the bank table
                           will be placed at this (file) address in the rom.
    '''

    rom = ct_rom.rom_data
    FSW = ctrom.freespace.FSWriteType

    if bank_table_addr is None:
        space_man = ct_rom.rom_data.space_manager
        bank_table_addr = space_man.get_free_addr(0x100)

    bank_table_b = b'\xCD' * 0x100
    rom.seek(bank_table_addr)
    rom.write(bank_table_b, FSW.MARK_USED)

    # This is Mauron's patch which fetches the tech script address using the
    # bank table.  I'm not disassembling it except to show the bank load.
    rt = bytearray.fromhex(
        'A8 0A AA BF F0 5F CD 85 40 BB'
        'BF B2 FE C1'  # LDA $C1FEB2, X
        '8542E2207BA8AAB7409581C8B7409580C8BBC00400D0F098C221654085407BA8C220'
        '0680901FADB3A0D016A9010099AC5D5A980A0AA8A74099BD5DA54299BF5D7AE6'
        '40E640C8C01000D0D57BE220ADB3A0F0099CB3A0A482848080C2'
    )

    bank_table_addr_b = int.to_bytes(
        byteops.to_rom_ptr(bank_table_addr), 3, 'little'
    )
    rt[11:14] = bank_table_addr_b

    rom.seek(0x014533)
    rom.write(rt, FSW.NO_MARK)  # Should already be marked used.


def apply_mauron_player_tech_patch(
        ct_rom: ctrom.CTRom,
        local_ptr_addr: Optional[int] = None,
        bank_table_addr: Optional[int] = None
):
    '''
    Apply Mauron's patch to allow player tech animation scripts to be in any
    bank.  Also expand the tech pointers to allow 0xFF techs.  The id 0xFF is
    reserved for some menu functions.

    param ct_rom:  The CTRom to apply the patch to.
    param bank_table_addr: If not none, the lookup table for the bank table
                           will be placed at this (file) address in the rom.
    '''

    rom = ct_rom.rom_data
    FSW = freespace.FSWriteType

    space_man = ct_rom.rom_data.space_manager
    if local_ptr_addr is None:
        # Allocate 2 bytes per tech for local pointers
        # We really only need 0x1FE bytes because tech 0xFF isn't allowed.
        local_ptr_addr = space_man.get_free_addr(0x200)

    if bank_table_addr is None:
        # Allocate 1 byte per tech for banks.
        # We really only need 0xFF bytes because tech 0xFF isn't allowed.
        bank_table_addr = space_man.get_free_addr(0x100)

    rom.seek(0x0D5EF0)
    script_local_ptrs = rom.read(0x80*2)
    script_local_ptrs += (b'\x00\x00' * 0x80)

    rom.seek(local_ptr_addr)
    rom.write(script_local_ptrs, FSW.MARK_USED)

    bank_table_b = (b'\xCE' * 0x80) + (b'\x00' * 0x80)
    rom.seek(bank_table_addr)
    rom.write(bank_table_b)

    local_ptr_addr_hex = int.to_bytes(
        byteops.to_rom_ptr(local_ptr_addr), 3, 'little'
    ).hex()
    bank_table_addr_hex = int.to_bytes(
        byteops.to_rom_ptr(bank_table_addr), 3, 'little'
    ).hex()

    mauron_tech_patch =  bytearray.fromhex(
        'a8 0a aa bf' +
        local_ptr_addr_hex +
        '85 40 bb bf' +
        bank_table_addr_hex +
        '85 42 e2 20 7b'
        'a8 aa b7 40 95 81 c8 b7 40 95 80 c8 bb c0 04 00'
        'd0 f0 98 c2 21 65 40 85 40 7b a8 c2 20 06 80 90'
        '1f ad b3 a0 d0 16 a9 01 00 99 ac 5d 5a 98 0a 0a'
        'a8 a7 40 99 bd 5d a5 42 99 bf 5d 7a e6 40 e6 40'
        'c8 c0 10 00 d0 d5 7b e2'
        '20 ad b3 a0 f0 09 9c b3 a0 a4 82 84 80 80 c2'
    )

    rom.seek(0x014615)
    rom.write(mauron_tech_patch, FSW.NO_MARK)


def apply_mauron_patches(ct_rom: ctrom.CTRom):
    apply_mauron_enemy_attack_patch(ct_rom)
    apply_mauron_enemy_tech_patch(ct_rom)
    apply_mauron_player_tech_patch(ct_rom)

# Unused EventIDs:
#     04B, 04C, 04D, 04E, 04F, 050, 051, 066
#     067, 068, 069, 06A, 06B, 06C, 06D, 06E
# Locations w/ EventID 0x18:
#     1F0, 1F1, 1F2, 1F3, 1F4, 1F5, 1F6, 1F7,
#     1F8, 1F9, 1FA, 1FB, 1FC, 1FD, 1FE, 1FF


def mark_initial_free_space(vanilla_rom: ctrom.CTRom):
    '''
    Marks free space as per the DB's Offsets guide.

    DB is from Geiger with contributions from many on CC forums.
    '''

    free_blocks = (
        (0x01FDD3, 0x01FFFF),  # junk
        (0x027DE4, 0x028000),
        (0x02FE0C, 0x030000),  # junk
        (0x03FF0A, 0x040000), (0x05F365, 0x060000), (0x061E71, 0x062000),
        (0x06DD05, 0x06E000), (0x06FC51, 0x06FD00),
        (0x0BF164, 0x0C0000),  # junk + unused
        (0x0C0424, 0x0C047E), (0x0C066C, 0x0C06A4),
        (0x0C36F4, 0x0C3A09),  # Unused + Junk
        (0x0C43AF, 0x0C4700),
        (0x0CFC2C, 0x0D0000),  # Junk + Unused
        (0x0D3FE4, 0x0D3FFF),  # 0x0DFA00 to 0x0E0000 is all FFs
        (0x0EDC1B, 0x0EE000), (0x0FFE85, 0x0FFFFC),
        (0x10DEC0, 0x10E000), (0x10FD60, 0x110000), (0x11FEF4, 0x120000),
        (0x12FF94, 0x130000), (0x13FFD8, 0x140000), (0x14FF73, 0x150000),
        (0x16F9F8, 0x170000), (0x17FEEE, 0x180000), (0x18CF68, 0x18D000),
        (0x19FC5B, 0x1A0000), (0x1AFC29, 0x1B0000), (0x1B7FF5, 0x1C0000),
        (0x1CDF98, 0x1D0000), (0x1DFD48, 0x1E0000), (0x1EBF90, 0x1EC000),
        (0x1FFF75, 0x200000),
        (0x20332C, 0x2034E2),  # junk
        (0x20FD93, 0x210000),  # junk + unused
        (0x21DDB2, 0x21DE00), (0x21DE2C, 0x21DE80), (0x21DF80, 0x21E000),
        (0x21F518, 0x220000), (0x22FE46, 0x230000), (0x23F8C0, 0x240000),
        (0x2417B8, 0x242000), (0x2422E8, 0x242300), (0x2425B5, 0x242600),
        (0x242784, 0x242800), (0x242BFA, 0x243000), (0x24A600, 0x24A800),
        (0x24CC60, 0x24F000), (0x24F523, 0x24F600), (0x251A44, 0x252000),
        (0x25FBA0, 0x260000), (0x26FEF9, 0x270000), (0x27FF09, 0x280000),
        (0x28FF03, 0x290000), (0x29FFD3, 0x2A0000), (0x2AFF4A, 0x2B0000),
        (0x2BFEF4, 0x2C0000), (0x2FB168, 0x2FC000), (0x2CFEB1, 0x2D0000),
        (0x2DFF4C, 0x2E0000), (0x2EFF8C, 0x2F0000), (0x2FFF18, 0x300000),
        (0x30F5E7, 0x310000), (0x31FE2A, 0x320000), (0x32FE64, 0x330000),
        (0x33FDFB, 0x340000), (0x34FDEE, 0x350000),
        (0x35F7E6, 0x360000),  # Junk + Unused
        (0x366DC2, 0x367380),
        (0x369FE9, 0x36A000),  # Junk
        #  (0x3748B8, 0x374900),  # Junk, moved to dialogue freeing
        (0x37FFD1, 0x380000), (0x384639, 0x384650),
        #  (0x38AA94, 0x38B170),  # Junk, moved to dialogue freeing
        (0x38FFF4, 0x390000),
        # (0x39AFE9, 0x39B000),  # moved to dialogue freeing
        # (0x39FA76, 0x3A0000),  # Junk,  moved to dialogue freeing
        (0x3AFAA0, 0x3B0000),  # Junk
        (0x3BFFD0, 0x3C0000),  # Junk
        (0x3D6693, 0x3D6800), (0x3D8E64, 0x3D9000), (0x3DBB67, 0x3DC000),
        (0x3F8C03, 0x3F8C60),  # junk
        (0x3D9FEB, 0x3DA000),
    )

    MARK_FREE = ctrom.freespace.FSWriteType.MARK_FREE

    for block in free_blocks:
        vanilla_rom.rom_data.space_manager.mark_block(block, MARK_FREE)


def mark_vanilla_dialogue_free(vanilla_rom: ctrom.CTRom):
    '''
    Mark all ranges corresponding to vanilla CT dialogue/dialogue pointers
    free.

    Based on DB from Geiger.
    '''

    dialogue_blocks = (
        (0x18D000, 0x190000),  # ptrs and dialogue.
        (0x1EC000, 0x1EFA00),  # ptrs and dialogue.
        (0x36A000, 0x36B350),  # ptrs and dialogue.
        (0x370000, 0x37F980),  # ptrs and dialogue and junk.
        (0x384650, 0x38B170),  # ptrs and dialogue and junk.
        (0x39AFE9, 0x3A0000),  # ptrs and dialogue and junk.
        (0x3CB9E8, 0x3CF9F0),  # ptrs and dialogue
        (0x3F4460, 0x3F8C60),  # ptrs and dialogue and junk.
    )

    MARK_FREE = ctrom.freespace.FSWriteType.MARK_FREE

    for block in dialogue_blocks:
        vanilla_rom.rom_data.space_manager.mark_block(block, MARK_FREE)


def patch_timegauge(ct_rom: ctrom.CTRom):
    '''
    Change the time gauge's behavior to read available time periods from
    $7E2881 - $7E288D.
    '''

    rom = ct_rom.rom_data
    FSW = ctrom.freespace.FSWriteType

    rt = bytes.fromhex(
        'DA'           # PHX
        'A2 00 00'     # LDX #$0000
        'C2 20'        # REP #$20
        'B7 10'        # LDA [$10], Y
        'DF 81 28 7E'  # CMP $7E2881, X
        'D0 02'        # BNE #$02
        'FA'           # PLX
        '6B'           # RTL
        'E8'           # INX
        'E8'           # INX
        'E0 0E 00'     # CPX #$000E
        '90 F1'        # BCC #$F1  [-0x0F]
        'AF 00 01 7E'  # LDA $7E0100  [Should hold current location]
        'FA'           # PLX
        '6B'           # RTL
    )

    rt_addr = rom.space_manager.get_free_addr(len(rt))
    rom.seek(rt_addr)
    rom.write(rt, FSW.MARK_USED)

    rt_addr = byteops.to_rom_ptr(rt_addr)
    rt_addr_b = rt_addr.to_bytes(3, 'little')
    hook = bytes.fromhex('22' + rt_addr_b.hex())
    rom.seek(0x027475)
    rom.write(hook)


def apply_tf_compressed_enemy_gfx_hack(ct_rom: ctrom.CTRom):
    '''
    By default, CT forces compressed graphics for enemies with id > 0xF8.
    This hack instead looks at the graphics packet id to determine whether to decompress.
    '''

    # Original code: @ $C04775 (0x004775)
    #   LDX $6D       - Load (2*) the object number
    #   LDA $1101,X   - Look up the enemy_id of that object
    #   CMP #$F8      - Compare the enemy_id to 0xF8
    #   BCC $C04781   - If < 0xF8 jump to the compressed gfx routine
    #   BRL $C04845   - If >= 0xF8 jump to the uncompressed gfx routine

    # Upon entering the above code A holds the graphics packet id.  Only graphics packets
    # 0 through 6 (PCs) are compressed, so jump to the routines based on that.

    # @ $C04775
    #   CMP #$07      - Compare the graphics packet id to 7
    #   BCS $C04781   - If >= 7 jump to the compressed gfx routine
    #   BRA $C0477E   - If < 7 jump to the BRL

    AM = inst.AddressingMode
    routine: assemble.ASMList = [
        inst.CMP(0x07, AM.IMM8),
        inst.BCS(0x08, AM.REL_8),
        inst.BRA(0x03, AM.REL_8)
    ]

    routine_b = assemble.assemble(routine)

    ct_rom.rom_data.seek(0x004775)
    ct_rom.rom_data.write(routine_b)


def apply_misc_patches(ct_rom: ctrom.CTRom):
    '''
    Apply short patches which require no JSL/freespace allocation

    List of patches:
    - Double HP on Greendream.
    - Remove Grandleon restriction on GranddDream (Gold Rock tech)
    - Remove Active/Wait screen from some rename screens
    '''

    # Double the HP given to a PC revived by Greendream
    ct_rom.rom_data.seek(0x01B324)
    ct_rom.rom_data.write(b'\x0A')  # Change from 5

    # Remove Grandleon restriction on GrandDream (Gold Rock tech)
    # Overwrite CMP #$42, BNE XX with NOP NOP NOP NOP.
    # 0x42 is the Grandleon's item id.
    ct_rom.rom_data.seek(0x010FED)
    ct_rom.rom_data.write(b'\xEA'*4)

    # Remove (some) Active/Wait screens
    # I'm not sure whether this is needed or not.  After the first name screen,
    # 0x7E299F should stay nonzero, and the ORA that this overwrites only makes
    # it more nonzero...
    ct_rom.rom_data.seek(0x02E1ED)
    ct_rom.rom_data.write(b'\xEA\xEA')  # Overwrites ORA $71


def patch_tabs(ct_rom: ctrom.CTRom):
    """
    Replace the add_item command with an add item from memory so that it can be randomized later on
    Update text to be consistent with other tab items
    """

    """
    Algorithm for normalizing tabs was originally written by Psuedoarc as a part of ctrando project.
    The original source code can be found here:
    https://github.com/Pseudoarc/ctrando/blob/main/src/ctrando/base/openworldutils.py#L862
    SHA1:9c97db1246094f8910cb6d9c84dfa75539
    The ctrando project, and this algorithm within it, are MIT licensed.
    Credit to Psuedoarc for the original implementation
    Thanks for allowing its use in JoT 
    """

    # Tabs which don't follow typical command convention, but share the same convention
    location_tab_id = [
        (LocID.SUN_KEEP_600,0x0A), # TID.SUN_KEEP_600_POWER_TAB
        (LocID.GENO_DOME_MAINFRAME,0x26), # TID.GENO_DOME_ATROPOS_MAGIC_TAB
        (LocID.GENO_DOME_LONG_CORRIDOR,0x08), # TID.GENO_DOME_CORRIDOR_POWER_TAB
        (LocID.GENO_DOME_LABS,0x30), # TID.GENO_DOME_LABS_MAGIC_TAB
        (LocID.LAST_VILLAGE_SHOP,0x0A) # TID.LAST_VILLAGE_NU_SHOP_MAGIC_TAB
    ]

    for location, object_id in location_tab_id:
        script = ct_rom.script_manager.get_script(location)
        pos = script.get_function_start(object_id, FID.ACTIVATE)
        
        # Delete existing text
        text_pos, _ = script.find_command([0xBB], pos)
        script.delete_commands(text_pos, 1)

        # Find existing tab
        item_pos, _ = script.find_command([0xCA], pos)
        item_id = script.data[item_pos + 1]

        # Remove possible extra set item mem command
        set_pos = script.find_exact_command_opt(
            EC.assign_val_to_mem(item_id, 0x7F0200, 1), pos, text_pos
        )
        if set_pos is not None:
            script.delete_commands(set_pos, 1)
            if set_pos < item_pos:
                item_pos -= len(EC.assign_val_to_mem(item_id, 0x7F0200, 1), pos, text_pos)
        script.delete_commands(item_pos, 1)

        """
        Create new block for tab, song, and text commands
        """

        # Add Tab
        new_block = (
            EF()
            .add(EC.assign_val_to_mem(item_id, 0x7F0200, 1))
            .add(EC.add_item_memory(0x7F0200))
        )

        # Add song
        song_pos, song_cmd = script.find_command_opt([0xEC], pos, text_pos)
        new_block.add(song_cmd)
        ins_pos = song_pos

        # Add text
        item_str_id = script.add_py_string("{line break}          Found 1 {item}!{null}")
        new_block.add( EC.auto_text_box(item_str_id))
        
        script.insert_commands(new_block.get_bytearray(), ins_pos)
        ins_pos += len(new_block)
        script.delete_commands(ins_pos, 1)


    """
    Algorithm for normalizing the Enhasa tabs was originally written by Psuedoarc as a part of ctrando project.
    The original source code can be found here:
    https://github.com/Pseudoarc/ctrando/blob/main/src/ctrando/base/openworld/enhasabalthasarstudy.py#L23
    SHA1:9c97db1246094f8910cb6d9c84dfa75539
    The ctrando project, and this algorithm within it, are MIT licensed.
    Credit to Psuedoarc for the original implementation
    Thanks for allowing its use in JoT 
    """

    # Enhasa Nu battle tabs require special handling
    # (LocID.ENHASA_NU_ROOM,0x08), # TID.ENHASA_NU_BATTLE_TABS

    #
    script = ct_rom.script_manager.get_script(LocID.ENHASA_NU_ROOM)
    item_str_id = script.add_py_string("{line break}          Found 1 {item}!{null}")

    # Get baseline magic tab location, update the commands as well as text
    pos = script.find_exact_command(
        EC.add_item(ItemID.MAGIC_TAB),
        script.get_function_start(0x08, FID.ACTIVATE),
    )
    script.delete_commands(pos, 2)

    pos, _ = script.find_command([0xBB], pos)
    script.data[pos + 1] = item_str_id

    script.insert_commands(
        EF()
        .add(EC.assign_val_to_mem(ItemID.MAGIC_TAB, 0x7F0200, 1))
        .add(EC.add_item_memory(0x7F0200))
        .get_bytearray(),
        pos,
    )

    # Get baseline speed tab location, update the commands as well as text
    pos = script.find_exact_command(EC.generic_command(0xEE), pos)
    script.insert_commands(
        EF()
        .add(EC.assign_val_to_mem(ItemID.SPEED_TAB, 0x7F0200, 1))
        .add(EC.add_item_memory(0x7F0200))
        .add(EC.auto_text_box(item_str_id))
        .get_bytearray(),
        pos,
    )

def apply_jets_patches(ct_rom: ctrom.CTRom):
    '''
    Apply all basic jets code patches to the given CTRom.
    '''
    apply_misc_patches(ct_rom)
    patch_timegauge(ct_rom)
        

def set_storyline_thresholds(ct_rom: ctrom.CTRom):
    '''
    Change storyline values which allow certain actions to be taken.
    '''

    rom = ct_rom.rom_data
    # 001994	001994	DATA	N
    # Storyline value for location party exchange
    # Jets changes 0x49 to 0x01
    rom.seek(0x001994)
    rom.write(b'\x01')

    # 022D96	022D96	DATA	N
    # Storyline value for Black Omen on overworld map
    # Change from 0xD4 to 0x0C
    rom.seek(0x022D96)
    rom.write(b'\x0C')

    # 02360C	02360C	DATA	N
    # Storyline value for overworld party exchange menu
    # Change from 0x49 to 0x00
    rom.seek(0x02360C)
    rom.write(b'\x00')

    # 027464	027464	DATA	N
    # Storyline value for Epoch time gauge 1F4->1F6 overworld map change
    # (Check 1)
    # Change from 0xCC to 0x10
    rom.seek(0x027464)
    rom.write(b'\x10')

    # 027484	027484	DATA	N
    # Storyline value for Epoch time gauge 1F4->1F6 overworld map change
    # (Check 2)	2007.01.15
    # Also changes 0xCC to 0x10
    rom.seek(0x027484)
    rom.write(b'\x10')


def main():
    pass


if __name__ == '__main__':
    main()
