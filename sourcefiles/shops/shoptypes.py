'''Module providing classes for manipulating shops.'''

from __future__ import annotations
from typing import Optional

import byteops
import ctenums
import ctrom
import itemdata


class ShopManager:
    '''Class to handle reading/writing of shop data to rom.'''
    shop_ptr = 0x02DAFD
    shop_data_bank_ptr = 0x02DB09

    # TODO: Change constructor to take dict[ShopID, list[int]] and use a
    #       Separate from_rom method.
    def __init__(self, rom: Optional[bytes] = None):

        self.shop_dict: dict[ctenums.ShopID, list[ctenums.ItemID]]
        if rom is None:
            self.shop_dict = {
                shop_id: [] for shop_id in sorted(list(ctenums.ShopID))
            }
            return

        shop_data_bank, shop_ptr_start = ShopManager.__get_shop_pointers(rom)

        # print(f"Shop data bank = {self.shop_data_bank:06X}")
        # print(f"Shop ptr start = {self.shop_ptr_start:06X}")

        # We're using some properties of ctenums.ShopID here.
        #  1) ctenums.ShopID starts from 0x00, and
        #  2) ctenums.ShopID contains all values from 0x00 to N-1 where N is
        #     the number of shops.

        self.shop_dict = {}

        # The sort shouldn't be necessary, but be explicit.
        for shop in sorted(list(ctenums.ShopID)):
            index = int(shop)
            ptr_start = shop_ptr_start + 2*index
            shop_ptr_local = byteops.get_value_from_bytes(
                rom[ptr_start:ptr_start+2]
            )
            shop_ptr = shop_ptr_local + shop_data_bank

            pos = shop_ptr
            self.shop_dict[shop] = []

            # Items in the shop are a 0-terminated list
            while rom[pos] != 0:
                # print(ctenums.ItemID(rom[pos]))
                self.shop_dict[shop].append(ctenums.ItemID(rom[pos]))
                pos += 1

    # Returns start of shop pointers, start of bank of shop data
    @classmethod
    def __get_shop_pointers(cls, rom: bytes):
        shop_data_bank = byteops.to_file_ptr(rom[cls.shop_data_bank_ptr] << 16)
        shop_ptr_start = \
            byteops.to_file_ptr(
                byteops.get_value_from_bytes(rom[cls.shop_ptr:cls.shop_ptr+3])
            )
        return shop_data_bank, shop_ptr_start

    def write_to_ctrom(self, ct_rom: ctrom.CTRom):
        '''Write all shops out to the CTRom.'''
        # The space used/freed by TF isn't available to me.  I just have to
        # assume that the space currently allotted is enough.

        shop_data_bank, shop_ptr_start = \
            ShopManager.__get_shop_pointers(ct_rom.rom_data.getbuffer())

        rom = ct_rom.rom_data

        ptr_loc = shop_ptr_start
        rom.seek(ptr_loc)
        data_loc = byteops.get_value_from_bytes(rom.read(2)) + shop_data_bank

        max_index = max(self.shop_dict.keys())

        for shop_id in range(max_index+1):
            shop = ctenums.ShopID(shop_id)

            rom.seek(ptr_loc)
            ptr = data_loc % 0x010000
            ptr_loc += rom.write(byteops.to_little_endian(ptr, 2))

            if shop in self.shop_dict:
                items = bytearray(self.shop_dict[shop]) + b'\x00'
            else:
                items = bytearray([ctenums.ItemID.MOP]) + b'\x00'

            rom.seek(data_loc)
            data_loc += rom.write(items)

    def set_shop_items(self, shop: ctenums.ShopID,
                       items: list[ctenums.ItemID]):
        '''Sets the items of a shop.'''
        self.shop_dict[shop] = items[:]

    def print_with_prices(self,
                          item_db: itemdata.ItemDB):
        '''Print out all shops with prices from item_db.'''
        print(self.get_spoiler_string(item_db))

    def to_jot_json(self):
        shops_ignored = [
            ctenums.ShopID.EMPTY_12, ctenums.ShopID.EMPTY_14,
            ctenums.ShopID.LAST_VILLAGE_UPDATED
        ]
        return {str(k): [str(i) for i in v]
                for (k, v) in self.shop_dict.items()
                if k not in shops_ignored}

    def get_spoiler_string(
            self,
            item_db: Optional[itemdata.ItemDB] = None) -> str:
        '''
        Return a string of all shops and items.  If an ItemDB is provided,
        include real names and prices.
        '''
        ret = ''
        for shop in sorted(self.shop_dict.keys()):
            if shop in [ctenums.ShopID.EMPTY_12, ctenums.ShopID.EMPTY_14,
                        ctenums.ShopID.LAST_VILLAGE_UPDATED]:
                continue

            ret += str(shop)
            ret += ':\n'
            for item in self.shop_dict[shop]:
                ret += ('    ' + str(item))

                if item_db is not None:
                    price = item_db.item_dict[item].secondary_stats.price
                    ret += f": {price}"

                ret += '\n'

        return ret

    def __str__(self):
        '''Returns a spoiler string without prices or names (just IDs).'''
        return self.get_spoiler_string(None)
