"""
Module for 65816 creating assembly instructions.

This file was inspired by ff6wc's instruction/asm.py.
The content of this file and naming conventions are originally from:
  http://www.6502.org/tutorials/65c816opcodes.html
"""
import typing
from dataclasses import dataclass
import enum
import inspect
import sys
from typing import ClassVar, Optional, Protocol, Type, Union


class InvalidAddressingModeException(Exception):
    """Raise when instantiating an instruction with an unsupported mode."""


class InvalidArgumentException(Exception):
    """Raise when the argument does not match the mode provided."""


class SpecialRegister(enum.IntEnum):
    M7A = 0x211B
    M7B = 0x211C
    MPYL = 0x2134
    MPYM = 0x2135
    MPYH = 0x2136
    WRMPYA = 0x4202   # Multiply A
    WRMPYB = 0x4203   # Multiply B
    WRDIVL = 0x4204   # Dividend Lo
    WRDIVH = 0x4205   # Dividend Hi
    WRDIVB = 0x4206   # Divisor
    RDDIVL = 0x4214   # Quotient Lo
    RDDIVH = 0x4215   # Quotient Hi
    RDMPYL = 0x4216   # Mult result Lo (also div remainder)
    RDMPYH = 0x4217   # Mult result Hi (also div remainder)



class AddressingMode(enum.Enum):
    """Class for storing an instruction's addressing mode."""

    # ( ) means 16-bit dereference using DBR for bank
    # [ ] means 24-bit dereference
    IMM8 = enum.auto()        # LDA #$FF
    DIR = enum.auto()         # DIRECT
    DIR_X = enum.auto()       # (DIRECT), X
    DIR_Y = enum.auto()       # (DIRECT), Y
    DIR_16 = enum.auto()      # (DIRECT)
    DIR_X_16 = enum.auto()    # (DIRECT, X) (+X before dereference)
    DIR_16_Y = enum.auto()    # (DIRECT), Y (+Y after dereference)
    DIR_24 = enum.auto()      # [DIRECT]
    DIR_24_Y = enum.auto()    # [DIRECT], Y
    STK = enum.auto()         # STACK, S
    STK_16_Y = enum.auto()    # (STACK, S), Y
    # Note, IMM8 and IMM16 are not actually different opcodes.  The CPU
    # determines how many bytes to fetch given the status register.
    IMM16 = enum.auto()       # LDA #$ABCD
    ABS = enum.auto()         # Use DBR
    ABS_X = enum.auto()       # ^ + X
    ABS_Y = enum.auto()       # ^^ + Y
    ABS_16 = enum.auto()      # (ABSOLUTE)
    ABS_X_16 = enum.auto()    # (ABSOLUTE, X)
    ABS_24 = enum.auto()      # [ABSOLUTE]
    LNG = enum.auto()         # LONG
    LNG_X = enum.auto()       # LONG, X
    REL_8 = enum.auto()
    REL_16 = enum.auto()
    SRC_DEST = enum.auto()
    # There are many no argument addressing modes (e.g. Accumulator, Implied)
    # But we just lump them together.
    NO_ARG = enum.auto()


_modes_8_bit = (
    AddressingMode.IMM8, AddressingMode.DIR, AddressingMode.DIR_X,
    AddressingMode.DIR_Y, AddressingMode.DIR_16, AddressingMode.DIR_16_Y,
    AddressingMode.DIR_24, AddressingMode.DIR_24_Y, AddressingMode.DIR_X_16,
    AddressingMode.STK, AddressingMode.STK_16_Y, AddressingMode.REL_8
)

_modes_16_bit = (
    AddressingMode.ABS, AddressingMode.ABS_16, AddressingMode.ABS_24,
    AddressingMode.ABS_X, AddressingMode.ABS_X_16, AddressingMode.ABS_Y,
    AddressingMode.REL_16, AddressingMode.SRC_DEST, AddressingMode.IMM16
)

_modes_24_bit = (
    AddressingMode.LNG, AddressingMode.LNG_X
)


