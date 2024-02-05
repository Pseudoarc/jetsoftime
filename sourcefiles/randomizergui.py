# python standard libraries
from functools import reduce
import copy
import os
import pathlib
import pickle
import random
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import askdirectory
from tkinter import messagebox
from typing import Optional

# custom/local libraries
import bucketgui
import randomizer
import bossrandotypes as rotypes
from randosettings import Settings, GameFlags, Difficulty, ShopPrices, \
    TechOrder, TabSettings, TabRandoScheme, ROSettings, ROFlags, \
    CosmeticFlags, GameMode, MysterySettings, CharNames
from ctenums import ActionMap, InputMap
import ctoptions
import ctrom
import ctstrings


#
# tkinter does not have a native tooltip implementation.
# This tooltip implementation is stolen from Stack Overflow:
# https://stackoverflow.com/a/36221216
# Re-stolen from Anguirel's original implementation
#
class CreateToolTip(object):
    """
    create a tooltip for a given widget
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 800     # miliseconds
        self.wraplength = 300   # pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        displaytext = self.text
        if isinstance(self.text, tk.StringVar):
            displaytext = self.text.get()
        label = tk.Label(self.tw, text=displaytext, justify='left',
                         background="#ffffff", relief='solid', borderwidth=1,
                         wraplength=self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()
# end class CreateToolTip


# Going to make a class for the gui to avoid reliance on globals
class RandoGUI:

    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.wm_title('Jets of Time')

        # Now that we have a tk window, we can make the variables
        # Game config variables
        self.flag_dict = dict()
        for x in list(GameFlags):
            self.flag_dict[x] = tk.IntVar()

        self.cosmetic_flag_dict = dict()
        for x in list(CosmeticFlags):
            self.cosmetic_flag_dict[x] = tk.IntVar()

        self.ro_flag_dict = dict()
        for x in list(ROFlags):
            self.ro_flag_dict[x] = tk.IntVar()

        self.flag_checkboxes = dict()

        self.item_difficulty = tk.StringVar()
        self.enemy_difficulty = tk.StringVar()
        self.shop_prices = tk.StringVar()
        self.tech_order = tk.StringVar()
        self.game_mode = tk.StringVar()

        # Tab stuff
        self.power_tab_max = tk.IntVar()
        self.power_tab_min = tk.IntVar()

        self.magic_tab_max = tk.IntVar()
        self.magic_tab_min = tk.IntVar()

        self.speed_tab_max = tk.IntVar()
        self.speed_tab_min = tk.IntVar()

        self.tab_rando_scheme = tk.StringVar()
        self.tab_success_chance = tk.DoubleVar()

        # RC stuff
        # By default, rc puts no restrictions on assignment
        self.char_choices = [[tk.IntVar(value=1) for i in range(7)]
                             for j in range(7)]

        self.duplicate_chars = tk.IntVar(value=0)
        self.duplicate_duals = tk.IntVar(value=0)

        # ro settings
        self.preserve_part_count = tk.IntVar(value=0)

        self.ctopts = {
            'battle_speed': tk.IntVar(value=5),
            'stereo_audio': tk.BooleanVar(value=True),
            'custom_control_pad': tk.BooleanVar(value=False),
            'save_menu_cursor': tk.BooleanVar(value=False),
            'active_battle': tk.BooleanVar(value=False),
            'skill_item_info': tk.BooleanVar(value=True),
            'menu_background': tk.IntVar(value=1),
            'battle_msg_speed': tk.IntVar(value=5),
            'save_battle_cursor': tk.BooleanVar(value=False),
            'save_tech_cursor': tk.BooleanVar(value=True),
            'battle_gauge_style': tk.IntVar(value=1),
            'consistent_paging': tk.BooleanVar(value=False)
        }

        self.controller_binds = {
            ActionMap.CONFIRM: tk.StringVar(value=InputMap.A_BUTTON),
            ActionMap.CANCEL: tk.StringVar(value=InputMap.B_BUTTON),
            ActionMap.MENU: tk.StringVar(value=InputMap.X_BUTTON),
            ActionMap.DASH: tk.StringVar(value=InputMap.B_BUTTON),
            ActionMap.MAP: tk.StringVar(value=InputMap.SELECT_BUTTON),
            ActionMap.WARP: tk.StringVar(value=InputMap.Y_BUTTON),
            ActionMap.PG_UP: tk.StringVar(value=InputMap.R_SHOULDER),
            ActionMap.PG_DN: tk.StringVar(value=InputMap.L_SHOULDER)
        }

        # Mystery Settings.
        # We have to make tk variable copies of the data structure.
        # There must be a better way.
        ms = MysterySettings()
        ms_mode_keys = ms.game_mode_freqs.keys()
        self.mys_game_mode_freqs = {
            key: tk.StringVar(value='0') for key in ms_mode_keys
        }

        self.mys_item_diff_freqs = {
            key: tk.StringVar(value='0')
            for key in ms.item_difficulty_freqs.keys()
        }

        self.mys_enemy_diff_freqs = {
            key: tk.StringVar(value='0')
            for key in ms.enemy_difficulty_freqs.keys()
        }

        self.mys_tech_order_freqs = {
            key: tk.StringVar(value='0')
            for key in ms.tech_order_freqs.keys()
        }

        self.mys_shop_price_freqs = {
            key: tk.StringVar(value='0')
            for key in ms.shop_price_freqs.keys()
        }

        self.mys_flag_prob_dict = {
            key: tk.StringVar(value=0.5)
            for key in ms.flag_prob_dict.keys()
        }

        self.char_names = {
            'Crono': tk.StringVar(value='Crono'),
            'Marle': tk.StringVar(value='Marle'),
            'Lucca': tk.StringVar(value='Lucca'),
            'Robo': tk.StringVar(value='Robo'),
            'Frog': tk.StringVar(value='Frog'),
            'Ayla': tk.StringVar(value='Ayla'),
            'Magus': tk.StringVar(value='Magus'),
            'Epoch': tk.StringVar(value='Epoch')
        }

        # generation variables
        self.seed = tk.StringVar()
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar()

        self.gen_thread = None

        # Set up the notebook tabs
        self.notebook = ttk.Notebook(self.main_window)
        self.notebook.pack(expand=True)

        self.bucket_page = bucketgui.BucketPage(self.notebook)
        
        self.general_page = self.get_general_page()
        self.tabs_page = self.get_tabs_page()
        self.rc_page = self.get_rc_page()
        self.qol_page = self.get_qol_page()
        self.cosmetic_page = self.get_cosmetic_page()
        self.options_page = self.get_options_page()
        self.extra_page = self.get_extra_page()
        self.mystery_page = self.get_mystery_page()


        # The boss rando page is a little different because the Tk.Listbox
        # does not use an underlying variable.  Instead the
        # self.location_listbox and self.boss_listbox will report their
        # selections as indices into the following two lists
        self.boss_locations = list(rotypes.BossSpotID)

        BossID = rotypes.BossID
        self.bosses = rotypes.get_assignable_bosses()
        self.bosses = sorted(self.bosses, key=str)

        no_shuffle_bosses = [
            # BossID.DRAGON_TANK, BossID.R_SERIES, BossID.MUD_IMP,
            BossID.MAGUS, BossID.BLACK_TYRANO, BossID.MAMMON_M,
            BossID.LAVOS_CORE, BossID.LAVOS_SHELL, BossID.INNER_LAVOS,
            BossID.ZEAL, BossID.ZEAL_2, BossID.TWIN_BOSS
        ]

        for x in no_shuffle_bosses:
            if x in self.bosses:
                self.bosses.remove(x)

        self.ro_page = self.get_ro_page()

        self.notebook.add(self.general_page, text='General')
        self.notebook.add(self.tabs_page, text='Tabs')
        self.notebook.add(self.rc_page, text='RC')
        self.notebook.add(self.ro_page, text='RO')
        self.notebook.add(self.qol_page, text='QoL')
        self.notebook.add(self.cosmetic_page, text='Cos')
        self.notebook.add(self.options_page, text='Opt')
        self.notebook.add(self.extra_page, text='Ext')
        self.notebook.add(self.mystery_page, text='Mys')
        self.notebook.add(self.bucket_page, text='Bucket')

        # This can only be called after all of the widgets are initialized
        self.load_settings_file()

    def get_settings(self):
        return self.__settings

    def set_settings(self, new_settings: Settings):
        self.__settings = new_settings
        # print(self.__settings.char_settings.choices)
        # print(self.__settings.gameflags)
        # print(self.__settings.get_flag_string())
        self.update_gui_vars()

    settings = property(get_settings, set_settings)

    # Methods for loading/unloading settings file.  Should be out of class?
    # Mostly copied from Anguirel's original
    def get_settings_file(self):
        filePath = ""
        if os.name == "nt":
            # If on Windows, put the settings file in roaming appdata
            direct = os.getenv('APPDATA')
            filePath = pathlib.Path(direct).joinpath('JetsOfTime')
        else:
            # If on Mac/Linux, make it a hidden file in the home directory
            filePath = pathlib.Path(os.path.expanduser('~')).joinpath(
                '.JetsOfTime')

        # changing from settings.dat to flags.dat to avoid errors reading
        # the old style settings object
        return filePath.joinpath("flags.dat")

    def save_settings(self):
        filePath = self.get_settings_file()
        if not filePath.parent.exists():
            filePath.parent.mkdir()

        with open(str(filePath), 'wb') as outfile:
            pickle.dump(
                [self.settings,
                 self.input_file.get(),
                 self.output_dir.get()],
                outfile
            )

    def load_settings_file(self):
        filePath = self.get_settings_file()
        if filePath.exists():
            with open(str(filePath), 'rb') as infile:
                try:
                    [settings, input_file, output_dir] = pickle.load(infile)
                    self.settings = settings
                except (ValueError, AttributeError, EOFError, KeyError) as ex:
                    tk.messagebox.showinfo(
                        title='Settings Error',
                        message='Unable to load saved settings.  This often'
                        'happens after an update.  Loading defaults.'
                    )
                    self.settings = Settings.get_race_presets()
                    input_file = ''
                    output_dir = ''

                self.input_file.set(input_file)
                self.output_dir.set(output_dir)
        else:
            self.settings = Settings.get_new_player_presets()
            self.input_file.set('')
            self.output_dir.set('')

    def gui_vars_to_settings(self):
        '''Turns RandoGUI variables back into Settings object'''

        # Seed
        self.settings.seed = self.seed.get()

        # Game Mode
        self.settings.game_mode = \
            GameMode.inv_str_dict()[self.game_mode.get()]

        # Look up difficulty enum given string
        inv_diff_dict = Difficulty.inv_str_dict()

        # Difficulties
        self.settings.item_difficulty = \
            inv_diff_dict[self.item_difficulty.get()]

        self.settings.enemy_difficulty = \
            inv_diff_dict[self.enemy_difficulty.get()]

        # Shop Prices
        self.settings.shopprices = \
            ShopPrices.inv_str_dict()[self.shop_prices.get()]

        # Tech randomization
        self.settings.techorder = \
            TechOrder.inv_str_dict()[self.tech_order.get()]

        # Main flags
        flags = [x for x in list(GameFlags)
                 if self.flag_dict[x].get() == 1]

        # Cosmetic flags
        cosmetic_flags = [x for x in list(CosmeticFlags)
                          if self.cosmetic_flag_dict[x].get() == 1]

        # RO Flags
        ro_flags = [x for x in ROFlags
                    if self.ro_flag_dict[x].get() == 1]

        # In-game options
        self.settings.ctoptions = ctoptions.CTOpts()

        decrement_vars = [
            'menu_background',
            'battle_speed',
            'battle_msg_speed'
        ]

        for attr, value in self.ctopts.items():
            if attr in decrement_vars:
                setattr(self.settings.ctoptions, attr, value.get()-1)
                continue

            setattr(self.settings.ctoptions, attr, value.get())

        for action, button in self.controller_binds.items():
            value = InputMap[button.get().upper().replace(' ', '_')]
            self.settings.ctoptions.controller_binds.mappings[action] = value

        for name in CharNames.default():
            self.settings.char_settings.names[name] = self.char_names[name].get()

        self.settings.gameflags = \
            reduce(lambda a, b: a | b, flags, GameFlags(False))
        self.settings.initial_flags = copy.deepcopy(self.settings.gameflags)
        self.settings.cosmetic_flags = \
            reduce(lambda a, b: a | b, cosmetic_flags, CosmeticFlags(False))

        # Tabs
        self.settings.tab_settings = \
            TabSettings(
                scheme=TabRandoScheme.inv_str_dict()[
                    self.tab_rando_scheme.get()
                ],
                binom_success=self.tab_success_chance.get(),
                power_min=self.power_tab_min.get(),
                power_max=self.power_tab_max.get(),
                magic_min=self.magic_tab_min.get(),
                magic_max=self.magic_tab_max.get(),
                speed_min=self.speed_tab_min.get(),
                speed_max=self.speed_tab_max.get()
            )

        # RC (dup duals already taken, just char choices)
        for i in range(7):
            self.settings.char_settings.choices[i] = []
            for j in range(7):
                if self.char_choices[i][j].get() == 1:
                    self.settings.char_settings.choices[i].append(j)

        # RO Settings
        # print(self.bosses)
        boss_list = [self.bosses[i]
                     for i in self.boss_listbox.curselection()]

        loc_list = [self.boss_locations[i]
                    for i in self.boss_location_listbox.curselection()]

        if loc_list:
            roset = ROSettings(loc_list, boss_list, False)
        else:
            roset = ROSettings.from_game_mode(self.settings.game_mode, bosses=boss_list)
        self.settings.ro_settings = roset
        self.settings.ro_settings.flags = \
            reduce(lambda a, b: a | b, ro_flags, ROFlags(False))

        # Bucket
        self.settings.bucket_settings = self.bucket_page.get_bucket_settings()

        # Mystery settings
        ms = MysterySettings()
        for mode in ms.game_mode_freqs:
            ms.game_mode_freqs[mode] = \
                int(self.mys_game_mode_freqs[mode].get())

        for diff in ms.item_difficulty_freqs:
            ms.item_difficulty_freqs[diff] = \
                int(self.mys_item_diff_freqs[diff].get())

        for diff in ms.enemy_difficulty_freqs:
            ms.enemy_difficulty_freqs[diff] = \
                int(self.mys_enemy_diff_freqs[diff].get())

        for tech_ord in ms.tech_order_freqs:
            ms.tech_order_freqs[tech_ord] = \
                int(self.mys_tech_order_freqs[tech_ord].get())

        for shop_price in ms.shop_price_freqs:
            ms.shop_price_freqs[shop_price] = \
                int(self.mys_shop_price_freqs[shop_price].get())

        for flag in ms.flag_prob_dict:
            ms.flag_prob_dict[flag] = \
                float(self.mys_flag_prob_dict[flag].get())

        self.settings.mystery_settings = ms

        # print(self.settings.gameflags)

    def update_gui_vars(self):

        # Set game mode
        self.game_mode.set(
            GameMode.str_dict()[self.settings.game_mode]
        )

        # Update the flags
        for x in self.flag_dict.keys():
            if x in self.settings.gameflags:
                self.flag_dict[x].set(1)
            else:
                self.flag_dict[x].set(0)

        for x in self.cosmetic_flag_dict.keys():
            if x in self.settings.cosmetic_flags:
                self.cosmetic_flag_dict[x].set(1)
            else:
                self.cosmetic_flag_dict[x].set(0)

        # Char names
        for name in CharNames.default():
            self.char_names[name].set(self.settings.char_settings.names[name])

        increment_vars = [
            'menu_background',
            'battle_speed',
            'battle_msg_speed'
        ]

        for key, item in self.settings.ctoptions:
            if key in increment_vars:
                self.ctopts[key].set(item + 1)
            else:
                self.ctopts[key].set(item)

        for key, item in self.settings.ctoptions.controller_binds:
            self.controller_binds[key].set(item)

        # Update difficulties
        self.enemy_difficulty.set(
            Difficulty.str_dict()[self.settings.enemy_difficulty]
        )

        self.item_difficulty.set(
            Difficulty.str_dict()[self.settings.item_difficulty]
        )

        self.shop_prices.set(
            ShopPrices.str_dict()[self.settings.shopprices]
        )

        self.tech_order.set(
            TechOrder.str_dict()[self.settings.techorder]
        )

        # Tab Page Stuff
        self.power_tab_min.set(self.settings.tab_settings.power_min)
        self.power_tab_max.set(self.settings.tab_settings.power_max)

        self.magic_tab_min.set(self.settings.tab_settings.magic_min)
        self.magic_tab_max.set(self.settings.tab_settings.magic_max)

        self.speed_tab_min.set(self.settings.tab_settings.speed_min)
        self.speed_tab_max.set(self.settings.tab_settings.speed_max)

        self.tab_rando_scheme.set(
            TabRandoScheme.str_dict()[self.settings.tab_settings.scheme]
        )

        self.tab_success_chance.set(self.settings.tab_settings.binom_success)

        # RC char choices
        for i in range(7):
            for j in range(7):
                if j in self.settings.char_settings.choices[i]:
                    self.char_choices[i][j].set(1)
                else:
                    self.char_choices[i][j].set(0)

        # push the ro flag lists
        ro_settings = self.settings.ro_settings
        boss_indices = [self.bosses.index(x)
                        for x in ro_settings.bosses]

        for index in boss_indices:
            self.boss_listbox.select_set(index)

        boss_loc_indices = [self.boss_locations.index(x)
                            for x in ro_settings.spots]

        for index in boss_loc_indices:
            self.boss_location_listbox.select_set(index)

        self.preserve_part_count.set(
            int(ROFlags.PRESERVE_PARTS in ro_settings.flags)
        )

        # Bucket Settings
        bucket_settings = self.settings.bucket_settings
        self.bucket_page.load_bucket_settings(bucket_settings)

        # Mystery Settings
        mys_settings = self.settings.mystery_settings

        settings_dicts = (
            mys_settings.game_mode_freqs,
            mys_settings.item_difficulty_freqs,
            mys_settings.enemy_difficulty_freqs,
            mys_settings.tech_order_freqs,
            mys_settings.shop_price_freqs,
            mys_settings.flag_prob_dict
        )
        gui_dicts = (
            self.mys_game_mode_freqs,
            self.mys_item_diff_freqs,
            self.mys_enemy_diff_freqs,
            self.mys_tech_order_freqs,
            self.mys_shop_price_freqs,
            self.mys_flag_prob_dict
        )

        for set_dict, gui_dict in zip(settings_dicts, gui_dicts):
            for key in set_dict:
                gui_dict[key].set(str(set_dict[key]))

        self.verify_settings()

    # Encodes rules for enabling/disabling options depending on what options
    # have been chosen
    def verify_settings(self):

        # For elements that can be set/reset by various flags, we need to
        # set them all normal, and then disable as needed.

        checkboxes = (
            self.chronosanity_checkbox,
            self.zeal_end_checkbox, self.boss_scaling_checkbox,
            self.unlocked_magic_checkbox,
            self.locked_chars_checkbox, self.fast_pendant_checkbox,
            self.boss_rando_checkbox
        )

        scales = (
            self.tab_prob_scale,
        )

        for checkbox in checkboxes:
            checkbox.config(state=tk.NORMAL)

        for scale in scales:
            scale.config(state=tk.NORMAL, fg='grey')

        # TODO: Dicts for disabling, etc so this can be streamlined
        GF = GameFlags

        lw_disabled_flags = [GF.BOSS_SCALE]
        lw_disabled_elements = [self.boss_scaling_checkbox,
                                self.unlocked_magic_checkbox]

        if self.game_mode.get() == GameMode.str_dict()[GameMode.LOST_WORLDS]:
            for flag in lw_disabled_flags:
                self.flag_dict[flag].set(0)

            self.flag_dict[GF.UNLOCKED_MAGIC].set(1)

            for element in lw_disabled_elements:
                element.config(state=tk.DISABLED)

        ia_disabled_flags = [
            GF.ZEAL_END,
            GF.BOSS_SCALE, GF.BUCKET_LIST,
        ]

        ia_disabled_elements = [
            self.zeal_end_checkbox, self.boss_scaling_checkbox,
            self.unlocked_magic_checkbox
        ]

        if self.game_mode.get() == GameMode.str_dict()[GameMode.ICE_AGE]:

            for flag in ia_disabled_flags:
                self.flag_dict[flag].set(0)

            self.flag_dict[GameFlags.UNLOCKED_MAGIC].set(1)

            for element in ia_disabled_elements:
                element.config(state=tk.DISABLED)

        loc_disabled_flags = [
            GF.ZEAL_END,
            GF.BUCKET_LIST,
            GF.BOSS_RANDO, GF.BOSS_SCALE, GF.BOSS_RANDO
        ]

        loc_disabled_elements = [
            self.zeal_end_checkbox, self.boss_scaling_checkbox,
            self.boss_rando_checkbox
        ]

        if self.game_mode.get() == \
           GameMode.str_dict()[GameMode.LEGACY_OF_CYRUS]:
            for flag in loc_disabled_flags:
                self.flag_dict[flag].set(0)

            self.flag_dict[GameFlags.UNLOCKED_MAGIC].set(1)

            for element in loc_disabled_elements:
                element.config(state=tk.DISABLED)

        if self.flag_dict[GameFlags.CHRONOSANITY].get() == 1:
            self.flag_dict[GameFlags.BOSS_SCALE].set(0)
            self.boss_scaling_checkbox.config(state=tk.DISABLED)

        # Check RC Page
        if self.flag_dict[GameFlags.CHAR_RANDO].get() == 1:
            self.notebook.tab(self.rc_page, state=tk.NORMAL)
        else:
            self.notebook.tab(self.rc_page, state=tk.DISABLED)

        # Check RO Page
        if self.flag_dict[GameFlags.BOSS_RANDO].get() == 1:
            self.notebook.tab(self.ro_page, state=tk.NORMAL)
        else:
            self.notebook.tab(self.ro_page, state=tk.DISABLED)

        # Check Mys Page
        if self.flag_dict[GameFlags.MYSTERY].get() == 1:
            self.notebook.tab(self.mystery_page, state=tk.NORMAL)
        else:
            self.notebook.tab(self.mystery_page, state=tk.DISABLED)

        # Check Bucket Page
        if self.flag_dict[GameFlags.BUCKET_LIST].get() == 1:
            self.notebook.tab(self.bucket_page, state=tk.NORMAL)
        else:
            self.notebook.tab(self.bucket_page, state=tk.DISABLED)

        # check the tab rando slider
        if self.tab_rando_scheme.get() == \
           TabRandoScheme.str_dict()[TabRandoScheme.UNIFORM]:
            self.tab_prob_scale.config(
                state=tk.DISABLED,
                fg='grey'
            )
        else:
            self.tab_prob_scale.config(
                state=tk.NORMAL,
                fg='black'
            )

    # Methods for constructing parts of the layout
    def get_presets_frame(self, parent):
        # Presets
        frame = tk.Frame(
            parent, borderwidth=1,
            highlightbackground="black",
            highlightthickness=1
        )

        row = 0
        # Presets Header
        tk.Label(
            frame,
            text="Preset Selection:"
        ).grid(row=row, column=0, sticky=tk.E)

        # Preset Buttons
        tk.Button(
            frame, text="Race",
            command=lambda: self.set_settings(
                Settings.get_race_presets()
            )
        ).grid(row=row, column=1)

        tk.Button(
            frame, text="Tourney T8",
            command=lambda: self.set_settings(
                Settings.get_tourney_top8_preset()
            )
        ).grid(row=row, column=2)

        tk.Button(
            frame, text="Lost Worlds",
            command=lambda: self.set_settings(
                Settings.get_lost_worlds_presets()
            )
        ).grid(row=row, column=3)

        tk.Button(
            frame, text="Hard",
            command=lambda: self.set_settings(
                Settings.get_hard_presets()
            )
        ).grid(row=row, column=4)

        return frame

    # Called by self.settings_valid
    def rc_settings_valid(self) -> bool:
        # check all character identities have a model associated
        model_missing = any(
            not any(
                model.get() == 1
                for model in self.char_choices[identity]
            )
            for identity in range(7)
        )
        if model_missing:
            return False

        # unless duplicate chars, also check all character models
        # are associated with at least one identity
        if not self.flag_dict[GameFlags.DUPLICATE_CHARS].get() == 1:
            identity_missing = any(
                not any(
                    identity[model].get() == 1
                    for identity in self.char_choices
                )
                for model in range(7)
            )
            if identity_missing:
                return False
        return True

    def get_rc_set_char_choices(self, parent):
        rcframe = tk.Frame(
            parent, borderwidth=1, highlightbackground='black',
            highlightthickness=1
        )

        row = 0
        col = 0

        char_names = CharNames.default()[:-1]

        row += 1

        for i in range(7):
            tk.Label(
                rcframe,
                text=char_names[i],
                anchor='center'
            ).grid(row=row, column=(i+1))

        row += 1

        for i in range(7):
            tk.Label(
                rcframe,
                text=char_names[i]+' choices:',
                anchor="w"
            ).grid(row=row, column=0)

            col += 1

            for j in range(7):
                tk.Checkbutton(
                    rcframe,  # text=char_names[j],
                    variable=self.char_choices[i][j]
                ).grid(row=row, column=col)

                col += 1

            col = 0
            row += 1

        return rcframe

    def get_rc_set_autofill(self, parent):

        # Helper for setting the underlying variables
        def set_all(val):
            for i in range(7):
                for j in self.char_choices[i]:
                    j.set(val)

        rcframe = tk.Frame(
            parent, borderwidth=1, highlightbackground='black',
            highlightthickness=1
        )

        row = 0

        button = tk.Button(rcframe, text='Check All',
                           command=lambda: set_all(1))
        button.grid(row=row, column=0, columnspan=2)

        button = tk.Button(rcframe, text='Uncheck All',
                           command=lambda: set_all(0))
        button.grid(row=row, column=2, columnspan=2)

        rcframe.pack(fill=tk.X)

        return rcframe

    def get_rc_set_additional_options(self, parent):

        rcframe = tk.Frame(parent, borderwidth=1,
                           highlightbackground='black',
                           highlightthickness=1)

        label = tk.Label(rcframe, text='Additional Options')
        label.pack(anchor=tk.W)

        checkbutton = tk.Checkbutton(
            rcframe, text='Duplicate Chars',
            variable=self.flag_dict[GameFlags.DUPLICATE_CHARS]
        )
        checkbutton.pack(anchor=tk.W)
        CreateToolTip(checkbutton,
                      'Check this to enable copies of the same character.')

        checkbutton = tk.Checkbutton(
            rcframe, text='Duplicate Duals',
            variable=self.flag_dict[GameFlags.DUPLICATE_TECHS]
        )
        checkbutton.pack(anchor=tk.W)
        CreateToolTip(checkbutton,
                      'Check this to enable dual techs betweeen copies of the '
                      + 'same character (e.g. Ayla+Ayla beast toss).')

        return rcframe

    def get_general_options(self, parent):
        frame = tk.Frame(
            parent, borderwidth=1,
            highlightbackground="black", highlightthickness=1
        )
        row = 0

        label = tk.Label(frame, text="Game Options:")
        label.grid(row=row, column=0, sticky=tk.W)
        row = row + 1

        # Disable glitches
        checkButton = tk.Checkbutton(
            frame,
            text="Disable Glitches (g)",
            variable=self.flag_dict[GameFlags.FIX_GLITCH]
        )
        checkButton.grid(row=row, column=0, sticky=tk.W, columnspan=2)
        CreateToolTip(
            checkButton,
            "Disables common glitches such as the unequip and save " +
            "anywhere glitches."
        )

        return frame

    def get_difficulty_options(self, parent):
        frame = tk.Frame(
            parent,
            borderwidth=1, highlightbackground="black", highlightthickness=1
        )

        row = 0

        # Dropdown for enemy difficulty

        # There is no Easy mode for enemy stats
        enemy_difficulty_values = [
            str(x)
            for x in Difficulty.str_dict()
            if x != Difficulty.EASY
        ]

        label = tk.Label(frame, text="Enemy Difficulty:")
        label.grid(row=row, column=0, sticky=tk.W)

        self.enemy_diff_dropdown = tk.OptionMenu(
            frame, self.enemy_difficulty, *enemy_difficulty_values
        )

        self.enemy_diff_dropdown.grid(
            row=row, column=1, sticky=tk.W, columnspan=2
        )

        CreateToolTip(
            self.enemy_diff_dropdown,
            'On hard mode, some enemies (particularly bosses) have increased '
            'stats and decreased XP/TP rewards.  See \'Hard Tweaks.txt\' '
            'for a complete list of changes.'
        )

        # row += 1

        # Dropdown for item_difficulty difficulty
        item_difficulty_values = Difficulty.str_dict().values()

        label = tk.Label(frame, text="Item Difficulty:")
        label.grid(row=row, column=3, sticky=tk.W)

        self.item_diff_dropdown = tk.OptionMenu(
            frame, self.item_difficulty, *item_difficulty_values
        )
        self.item_diff_dropdown.grid(
            row=row, column=4, sticky=tk.W, columnspan=2
        )

        CreateToolTip(
            self.item_diff_dropdown,
            'Easier difficulties improve the quality of treasure and enemy '
            'drops.'
        )

        return frame

    def get_general_flags_frame(self, parent):
        frame = tk.Frame(
            parent,
            borderwidth=1,
            highlightbackground="black",
            highlightthickness=1
        )

        row = 0

        label = tk.Label(frame, text="Randomizer Options:")
        label.grid(row=row, column=0, sticky=tk.W)
        row = row + 1

        # Game Mode
        game_mode_values = GameMode.str_dict().values()

        # We want to call self.verify_settings after the OptionMenu is
        # updated.  The command= option forces a string argument of the
        # current selection to the callback.
        # We wrap in a lambda to discard the argument.
        self.game_mode_dropdown = tk.OptionMenu(
            frame,
            self.game_mode,
            *game_mode_values,
            command=lambda x: self.verify_settings()
        )

        self.game_mode_dropdown.config(width=20)
        self.game_mode_dropdown.grid(
            row=row, column=0, sticky=tk.W, columnspan=2
        )

        '''
        # TODO: Redo tool tip for game mode dropdown.  Can tool tips change
        #       dynamically?
        CreateToolTip(
            self.lost_worlds_checkbox,
            'An alternate game mode where you start with access to '
            'Prehistory, the Dark Ages, and the Future. Find the clone and '
            'c.trigger to climb Death Peak and beat the Black Omen, or find '
            'the Dreamstone and Ruby Knife to make your way to Lavos '
            'through the Ocean Palace. 600AD and 1000AD are unavailable '
            'until the very end of the game.'
        )
        '''
        # Boss Rando
        self.boss_rando_checkbox = tk.Checkbutton(
            frame,
            text="Randomize bosses (ro)",
            variable=self.flag_dict[GameFlags.BOSS_RANDO],
            command=self.verify_settings
        )
        self.boss_rando_checkbox.grid(
            row=row, column=2, sticky=tk.W, columnspan=2
        )
        CreateToolTip(
            self.boss_rando_checkbox,
            'Various dungeon bosses are shuffled and scaled.  Does not '
            'affect end game bosses.')
        row = row + 1

        # Boss Scaling
        self.boss_scaling_checkbox = tk.Checkbutton(
            frame,
            text="Boss scaling (b)",
            variable=self.flag_dict[GameFlags.BOSS_SCALE],
            command=self.verify_settings
        )
        self.boss_scaling_checkbox.grid(
            row=row, column=0, sticky=tk.W, columnspan=2
        )
        CreateToolTip(
            self.boss_scaling_checkbox,
            'Bosses are scaled in difficulty based on how many key items '
            'they block.  Early bosses are unaffected.'
        )

        # Zeal 2 End
        self.zeal_end_checkbox = tk.Checkbutton(
            frame,
            text="Zeal 2 as last boss (z)",
            variable=self.flag_dict[GameFlags.ZEAL_END],
            command=self.verify_settings
        )
        self.zeal_end_checkbox.grid(
            row=row, column=2, sticky=tk.W, columnspan=2
        )
        CreateToolTip(
            self.zeal_end_checkbox,
            'The game ends after defeating Zeal 2 when going through the '
            'Black Omen.  Lavos is still required for the Ocean Palace route.'
        )
        row = row + 1

        # Fast Pendant
        self.fast_pendant_checkbox = tk.Checkbutton(
            frame,
            text="Early Pendant Charge (p)",
            variable=self.flag_dict[GameFlags.FAST_PENDANT],
            command=self.verify_settings
        )
        self.fast_pendant_checkbox.grid(
            row=row, column=0, sticky=tk.W, columnspan=2
        )
        CreateToolTip(
            self.fast_pendant_checkbox,
            'The pendant becomes charged immediately upon access to the '
            'Future, granting access to sealed doors and chests.'
        )

        # Locked Chars
        self.locked_chars_checkbox = tk.Checkbutton(
            frame, text="Locked characters (c)",
            variable=self.flag_dict[GameFlags.LOCKED_CHARS],
            command=self.verify_settings
        )
        self.locked_chars_checkbox.grid(
            row=row, column=2, sticky=tk.W, columnspan=2
        )
        CreateToolTip(
            self.locked_chars_checkbox,
            'The Dreamstone is required to access the character in the '
            'Dactyl Nest and power must be turned on at the Factory before '
            'the Proto Dome character can be obtained.'
        )
        row = row + 1

        self.unlocked_magic_checkbox = tk.Checkbutton(
            frame,
            text="Unlocked Magic (m)",
            variable=self.flag_dict[GameFlags.UNLOCKED_MAGIC],
            command=self.verify_settings
        )
        self.unlocked_magic_checkbox.grid(
            row=row, column=0, sticky=tk.W, columnspan=2
        )
        CreateToolTip(
            self.unlocked_magic_checkbox,
            'Magic is unlocked at the start of the game, no trip to Spekkio '
            'required.'
        )

        # Tab Treasures
        self.tab_treasure_checkbox = tk.Checkbutton(
            frame,
            text="Make all treasures tabs (tb)",
            variable=self.flag_dict[GameFlags.TAB_TREASURES],
            command=self.verify_settings
        )
        self.tab_treasure_checkbox.grid(
            row=row, column=2, sticky=tk.W, columnspan=3
        )
        CreateToolTip(
            self.tab_treasure_checkbox,
            'All treasures chest contents are replaced with power, magic, '
            'or speed tabs.'
        )
        row = row + 1

        # Chronosanity
        self.chronosanity_checkbox = tk.Checkbutton(
            frame, text="Chronosanity (cr)",
            variable=self.flag_dict[GameFlags.CHRONOSANITY],
            command=self.verify_settings,
        )
        self.chronosanity_checkbox.grid(
            row=row, sticky=tk.W, columnspan=2
        )
        CreateToolTip(
            self.chronosanity_checkbox,
            'Key items can now show up in most treasure chests in addition '
            'to their normal locations.'
        )

        # Character Rando
        self.char_rando_checkbox = tk.Checkbutton(
            frame,
            text="Character Rando (rc)",
            variable=self.flag_dict[GameFlags.CHAR_RANDO],
            command=self.verify_settings
        )
        self.char_rando_checkbox.grid(
            row=row, column=2, sticky=tk.W, columnspan=2
        )
        CreateToolTip(
            self.char_rando_checkbox,
            'Character identities are randomized. Each named character '
            'identity uses a random character model; techs match character '
            'model and identity determines progression (e.g. the '
            'character named "Marle" could be an "Ayla" model with Ayla '
            'techs and needed for Marle\'s Prism Shard quest).')
        row = row + 1

        checkbox = tk.Checkbutton(
            frame,
            text='Randomize Healing Items (h)',
            variable=self.flag_dict[GameFlags.HEALING_ITEM_RANDO]
        )
        checkbox.grid(row=row, column=0, stick=tk.W, columnspan=2)

        CreateToolTip(
            checkbox,
            'Amount healed by Tonics and Ethers are randomized.  Strength '
            'order of regular/mid/full is preserved.  Lapis can roll as a '
            'party-wide MP heal.'
        )

        checkbox = tk.Checkbutton(
            frame,
            text='Randomize Gear (q)',
            variable=self.flag_dict[GameFlags.GEAR_RANDO]
        )
        checkbox.grid(row=row, column=2, stick=tk.W, columnspan=2)

        CreateToolTip(
            checkbox,
            'Random effects on some accessories.  Random stat boosts and '
            'effects on weapons and armor according to their tier.'
        )
        row += 1

        # Mystery seed checkbox
        self.mystery_checkbox = tk.Checkbutton(
            frame,
            text='Mystery Seed',
            variable=self.flag_dict[GameFlags.MYSTERY],
            command=self.verify_settings,
        )
        self.mystery_checkbox.grid(
            row=row, column=0, sticky=tk.W, columnspan=2
        )

        checkbox = tk.Checkbutton(
            frame,
            text='Epoch Fail (ef)',
            variable=self.flag_dict[GameFlags.EPOCH_FAIL]
        )
        checkbox.grid(row=row, column=2,  sticky=tk.W, columnspan=2)

        CreateToolTip(
            checkbox,
            'Players start without wings on the '
            'Epoch.  The \'Jets of Time\' can be obtained and turned in '
            'to Dalton in the Snail Stop to upgrade the Epoch.'
        )

        row += 1

        # Shop Prices dropdown
        shop_price_values = ShopPrices.str_dict().values()
        label = tk.Label(frame, text="Shop Prices:")
        label.grid(row=row, column=0, sticky=tk.W)

        self.shop_price_dropdown = tk.OptionMenu(
            frame,
            self.shop_prices,
            *shop_price_values
        )
        self.shop_price_dropdown.config(width=20)
        self.shop_price_dropdown.grid(
            row=row, column=1, sticky=tk.W, columnspan=2
        )

        CreateToolTip(
            self.shop_price_dropdown,
            "Determines shop prices:\n"
            "Normal - Standard randomizer shop prices\n"
            "Free - Everything costs 1G (minimum allowed by the game)\n"
            "Mostly Random - Random prices except for some key consumables\n"
            "Fully Random - Random price for every item"
        )

        row += 1

        tech_order_values = TechOrder.str_dict().values()
        label = tk.Label(frame, text="Tech Randomization:")
        label.grid(row=row, column=0, sticky=tk.W)

        self.tech_order_dropdown = tk.OptionMenu(
            frame, self.tech_order, *tech_order_values)
        self.tech_order_dropdown.config(width=20)
        self.tech_order_dropdown.grid(
            row=row, column=1, sticky=tk.W, columnspan=2
        )

        CreateToolTip(
            self.tech_order_dropdown,
            "Determines the order in which techs are learned:\n"
            "Normal - Vanilla tech order.\n"
            "Balanced Random - Random tech order, but stronger techs are "
            "more likely to show up later.\n"
            "Fully Random - Tech order is fully randomized."
        )
        row = row + 1

        return frame

    def get_generate_options(self, parent):
        frame = tk.Frame(
            parent,
            borderwidth=1, highlightbackground="black",
            highlightthickness=1
        )
        frame.columnconfigure(4, weight=1)
        row = 0

        # Let the user choose a seed (optional parameter)
        label = tk.Label(frame, text="Seed(optional):")
        label.grid(row=row, column=0, sticky=tk.W+tk.E)

        tk.Entry(
            frame, textvariable=self.seed
        ).grid(row=row, column=1, columnspan=3)
        CreateToolTip(
            label,
            'Enter a seed for the randomizer.  Games generated with the '
            'same seed and flags will be identical every time.  This field '
            'is optional and a seed will be randomly selected if none is '
            'provided.'
        )
        row = row + 1

        # Let the user select the base ROM to copy and patch
        label = tk.Label(frame, text="Input ROM:")
        label.grid(row=row, column=0, sticky=tk.W+tk.E)
        tk.Entry(
            frame, textvariable=self.input_file
        ).grid(row=row, column=1, columnspan=3)
        tk.Button(
            frame,
            text="Browse",
            command=lambda: self.input_file.set(askopenfilename())
        ).grid(row=row, column=4, sticky=tk.W)
        CreateToolTip(
            label,
            'The vanilla Chrono Trigger ROM used to generate a randomized '
            'game.'
        )
        row = row + 1

        # Let the user select the output directory
        label = tk.Label(frame, text="Output Folder:")
        label.grid(row=row, column=0, sticky=tk.W+tk.E)

        tk.Entry(
            frame, textvariable=self.output_dir
        ).grid(row=row, column=1, columnspan=3)

        tk.Button(
            frame, text="Browse",
            command=lambda: self.output_dir.set(askdirectory())
        ).grid(row=row, column=4, sticky=tk.W)
        CreateToolTip(
            label,
            'The output location of the randomized ROM.  Defaults to the '
            'input ROM location if left blank.'
        )
        row = row + 1

        # Add a progress bar to the GUI for ROM generation
        self.progressBar = ttk.Progressbar(
            frame, orient='horizontal', mode='indeterminate'
        )
        self.progressBar.grid(
            row=row, column=0, columnspan=5, sticky=tk.E+tk.W
        )
        row = row + 1

        tk.Button(
            frame, text="Generate", command=self.generate_handler
        ).grid(row=row, column=2, sticky=tk.W, columnspan=2)

        return frame

    def settings_valid(self):

        # First check the mystery settings page.  Perhaps we can use it to
        # better inform error message.
        if self.flag_dict[GameFlags.MYSTERY].get() == 1 or True:
            mys_valid = self.mys_settings_valid()
            if not mys_valid:
                return

        # Check for bad input from RC page
        if not self.rc_settings_valid():
            rc_err = (
                'Each character identity (row) must have at least '
                'one model (column) selected.'
            )
            if not self.flag_dict[GameFlags.DUPLICATE_CHARS].get() == 1:
                rc_err += (
                    ' Each character model (column) must have at least '
                    'one identity (row) selected.'
                )
            if self.flag_dict[GameFlags.CHAR_RANDO].get() == 1:
                self.notebook.select(self.rc_page)
                messagebox.showerror('RC Settings Error', rc_err)
                return
            elif self.flag_dict[GameFlags.MYSTERY].get() == 1:
                messagebox.showerror(
                    'RC+Mystery Settings Error',
                    rc_err,
                    'Enable rc flag and adjust the settings.'
                )
                return

        # Check for bad input in controller binds
        testbinds = {}
        for action, button in self.controller_binds.items():
            try:
                value = InputMap[button.get().upper().replace(' ', '_')]
            except Exception:
                messagebox.showerror(
                    'Options Controller Error',
                    'All button binds must be set.'
                )
                self.notebook.select(self.options_page)
                return
            testbinds[action] = value

        if not ctoptions.ControllerBinds.is_valid_mappings(testbinds):
            messagebox.showerror(
                'Options Controller Error',
                'Invalid input in button binds.'
            )
            self.notebook.select(self.options_page)
            return

        # Check for bad input from RO page
        boss_loc_dict = rotypes.get_default_boss_assignment()

        if self.flag_dict[GameFlags.BOSS_RANDO].get() == 1 or \
           self.flag_dict[GameFlags.MYSTERY].get() == 1:
            loc_selection_ind = self.boss_location_listbox.curselection()
            boss_selection_ind = self.boss_listbox.curselection()

            if self.preserve_part_count.get() == 1:
                # Legacy Boss Rando is on.  Cue many annoying checks.
                # Some of this can be cleaned up, but I'm hoping the option
                # goes away in favor of 'Safe Mode' flags.

                # Check one spots
                one_part_bosses = rotypes.get_one_part_bosses()
                one_part_boss_ind = [
                    i for i in boss_selection_ind
                    if self.bosses[i] in one_part_bosses
                ]
                one_part_loc_ind = [
                    i for i in loc_selection_ind
                    if boss_loc_dict[self.boss_locations[i]] in one_part_bosses
                ]

                if len(one_part_boss_ind) < len(one_part_loc_ind):
                    messagebox.showerror(
                        'RO Settings Error',
                        f"Legacy boss randomization set with "
                        f"{len(one_part_loc_ind)} one part bosses set "
                        f"but only {len(one_part_boss_ind)} one part bosses "
                        "set.\n"
                        "Try hitting the \"Loc to Boss\" button."
                    )
                    self.notebook.select(self.ro_page)
                    return False

                # Check two spots -- some code duplication here is ugly
                two_part_bosses = rotypes.get_two_part_bosses()
                two_part_boss_ind = [
                    i for i in boss_selection_ind
                    if self.bosses[i] in two_part_bosses
                ]
                two_part_loc_ind = [
                    i for i in loc_selection_ind
                    if boss_loc_dict[self.boss_locations[i]] in two_part_bosses
                ]

                if len(two_part_boss_ind) < len(two_part_loc_ind):
                    messagebox.showerror(
                        'RO Settings Error',
                        f"Legacy boss randomization set with "
                        f"{len(two_part_loc_ind)} two part bosses set "
                        f"but only {len(two_part_boss_ind)} two part bosses "
                        "set.\n"
                        "Try hitting the \"Loc to Boss\" button."
                    )
                    self.notebook.select(self.ro_page)
                    return False

                one_two_part_bosses = one_part_bosses + two_part_bosses

                multi_part_boss_ind = [
                    i for i in boss_selection_ind
                    if self.bosses[i] not in one_two_part_bosses
                ]

                multi_part_loc_ind = [
                    i for i in loc_selection_ind
                    if boss_loc_dict[self.boss_locations[i]]
                    not in one_two_part_bosses
                ]

                err_msg = str()
                if len(multi_part_boss_ind) > 0:
                    err_msg += (
                        'The following bosses are not allowed with Legacy '
                        'boss randomization:\n'
                    )

                    for i in multi_part_boss_ind:
                        err_msg += f"    {str(self.bosses[i])}\n"

                if len(multi_part_loc_ind) > 0:
                    err_msg += (
                        '\nThe following boss locations are not allowed with '
                        'Legacy boss randomization:\n'
                    )

                    for i in multi_part_loc_ind:
                        err_msg += f"    {str(self.boss_locations[i])}\n"

                if len(err_msg) > 0:
                    messagebox.showerror(
                        'RO Settings Error',
                        err_msg
                    )
                    self.notebook.select(self.ro_page)
                    return False
            else:
                # Legacy Boss Rando is not on.
                if len(boss_selection_ind) < len(loc_selection_ind):
                    messagebox.showerror(
                        'RO Settings Error',
                        f"Not enough bosses ({len(boss_selection_ind)}) "
                        f"to fill the locations ({len(loc_selection_ind)}.  "
                        "Please use the \"Loc to Boss\" button to fix this."
                    )
                    self.notebook.select(self.ro_page)
                    return False
        # End if boss rando set

        # Check the default character names
        good_symbols = set(
            x for x in range(0xA0, 0xEE)
        )
        good_symbols.add(0)

        for char_name, var in self.char_names.items():
            try:
                new_name = var.get()
                ct_name = ctstrings.CTNameString.from_string(new_name,
                                                             length=6,
                                                             pad_val=0)
            except ValueError as err:
                messagebox.showerror(
                    'Name Error',
                    f'Error in {char_name}\'s name: Can\'t parse '
                    f'\'{str(err)}\''
                )
                self.notebook.select(self.cosmetic_page)
                return False

            ct_name.append(0)
            true_len = ct_name.find(0)
            if true_len > 5:
                messagebox.showerror(
                    'Name Error',
                    f'Error in {char_name}\'s name: length can not exceed '
                    'five characters.'
                )
                self.notebook.select(self.cosmetic_page)
                return False

            symbol_set = set(x for x in ct_name)
            if not symbol_set.issubset(good_symbols):
                messagebox.showwarning(
                    'Name Warning',
                    f'{char_name}\'s name has unusual symbols.  This may be '
                    'unstable.'
                )

        passed, msg = self.bucket_page.validate_hints()
        if not passed:
            messagebox.showerror('Objective Error', msg)
            self.notebook.select(self.bucket_page)
            return False

        # Check the paths so that we don't have to do it later.
        input_path = pathlib.Path(self.input_file.get())
        if not input_path.is_file():
            tk.messagebox.showerror(
                title='Invalid Input ROM Path',
                message='Provided path to Chrono Trigger ROM is invalid'
            )
            return False

        output_path = pathlib.Path(self.output_dir.get())
        if not (self.output_dir.get() == '' or output_path.is_dir):
            tk.messagebox.showerror(
                title='Invalid Output Directory',
                message='Provided path to output directory is invalid.'
            )
            return False

        # Failed to find an error
        return True

    def mys_settings_valid(self) -> bool:
        format_error = False

        dists = (self.mys_game_mode_freqs,
                 self.mys_item_diff_freqs,
                 self.mys_enemy_diff_freqs,
                 self.mys_tech_order_freqs,
                 self.mys_shop_price_freqs)

        for dist in dists:
            dist_sum = 0
            for key in dist:
                val = dist[key]
                try:
                    int_val = int(val.get())
                except ValueError:
                    format_error = True
                    int_val = 0

                if int_val < 0:
                    format_error = True

                if format_error:
                    messagebox.showerror(
                        'Mystery Settings Error',
                        'Relative frequencies must be nonnegative integers.'
                    )
                    self.notebook.select(self.mystery_page)
                    return False

                dist_sum += int_val

            if dist_sum == 0:
                messagebox.showerror(
                    'Mystery Settings Error',
                    'Each category must have at least one positive frequency.'
                )
                self.notebook.select(self.mystery_page)
                return False

        prob_error = False
        for flag in self.mys_flag_prob_dict:
            try:
                flag_prob = float(self.mys_flag_prob_dict[flag].get())
            except ValueError:
                flag_prob = 0
                prob_error = True

            if not (0 <= flag_prob <= 1):
                prob_error = True

            if prob_error:
                messagebox.showerror(
                    'Mystery Settings Error',
                    'Each probability must be a decimal number between 0 '
                    'and 1 (inclusive).'
                )
                return False

        return True

    def get_rom_from_file(self) -> bytearray:
        infile_path = pathlib.Path(self.input_file.get())

        if not infile_path.exists():
            raise FileNotFoundError

        with open(str(infile_path), 'rb') as infile:
            rom = bytearray(infile.read())

            if len(rom) % 0x400 == 0x200:
                print('Header detectected.  Header will be removed from the'
                      'output rom.')
                rom = rom[0x200:]

        return rom

    def randomize(self):
        self.gui_vars_to_settings()

        # Settings are tested when the generate button is clicked.
        # Maybe we should test them inside this method instead?

        rom = self.get_rom_from_file()

        valid = ctrom.CTRom.validate_ct_rom_bytes(rom)
        proceed = True
        if not valid:
            proceed = tk.messagebox.askyesno(
                title='Warning',
                message=(
                    'Provided rom is not a vanilla Chrono Trigger '
                    'rom.  Randomization is likely to fail.  Proceed?'
                )
            )

        if proceed:
            seed = self.settings.seed
            if seed is None or seed == '':
                names = randomizer.read_names()
                seed = ''.join([random.choice(names) for i in range(2)])
                self.settings.seed = seed
                self.seed.set(seed)

            rando = randomizer.Randomizer(rom, is_vanilla=False)
            rando.settings = self.settings
            try:
                rando.set_random_config()
                out_rom = rando.get_generated_rom()
            except Exception as ex:
                tk.messagebox.showerror(
                    title='Error generating rom!', message=str(ex)
                )
                # clear seed field on error
                self.seed.set('')
            else:
                input_path = pathlib.Path(self.input_file.get())

                if self.output_dir is None or self.output_dir.get() == '':
                    self.output_dir.set(str(input_path.parent))

                base_name = pathlib.Path(input_path.name.split('.')[0])
                out_dir = pathlib.Path(self.output_dir.get())

                writer = randomizer.RandomizerWriter(rando, base_name=base_name)
                writer.write_output_rom(out_dir)
                writer.write_spoiler_log(out_dir)
                writer.write_json_spoiler_log(out_dir)

                tk.messagebox.showinfo(
                    title='Randomization Complete',
                    message=f'Randomization Complete.  Seed: {seed}.'
                )

                self.save_settings()

        # Regardless of generation, stop the progress bar
        self.progressBar.stop()
        self.progressBar.config(value=0)

    def generate_handler(self):
        if self.gen_thread is None or not self.gen_thread.is_alive():

            if self.settings_valid():
                self.gen_thread = threading.Thread(target=self.randomize)
                self.progressBar.start(50)
                self.gen_thread.start()

    def get_general_page(self):
        frame = ttk.Frame(self.notebook)
        self.get_presets_frame(frame).pack(fill='both', expand=True)
        self.get_difficulty_options(frame).pack(fill='both', expand=True)
        self.get_general_options(frame).pack(fill='both', expand=True)
        self.get_general_flags_frame(frame).pack(fill='both', expand=True)
        self.get_generate_options(frame).pack(fill='both', expand=True)

        return frame

    def get_tabs_page(self):

        page = tk.Frame(self.notebook)

        frame = tk.Frame(
            page, borderwidth=1,
            highlightbackground="black",
            highlightthickness=1
        )

        tk.Label(
            frame, text='Tab Magnitudes:'
        ).pack(side='left', fill='both', expand=True)

        self.get_tab_magnigtude_frame(
            frame,
            'Power',
            self.power_tab_min,
            self.power_tab_max
        ).pack(fill=tk.X)

        self.get_tab_magnigtude_frame(
            frame,
            'Magic',
            self.magic_tab_min,
            self.magic_tab_max
        ).pack(fill=tk.X)

        self.get_tab_magnigtude_frame(
            frame,
            'Speed',
            self.speed_tab_min,
            self.speed_tab_max
        ).pack(fill=tk.X)

        frame.pack(fill=tk.X)

        frame = tk.Frame(page)

        tk.Label(
            frame, text='Tab Randomization Scheme: '
        ).grid(row=0, column=0, columnspan=3)

        tab_rando_options = TabRandoScheme.str_dict().values()
        tab_scheme_dropdown = ttk.OptionMenu(
            frame,
            self.tab_rando_scheme,
            None,
            *tab_rando_options,
            command=lambda x: self.verify_settings()
        )
        tab_scheme_dropdown.grid(row=0, column=3)

        tk.Label(frame, text='p = ').grid(row=1, column=0)

        self.tab_prob_scale = tk.Scale(
            frame,
            from_=0,
            to=1,
            length=300,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            variable=self.tab_success_chance
        )

        self.tab_prob_scale.grid(row=1, column=1, columnspan=3)

        frame.pack()

        return page

    def get_tab_magnigtude_frame(self, parent,
                                 tab_type: str,
                                 min_val: tk.IntVar,
                                 max_val: tk.IntVar):

        def set_high_given_low(low: int, high: tk.IntVar):
            a = low
            b = high.get()

            if a > b:
                high.set(a)

        def set_low_given_high(low: tk.IntVar, high: int):
            a = low.get()
            b = high

            if a > b:
                low.set(b)

        frame = tk.Frame(parent)

        row = 0

        tab_choices = [x for x in range(1, 10)]

        label = tk.Label(
            frame,
            text=tab_type+' Min:'
        )
        label.grid(row=row, column=0, sticky=tk.E)

        min_dropdown = ttk.OptionMenu(
            frame,
            min_val,
            1,  # Have to set a default for integer options
            *tab_choices,
            command=lambda x: set_high_given_low(x, max_val)
        )
        min_dropdown.grid(row=row, column=1)

        label = tk.Label(
            frame,
            text=tab_type+' Max:'
        )
        label.grid(row=row, column=3, sticky=tk.E)

        max_dropdown = ttk.OptionMenu(
            frame,
            max_val,
            1,  # Have to set a default for integer options
            *tab_choices,
            command=lambda x: set_low_given_high(min_val, x)
        )
        max_dropdown.grid(row=row, column=4)

        return frame

    def get_rc_page(self):
        frame = ttk.Frame(self.notebook)

        instruction_frame = tk.Frame(frame)

        tk.Label(
            instruction_frame,
            text='Indicate allowed character assignments below:'
        ).pack(fill=tk.X, side=tk.LEFT)

        instruction_frame.pack(fill=tk.X)

        self.get_rc_set_char_choices(frame).pack(fill=tk.X)
        self.get_rc_set_autofill(frame).pack(fill=tk.X)
        self.get_rc_set_additional_options(frame).pack(fill=tk.X)

        return frame

    # returns listbox, containing frame
    def get_ro_listbox(self, parent, options, label_text):

        # frame containing everything: listbox, scrollbar, all/none buttons
        outerframe = ttk.Frame(parent)

        # frame for listbox, scrollbar, label
        lbframe = ttk.Frame(outerframe)

        tk.Label(
            lbframe,
            text=label_text,
            anchor=tk.CENTER
        ).pack(fill=tk.X)

        listbox = tk.Listbox(
            lbframe,
            selectmode=tk.MULTIPLE,
            exportselection=0
        )

        sb = tk.Scrollbar(lbframe, orient=tk.VERTICAL)

        # attach scrollbar to listbox
        listbox.configure(yscrollcommand=sb.set)
        sb.config(command=listbox.yview)

        for ind, obj in enumerate(options):
            listbox.insert(ind, str(obj))

        # Fill both in Y so the scrollbar matches the listbox
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.pack(fill=tk.Y)

        lbframe.pack(side=tk.TOP)

        # Helpers for (un)set all
        def set_all(listbox: tk.Listbox):
            for x in range(listbox.size()):
                listbox.selection_set(x)

        def unset_all(listbox: tk.Listbox):
            for x in range(listbox.size()):
                listbox.selection_clear(x)

        buttonframe = ttk.Frame(outerframe)
        tk.Button(
            buttonframe,
            text='All',
            command=lambda: set_all(listbox)
        ).pack(side=tk.LEFT)

        tk.Button(
            buttonframe,
            text='None',
            command=lambda: unset_all(listbox)
        ).pack(side=tk.RIGHT)

        buttonframe.pack(side=tk.TOP)

        return listbox, outerframe

    def get_ro_boss_location_listboxes(self, parent):

        ret_frame = ttk.Frame(parent)

        self.boss_location_listbox, frame = \
            self.get_ro_listbox(
                ret_frame,
                self.boss_locations,
                'Location Pool'
            )
        frame.pack(side=tk.LEFT, padx=(15, 0))

        self.boss_listbox, frame = \
            self.get_ro_listbox(
                ret_frame,
                self.bosses,
                'Boss Pool'
            )
        frame.pack(side=tk.RIGHT, padx=(0, 15))

        return ret_frame

    def get_ro_listbox_settings_buttons(self, parent):
        outerframe = ttk.Frame(parent)

        # frame for three special buttons
        frame = ttk.Frame(outerframe)

        boss_loc_dict = rotypes.get_default_boss_assignment()

        # Helper method for propogating locations to bosses
        def location_to_boss():
            loc_ind = self.boss_location_listbox.curselection()

            loc_boss_ind = [
                self.bosses.index(boss_loc_dict[self.boss_locations[x]])
                for x in loc_ind
            ]

            for x in loc_boss_ind:
                self.boss_listbox.selection_set(x)

        def restrict_boss_to_loc():
            loc_ind = self.boss_location_listbox.curselection()

            loc_boss_ind = [
                self.bosses.index(boss_loc_dict[self.boss_locations[x]])
                for x in loc_ind
            ]

            for x in range(len(self.bosses)):
                if x not in loc_boss_ind:
                    self.boss_listbox.selection_clear(x)

        def all_but_unselected_loc():
            loc_ind = self.boss_location_listbox.curselection()
            loc_ind_comp = [x for x in range(len(self.boss_locations))
                            if x not in loc_ind]

            loc_boss_ind_comp = [
                self.bosses.index(boss_loc_dict[self.boss_locations[x]])
                for x in loc_ind_comp
            ]

            for x in range(len(self.bosses)):
                if x in loc_boss_ind_comp:
                    self.boss_listbox.selection_clear(x)
                else:
                    self.boss_listbox.selection_set(x)

        loc_to_boss_button = tk.Button(
            frame,
            text='Loc to Boss',
            command=location_to_boss
        )
        loc_to_boss_button.pack(side=tk.LEFT)
        CreateToolTip(
            loc_to_boss_button,
            'Selects all bosses corresponding to the locations selected. '
            'Does not deselect any already selected bosses.  Ensures that '
            'a vanilla placement is possible.'
        )

        restrict_to_loc_button = tk.Button(
            frame,
            text='Restrict Boss to Loc',
            command=restrict_boss_to_loc
        )
        restrict_to_loc_button.pack(side=tk.LEFT)
        CreateToolTip(
            restrict_to_loc_button,
            'Deselects bosses that do not correspond to the selected '
            'locations.'
        )

        all_but_unselected_loc_button = tk.Button(
            frame,
            text='All Possible from Locs',
            command=all_but_unselected_loc
        )
        all_but_unselected_loc_button.pack(side=tk.LEFT)
        CreateToolTip(
            all_but_unselected_loc_button,
            'Select all bosses except those from unselected locations.'
        )

        frame.pack(side=tk.TOP)

        extraoptionframe = ttk.Frame(outerframe)

        checkbox = tk.Checkbutton(
            extraoptionframe,
            text='Legacy Boss Placement',
            variable=self.preserve_part_count
        )
        checkbox.pack(anchor=tk.W)

        CreateToolTip(
            checkbox,
            'Follow 3.1 boss randomizer rules.  N part bosses will be only '
            'be placed in locations which normally contain an N part boss. '
        )

        checkbox = tk.Checkbutton(
            extraoptionframe,
            text='Boss Spot HPs',
            variable=self.ro_flag_dict[ROFlags.BOSS_SPOT_HP]
        )
        checkbox.pack(anchor=tk.W)

        CreateToolTip(
            checkbox,
            'Boss HP in boss rando is determined by the spot instead of the '
            'usual scaling algorithm'
        )

        extraoptionframe.pack(anchor=tk.W)

        return outerframe

    def get_ro_page(self):
        frame = ttk.Frame(self.notebook)

        self.get_ro_boss_location_listboxes(frame).pack()
        self.get_ro_listbox_settings_buttons(frame).pack()

        return frame

    def get_qol_page(self):
        frame = ttk.Frame(self.notebook)

        checkbox = tk.Checkbutton(
            frame,
            text='Sightscope Always On',
            variable=self.flag_dict[GameFlags.VISIBLE_HEALTH]
        )
        checkbox.pack(anchor=tk.W)
        CreateToolTip(
            checkbox,
            'The sightscope effect will always be present in battle.  '
            'Note that this does change which enemies can have their HP seen '
            'by the sightscope.'
        )

        checkbox = tk.Checkbutton(
            frame,
            text='Boss Sightscope',
            variable=self.flag_dict[GameFlags.BOSS_SIGHTSCOPE]
        )
        checkbox.pack(anchor=tk.W)
        CreateToolTip(
            checkbox,
            'Enable the sightscope to see boss HP values.'
        )

        checkbox = tk.Checkbutton(
            frame,
            text='Fast Tabs',
            variable=self.flag_dict[GameFlags.FAST_TABS]
        )
        checkbox.pack(anchor=tk.W)

        CreateToolTip(
            checkbox,
            'Players are not frozen in place when tabs are picked up.  '
            'The power tab on the Death Peak entrance is the only '
            'exception.'
        )

        checkbox = tk.Checkbutton(
            frame,
            text='Free Menu Glitch',
            variable=self.flag_dict[GameFlags.FREE_MENU_GLITCH]
        )
        checkbox.pack(anchor=tk.W)

        CreateToolTip(
            checkbox,
            'After the screen fade before Mammon Machine and Lavos 3 the '
            'player regains control for two seconds in order to input a menu '
            'command.'
        )

        return frame

    def get_extra_page(self):
        frame = ttk.Frame(self.notebook)

        checkbox = tk.Checkbutton(
            frame,
            text='Use Anti-Life',
            variable=self.flag_dict[GameFlags.USE_ANTILIFE]
        )
        checkbox.pack(anchor=tk.W)

        CreateToolTip(
            checkbox,
            'Anti-Life is a powerful, single target, nonelemental spell '
            'which also kills its user.  If enabled, this will replace black '
            'hole in Magus\'s tech list.'
        )

        checkbox = tk.Checkbutton(
            frame,
            text='Tackle On-Hit Effects',
            variable=self.flag_dict[GameFlags.TACKLE_EFFECTS_ON]
        )
        checkbox.pack(anchor=tk.W)

        CreateToolTip(
            checkbox,
            'Allow Robo Tackle to gain the on hit effects of weapons, most '
            'notably, the Crisis Arm.'
        )

        checkbox = tk.Checkbutton(
            frame,
            text='Starters Sufficient',
            variable=self.flag_dict[GameFlags.STARTERS_SUFFICIENT]
        )
        checkbox.pack(anchor=tk.W)

        CreateToolTip(
            checkbox,
            'For Standard Game mode only.  The game will be completable '
            'through Omen and Ocean Palace with only the starting two. '
            'It is possible but not guaranteed that Magus\'s castle will be '
            'available if Frog is among the starters.'
        )

        CreateToolTip(
            checkbox,
            'Players start without wings on the '
            'Epoch.  The \'Jets of Time\' can be obtained and turned in '
            'to Dalton in the Snail Stop to upgrade the Epoch.'
        )

        checkbox = tk.Checkbutton(
            frame,
            text='Bucket List',
            variable=self.flag_dict[GameFlags.BUCKET_LIST],
            command=self.verify_settings
        )
        checkbox.pack(anchor=tk.W)

        CreateToolTip(
            checkbox,
            'Allow for objectives to control bucket activation.'
        )

        checkbox = tk.Checkbutton(
            frame,
            text='Tech Damage Randomization',
            variable=self.flag_dict[GameFlags.TECH_DAMAGE_RANDO],
        )
        checkbox.pack(anchor=tk.W)

        CreateToolTip(
            checkbox,
            'Randomize damage inflicted by single techs.'
        )

        ercheck = tk.Checkbutton(
            frame,
            text='Element Randomization',
            variable=self.flag_dict[GameFlags.ELEMENT_RANDO]
        )
        ercheck.pack(anchor=tk.W)

        CreateToolTip(
            ercheck,
            'Shuffle the 4 elements among characters and Robo techs.'
        )

        plus_ki_flags = [
            GameFlags.RESTORE_JOHNNY_RACE, GameFlags.RESTORE_TOOLS
        ]

        adjust_spot_flags = [
            GameFlags.ADD_BEKKLER_SPOT, GameFlags.ADD_OZZIE_SPOT,
            GameFlags.ADD_RACELOG_SPOT, GameFlags.VANILLA_ROBO_RIBBON,
            GameFlags.ADD_CYRUS_SPOT, GameFlags.REMOVE_BLACK_OMEN_SPOT
        ]

        ki_neutral_flags = [
            GameFlags.UNLOCKED_SKYGATES, GameFlags.ADD_SUNKEEP_SPOT,
            GameFlags.SPLIT_ARRIS_DOME, GameFlags.VANILLA_DESERT,
            GameFlags.ROCKSANITY
        ]

        flag_names = {
            GameFlags.UNLOCKED_SKYGATES: 'Unlocked Skygates',
            GameFlags.ADD_SUNKEEP_SPOT: 'Add Sun Keep Spot',
            GameFlags.ADD_BEKKLER_SPOT: 'Add Bekkler Spot',
            GameFlags.ADD_CYRUS_SPOT: 'Add Cyrus Grave Spot',
            GameFlags.RESTORE_TOOLS: 'Restore Tools',
            GameFlags.ADD_OZZIE_SPOT: 'Add Ozzie\'s Fort Spot',
            GameFlags.RESTORE_JOHNNY_RACE: 'Restore Johnny Race',
            GameFlags.ADD_RACELOG_SPOT: 'Add Race Log Spot',
            GameFlags.REMOVE_BLACK_OMEN_SPOT: 'Remove Black Omen Spot',
            GameFlags.SPLIT_ARRIS_DOME: 'Split Arris Dome',
            GameFlags.VANILLA_ROBO_RIBBON: 'Vanilla Robo Ribbon',
            GameFlags.VANILLA_DESERT: 'Vanilla Desert',
            GameFlags.ROCKSANITY: 'Rocksanity',
        }
        tooltip_text = {
            GameFlags.UNLOCKED_SKYGATES: (
                'Skygates are open as soon as the Dark Ages are reached. '
                'If Epoch Fail is selected, also moves the Jets turn-in to '
                'The Blackbird Dock'
            ),
            GameFlags.ADD_SUNKEEP_SPOT: (
                'The Moon Stone will charge into a random item, and the Sun '
                'Stone can be found independently.'
            ),
            GameFlags.ADD_BEKKLER_SPOT: (
                'After the C.Trigger is obtained, Bekkler will allow you to '
                'play the vanilla Clone game for random Key Item.'
            ),
            GameFlags.ADD_CYRUS_SPOT: (
                'Interacting with Cyrus\'s grave with Frog will yield a KI '
                'instead of a stat boost'
            ),
            GameFlags.RESTORE_TOOLS: (
                'Adds the Tools as a KI, and the Tools are required to fix '
                'the Northern Ruins.'
            ),
            GameFlags.ADD_OZZIE_SPOT: (
                'Adds a KI as a reward for defeating Ozzie in Ozzie\'s Fort'
            ),
            GameFlags.RESTORE_JOHNNY_RACE: (
                'Adds the Gate Key as a KI which can be used by Crono to '
                'race Johnny'
            ),
            GameFlags.ADD_RACELOG_SPOT: (
                'Adds a KI in the Lab32 Race Log chest.'
            ),
            GameFlags.REMOVE_BLACK_OMEN_SPOT: (
                'Removes Black Omen rock chest as a KI location. Currently '
                'only relevant when Rocksanity is used.'
            ),
            GameFlags.SPLIT_ARRIS_DOME: (
                'Adds a KI as a reward for interacting with the corpse in '
                'Arris Dome Food Locker.  Adds the Seed as a KI.  Changes the '
                'normal Doan KI reward to additionally require the Seed.'
            ),
            GameFlags.VANILLA_ROBO_RIBBON: (
                'The Robo Ribbon is removed from the KI pool.  Instead, a '
                'permanent stat boost of +10 Mdef and +3 speed is rewarded '
                'when the Geno Dome is completed.'
            ),
            GameFlags.VANILLA_DESERT: (
                'The Desert begins locked and is only unlocked by talking to '
                'the plant lady in Zeal palace.'
            ),
            GameFlags.ROCKSANITY: (
                'Rocks are added to the KI pool and rock locations will yield '
                'a KI.'
            )
        }

        def gridify(frame: tk.Frame, flags: list):
            row, col = 0, 0
            for flag in flags:
                checkbox = tk.Checkbutton(
                    frame,
                    text=flag_names[flag],
                    variable=self.flag_dict[flag],
                    width=22,
                    anchor=tk.W
                )
                CreateToolTip(checkbox, text=tooltip_text[flag])
                checkbox.grid(row=row, column=col, sticky=tk.W)
                col += 1
                if col == 2:
                    col = 0
                    row += 1

        tk.Label(frame, text='Logic Tweaks').pack(anchor=tk.W)
        logic_tweak_frame = tk.Frame(frame)

        label = tk.Label(logic_tweak_frame, text='Flags that Add a KI:')
        label.pack(anchor=tk.W)
        CreateToolTip(
            label,
            'For each of these flags which are chosen, you MUST also select a '
            'flag which adds a spot.'
        )
        check_frame = tk.Frame(logic_tweak_frame)
        gridify(check_frame, plus_ki_flags)
        check_frame.pack(anchor=tk.W, padx=10)

        label = tk.Label(logic_tweak_frame, text='Flags that Add/Remove a KI Spot:')
        label.pack(anchor=tk.W)
        check_frame = tk.Frame(logic_tweak_frame)
        gridify(check_frame, adjust_spot_flags)
        check_frame.pack(anchor=tk.W, padx=10)

        label = tk.Label(logic_tweak_frame, text='KI-count neutral Flags:')
        label.pack(anchor=tk.W)
        check_frame = tk.Frame(logic_tweak_frame)
        gridify(check_frame, ki_neutral_flags)
        check_frame.pack(anchor=tk.W, padx=10)

        logic_tweak_frame.pack(anchor=tk.W, padx=10)

        return frame

    def get_cosmetic_page(self):
        frame = ttk.Frame(self.notebook)

        checkbox = tk.Checkbutton(
            frame,
            text='Zenan Alt Battle Music',
            variable=self.cosmetic_flag_dict[CosmeticFlags.ZENAN_ALT_MUSIC]
        )
        checkbox.pack(anchor=tk.W)
        CreateToolTip(
            checkbox,
            'Plays the unused alternate battle theme during the Zenan Bridge '
            'gauntlet.'
        )

        checkbox = tk.Checkbutton(
            frame,
            text='Death Peak Alt Music',
            variable=self.cosmetic_flag_dict[
                CosmeticFlags.DEATH_PEAK_ALT_MUSIC
            ]
        )
        checkbox.pack(anchor=tk.W)

        CreateToolTip(
            checkbox,
            'Plays the unused Singing Mountain theme during Death Peak.'
        )

        # Quiet Mode (No Music)
        checkButton = tk.Checkbutton(
            frame,
            text="Quiet Mode - No Music",
            variable=self.cosmetic_flag_dict[CosmeticFlags.QUIET_MODE]
        )
        checkButton.pack(anchor=tk.W)
        CreateToolTip(
            checkButton,
            "Music is disabled.  Sound effects will still play."
        )

        checkButton = tk.Checkbutton(
            frame,
            text="Reduce Flashes",
            variable=self.cosmetic_flag_dict[CosmeticFlags.REDUCE_FLASH]
        )
        checkButton.pack(anchor=tk.W)
        CreateToolTip(
            checkButton,
            "Reduces the number of bright flashes in the game."
        )

        checkButton = tk.Checkbutton(
            frame,
            text="AutoRun",
            variable=self.cosmetic_flag_dict[CosmeticFlags.AUTORUN]
        )
        checkButton.pack(anchor=tk.W)
        CreateToolTip(
            checkButton,
            "Characters run by default and walk if the run button is pressed."
        )

        label = tk.Label(frame, text='Default Names:')
        label.pack(anchor=tk.W)

        for name, var in self.char_names.items():
            tempframe = tk.Frame(frame)
            label = tk.Label(tempframe, text=name+':', width=6)
            entry = tk.Entry(tempframe, textvariable=var)

            label.pack(side=tk.LEFT)
            entry.pack(side=tk.LEFT)
            tempframe.pack(anchor=tk.W)

        return frame

    def get_options_page(self):
        frame = ttk.Frame(self.notebook)

        self.get_ctoptions_frame(frame).pack(fill=tk.X)

        return frame

    def get_ctoptions_frame(self, parent):
        frame = tk.Frame(
            parent
        )

        frame.columnconfigure([0, 2], weight=1)

        label = tk.Label(frame, text='In-Game Options')
        label.grid(row=0, column=1, sticky='we')
        CreateToolTip(
            label,
            'New games will start with these settings. '
            'Saved games with differing settings are not affected.'
            )

        self.get_ctoptions_config_frame(frame).grid(
            row=1, column=1, sticky='wen')
        self.get_ctoptions_assignment_frame(frame).grid(
            row=2, column=1, sticky='we')

        return frame

    def get_ctoptions_config_frame(self, parent):
        frame = tk.Frame(
            parent, borderwidth=1, highlightbackground='black',
            highlightthickness=1
        )

        frame.columnconfigure(1, weight=1)

        # dicts instead of tuples?
        checkboxes = {
            'Stereo Audio': (
                'stereo_audio',
                'Audio output is dual channel, rather than single channel.'
            ),
            'Save Menu Cursor': (
                'save_menu_cursor',
                'The menu saves the last page displayed, and starts on it '
                'every time the menu opens. Additionally, in menu, inventory '
                'cursor position is saved.'
            ),
            'Save Battle Cursor': (
                'save_battle_cursor',
                'Battle cursor position is saved for each character. '
                'When changing which character to command, the cursor moves '
                'to that character\'s previously-used option.'
            ),
            'Save Skill/Item Cursor': (
                'save_tech_cursor',
                'Cursor positions for in-battle Tech and Inventory menus are '
                'saved, and returned to when the action is chosen.'
            ),
            'Skill/Item Info': (
                'skill_item_info',
                'In battle, Tech and item descriptions are displayed when '
                'using them.'
            ),
            'Consistent Paging': (
                'consistent_paging',
                'Make paging up and down consistent across different menus. '
                'Not able to be changed during game.'
            )  # yet
        }

        dropdowns = {
            'Menu Background': (
                'menu_background', 8, True,
                'Controls the default menu background option. '
                'Corrosponds to the in-game options menu, '
                'i.e. 1 = default gray, 3 = Final Fantasy blue, etc'
            ),
            'Battle Speed': (
                'battle_speed', 8, True,
                'In battle, controls how quickly ATB ticks occur. '
                'Lower numbers are faster.'
            ),
            'Battle Message Speed': (
                'battle_msg_speed', 8, True,
                'In battle, controls how quickly messages about enemy status '
                'and loot drops disappear. Lower numbers are faster.'
            ),
            'Battle Gauge Style': (
                'battle_gauge_style', 3, False,
                'In battle, controls position of ATB bars, character names, '
                'and HP/MP values.'
            )
        }

        row = 0
        col = 0

        for x, y in checkboxes.items():
            label = tk.Label(frame, text=x)
            label.grid(row=row-((row // 5)*5),
                       column=col+((row // 5)*2),
                       sticky=tk.W)
            CreateToolTip(label, y[1])

            tk.Checkbutton(
                frame,
                variable=self.ctopts[y[0]]
            ).grid(row=row-((row // 5)*5), column=col+((row // 5)*2)+1,
                   sticky=tk.E)

            row += 1

        row = 1
        col += 2

        for x, y in dropdowns.items():
            label = tk.Label(frame, text=x)
            label.grid(row=row, column=col, sticky=tk.W)
            CreateToolTip(label, y[3])

            dropdown = tk.OptionMenu(
                frame,
                self.ctopts[y[0]],
                *[i for i in range(0+y[2], y[1]+y[2])],
            )
            dropdown.grid(row=row, column=col+1, sticky=tk.E)
            row += 1

        return frame

    def get_ctoptions_assignment_frame(self, parent):
        frame = tk.Frame(
            parent, borderwidth=1, highlightbackground='black',
            highlightthickness=1
        )

        frame.columnconfigure(0, weight=1)

        # updates listbox on write
        frame.listbox_values = tk.StringVar(frame)
        # used for interframe comms, for gui design
        frame.ipc = tk.StringVar(frame, value='idle')

        buttons_dropdowns = self.get_ctoptions_button_frame(frame)
        buttons_dropdowns.grid(row=0, column=0, sticky='we')

        buttons_listbox = self.get_ctoptions_button_listbox(frame)
        buttons_listbox.grid(row=0, column=1, sticky='ne')

        return frame

    def get_ctoptions_button_listbox(self, parent):

        frame = ttk.Frame(parent)
        # lbframe = ttk.Frame(frame)
        row = 0
        col = 0

        # unsets all binds, writes ipc
        def _unset_all(self, listbox):
            for action in [x for x in self.controller_binds.keys()
                           if x not in (ActionMap.PG_DN, ActionMap.PG_UP)]:
                self.controller_binds[action].set('Unset')
            parent.ipc.set('unset_all')

        # resets to vanilla, writes ipc
        def _reset_to_vanilla(self, listbox):
            vanilla = ctoptions.ControllerBinds.get_vanilla().items()

            for x, y in vanilla:
                self.controller_binds[x].set(y)
            parent.ipc.set('vanilla')

        label = tk.Label(
            frame,
            text='Buttons Remaining (?)',
            anchor=tk.CENTER
        )
        label.grid(row=row, column=0)
        CreateToolTip(
            label,
            'All buttons must be bound. '
            'Cancel and Dash will be automatically mirrored.'
        )

        row += 1

        listbox = tk.Listbox(
            frame,
            selectmode=tk.SINGLE,
            exportselection=0,
            height=len(InputMap),
            listvariable=parent.listbox_values
        )

        listbox.grid(row=row, column=col)

        # row += 1
        button = tk.Button(
            frame, text="Unset All", command=lambda: _unset_all(self, listbox)
        )
        button.grid(row=row+1, column=0, columnspan=2, sticky='s')
        CreateToolTip(
            button,
            'Unset all binds, except Page Up and Page Down.'
        )

        button = tk.Button(
            frame, text="Reset to Vanilla",
            command=lambda: _reset_to_vanilla(self, listbox)
        )
        button.grid(row=row+2, column=0, columnspan=2, sticky='n')
        CreateToolTip(
            button,
            'Reset button bindings to their vanilla values.'
        )

        return frame

    def get_ctoptions_button_frame(self, parent):
        frame = tk.Frame(
            parent  # , borderwidth=1, highlightbackground='black',
            # highlightthickness=1
        )

        frame.columnconfigure(0, weight=1)

        def _read_ipc():
            command = parent.ipc.get()
            if command not in ['unset_all', 'vanilla']:
                return
            # parent.ipc.set('idle')
            _update_gui()

        def _build_input_list(action):
            '''
            Builds the InputMap list for populating Remaining Buttons listbox
            and assignment dropdowns.
            '''

            # Get the assigned buttons.
            assigned = [
                y.get() for x, y in binds.items() if y.get() != 'Unset'
            ]

            return [str(x) for x in InputMap if str(x) not in assigned]

        def _update_display_pg(pg_strs):
            '''
            Modifies GUI page up/down display text to account for consistent paging.
            '''

            data = [
                (ActionMap.PG_UP, 'Pages upward in scrollable menus, affected by Consistent Paging.'),
                (ActionMap.PG_DN, 'Pages downward in scrollable menus, affected by Consistent Paging.')
                ]

            if self.ctopts['consistent_paging'].get():
                data.reverse()

            pg_strs['pg_up_label'].set(data[0][0])
            pg_strs['pg_dn_label'].set(data[1][0])
            pg_strs['pg_up_desc'].set(data[0][1])
            pg_strs['pg_dn_desc'].set(data[1][1])
            
        def _update_dropdown(dropdown, write_list, action):
            '''
            Clear the dropdown's entry list.
            Add entries into the OptionMenu widget, callback included as if command=... was passed during init.
            Reference Python/Lib/tkinter/__init__.py definition of class OptionMenu(Menubutton)
            '''
            callback = actions[action]['callback']
            dropdown['menu'].delete(0,'end')
            
            targetvar = binds[action]
            
            #Ensure 'Unset' is available if the action is set to a button.
            for idx, x in enumerate([x for x in ['Unset'] if x != targetvar.get()] + write_list):
                dropdown['menu'].add_command(label=x, command=tk._setit(targetvar, x, callback))

        def _update_gui(button = None, action = None):

            #Update the mirrored actions (Cancel, Dash) whenever one of them is 
            if action in [ActionMap.CANCEL, ActionMap.DASH]:
                other_action = [x for x in [ActionMap.CANCEL, ActionMap.DASH] if x != action][0]
                binds[other_action].set(binds[action].get())

            options = _build_input_list(action)
            
            #update dropdowns
            for key, data in actions.items():
                dropdown = data['dropdown']
                
                write_list = options
                
                _update_dropdown(dropdown, write_list, key)
            
            #update listbox in another frame
            parent.listbox_values.set(options)
            
        def _construct_callback(action: Optional[ActionMap] = None):
            '''
            Constructs callback function for gui usage.
            '''
            def _callback(button):
                _update_gui(button, action)
                
            return _callback

        binds = self.controller_binds
        row = 0

        pg_strs = {
            'pg_up_label': tk.StringVar(),
            'pg_dn_label': tk.StringVar(),
            'pg_up_desc': tk.StringVar(),
            'pg_dn_desc': tk.StringVar()
        }

        self.ctopts['consistent_paging'].trace_add('write', lambda x,y,z, pg_strs=pg_strs: _update_display_pg(pg_strs)) #swap the labels and tooltips of Pg Up/Dn depending on state of Consistent Paging
        parent.ipc.trace_add('write', lambda x,y,z: _read_ipc())

        actions = {
            ActionMap.CONFIRM: {'desc': 'Chooses selections, activates NPCs and objects.', 'callback': _construct_callback(), 'dropdown': None},
            ActionMap.CANCEL: {'desc': 'Backs out of menus, deselects targets of techs and items.', 'callback': _construct_callback(ActionMap.CANCEL), 'dropdown': None},
            ActionMap.MENU: {'desc': 'Opens the equipment, inventory, tech, etc menu.\nIf Save Battle Cursor is on, also selects and performs basic attacks.', 'callback': _construct_callback(), 'dropdown': None},
            ActionMap.DASH: {'desc': 'If held, causes characters to run faster.', 'callback': _construct_callback(ActionMap.DASH), 'dropdown': None},
            ActionMap.MAP: {'desc': 'On the overworld, shows a zoomed-out world map of the current time period.', 'callback': _construct_callback(), 'dropdown': None},
            ActionMap.WARP: {'desc': 'Opens the character exchange or the Epoch time gauge. Also swaps text boxes and battle menus from top to bottom of screen, and vice versa.', 'callback': _construct_callback(), 'dropdown': None}
        }

        for action, data in actions.items():

            label = tk.Label(frame, text=action)
            label.grid(row=row, column=0, sticky=tk.W)
            CreateToolTip(
                label,
                data['desc']
            )

            #Create an empty dropdown widget for action. _update_gui() will populate with entries and callbacks.
            dropdown = tk.OptionMenu(
                                    frame,
                                    binds[action],
                                    [] #dummy, filled in by _update_gui
                                    )
            dropdown.grid(row=row, column=1, sticky=tk.E)
            
            data['dropdown'] = dropdown # save a reference for _update_gui

            row += 1
            
        _update_gui()

        label = tk.Label(frame, textvariable=pg_strs['pg_dn_label'])
        label.grid(row=row, column=0, sticky=tk.W)
        CreateToolTip(
            label,
            pg_strs['pg_dn_desc']
        )

        view = tk.Label(frame, textvariable=binds[ActionMap.PG_DN], borderwidth=2, relief='ridge')
        view.grid(row=row, column=1, sticky='we')

        row += 1

        label = tk.Label(frame, textvariable=pg_strs['pg_up_label'])
        label.grid(row=row, column=0, sticky=tk.W)
        CreateToolTip(
            label,
            pg_strs['pg_up_desc']
        )

        view = tk.Label(frame, textvariable=binds[ActionMap.PG_UP], borderwidth=2, relief='ridge')
        view.grid(row=row, column=1, sticky='we')


        frame.grid_rowconfigure(row+1, weight=1)
        
        return frame

    def get_mystery_page(self):
        mys_page = ttk.Frame(self.notebook)

        label = tk.Label(
            mys_page,
            text='Relative Frequencies of Selections'
        )
        label.pack(anchor=tk.W)

        # Give boxes for relative frequencies of game modes
        mode_strs = {
            GameMode.STANDARD: "Std",
            GameMode.LOST_WORLDS: "LW",
            GameMode.LEGACY_OF_CYRUS: "LoC",
            GameMode.ICE_AGE: "IA",
            GameMode.VANILLA_RANDO: "Van"
        }

        game_mode_frame = self.get_rel_freq_frame(
            mys_page,
            'Game Modes:',
            mode_strs,
            self.mys_game_mode_freqs)
        game_mode_frame.pack(fill=tk.X)

        # Item Difficulty
        mode_strs = {diff: str(diff)
                     for diff in self.mys_item_diff_freqs}
        item_diff_frame = self.get_rel_freq_frame(
            mys_page,
            'Item Difficulty:',
            mode_strs,
            self.mys_item_diff_freqs
        )
        item_diff_frame.pack(fill=tk.X)

        # Enemy Difficulty
        mode_strs = {diff: str(diff)
                     for diff in self.mys_enemy_diff_freqs}
        item_diff_frame = self.get_rel_freq_frame(
            mys_page,
            'Enemy Difficulty:',
            mode_strs,
            self.mys_enemy_diff_freqs
        )
        item_diff_frame.pack(fill=tk.X)

        # Tech Order
        mode_strs = {to: str(to) for to in TechOrder}
        self.get_rel_freq_frame(
            mys_page,
            'Tech Order:',
            mode_strs,
            self.mys_tech_order_freqs
        ).pack(fill=tk.X)

        # Shop Prices
        mode_strs = {
            ShopPrices.NORMAL: 'Norm',
            ShopPrices.FULLY_RANDOM: 'Random',
            ShopPrices.MOSTLY_RANDOM: 'MostlyRand',
            ShopPrices.FREE: 'Free'
        }
        self.get_rel_freq_frame(
            mys_page,
            'Shop Prices:',
            mode_strs,
            self.mys_shop_price_freqs
        ).pack(fill=tk.X)

        # Flag Prob settings
        label = tk.Label(
            mys_page,
            text='Probability to Enable Flag'
        )
        label.pack(anchor=tk.W)
        label = tk.Label(
            mys_page,
            text='Note: Flags not listed below will be given whatever value\n'
            'they are set to elsewhere in the gui.  If a flag is chosen, its\n'
            'settings will be as in that flag\'s settings page.',
            anchor=tk.W,
            justify=tk.LEFT
        )
        label.pack(padx=10, anchor=tk.W)

        flag_frame = tk.Frame(mys_page)

        row = 0
        col = 0

        flag_strs = {
            GameFlags.BOSS_RANDO: 'Boss Rando',
            GameFlags.BOSS_SCALE: 'Boss Scale',
            GameFlags.UNLOCKED_MAGIC: 'UnlockMag',
            GameFlags.BUCKET_LIST: 'BucketList',
            GameFlags.CHRONOSANITY: 'Chronosanity',
            GameFlags.CHAR_RANDO: 'CharRando',
            GameFlags.DUPLICATE_CHARS: 'DupeChars',
            GameFlags.LOCKED_CHARS: 'LockChars',
            GameFlags.TAB_TREASURES: 'TabTreas',
            GameFlags.EPOCH_FAIL: 'EpochFail',
            GameFlags.GEAR_RANDO: 'GearRando',
            GameFlags.HEALING_ITEM_RANDO: 'HealRando'
        }

        for flag in self.mys_flag_prob_dict:
            string = flag_strs[flag]
            label = tk.Label(flag_frame, text=string)
            label.grid(row=row, column=col)

            col += 1

            tk.Entry(
                flag_frame,
                width=5,
                textvariable=self.mys_flag_prob_dict[flag]
            ).grid(row=row, column=col)
            col += 1

            if col == 6:
                row += 1
                col = 0

        flag_frame.pack()

        return mys_page

    def get_rel_freq_frame(self, parent,
                           desc_text,
                           cat_labels,
                           cat_values) -> ttk.Frame:

        outer_frame = ttk.Frame(parent)

        label = tk.Label(
            outer_frame,
            text=desc_text
        )
        label.pack(padx=10, side=tk.TOP, anchor=tk.W)

        frame = ttk.Frame(outer_frame)
        for item in cat_labels:
            # cat_labels item -> name
            # cat_values item -> tk variable
            label_text = cat_labels[item]
            label_var = cat_values[item]

            tklabel = tk.Label(frame, text=label_text)
            tklabel.pack(side=tk.LEFT)

            tkEntry = tk.Entry(
                frame,
                textvariable=label_var,
                width=5)
            tkEntry.pack(side=tk.LEFT)

        frame.pack(padx=20, anchor=tk.W, side=tk.TOP)
        return outer_frame

def main():
    gui = RandoGUI()
    gui.main_window.mainloop()


if __name__ == '__main__':
    main()
