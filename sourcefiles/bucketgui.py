'''
Module for creating a frame with bucket settings.
'''

from __future__ import annotations

import dataclasses
import tkinter as tk
import typing

import objectivehints as oh
import randosettings as rset


# Build a list of preset objective hint strings with the more common random
# categories at the top
_objective_preset_dict: dict[str, str] = {
    'Random': '65:quest_gated, 30:boss_nogo, 15:recruit_gated',
    'Random Gated Quest': 'quest_gated',
    'Random Hard Quest': 'quest_late',
    'Random Go Mode Quest': 'quest_go',
    'Random Gated Character Recruit': 'recruit_gated',
    'Random Boss (Includes Go Mode Dungeons)': 'boss_any',
    'Random Boss from Go Mode Dungeon': 'boss_go',
    'Random Boss (No Go Mode Dungeons)': 'boss_nogo',
    'Recruit 3 Characters (Total 5)': 'recruit_3',
    'Recruit 4 Characters (Total 6)': 'recruit_4',
    'Recruit 5 Characters (Total 7)': 'recruit_5',
    'Collect 10 of 20 Fragments': 'collect_fragments_10_10',
    'Collect 10 of 30 Fragments': 'collect_fragments_10_20',
    'Collect 3 Rocks': 'collect_rocks_3',
    'Collect 4 Rocks': 'collect_rocks_4',
    'Collect 5 Rocks': 'collect_rocks_5',
    'Forge the Masamune': 'quest_forge',
    'Charge the Moonstone': 'quest_moonstone',
    'Trade the Jerky Away': 'quest_jerky',
    'Defeat the Arris Dome Boss': 'quest_arris',
    'Visit Cyrus\'s Grave with Frog': 'quest_cyrus',
    'Defeat the Boss of Death\'s Peak': 'quest_deathpeak',
    'Defeat the Boss of Denadoro Mountains': 'quest_denadoro',
    'Gain Epoch Flight': 'quest_epoch',
    'Defeat the Boss of the Factory Ruins': 'quest_factory',
    'Defeat the Boss of the Geno Dome': 'quest_geno',
    'Defeat the Boss of the Giant\'s Claw': 'quest_claw',
    'Defeat the Boss of Heckran\'s Cave': 'quest_heckran',
    'Defeat the Boss of the King\'s Trial': 'quest_shard',
    'Defeat the Boss of Manoria Cathedral': 'quest_cathedral',
    'Defeat the Boss of Mount Woe': 'quest_woe',
    'Defeat the Boss of the Pendant Trial': 'quest_pendant',
    'Defeat the Boss of the Reptite Lair': 'quest_reptite',
    'Defeat the Boss of the Sun Palace': 'quest_sunpalace',
    'Defeat the Boss of the Sunken Desert': 'quest_desert',
    'Defeat the Boss in the Zeal Throneroom': 'quest_zealthrone',
    'Defeat the Boss of Zenan Bridge': 'quest_zenan',
    'Defeat the Black Tyrano': 'quest_blacktyrano',
    'Defeat the Tyrano Lair Midboss': 'quest_tyranomid',
    'Defeat the Boss in Flea\'s Spot': 'quest_flea',
    'Defeat the Boss in Slash\'s Spot': 'quest_slash',
    'Defeat Magus in Magus\'s Castle': 'quest_magus',
    'Defeat the Boss in the GigaMutant Spot': 'quest_omengiga',
    'Defeat the Boss in the TerraMutant Spot': 'quest_omenterra',
    'Defeat the Boss in the ElderSpawn Spot': 'quest_omenelder',
    'Defeat the Boss in the Twin Golem Spot': 'quest_twinboss',
    'Beat Johnny in a Race': 'quest_johnny',
    'Bet on a Fair Race and Win': 'quest_fairrace',
    'Play the Fair Drinking Game': 'quest_soda',
    'Defeat AtroposXR': 'boss_atropos',
    'Defeat DaltonPlus': 'boss_dalton',
    'Defeat DragonTank': 'boss_dragontank',
    'Defeat ElderSpawn': 'boss_elderspawn',
    'Defeat Flea': 'boss_flea',
    'Defeat Flea Plus': 'boss_fleaplus',
    'Defeat Giga Gaia': 'boss_gigagaia',
    'Defeat GigaMutant': 'boss_gigamutant',
    'Defeat Golem': 'boss_golem',
    'Defeat Golem Boss': 'boss_golemboss',
    'Defeat Guardian': 'boss_guardian',
    'Defeat Heckran': 'boss_heckran',
    'Defeat LavosSpawn': 'boss_lavosspawn',
    'Defeat Magus (North Cape)': 'boss_magusnc',
    'Defeat Masamune': 'boss_masamune',
    'Defeat Mother Brain': 'boss_motherbrain',
    'Defeat Mud Imp': 'boss_mudimp',
    'Defeat Nizbel': 'boss_nizbel',
    'Defeat Nizbel II': 'boss_nizbel2',
    'Defeat R-Series': 'boss_rseries',
    'Defeat Retinite': 'boss_retinite',
    'Defeat RustTyrano': 'boss_rusttyrano',
    'Defeat Slash': 'boss_slash',
    'Defeat Son of Sun': 'boss_sonofsun',
    'Defeat Super Slash': 'boss_superslash',
    'Defeat TerraMutant': 'boss_terramutant',
    # Skip twinboss b/c it's in quests
    'Defeat Yakra': 'boss_yakra',
    'Defeat Yakra XIII': 'boss_yakraxiii',
    'Defeat Zombor': 'boss_zombor'
}