class _Instruction(Protocol):
    """Protocol for Instructions"""
    _opcode_dict: ClassVar[typing.Dict[AddressingMode, int]]
    mode: AddressingMode
    _argument: Optional[int]

    @property
    def opcode(self) -> int:
        """Returns the command's opcode (read only)"""
        return self._opcode_dict[self.mode]

    @property
    def argument(self) -> Optional[int]:
        """This command's argument."""
        return self._argument

    @argument.setter
    def argument(self, val: Optional[int]):
        _verify_argument(val, self.mode)
        self._argument = val

    @classmethod
    def get_opcode_dict(cls) -> typing.Dict[AddressingMode, int]:
        return dict(cls._opcode_dict)

    def to_bytearray(self) -> bytearray:
        """Convert a command to binary"""
        ret = bytearray()
        ret.append(self._opcode_dict[self.mode])
        ret.extend(_get_argument_bytes(self.argument, self.mode))
        return ret

    def __str__(self) -> str:
        cmd_name = self.__class__.__name__

        if self.mode == _AM.NO_ARG:
            arg_str = ''
        else:
            if self.argument is None:
                raise InvalidArgumentException

            arg_bytes = _get_argument_bytes(
                self.argument, self.mode
            )

            num_bytes = len(arg_bytes)
            arg_val = int.from_bytes(arg_bytes, 'little')
            arg_bytestr = f'{arg_val:0{num_bytes*2}X}'

            if self.mode in (_AM.ABS, _AM.REL_16):
                arg_str = f'${arg_bytestr}'
            elif self.mode == _AM.ABS_16:
                arg_str = f'(${arg_bytestr})'
            elif self.mode == _AM.ABS_24:
                arg_str = f'[${arg_bytestr}]'
            elif self.mode == _AM.ABS_X:
                arg_str = f'${arg_bytestr},X'
            elif self.mode == _AM.ABS_X_16:
                arg_str = f'(${arg_bytestr},X)'
            elif self.mode == _AM.ABS_Y:
                arg_str = f'${arg_bytestr},Y'
            elif self.mode in (_AM.DIR, _AM.REL_8):
                arg_str = f'${arg_bytestr}'
            elif self.mode == _AM.DIR_16:
                arg_str = f'(${arg_bytestr})'
            elif self.mode == _AM.DIR_16_Y:
                arg_str = f'(${arg_bytestr}),Y'
            elif self.mode == _AM.DIR_24:
                arg_str = f'[${arg_bytestr}]'
            elif self.mode == _AM.DIR_24_Y:
                arg_str = f'[${arg_bytestr}],Y'
            elif self.mode == _AM.DIR_X:
                arg_str = f'${arg_bytestr},X'
            elif self.mode == _AM.DIR_X_16:
                arg_str = f'(${arg_bytestr}, X)'
            elif self.mode == _AM.DIR_Y:
                arg_str = f'${arg_bytestr},Y'
            elif self.mode == _AM.IMM16:
                arg_str = f'#${arg_bytestr}'
            elif self.mode == _AM.IMM8:
                arg_str = f'#${arg_bytestr}'
            elif self.mode == _AM.LNG:
                arg_str = f'${arg_bytestr}'
            elif self.mode == _AM.LNG_X:
                arg_str = f'${arg_bytestr},X'
            elif self.mode == _AM.SRC_DEST:
                from_bank = (self.argument & 0xFF00) >> 8
                to_bank = self.argument & 0x00FF
                arg_str = f'#${from_bank:02X} #${to_bank:02X}'
            elif self.mode == _AM.STK:
                arg_str = f'${arg_bytestr},S'
            elif self.mode == _AM.STK_16_Y:
                arg_str = f'(${arg_bytestr},S),Y'
            else:
                raise InvalidAddressingModeException

        return f'{cmd_name} {arg_str}'

    def __len__(self) -> int:
        if self.mode == _AM.NO_ARG:
            return 1
        if self.mode in _modes_8_bit:
            return 2
        if self.mode in _modes_16_bit:
            return 3
        if self.mode in _modes_24_bit:
            return 4

        raise InvalidAddressingModeException


