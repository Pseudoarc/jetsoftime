from byteops import get_record
from common.random import RNGType
from techdb import TechDB
import copy

import ctenums
import randosettings as rset
import randoconfig as cfg


# These are the relative frequencies for "balanced" tech rando
# Just make this a script variable instead of duplicating it.
freqs = [[8, 7, 6, 4, 3, 5, 1, 2],  # Crono
         [7, 8, 6, 5, 1, 2, 3, 4],  # Marle
         [8, 4, 6, 5, 7, 2, 3, 1],  # Lucca
         [8, 7, 6, 2, 3, 1, 5, 4],  # Robo
         [8, 6, 7, 1, 3, 2, 4, 5],  # Frog
         [8, 7, 5, 2, 6, 4, 3, 1],  # Ayla
         [5, 5, 5, 7, 8, 2, 3, 1]]  # Magus


# This needs to be done after char duplicate assignments since balanced tech
# distribution varies by character.
def write_tech_order_to_config(settings: rset.Settings,
                               config: cfg.RandoConfig,
                               rng: RNGType):

    global freqs

    pcstats = config.pcstats
    tech_order = settings.techorder

    for char_id in range(7):
        if tech_order == rset.TechOrder.FULL_RANDOM:
            perm = generate_permutation_freq([1 for i in range(8)], rng)
        elif tech_order == rset.TechOrder.BALANCED_RANDOM:
            pc_id = ctenums.CharID(char_id)
            assigned_id = pcstats.get_character_assignment(pc_id)
            perm = generate_permutation_freq(freqs[int(assigned_id)], rng)
        else:
            perm = [i for i in range(8)]

        # char_man.pcs[char_id].tech_permutation = perm[:]
        # TODO: Make sure it's safe to randomize techs now.  It should be,
        #       but I always did it at the very end before.  For now, let's
        #       give it a shot and remember this if things break.
        randomize_pc_techs(config.tech_db, char_id, perm)


# generate a random permutation where each object has a different probability
# of being drawn.
# Uniform distribution is [1,1,1,....,1]
def generate_permutation_freq(rel_freqs, rng: RNGType):

    perm = [0]*len(rel_freqs)
    for i in range(len(rel_freqs)):
        perm[i] = i

    for start in range(0, len(rel_freqs)-1):
        N = sum(rel_freqs[start:])
        x = rng.randrange(1, N+1)

        for i in range(start, len(rel_freqs)):
            x -= rel_freqs[i]
            if x <= 0:
                perm[start], perm[i] = perm[i], perm[start]
                rel_freqs[start], rel_freqs[i] = rel_freqs[i], rel_freqs[start]
                break

    return perm


def randomize_single_techs_uniform(db, rng: RNGType):

    freqs = [1]*8

    for i in range(7):
        perm = generate_permutation_freq(freqs, rng)
        randomize_pc_techs(db, i, perm)


def randomize_single_techs_balanced(db, rng: RNGType):
    global freqs

    for i in range(7):
        perm = generate_permutation_freq(freqs[i], rng)
        randomize_pc_techs(db, i, perm)


def randomize_pc_techs(db, char_id, perm, preserve_magic=True):
    # Shuffle everything goes goes with tech_id: gfx, target, name, desc_ptr,
    #   effect, mp, atb_pen
    # Fix pointers to effect headers in control headers
    # Shuffle menu usability
    # Update effect indices in control headers
    # Update lrn_reqs
    # Update menu_mp_reqs

    dat = [db.effects, db.mps,
           db.controls,
           db.gfx,
           db.targets,
           db.names,
           db.desc_ptrs,
           db.menu_usable_ids,
           db.pc_target,
           db.atb_pens]

    sizes = [TechDB.effect_size, 1,
             TechDB.control_size,
             TechDB.gfx_size,
             TechDB.target_size,
             TechDB.name_size,
             TechDB.desc_ptr_size,
             1,
             1,
             1]

    temp_dat = copy.deepcopy(dat)

    # shuffle it all up!  PC's tech #i to goes to #perm[i]
    for i in range(0, 8):
        to_ind = 1+8*char_id + perm[i]
        from_ind = 1+8*char_id + i

        for j in range(0, len(dat)):
            x = get_record(temp_dat[j], from_ind, sizes[j])
            dat[j][to_ind*sizes[j]:(to_ind+1)*sizes[j]] = x[:]

    if preserve_magic:
        # Copy the old first bytes back to the new control headers.
        # Technically we only need the x80 (magic) bit, but the first byte
        # of the hearder is just (magic_bit | pc_ind) for single techs
        old_controls = temp_dat[2]
        ctl_start = (1+8*char_id)*TechDB.control_size

        for i in range(8):
            db.controls[ctl_start+TechDB.control_size*i] = \
                old_controls[ctl_start+TechDB.control_size*i]

    # update effect indices in control headers
    eff_min = 1+8*char_id
    eff_max = eff_min + 7
    for i in range(0, db.control_count):
        # bytes 5,6,7 are effect indices
        ctl_start = i*TechDB.control_size
        for j in range(5, 8):
            eff = db.controls[ctl_start+j]
            eff_x80 = eff & 0x80
            eff_ind = eff & 0x7F

            if eff_min <= eff_ind <= eff_max:
                new_ind = perm[eff_ind - eff_min]+eff_min
                db.controls[ctl_start+j] = eff_x80 | new_ind

    # update lrn_reqs
    # look through menu grps for the pc of interest.  Figure out where they
    # are in the lrn_req list, and apply perm
    char_bit = 0x80 >> char_id
    for i in range(db.first_dual_grp, db.first_rock_grp):
        if db.menu_grps[i] & char_bit != 0:
            # our pc is in the menu group
            grp = db.menu_grps[i]

            num_chars = 0
            mask = 0x80
            pos = 0

            for j in range(0, 8):
                if mask & grp != 0:
                    if j == char_id:
                        pos = num_chars
                    num_chars += 1
                mask = mask >> 1

            size = 0
            if num_chars == 2:
                size = 3
            else:
                size = 1

            start_tech = db.group_sizes[i]
            lrn_loc = (start_tech-0x39)*TechDB.lrn_req_size+pos

            for tech in range(start_tech, start_tech+size):
                tech_lrn_start = (tech-0x39)*TechDB.lrn_req_size
                lrn_loc = tech_lrn_start+pos
                db.lrn_reqs[lrn_loc] = perm[db.lrn_reqs[lrn_loc]-1]+1

    # update menu_mp_reqs for triple techs (and menu if that ever works)
    for (i, x) in enumerate(db.menu_mp_reqs):
        pc = (x-1) // 8
        if pc == char_id:
            tech_num = (x-1) % 8
            tech_num = perm[tech_num]
            db.menu_mp_reqs[i] = pc*8+tech_num+1

    # Is that it?