class BucketPage(tk.Frame):

    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)

        # Pre-make the objective hint boxes so that there is no error
        # in enabling/disabling them
        self.num_objectives = tk.IntVar(value='5')
        self.num_objectives_needed = tk.IntVar(value='4')

        self.obj_hint_entries = []
        self.obj_hint_dropdowns = []
        self.objective_entry_frame = tk.Frame(self)
        self.obj_labels = [
            tk.Label(self.objective_entry_frame,
                     text=f'Obj {ind+1}:')
            for ind in range(8)
        ]

        self.advanced_mode = False

        self.obj_hints = [tk.StringVar() for ind in range(8)]
        self.simple_mode_choices = [tk.StringVar() for ind in range(8)]

        self.mode_select_button = tk.Button(
            self,
            command=lambda: self.toggle_objective_mode(),
            text='Switch to Advanced Mode'
        )
        self.disable_non_bucket_go = tk.IntVar(value=0)
        self.objectives_win = tk.IntVar(value=0)

        self.obj_entry_frame = tk.Frame(self)
        self.advanced_mode_frame = tk.Frame(self.obj_entry_frame)
        self.simple_mode_frame = tk.Frame(self.obj_entry_frame)
        self.simple_mode_hint_labels = []

        # Create the Advanced mode
        for ind in range(8):
            frame = tk.Frame(self.advanced_mode_frame)
            tk.Label(frame, text=f'Obj {ind+1}:').pack(side=tk.LEFT)
            entry = tk.Entry(
                frame,
                textvariable=self.obj_hints[ind],
                width=40
            )
            self.obj_hint_entries.append(entry)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            frame.pack()

        def get_handler_fn(index: int):
            return lambda event: self.check_combobox_input(event, index)

        # Create the Simplified mode
        for ind in range(8):
            frame = tk.Frame(self.simple_mode_frame)
            tk.Label(frame, text=f'Obj {ind+1}:').pack(side=tk.LEFT)
            option = tk.ttk.Combobox(
                frame,
                values=list(_objective_preset_dict.keys()),
                textvariable=self.simple_mode_choices[ind]
            )

            option.configure(width=40)
            option.bind('<KeyRelease>', get_handler_fn(ind))
            option.bind('<<ComboboxSelected>>', get_handler_fn(ind))
            option.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.obj_hint_dropdowns.append(option)

            label = tk.Label(self.simple_mode_frame, text=f'')
            self.simple_mode_hint_labels.append(label)

            frame.pack()
            label.pack()

        frame = tk.Frame(self)
        tk.Label(frame, text='Number of Objectives: ').pack(
            side=tk.LEFT, anchor=tk.W)
        self.num_objectives_entry = tk.Entry(
            frame,
            width=2,
            textvariable=self.num_objectives,
            validate='focusout',
            validatecommand=self.validate_num_objs
        )
        self.num_objectives_entry.pack(side=tk.LEFT)
        frame.pack(anchor=tk.W)

        frame = tk.Frame(self)
        tk.Label(frame, text='Number of Required Objectives: ')\
          .pack(side=tk.LEFT)
        self.num_objectives_needed_entry = tk.Entry(
            frame,
            width=2,
            textvariable=self.num_objectives_needed,
            validate='focusout',
            validatecommand=self.validate_num_objs_needed
        )
        self.num_objectives_needed_entry.pack(side=tk.LEFT)
        frame.pack(anchor=tk.W)

        self.mode_select_button.pack()
        self.simple_mode_frame.pack()
        self.obj_entry_frame.pack()

        checkframe = tk.Frame(self)
        self.disable_non_bucket_go_cb = tk.Checkbutton(
            checkframe,
            variable=self.disable_non_bucket_go
        )
        self.disable_non_bucket_go_cb.pack(side=tk.LEFT)
        tk.Label(
            checkframe,
            text='Disable Non-Bucket Go Modes'
        ).pack(side=tk.LEFT)
        checkframe.pack(anchor=tk.W)

        checkframe = tk.Frame(self)
        self.disable_non_bucket_go_cb = tk.Checkbutton(
            checkframe,
            variable=self.objectives_win
        )
        self.disable_non_bucket_go_cb.pack(side=tk.LEFT)
        tk.Label(
            checkframe,
            text='Objectives Auto-Win'
        ).pack(side=tk.LEFT)
        checkframe.pack(anchor=tk.W)

    def validate_hints(self) -> typing.Tuple[bool, str]:
        for ind, hint in enumerate(self.obj_hints):

            hint_str = hint.get()
            passed, msg = oh.is_hint_valid(hint_str)

            if not passed:
                return passed, f'Obj {ind+1}: {msg}' 

        return True, ''

    # https://stackoverflow.com/questions/55649709/
    # is-autocomplete-search-feature-available-in-tkinter-combo-box
    def check_combobox_input(self, event, index: int = None):
        value = event.widget.get()

        if value == '':
            event.widget.configure(values=list(_objective_preset_dict.keys()))
        else:
            cur_values = event.widget.cget('values')
            cur_values = [
                option for option in cur_values
                if value.lower() in option.lower()
            ]
            event.widget.configure(values=cur_values)

        label = self.simple_mode_hint_labels[index]
        if value in _objective_preset_dict:
            label['text'] = _objective_preset_dict[value]
        else:
            label['text'] = ''

    def toggle_objective_mode(self):
        if self.advanced_mode:
            self.advanced_mode_frame.pack_forget()
            self.simple_mode_frame.pack()
            self.advanced_mode = False
            self.mode_select_button.configure(text='Switch to Advanced Mode')
        else:
            self.simple_mode_frame.pack_forget()
            self.advanced_mode_frame.pack()
            self.advanced_mode = True
            self.mode_select_button.configure(text='Switch to Simple Mode')

    def get_bucket_settings(self) -> rset.BucketSettings:
        ret = rset.BucketSettings()
        ret.disable_other_go_modes = False
        ret.num_objectives = int(self.num_objectives.get())
        ret.num_objectives_needed = int(self.num_objectives_needed.get())
        ret.hints = ['' for ind in range(ret.num_objectives)]

        if self.advanced_mode:
            for ind, hint in enumerate(self.obj_hint_entries):
                if ind == ret.num_objectives:
                    break
                ret.hints[ind] = hint.get()
        else:
            for ind, combobox in enumerate(self.obj_hint_dropdowns):
                if ind == ret.num_objectives:
                    break

                value = combobox.get()
                if value in _objective_preset_dict:
                    ret.hints[ind] = _objective_preset_dict[value]
                else:
                    ret.hints[ind] = value

        ret.disable_other_go_modes = bool(self.disable_non_bucket_go.get())
        ret.objectives_win = bool(self.objectives_win.get())

        return ret

    def load_bucket_settings(self, bucket_settings: rset.BucketSettings):
        bs = bucket_settings
        self.num_objectives.set(str(bs.num_objectives))
        self.num_objectives_needed.set(str(bs.num_objectives_needed))

        for ind, hint in enumerate(bs.hints):
            match = [
                (name, code) for name, code in _objective_preset_dict.items()
                if code == hint.lower()
            ]

            if match:
                name, code = match[0]
                self.simple_mode_choices[ind].set(name)
                self.simple_mode_hint_labels[ind]['text'] = code
            elif not self.advanced_mode:
                self.toggle_objective_mode()

            self.obj_hints[ind].set(hint)

        for ind, hint in enumerate(bs.hints):
            self.obj_hints[ind].set(hint)

        self.disable_non_bucket_go.set(bs.disable_other_go_modes)
        self.objectives_win.set(bs.objectives_win)

    def validate_num_objs(self):
        try:
            num_objs = int(self.num_objectives.get())
            if num_objs not in range(1, 9):
                raise ValueError
        except ValueError:
            self.num_objectives_entry.delete(0, tk.END)
            self.num_objectives.set(self.num_objectives_needed.get())
            self.num_objectives_entry.insert(
                0, self.num_objectives.get()
            )
            num_objs = int(self.num_objectives.get())
            tk.messagebox.showerror(
                'Error',
                'Number of Objectives Must be a number between 1 and 8'
            )

        num_needed = int(self.num_objectives_needed.get())
        if num_needed > num_objs:
            self.num_objectives_needed.set(str(num_objs))

        for ind in range(0, num_objs):
            self.obj_hint_entries[ind]['state'] = tk.NORMAL
            self.obj_hint_dropdowns[ind]['state'] = tk.NORMAL

        for ind in range(num_objs, 8):
            self.obj_hint_entries[ind]['state'] = tk.DISABLED
            self.obj_hint_dropdowns[ind]['state'] = tk.DISABLED

        return True

    def validate_num_objs_needed(self):
        num_objs = int(self.num_objectives.get())
        try:
            num_objs_needed = int(self.num_objectives_needed.get())
            if num_objs_needed not in range(1, 9) or \
               num_objs_needed > num_objs:
                raise ValueError

        except ValueError:
            self.num_objectives_needed_entry.delete(0, tk.END)
            self.num_objectives_needed.set(self.num_objectives.get())
            self.num_objectives_needed_entry.insert(
                0, self.num_objectives_needed.get()
            )
            tk.messagebox.showerror(
                'Error',
                'Number of Required Objectives must be a number between 1 '
                'and the number of objectives.'
            )
            return False

        return True