def _verify_argument(argument: Optional[int],
                     mode: AddressingMode) -> None:
    """
    Raise an InvalidArgumentException if the argument does not match their
    addressing mode.
    """
    AM = AddressingMode
    if mode == AM.NO_ARG:
        if argument is not None:
            raise InvalidArgumentException(
                f"Given mode: {mode} but argument was provided"
            )
    elif mode == AM.REL_8:
        if argument is not None and \
                not (-0x80 <= argument < 0x80):
            raise InvalidArgumentException
    elif mode == AM.REL_16:
        if argument is not None and \
                not (-0x800 <= argument < 0x800):
            raise InvalidArgumentException
    elif mode in _modes_8_bit:
        if not (0 <= argument < 0x100):
            raise InvalidArgumentException
    elif mode in _modes_16_bit:
        if not (0 <= argument < 0x10000):
            raise InvalidArgumentException
    elif mode in _modes_24_bit:
        if not (0 <= argument < 0x1000000):
            raise InvalidArgumentException
    else:
        raise TypeError(f"Uncaught mode {mode}")


def _get_argument_bytes(argument: Optional[int],
                        mode: AddressingMode) -> bytes:
    AM = AddressingMode
    if mode == AM.NO_ARG:
        return b''

    if argument is None:
        raise InvalidArgumentException

    is_signed = False
    if mode in (AM.REL_16, AM.REL_8):
        is_signed = True

    if mode in _modes_8_bit:
        num_bytes = 1
    elif mode in _modes_16_bit:
        num_bytes = 2
    else:
        num_bytes = 3

    return argument.to_bytes(num_bytes, 'little',
                             signed=is_signed)


class _NormalInstruction(_Instruction):
    """
    Class for a non-branch instruction with a single argument
    """
    _opcode_dict = {}

    def __init__(self,
                 argument: Optional[int] = None,
                 mode: Optional[AddressingMode] = None):

        if mode is None:
            # Allow None for mode if there is only one option
            if len(self._opcode_dict) == 1:
                mode = next(iter(self._opcode_dict))

        if mode not in self._opcode_dict:
            raise InvalidAddressingModeException
        self.mode = mode
        self.argument = argument


class _BranchInstruction(_Instruction):
    """
    Class for a branch instruction.

    The main difference is that a branch instruction allows for a string
    as an argument.  The string is interpreted as a label to branch to.
    The string must be resolved to an integer before conversion to bytes.
    """

    _opcode_dict = {}

    def __init__(self,
                 argument: Optional[Union[int, str]] = None,
                 mode: Optional[AddressingMode] = None):
        self.label: Optional[str]

        if mode is None:
            # Allow None for mode if there is only one option
            if len(self._opcode_dict) == 1:
                mode = next(iter(self._opcode_dict))

        if mode not in self._opcode_dict:
            raise InvalidAddressingModeException
        self.mode = mode

        if argument is None:
            raise InvalidArgumentException

        if isinstance(argument, str):
            self.label = argument
            self._argument = None
        else:
            self.label = None
            self.argument = argument

    def __str__(self):
        if self.argument is None and self.label is None:
            raise InvalidArgumentException

        if self.argument is None:
            arg_str = self.label
        else:
            arg_bytes = _get_argument_bytes(self.argument,
                                            self.mode)
            arg_bytestr = ''.join(f'{x:02X}' for x in arg_bytes)
            if self.mode == _AM.REL_8:
                arg_str = f'${arg_bytestr}'
            elif self.mode == _AM.REL_16:
                arg_str = f'${arg_bytestr}'

            if self.label is not None:
                arg_str += f' (to {self.label})'

        return f'{self.__class__.__name__} {arg_str}'


_AM = AddressingMode


class ADC(_NormalInstruction):
    """Add with Carry."""
    _opcode_dict = {
        _AM.ABS: 0x6D,
        _AM.ABS_X: 0x7D,
        _AM.ABS_Y: 0x79,
        _AM.DIR: 0x65,
        _AM.DIR_16: 0x72,
        _AM.DIR_16_Y: 0x71,
        _AM.DIR_24: 0x67,
        _AM.DIR_24_Y: 0x77,
        _AM.DIR_X: 0x75,
        _AM.DIR_X_16: 0x61,
        _AM.IMM16: 0x69,
        _AM.IMM8: 0x69,
        _AM.LNG: 0x6F,
        _AM.STK: 0x63,
        _AM.STK_16_Y: 0x73,
        _AM.LNG_X: 0x7F,
    }


