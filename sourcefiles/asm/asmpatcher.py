from typing import Optional

from asm import assemble, instructions as inst
from asm.instructions import AddressingMode as AM
import byteops
import ctrom
import freespace


def apply_jmp_patch(
        patch: assemble.ASMList,
        hook_addr: int,
        ct_rom: ctrom.CTRom,
        return_addr: Optional[int] = None
):
    """Apply patch at position which jumps and jumps back."""
    rom = ct_rom.rom_data
    routine_b = assemble.assemble(patch)
    routine_addr = rom.space_manager.get_free_addr(len(routine_b))

    hook = [
        inst.JMP(byteops.to_rom_ptr(routine_addr), AM.LNG),
    ]
    hook_b = assemble.assemble(hook)

    rom.seek(hook_addr)
    rom.write(hook_b)
    if return_addr is not None:
        nop_len = return_addr - rom.tell()
        payload = bytes.fromhex('EA'*nop_len)
        rom.write(payload)

    rom.seek(routine_addr)
    rom.write(routine_b, freespace.FSWriteType.MARK_USED)


def add_jsl_routine(
        routine: assemble.ASMList,
        ct_rom: ctrom.CTRom,
        hint: Optional[int] = None
) -> int:
    """
    Adds a subroutine which should be called with JSL.
    Returns the file address (not rom) of the routine.
    """
    rom = ct_rom.rom_data
    routine_b = assemble.assemble(routine)
    routine_addr = rom.space_manager.get_free_addr(len(routine_b), hint)
    rom.seek(routine_addr)
    rom.write(routine_b, freespace.FSWriteType.MARK_USED)

    return routine_addr