class SBC(_NormalInstruction):
    """Subtract with Carry (Borrow)."""
    _opcode_dict = {
        _AM.DIR_X_16: 0xE1,
        _AM.STK: 0xE3,
        _AM.DIR: 0xE5,
        _AM.DIR_24: 0xE7,
        _AM.IMM16: 0xE9,
        _AM.IMM8: 0xE9,
        _AM.ABS: 0xED,
        _AM.LNG: 0xEF,
        _AM.DIR_16_Y: 0xF1,
        _AM.DIR_16: 0xF2,
        _AM.STK_16_Y: 0xF3,
        _AM.DIR_X: 0xF5,
        _AM.DIR_24_Y: 0xF7,
        _AM.ABS_Y: 0xF9,
        _AM.ABS_X: 0xFD,
        _AM.LNG_X: 0xFF
    }


class CMP(_NormalInstruction):
    """Compare to accumulator"""
    _opcode_dict = {
        _AM.DIR_X_16: 0xC1,
        _AM.STK: 0xC3,
        _AM.DIR: 0xC5,
        _AM.DIR_24: 0xC7,
        _AM.IMM16: 0xC9,
        _AM.IMM8: 0xC9,
        _AM.ABS: 0xCD,
        _AM.LNG: 0xCF,
        _AM.DIR_16_Y: 0xD1,
        _AM.DIR_16: 0xD2,
        _AM.STK_16_Y: 0xD3,
        _AM.DIR_X: 0xD5,
        _AM.DIR_24_Y: 0xD7,
        _AM.ABS_Y: 0xD9,
        _AM.ABS_X: 0xDD,
        _AM.LNG_X: 0xDF
    }


class CPX(_NormalInstruction):
    """Compare to X"""
    _opcode_dict = {
        _AM.IMM16: 0xE0,
        _AM.IMM8: 0xE0,
        _AM.DIR: 0xE4,
        _AM.ABS: 0xEC,
    }


class CPY(_NormalInstruction):
    """Compare to Y"""
    _opcode_dict = {
        _AM.IMM16: 0xC0,
        _AM.IMM8: 0xC0,
        _AM.DIR: 0xC4,
        _AM.ABS: 0xCC,
    }


class DEC(_NormalInstruction):
    """Decrement"""
    _opcode_dict = {
        _AM.NO_ARG: 0x3A,  # Accumulator
        _AM.DIR: 0xC6,
        _AM.ABS: 0xCE,
        _AM.DIR_X: 0xD6,
        _AM.ABS_X: 0xDE,
    }

class DEX(_NormalInstruction):
    """Decrement X"""
    _opcode_dict = {_AM.NO_ARG: 0xCA}  # Implied


class DEY(_NormalInstruction):
    """Decrement Y"""
    _opcode_dict = {_AM.NO_ARG: 0x88}  # Implied


class INC(_NormalInstruction):
    """Increment"""
    _opcode_dict = {
        _AM.NO_ARG: 0x1A,  # Accumulator
        _AM.DIR: 0xE6,
        _AM.ABS: 0xEE,
        _AM.DIR_X: 0xF6,
        _AM.ABS_X: 0xFE,
    }


class INX(_NormalInstruction):
    """Increment X"""
    _opcode_dict = {_AM.NO_ARG: 0xE8}  # Implied


class INY(_NormalInstruction):
    """Increment Y"""
    _opcode_dict = {_AM.NO_ARG: 0xC8}  # Implied


class AND(_NormalInstruction):
    """Bitwise AND"""
    _opcode_dict = {
        _AM.DIR_X_16: 0x21,
        _AM.STK: 0x23,
        _AM.DIR: 0x25,
        _AM.DIR_24: 0x27,
        _AM.IMM16: 0x29,
        _AM.IMM8: 0x29,
        _AM.ABS: 0x2D,
        _AM.LNG: 0x2F,
        _AM.DIR_16_Y: 0x31,
        _AM.DIR_16: 0x32,
        _AM.STK_16_Y: 0x33,
        _AM.DIR_X: 0x35,
        _AM.DIR_24_Y: 0x37,
        _AM.ABS_Y: 0x39,
        _AM.ABS_X: 0x3D,
        _AM.LNG_X: 0x3F,
    }

class EOR(_NormalInstruction):
    """Bitwise Exclusive OR"""
    _opcode_dict = {
        _AM.DIR_X_16: 0x41,
        _AM.STK: 0x43,
        _AM.DIR: 0x45,
        _AM.DIR_24: 0x47,
        _AM.IMM16: 0x49,
        _AM.IMM8: 0x49,
        _AM.ABS: 0x4D,
        _AM.LNG: 0x4F,
        _AM.DIR_16_Y: 0x51,
        _AM.DIR_16: 0x52,
        _AM.STK_16_Y: 0x53,
        _AM.DIR_X: 0x55,
        _AM.DIR_24_Y: 0x57,
        _AM.ABS_Y: 0x59,
        _AM.ABS_X: 0x5D,
        _AM.LNG_X: 0x5F,
    }


class OR(_NormalInstruction):
    """Bitwise OR"""
    _opcode_dict = {
        _AM.DIR_X_16: 0x01,
        _AM.STK: 0x03,
        _AM.DIR: 0x05,
        _AM.DIR_24: 0x07,
        _AM.IMM16: 0x09,
        _AM.IMM8: 0x09,
        _AM.ABS: 0x0D,
        _AM.LNG: 0x0F,
        _AM.DIR_16_Y: 0x11,
        _AM.DIR_16: 0x12,
        _AM.STK_16_Y: 0x13,
        _AM.DIR_X: 0x15,
        _AM.DIR_24_Y: 0x17,
        _AM.ABS_Y: 0x19,
        _AM.ABS_X: 0x1D,
        _AM.LNG_X: 0x1F,
    }


class BIT(_NormalInstruction):
    """Test BITs"""
    _opcode_dict = {
        _AM.DIR: 0x24,
        _AM.ABS: 0x2C,
        _AM.DIR_X: 0x34,
        _AM.ABS_X: 0x3C,
        _AM.IMM16: 0x89,
        _AM.IMM8: 0x89
    }


class TRB(_NormalInstruction):
    """Test and Reset Bits"""
    _opcode_dict = {
        _AM.DIR: 0x14,
        _AM.ABS: 0x1C
    }


class TSB(_NormalInstruction):
    """Test and Set Bits"""
    _opcode_dict = {
        _AM.DIR: 0x04,
        _AM.ABS: 0x0C
    }


class ASL(_NormalInstruction):
    """Arithmetic Shift Left"""
    _opcode_dict = {
        _AM.DIR: 0x06,
        _AM.NO_ARG: 0x0A,  # Accumulator
        _AM.ABS: 0x0E,
        _AM.DIR_X: 0x16,
        _AM.ABS_X: 0x1E
    }


class LSR(_NormalInstruction):
    """Logial Shift Right"""
    _opcode_dict = {
        _AM.DIR: 0x46,
        _AM.NO_ARG: 0x4A,  # Accumulator
        _AM.ABS: 0x4E,
        _AM.DIR_X: 0x56,
        _AM.ABS_X: 0x5E
    }


class ROL(_NormalInstruction):
    """ROtate Left"""
    _opcode_dict = {
        _AM.DIR: 0x26,
        _AM.NO_ARG: 0x2A,  # Accumulator
        _AM.ABS: 0x2E,
        _AM.DIR_X: 0x36,
        _AM.ABS_X: 0x3E
    }


class ROR(_NormalInstruction):
    """ROtate Right"""
    _opcode_dict = {
        _AM.DIR: 0x66,
        _AM.NO_ARG: 0x6A,  # Accumulator
        _AM.ABS: 0x6E,
        _AM.DIR_X: 0x76,
        _AM.ABS_X: 0x7E
    }


class BCC(_BranchInstruction):
    """Branch if Carry Clear"""
    _opcode_dict = {_AM.REL_8: 0x90}


class BCS(_BranchInstruction):
    """Branch if Carry Set"""
    _opcode_dict = {_AM.REL_8: 0xB0}


class BEQ(_BranchInstruction):
    """Branch if EQual"""
    _opcode_dict = {_AM.REL_8: 0xF0}


class BMI(_BranchInstruction):
    """Branch if MInus"""
    _opcode_dict = {_AM.REL_8: 0x30}


class BNE(_BranchInstruction):
    """Branch if Not Equal"""
    _opcode_dict = {_AM.REL_8: 0xD0}


class BPL(_BranchInstruction):
    """Branch if PLus"""
    _opcode_dict = {_AM.REL_8: 0x10}


class BRA(_BranchInstruction):
    """BRanch Always"""
    _opcode_dict = {_AM.REL_8: 0x80}


class BVC(_BranchInstruction):
    """Branch if oVerflow Clear"""
    _opcode_dict = {_AM.REL_8: 0x50}


class BVS(_BranchInstruction):
    """Branch if oVerflow Set"""
    _opcode_dict = {_AM.REL_8: 0x70}


class BRL(_BranchInstruction):
    """BRanch Long"""
    _opcode_dict = {_AM.REL_16: 0x82}


class JMP(_NormalInstruction):
    """JuMP"""
    _opcode_dict = {
        _AM.ABS: 0x4C,
        _AM.LNG: 0x5C,
        _AM.ABS_16: 0x6C,
        _AM.ABS_X_16: 0x7C,
        _AM.ABS_24: 0xDC,
    }


class JSL(_NormalInstruction):
    """Jump to Subroutine Long"""
    _opcode_dict = {_AM.LNG: 0x22}


class JSR(_NormalInstruction):
    """Jump to SubRoutine"""
    _opcode_dict = {
        _AM.ABS: 0x20,
        _AM.ABS_X_16: 0xFC,
    }


class RTL(_NormalInstruction):
    """ReTurn from subroutine Long"""
    _opcode_dict = {_AM.NO_ARG: 0x6B}


class RTS(_NormalInstruction):
    """ReTurn from Subroutine"""
    _opcode_dict = {_AM.NO_ARG: 0x60}


class BRK(_NormalInstruction):
    """BReaKpoint"""
    _opcode_dict = {_AM.NO_ARG: 0x00}


class COP(_NormalInstruction):
    """COProcessor"""
    _opcode_dict = {
        _AM.IMM16: 0x02,
        _AM.IMM8: 0x02
    }


class RTI(_NormalInstruction):
    """ReTurn from Interrupt"""
    _opcode_dict = {_AM.NO_ARG: 0x40}


class CLC(_NormalInstruction):
    """CLear Carry"""
    _opcode_dict = {_AM.NO_ARG: 0x18}


class CLD(_NormalInstruction):
    """CLear Decimal mode"""
    _opcode_dict = {_AM.NO_ARG: 0xD8}


class CLI(_NormalInstruction):
    """CLear Interrupt disable"""
    _opcode_dict = {_AM.NO_ARG: 0x58}

class CLV(_NormalInstruction):
    """CLear oVerflow"""
    _opcode_dict = {_AM.NO_ARG: 0xB8}


class SEC(_NormalInstruction):
    """SEt Carry"""
    _opcode_dict = {_AM.NO_ARG: 0x38}


class SED(_NormalInstruction):
    """SEt Decimal mode"""
    _opcode_dict = {_AM.NO_ARG: 0xF8}


class SEI(_NormalInstruction):
    """SEt Interrupt disable"""
    _opcode_dict = {_AM.NO_ARG: 0x78}


class REP(_NormalInstruction):
    """REset Processor status bits"""
    _opcode_dict = {_AM.IMM8: 0xC2}


class SEP(_NormalInstruction):
    """SEt Processor status bits"""
    _opcode_dict = {_AM.IMM8: 0xE2}


class LDA(_NormalInstruction):
    """LoaD Accumulator"""
    _opcode_dict = {
        _AM.DIR_X_16: 0xA1,
        _AM.STK: 0xA3,
        _AM.DIR: 0xA5,
        _AM.DIR_24: 0xA7,
        _AM.IMM16: 0xA9,
        _AM.IMM8: 0xA9,
        _AM.ABS: 0xAD,
        _AM.LNG: 0xAF,
        _AM.DIR_16_Y: 0xB1,
        _AM.DIR_16: 0xB2,
        _AM.STK_16_Y: 0xB3,
        _AM.DIR_X: 0xB5,
        _AM.DIR_24_Y: 0xB7,
        _AM.ABS_Y: 0xB9,
        _AM.ABS_X: 0xBD,
        _AM.LNG_X: 0xBF,
    }


class LDX(_NormalInstruction):
    """LoaD register X"""
    _opcode_dict = {
        _AM.IMM16: 0xA2,
        _AM.IMM8: 0xA2,
        _AM.DIR: 0xA6,
        _AM.ABS: 0xAE,
        _AM.DIR_Y: 0xB6,
        _AM.ABS_Y: 0xBE,
    }


class LDY(_NormalInstruction):
    """LoaD register Y"""
    _opcode_dict = {
        _AM.IMM16: 0xA0,
        _AM.IMM8: 0xA0,
        _AM.DIR: 0xA4,
        _AM.ABS: 0xAC,
        _AM.DIR_X: 0xB4,
        _AM.ABS_X: 0xBC,
    }


class STA(_NormalInstruction):
    """STore Accumulator"""
    _opcode_dict = {
        _AM.DIR_X_16: 0x81,
        _AM.STK: 0x83,
        _AM.DIR: 0x85,
        _AM.DIR_24: 0x87,
        _AM.ABS: 0x8D,
        _AM.LNG: 0x8F,
        _AM.DIR_16_Y: 0x91,
        _AM.DIR_16: 0x92,
        _AM.STK_16_Y: 0x93,
        _AM.DIR_X: 0x95,
        _AM.DIR_24_Y: 0x97,
        _AM.ABS_Y: 0x99,
        _AM.ABS_X: 0x9D,
        _AM.LNG_X: 0x9F,
    }


class STX(_NormalInstruction):
    """STore register X"""
    _opcode_dict = {
        _AM.DIR: 0x86,
        _AM.ABS: 0x8E,
        _AM.DIR_Y: 0x96,
    }


class STY(_NormalInstruction):
    """STore register Y"""
    _opcode_dict = {
        _AM.DIR: 0x84,
        _AM.ABS: 0x8C,
        _AM.DIR_X: 0x94,
    }


class STZ(_NormalInstruction):
    """STore Zero"""
    _opcode_dict = {
        _AM.DIR: 0x64,
        _AM.DIR_X: 0x74,
        _AM.ABS: 0x9C,
        _AM.ABS_X: 0x9E
    }


class MVN(_NormalInstruction):
    """MoVe memory Negative"""
    _opcode_dict = {_AM.SRC_DEST: 0x54}


class MVP(_NormalInstruction):
    """MoVe memory Positive"""
    _opcode_dict = {_AM.SRC_DEST: 0x44}


class NOP(_NormalInstruction):
    """No OPeration"""
    _opcode_dict = {_AM.NO_ARG: 0xEA}
# Skip WDM


class PEA(_NormalInstruction):
    """Push Effective Address"""
    _opcode_dict = {_AM.IMM16: 0xF4}


class PEI(_NormalInstruction):
    """Push Effective Indirect address"""
    _opcode_dict = {_AM.DIR: 0xD4}


class PER(_NormalInstruction):
    """Push Effective Rndirect address"""
    _opcode_dict = {_AM.IMM16: 0x62}


class PHA(_NormalInstruction):
    """PusH Accumulator"""
    _opcode_dict = {_AM.NO_ARG: 0x48}


class PHX(_NormalInstruction):
    """PusH X register"""
    _opcode_dict = {_AM.NO_ARG: 0xDA}


class PHY(_NormalInstruction):
    """PusH Y register"""
    _opcode_dict = {_AM.NO_ARG: 0x5A}


class PLA(_NormalInstruction):
    """PulL Accumulator"""
    _opcode_dict = {_AM.NO_ARG: 0x68}


class PLX(_NormalInstruction):
    """PulL X register"""
    _opcode_dict = {_AM.NO_ARG: 0xFA}


class PLY(_NormalInstruction):
    """PulL Y register"""
    _opcode_dict = {_AM.NO_ARG: 0x7A}


class PHB(_NormalInstruction):
    """PusH data Bank register"""
    _opcode_dict = {_AM.NO_ARG: 0x8B}


class PHD(_NormalInstruction):
    """PusH Direct register"""
    _opcode_dict = {_AM.NO_ARG: 0x0B}


class PHK(_NormalInstruction):
    """PusH K register"""
    _opcode_dict = {_AM.NO_ARG: 0x4B}


class PHP(_NormalInstruction):
    """PusH Processor status register"""
    _opcode_dict = {_AM.NO_ARG: 0x08}


class PLB(_NormalInstruction):
    """PulL data Bank register"""
    _opcode_dict = {_AM.NO_ARG: 0xAB}


class PLD(_NormalInstruction):
    """PulL Direct register"""
    _opcode_dict = {_AM.NO_ARG: 0x2B}


class PLP(_NormalInstruction):
    """PulL Processor status register"""
    _opcode_dict = {_AM.NO_ARG: 0x28}


class STP(_NormalInstruction):
    """SToP the clock"""
    _opcode_dict = {_AM.NO_ARG: 0xDB}


class WAI(_NormalInstruction):
    """WAit for Interrupt"""
    _opcode_dict = {_AM.NO_ARG: 0xCB}


class TAX(_NormalInstruction):
    """Transfer Accumulator to X register"""
    _opcode_dict = {_AM.NO_ARG: 0xAA}


class TAY(_NormalInstruction):
    """Transfer Accumulator to Y register"""
    _opcode_dict = {_AM.NO_ARG: 0xA8}


class TSX(_NormalInstruction):
    """Transfer Stack pointer to X register"""
    _opcode_dict = {_AM.NO_ARG: 0xBA}


class TXA(_NormalInstruction):
    """Transfer X register to Accumulator"""
    _opcode_dict = {_AM.NO_ARG: 0x8A}


class TXS(_NormalInstruction):
    """Transfer X register to Stack pointer"""
    _opcode_dict = {_AM.NO_ARG: 0x9A}


class TXY(_NormalInstruction):
    """Transfer X register to Y register"""
    _opcode_dict = {_AM.NO_ARG: 0x9B}


class TYA(_NormalInstruction):
    """Transfer Y register to Accumulator"""
    _opcode_dict = {_AM.NO_ARG: 0x98}


class TYX(_NormalInstruction):
    """Transfer Y register to X register"""
    _opcode_dict = {_AM.NO_ARG: 0xBB}


class TCD(_NormalInstruction):
    """Transfer C accumulator to Direct register"""
    _opcode_dict = {_AM.NO_ARG: 0x5B}


class TCS(_NormalInstruction):
    """Transfer C accumulator to Stack pointer"""
    _opcode_dict = {_AM.NO_ARG: 0x1B}


class TDC(_NormalInstruction):
    """Transfer Direct register to C accumulator"""
    _opcode_dict = {_AM.NO_ARG: 0x7B}


class TSC(_NormalInstruction):
    """Transfer Stack pointer to C accumulator"""
    _opcode_dict = {_AM.NO_ARG: 0x3B}


class XBA(_NormalInstruction):
    """eXchange B and A accumulator"""
    _opcode_dict = {_AM.NO_ARG: 0xEB}


class XCE(_NormalInstruction):
    """eXchange Carry and Emulation flags"""
    _opcode_dict = {_AM.NO_ARG: 0xFB}


# For parsing, have a reverse dictionary of Opcode -> (Instruction, Mode)
@dataclass
class InstructionData:
    """Class with data for determining an instruction"""
    instruction_type: Type[_Instruction]
    addressing_mode: AddressingMode


_opcode_instruction_dict: typing.Dict[int, InstructionData] = {}

# When we're sure everything is fine, probably better to hardcode this and add
# unit tests to verify consistency.
for _name, _obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(_obj):
        if issubclass(_obj, (_NormalInstruction, _BranchInstruction)) and \
           _obj not in (_NormalInstruction, _BranchInstruction):
            _opcode_dict = _obj.get_opcode_dict()

            for (_mode, _opcode) in _opcode_dict.items():
                if _opcode in _opcode_instruction_dict and \
                   _mode not in (_AM.IMM16, _AM.IMM8):
                    raise ValueError(f'{_opcode:02X}')
                _opcode_instruction_dict[_opcode] = \
                    InstructionData(_obj, _mode)

def main():
    cmd = LDA(0x54, _AM.IMM8)
    print(cmd)

    cmd2 = BCC('LABEL')
    cmd2.argument = 4
    print(cmd2)


if __name__ == '__main__':
    main()
