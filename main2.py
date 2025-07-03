# Imports
import random
import time
from colorama import Fore, Style
import os
import sys
import platform
import json

from game_data import drop_table, skill_table, monster_list
from main import explore_floor

# === Constants and Globals ===
current_version = "0.1"
save_directory = "eyum/saves"
os.makedirs(save_directory, exist_ok=True)

player_data = {
    "current_character": 0, # default to lucian
    "character": ['Lucian','Ilana','George'],
    "unlocked": [True, True, True],
    "is_dead": [False, False, False],
    "level": [1, 1, 1],
    "max_health": [20, 15, 25],
    "health": [20, 15, 25],
    "max_mana": [10, 10, 5],
    "mana": [10, 10, 5],
    "damage": [1, 1, 2], # Number of d2's per attack
    "xp": [0, 0, 0],
    "xp_to_next": [10, 10, 10],
    "skill_points": [0, 0, 0],
    # What the characters do on their turn when they aren't selected
    "idle_attacks": [3,0,1], # How many attacks they get/how many monsters are targeted
    "idle_damage": ['1d4','None','1d8'], # +1 dice per level
    "idle_healing": ['None','1d8','None'], # +1 dice per level
    # The inventory and such are shared
    "coins": 0,
    "inventory": [],
    "equipped": [],
}

persistent_stats = {
    "current_version": current_version,
    "floor": 1,
    "room": 1,
    "current_monsters": None,
    "rooms_since_shop": 0,
    "rooms_since_treasure": 0,
    "monster_rotation_index": 0,
}

character_skills = {
    "Lucian": {
        "skills": ["Fireblast", "Firebolt"],
        "damage": ["1d2","2d8"],
        "attacks": [2, 1], # The number of targets it can hit/attacks it can make
        "healing": ['None', 'None'],
        "mana_costs": [4, 8],
        "level": [1, 1],
        "max_level": [10, 10]
    },
    "Ilana": {
        "skills": ["Necro Blast", "Life Drain"],
        "damage": ["1d4", "1d4"],
        "attacks": [1, 2],
        "healing": ['1d4', '1d4'],
        "mana_costs": [2, 4],
        "level": [1, 1],
        "max_level": [10, 10]
    },
    "George": {
        "skills": ["Sword Slash", "Sword Burst"],
        "damage": ["1d6", "1d4"],
        "attacks": [2, 4],
        "healing": ['None', 'None'],
        "mana_costs": [3, 8],
        "level": [1, 1],
        "max_level": [10, 10]
    },
}

characters = list(character_skills.keys())
current_save_name = ''
global_save_path = ''
current_monster_group = None  # global variable for active encounter

# Helper/Utility Functions
def rainbow_text(text): # TASTE THE RAINBOW, MUTHA****
    colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
    output = ""
    for i, char in enumerate(text):
        output += colors[i % len(colors)] + char
    return output + Style.RESET_ALL

def render_bar(current, max_val, length=40, color=Fore.GREEN): #
    # Example:
    # player_bar = render_health_bar(player_data["health"], player_data["max_health"], color=Fore.GREEN)
    # print(player_bar)
    filled_length = int(length * current / max_val)
    empty_length = length - filled_length

    filled_bar = f"{Style.BRIGHT}{color}{'█' * filled_length}"
    empty_bar = f"{Fore.WHITE}{'░' * empty_length}"
    return f"{filled_bar}{empty_bar}{Style.RESET_ALL}"

def roll_dice(dice_str):
    try:
        if isinstance(dice_str, int):
            raise ValueError("roll_dice received integer; expected 'XdY' string")
        if not isinstance(dice_str, str):
            raise ValueError("Dice input must be string or int")
        dice_str = dice_str.lower()
        if dice_str == "none":
            return 0
        num, sides = map(int, dice_str.split('d'))
        return sum(random.randint(1, sides) for _ in range(num))
    except Exception as e:
        print(Fore.RED + f"Invalid dice format '{dice_str}': {e}")
        return 0

def press_enter():
    print(Fore.BLUE + "Press ENTER to continue.")
    input(Fore.GREEN + "> ")

def clear_screen():
    print(Style.RESET_ALL)
    os.system("cls" if platform.system() == "Windows" else "clear")

# === Save/Load Functions ===
def save_to_file():
    global_save_path = os.path.join(save_directory, "Eyum.json")
    save_data = {
        "player": player_data,
        "persistent_stats": persistent_stats,
        "current_monsters": current_monster_group
    }
    with open(global_save_path, "w") as f:
        json.dump(save_data, f, indent=4)

def load_from_file():
    global global_save_path, player_data, persistent_stats
    global_save_path = os.path.join(save_directory, "Eyum.json")
    if not os.path.exists(global_save_path):
        return False
    with open(global_save_path, "r") as f:
        data = json.load(f)
    player_data.update(data.get("player", {}))
    persistent_stats.update(data.get("persistent_stats", {}))
    current_monster_group = data.get("current_monsters")
    return True

# Normal Functions
def generate_monster_group():
    i = persistent_stats.get("monster_rotation_index", 0)
    pool = monster_list[i:i + 3]

    # Ensure exactly 3 entries unless list is too short
    while len(pool) < 3 and i + len(pool) < len(monster_list):
        pool.append(monster_list[i + len(pool)])

    weights = [10, 7, 3][:len(pool)]  # Favors weakest in current pool

    group = [random.choices(pool, weights=weights)[0].copy()]
    if random.random() < 0.30:
        group.append(random.choices(pool, weights=weights)[0].copy())
        if random.random() < 0.15:
            group.append(random.choices(pool, weights=weights)[0].copy())
            if random.random() < 0.10:
                group.append(random.choices(pool, weights=weights)[0].copy())
                if random.random() < 0.05:
                    group.append(random.choices(pool, weights=weights)[0].copy())

    for m in group:
        m["max_health"] = m["health"]

    return group

def get_boss(floor):
    i = persistent_stats.get("monster_rotation_index", 0)
    boss_index = min(i + 3, len(monster_list) - 1)
    return monster_list[boss_index]

def rotate_monsters():
    i = persistent_stats.get("monster_rotation_index", 0)
    if i + 3 < len(monster_list):
        persistent_stats["monster_rotation_index"] = i + 1

def gain_xp(amount):
    i = player_data["current_character"]
    player_data["xp"][i] += amount
    print(Fore.CYAN + f"You gained {amount} XP!")

    while player_data["xp"][i] >= player_data["xp_to_next"][i]:
        player_data["xp"][i] -= player_data["xp_to_next"][i]
        player_data["level"][i] += 1

        floor = persistent_stats.get("floor", 1)
        earned_points = max(1, floor)
        player_data["skill_points"][i] += earned_points

        player_data["xp_to_next"][i] = int(player_data["xp_to_next"][i] * 1.5)

        # Restore HP/MP
        player_data["max_mana"][i] = int(player_data["max_mana"][i] * 1.2)
        player_data["mana"][i] = player_data["max_mana"][i]
        player_data["max_health"][i] = int(player_data["max_health"][i] * 1.1)
        player_data["health"][i] = player_data["max_health"][i]

        print(Fore.YELLOW + f"Level up! Now level {player_data['level'][i]}")
        print(Fore.MAGENTA + f"+{earned_points} Skill Point{'s' if earned_points > 1 else ''}! Total: {player_data['skill_points'][i]}")
        print(Fore.BLUE + f"Stats restored to full!")

def show_combat_stats(monsters):
    """
    Displays the full combat UI: player info, allies, monster HP bars, and action menu.
    Uses current_character index to access the correct stats from player_data arrays.
    """

    # === Load player info ===
    i = player_data["current_character"]  # active character index
    name = player_data["character"][i]    # character name
    level = player_data["level"][i]       # character level
    xp = player_data["xp"][i]
    xp_next = player_data["xp_to_next"][i]
    hp = player_data["health"][i]
    max_hp = player_data["max_health"][i]
    mp = player_data["mana"][i]
    max_mp = player_data["max_mana"][i]

    # === Render bars and XP ===
    xp_bar = f"{Fore.CYAN}{xp}{Fore.GREEN}/{Fore.YELLOW}{xp_next}{Fore.GREEN}"
    hp_bar = render_bar(hp, max_hp, color=Fore.GREEN)
    mp_bar = render_bar(mp, max_mp, color=Fore.BLUE)

    # === Display player header ===
    print(Fore.GREEN + f"{name} (Lv{level} {xp_bar})")
    print(Fore.LIGHTBLACK_EX + f"Floor {persistent_stats['floor']} - Room {persistent_stats['room']}\n")

    # === Display ally statuses ===
    print(Fore.LIGHTBLACK_EX + "--- Allies ---")
    for j, ally in enumerate(player_data["character"]):
        if j == i:
            continue  # skip active player
        ahp = player_data["health"][j]
        amax = player_data["max_health"][j]
        dead = ahp <= 0
        color = Fore.RED if dead else Fore.LIGHTBLACK_EX
        status = "(dead)" if dead else f"{ahp} / {amax} HP"
        print(color + f"{ally}: {status}")

    # === Show main character HP/MP Bars ===
    print(f"{Fore.GREEN}HP: {hp} / {max_hp}")
    print(hp_bar)
    print(f"{Fore.BLUE}MP: {mp} / {max_mp}")
    print(mp_bar)

    # === Display monsters ===
    print(Fore.RED + "\n--- Monsters ---")
    for idx, m in enumerate(monsters):
        m_hp = m.get("health", 0)
        m_max = m.get("max_health", 0)
        bar_color = Fore.RED if m_hp > 0 else Fore.BLACK
        bar = render_bar(m_hp, m_max, color=bar_color)
        name_line = f"[{idx + 1}] {m['name']}"

        if m_hp <= 0:
            print(Fore.RED + f"{name_line} (defeated)")
        else:
            print(Fore.RED + f"{name_line} HP: {m_hp} / {m_max}")
        print(bar)

    # === Action Menu ===
    print(Fore.GREEN + "\n[1] Attack  [2] Use Skill  [3] Retreat  [4] Upgrade Menu  [5] Equipment  [6] Character Selection")

    # === Get input and return it to combat loop ===
    action = input(Fore.GREEN + "> ").strip().lower()
    return action

def get_item_value(item, floor=1):
    """
    Calculate the price of an item based on its bonuses and the current floor.
    """
    bonus = item.get("bonus", {})
    value = 10 * floor  # base price

    # Add value based on item bonuses
    if "damage" in bonus:
        value += bonus["damage"] * 5 * floor
    if "max_health" in bonus:
        value += bonus["max_health"] * 2
    if "max_mana" in bonus:
        value += bonus["max_mana"] * 3
    if item.get("restore_full"):
        value += 25 * floor

    return max(value, 5)


def generate_random_shop_items(drop_table, floor=1):
    """
    Selects 2–5 random items from the drop table and assigns a calculated price.
    """
    count = random.randint(2, 5)
    items = random.sample(drop_table, k=count)
    for item in items:
        item["price"] = get_item_value(item, floor)
    return items


def generate_shop_skill(skill_table, floor=1):
    """
    20% chance to generate a skill to be sold at a high price.
    """
    if random.random() < 0.2:
        skill = random.choice(skill_table)
        return {
            "type": "skill",
            "name": skill["name"],
            "price": 50 * floor + random.randint(20, 50)
        }
    return None

def shop():
    """
    Presents the player with a shop containing 2–5 items and a 20% chance of a skill.
    Prices scale with floor and bonuses. Player can buy if they have enough coins.
    """

    # Fix this to use actual stuff from the game_data file
    clear_screen()
    print(Fore.YELLOW + "--- Mysterious Shop ---\n")

    floor = persistent_stats.get("floor", 1)
    shop_items = generate_random_shop_items(drop_table, floor)
    skill_offer = generate_shop_skill(skill_table, floor)
    if skill_offer:
        shop_items.append(skill_offer)

    # Display items
    for i, item in enumerate(shop_items):
        name = item["name"]
        price = item["price"]
        affordable = player_data["coins"] >= price
        color = Fore.CYAN if affordable else Fore.RED

        if item.get("type") == "skill":
            print(color + f"[{i + 1}] Skill: {name} - {price} coins")
        else:
            bonuses = ", ".join(f"{k}+{v}" for k, v in item.get("bonus", {}).items())
            print(color + f"[{i + 1}] {name} ({bonuses}) - {price} coins")

    print(Fore.MAGENTA + f"\nCoins: {player_data['coins']}")
    print(Fore.GREEN + "Type item number to buy or 'exit' to leave.")

    while True:
        choice = input(Fore.GREEN + "> ").strip().lower()
        if choice == "exit":
            break
        if not choice.isdigit():
            print(Fore.RED + "Invalid input.")
            continue
        index = int(choice) - 1
        if 0 <= index < len(shop_items):
            item = shop_items[index]
            if player_data["coins"] < item["price"]:
                print(Fore.RED + "Not enough coins.")
            else:
                player_data["coins"] -= item["price"]
                if item.get("type") == "skill":
                    char = player_data["character"][player_data["current_character"]]
                    character_skills[char]["skills"].append(item["name"])
                    character_skills[char]["mana_costs"].append(6)
                    character_skills[char]["damage"].append("1d4")
                    character_skills[char]["attacks"].append(1)
                    character_skills[char]["healing"].append('None')
                    character_skills[char]["level"].append(1)
                    print(Fore.YELLOW + f"You learned the skill: {item['name']}!")
                else:
                    player_data["inventory"].append(item)
                    print(Fore.YELLOW + f"You bought: {item['name']}!")
        else:
            print(Fore.RED + "Invalid item number.")


def treasure():
    """
    Displays a treasure chest with gold, and a 25% chance of a random item.
    Scales gold with floor. Always adds coins to player.
    """
    clear_screen()
    print(Fore.YELLOW + "You found a sparkling treasure room!\n")
    floor = persistent_stats.get("floor", 1)
    coins_found = random.randint(10, 30) + floor * 5
    player_data["coins"] += coins_found
    print(Fore.CYAN + f"You open the chest and find {coins_found} coins!")

    if random.random() < 0.25:
        item = random.choice(drop_table).copy()
        player_data["inventory"].append(item)
        print(Fore.GREEN + f"You also find an item: {item['name']}!")

    press_enter()

def upgrade_current_player():
    clear_screen()
    i = player_data["current_character"]
    name = player_data["character"][i]
    points = player_data["skill_points"]

    if points <= 0:
        print(Fore.RED + "You have no skill points to spend.")
        press_enter()
        return

    while points > 0:
        clear_screen()
        print(Fore.YELLOW + f"Upgrade Menu - {name}")
        print(Fore.MAGENTA + f"Skill Points: {points}")
        color = Fore.GREEN if points > 0 else Fore.RED
        print(color + f"[1] Max Health: {player_data['max_health'][i]}")
        print(color + f"[2] Max Mana:   {player_data['max_mana'][i]}")
        print(color + f"[3] Damage Dice: {player_data['damage'][i]}d2")
        print(color + "[4] Upgrade a Skill")
        print(Fore.LIGHTBLACK_EX + "[exit] Leave upgrade menu")

        choice = input(Fore.GREEN + "> ").strip().lower()

        if choice in ["exit", "leave", "back"]:
            break

        cost = 1
        if choice == "1":
            player_data["max_health"][i] += 5
            player_data["health"][i] = player_data["max_health"][i]
        elif choice == "2":
            player_data["max_mana"][i] += 3
            player_data["mana"][i] = player_data["max_mana"][i]
        elif choice == "3":
            player_data["damage"][i] += 1
        elif choice == "4":
            points = upgrade_skill(player_data["character"][i], points)
            continue
        else:
            print(Fore.RED + "Invalid choice.")
            continue

        points -= cost
        player_data["skill_points"] = points
        save_to_file()
        press_enter()

def upgrade_skill(char_name, points):
    skills = character_skills[char_name]["skills"]
    levels = character_skills[char_name]["level"]
    max_lvls = character_skills[char_name]["max_level"]

    while True:
        clear_screen()
        print(Fore.LIGHTYELLOW_EX + f"Upgrade a Skill - {char_name}")
        print(Fore.MAGENTA + f"Skill Points: {points}")
        for i, skill in enumerate(skills):
            level = levels[i]
            max_level = max_lvls[i]
            color = Fore.GREEN if level < max_level and points > 0 else Fore.RED
            print(color + f"[{i + 1}] {skill}: Lv {level}/{max_level}")

        print(Fore.LIGHTBLACK_EX + "[exit] Back")
        choice = input(Fore.GREEN + "> ").strip().lower()
        if choice in ["exit", "back"]:
            return points
        if not choice.isdigit():
            print(Fore.RED + "Invalid input.")
            press_enter()
            continue

        idx = int(choice) - 1
        if not (0 <= idx < len(skills)):
            print(Fore.RED + "Invalid choice.")
            press_enter()
            continue

        if levels[idx] >= max_lvls[idx]:
            print(Fore.RED + "Skill already at max level.")
            press_enter()
            continue

        levels[idx] += 1
        if character_skills[char_name]["attacks"][idx] > 1:
            character_skills[char_name]["attacks"][idx] += 1
        for key in ["damage", "healing"]:
            val = character_skills[char_name][key][idx]
            if val.lower() != "none":
                num, die = map(int, val.lower().split("d"))
                num += 1
                character_skills[char_name][key][idx] = f"{num}d{die}"

        print(Fore.YELLOW + f"{skills[idx]} upgraded to Lv {levels[idx]}")
        points -= 1
        player_data["skill_points"] = points
        save_to_file()
        press_enter()
        return points

def equipment():
    while True:
        clear_screen()
        print(Fore.YELLOW + "--- Equipment Menu ---")
        for i, name in enumerate(player_data["character"]):
            print(f"[{i + 1}] {name}")
        print(Fore.LIGHTBLACK_EX + "\nType character number to manage or 'exit'.")
        choice = input(Fore.GREEN + "> ").strip().lower()
        if choice == "exit":
            return
        if not choice.isdigit():
            continue
        idx = int(choice) - 1
        if 0 <= idx < len(player_data["character"]):
            manage_equipment_for(idx)

def manage_equipment_for(char_index):
    name = player_data["character"][char_index]
    while True:
        clear_screen()
        print(Fore.YELLOW + f"Equipment - {name}")
        equipped = [item for item in player_data["equipped"] if item["owner"] == name]
        if equipped:
            print(Fore.CYAN + "\nEquipped:")
            for i, item in enumerate(equipped):
                print(f"[{i + 1}] {item['name']} ({item['type']})")
        else:
            print(Fore.RED + "No items equipped.")
        print(Fore.YELLOW + "\nInventory:")
        inv = [item for item in player_data["inventory"] if item.get("type") in ["armor", "weapon", "relic"]]
        for i, item in enumerate(inv):
            print(f"[{i + 1}] {item['name']} ({item['type']})")
        print(Fore.LIGHTBLACK_EX + "\n[equip X], [unequip X], [exit]")
        cmd = input(Fore.GREEN + "> ").strip().lower()
        if cmd == "exit":
            return
        elif cmd.startswith("equip "):
            try:
                idx = int(cmd.split()[1]) - 1
                item = inv[idx]
                equip_item(name, item, char_index)
            except:
                print(Fore.RED + "Invalid input.")
                press_enter()
        elif cmd.startswith("unequip "):
            try:
                idx = int(cmd.split()[1]) - 1
                item = equipped[idx]
                unequip_item(name, item, char_index)
            except:
                print(Fore.RED + "Invalid input.")
                press_enter()

def equip_item(name, item, char_index):
    for e in player_data["equipped"]:
        if e["owner"] == name and e["type"] == item["type"]:
            unequip_item(name, e, char_index)
            break
    apply_bonuses(char_index, item["bonus"])
    item["owner"] = name
    player_data["equipped"].append(item)
    player_data["inventory"].remove(item)
    print(Fore.GREEN + f"{item['name']} equipped!")
    save_to_file()
    press_enter()

def unequip_item(name, item, char_index):
    remove_bonuses(char_index, item["bonus"])
    player_data["equipped"].remove(item)
    item.pop("owner", None)
    player_data["inventory"].append(item)
    print(Fore.YELLOW + f"{item['name']} unequipped.")
    save_to_file()
    press_enter()

def apply_bonuses(index, bonus):
    for key, val in bonus.items():
        if key in player_data:
            player_data[key][index] += val

def remove_bonuses(index, bonus):
    for key, val in bonus.items():
        if key in player_data:
            player_data[key][index] -= val

def other_character_turn():
    """
    Each non-selected character performs their idle action:
    - Damage dealt to monsters
    - Healing to party
    """
    i = player_data["current_character"]
    for j, name in enumerate(player_data["character"]):
        if j == i or player_data["health"][j] <= 0:
            continue

        attacks = player_data["idle_attacks"][j]
        dmg_dice = str(player_data["idle_damage"][j])
        heal_dice = str(player_data["idle_healing"][j])

        # Damage
        if dmg_dice.lower() != "none":
            for _ in range(attacks):
                valid_targets = [m for m in current_monster_group if m["health"] > 0]
                if not valid_targets:
                    return  # <-- Safely exit if no valid monsters
                target = random.choice(valid_targets)
                dmg = roll_dice(dmg_dice)

                target["health"] = max(0, target["health"] - dmg)
                print(Fore.LIGHTRED_EX + f"{name} hits {target['name']} for {dmg} damage!")

        # Healing
        if heal_dice.lower() != "none":
            injured = [(k, hp) for k, hp in enumerate(player_data["health"]) if hp < player_data["max_health"][k]]
            if not injured:
                continue
            if injured:
                idx = random.choice(injured)[0]
                healed = roll_dice(heal_dice)
                player_data["health"][idx] = min(player_data["health"][idx] + healed, player_data["max_health"][idx])
                print(Fore.LIGHTGREEN_EX + f"{name} heals {player_data['character'][idx]} for {healed} HP!")

def monster_death_check():
    global current_monster_group
    current_monster_group = [m for m in current_monster_group if m["health"] > 0]
    if not current_monster_group:
        print(Fore.GREEN + "All monsters defeated!")
        gain_xp(10 + persistent_stats["floor"] * 2)
        press_enter()
        return True
    return False

def monster_attack():
    """
    Each monster attacks a random party member (weighted toward current player).
    """
    i = player_data["current_character"]
    weights = [5 if k == i else 1 for k in range(len(player_data["character"]))]

    for m in current_monster_group:
        if m["health"] <= 0:
            continue
        target = random.choices(range(len(weights)), weights=weights)[0]
        if player_data["health"][target] <= 0:
            continue
        dmg_str = m["damage"]
        if isinstance(dmg_str, int):
            dmg_str = f"{dmg_str}d2"  # interpret plain numbers as Xd2
        dmg = roll_dice(dmg_str)
        player_data["health"][target] = max(0, player_data["health"][target] - dmg)
        print(Fore.RED + f"{m['name']} strikes {player_data['character'][target]} for {dmg}!")

def character_death_check():
    """
    Check if all characters are dead. If so, end the game.
    """
    all_dead = all(hp <= 0 for hp in player_data["health"])
    if all_dead:
        print(Fore.RED + "All characters have fallen...")
        persistent_stats["is_dead"] = True
        save_to_file()
        sys.exit()

def player_attack():
    """
    Player performs a basic attack on a chosen monster.
    Prevents attacking invalid or already defeated targets.
    """
    i = player_data["current_character"]
    dmg_rolls = player_data["damage"][i]
    targets = [idx for idx, m in enumerate(current_monster_group) if m["health"] > 0]

    if not targets:
        print(Fore.RED + "There are no valid targets.")
        press_enter()
        return False  # Prevents combat_macro()

    print(Fore.GREEN + "Choose a monster to attack:")
    for idx in targets:
        m = current_monster_group[idx]
        print(f"[{idx + 1}] {m['name']} ({m['health']} HP)")

    try:
        choice = int(input(Fore.GREEN + "> ")) - 1
        if choice not in targets:
            print(Fore.RED + "Invalid target.")
            press_enter()
            return False  # Prevents combat_macro()
    except:
        print(Fore.RED + "Invalid input.")
        press_enter()
        return False

    dmg = sum(random.randint(1, 2) for _ in range(dmg_rolls))
    current_monster_group[choice]["health"] = max(0, current_monster_group[choice]["health"] - dmg)
    print(Fore.YELLOW + f"You deal {dmg} damage to {current_monster_group[choice]['name']}!")
    return True

def player_skill_select():
    success = False
    """
    Prompts player to select a skill and targets, then executes it.
    """
    i = player_data["current_character"]
    name = player_data["character"][i]
    skills = character_skills[name]["skills"]
    mana_costs = character_skills[name]["mana_costs"]

    print(Fore.GREEN + "Choose a skill:")
    for idx, skill in enumerate(skills):
        cost = mana_costs[idx]
        color = Fore.RED if player_data["mana"][i] < cost else Fore.GREEN
        print(color + f"[{idx + 1}] {skill} ({cost} MP)")

    try:
        s = int(input(Fore.GREEN + "> ")) - 1
        if s not in range(len(skills)):
            print(Fore.RED + "Invalid skill.")
            return False
    except:
        print(Fore.RED + "Invalid input.")
        return False

    # Skill validation
    if player_data["mana"][i] < mana_costs[s]:
        print(Fore.RED + "Not enough mana.")
        press_enter()
        return False

    # Deduct mana
    cost = mana_costs[s]
    player_data["mana"][i] = max(0, player_data["mana"][i] - cost)

    # Apply damage
    attacks = character_skills[name]["attacks"][s]
    damage = str(character_skills[name]["damage"][s])
    healing = str(character_skills[name]["healing"][s])

    for _ in range(attacks):
        living = [m for m in current_monster_group if m["health"] > 0]
        if not living:
            break
        m = random.choice(living)
        dmg = roll_dice(damage)
        m["health"] = max(0, m["health"] - dmg)
        print(Fore.LIGHTYELLOW_EX + f"{name}'s {skills[s]} hits {m['name']} for {dmg}!")
        success = True

    # Apply healing
    if healing.lower() != "none":
        amt = roll_dice(healing)
        player_data["health"][i] = min(player_data["health"][i] + amt, player_data["max_health"][i])
        print(Fore.LIGHTGREEN_EX + f"{name} heals for {amt} HP!")
        success = True

    return success

def try_retreat():
    """
    75% chance to retreat. If failed, monster turn happens.
    """
    if random.random() < 0.75:
        print(Fore.YELLOW + "You successfully escaped!")
        press_enter()
    else:
        print(Fore.RED + "Retreat failed!")
        monster_attack()
        character_death_check()
        press_enter()
        return False
    return True

def combat():
    """
    Handles monster combat: generate monsters, enter loop, break on win or retreat.
    """
    global current_monster_group
    if persistent_stats.get("current_monsters"):
        current_monster_group = persistent_stats["current_monsters"]
    else:
        current_monster_group = generate_monster_group()
        persistent_stats["current_monsters"] = current_monster_group

    def combat_macro():
        if not any(m["health"] > 0 for m in current_monster_group):
            return  # Skip if monsters somehow all died mid-turn

        other_character_turn()
        monster_attack()
        character_death_check()
        persistent_stats["current_monsters"] = current_monster_group
        save_to_file()
        press_enter()

    while True:
        clear_screen()
        action = show_combat_stats(current_monster_group)

        if player_attack():
            if monster_death_check():
                persistent_stats["current_monsters"] = None
                save_to_file()
                return "cleared"
            result = combat_macro()
            if result == "cleared":
                return "cleared"
        if action in ["2", "skill", "useskill"]:
            skill_success = player_skill_select()
            if skill_success:
                if monster_death_check():
                    persistent_stats["current_monsters"] = None
                    save_to_file()
                    return "cleared"
                result = combat_macro()
                if result == "cleared":
                    return "cleared"
        if action in ["3", "retreat"]:
            try_retreat() # tries to retreat from the battle, 75% chance of sucess
        if action in ["4","upgrade","upgrades","shop","shp","lvl","level","levelup"]:
            upgrade_current_player() # Takes the player to the upgrade screen for their character, allows spending their level up points for things
            # This screen will allow spending 1 point to upgrade max_health, max_mana, damage dice, skills
            # each one will get more expensive each time at a scale of x 1.2 with a minimum of +1 to the price, each skill can be upgraded individulaly, this will increase the number of dice for healing or damage and if the skill does more than 1 attack it will also increase the attacks by 1. Each skill can be upgraded up to their max_upgrade
        if action in ["5", "equipment","equip","inv","inventory"]:
            equipment() # Takes the player to the equipment management screen where they can equip items to any character
            # Each character can have one of each type of item equipped, this will boost the characters stats, unequipping the item will decrease the stats
        if action in ["6","exit","leave","character","select"]:
            return "switch"

def explore_floor():
    """
    Manages room generation and type selection: shop, treasure, combat, etc.
    Probabilities:
      - 75%: regular monster fight
      - 10%: shop
      - 5%: treasure
      - 20% chance (independent) to add more monsters up to 10
    """
    persistent_stats["room"] += 1
    roll = random.random()
    floor = persistent_stats.get("floor", 1)

    if roll < 0.05:
        treasure()
    elif roll < 0.15:
        shop()
    else:
        result = combat()
        if result in ["switch", "cleared"]:
            return "exit"

    save_to_file()
    return True

def startup():
    global current_save_name, global_save_path

    global_save_path = os.path.join(save_directory, "Eyum.json")
    if not load_from_file():
        print(Fore.YELLOW + "No save file found. Creating new save...")
        save_to_file()

    while True:
        clear_screen()
        print(Fore.YELLOW + f"Eyum Terminal Adventure v{current_version}")
        print(Fore.BLUE + "Choose your character or type 'reset' or 'exit':")
        print(Fore.CYAN + "You will control one character, but the others act with you.\n")

        for i, name in enumerate(characters):
            dead = player_data["health"][i] <= 0
            color = Fore.RED if dead else Fore.GREEN
            print(color + f"{name}: Lv {player_data['level'][i]} | HP: {player_data['health'][i]} / {player_data['max_health'][i]}")

        choice = input(Fore.GREEN + "\n> ").strip().capitalize()

        if choice.lower() == "exit":
            print(Fore.RED + "Exiting...")
            time.sleep(0.5)
            clear_screen()
            return "exit"

        if choice.lower() == "reset":
            confirm = input(Fore.RED + "Type 'yes' to confirm full reset: ").strip().lower()
            if confirm == "yes":
                os.remove(global_save_path)
                generate_monster_group()
                print(Fore.GREEN + "Save file deleted.")
                time.sleep(1)
                return startup()
            else:
                print("Reset cancelled.")
                time.sleep(1)
                continue

        if choice in characters:
            index = characters.index(choice)
            if player_data["health"][index] <= 0:
                print(Fore.RED + f"{choice} is dead.")
                time.sleep(1)
                continue
            player_data["current_character"] = index
            return
        else:
            print("Invalid choice.")
            time.sleep(1)

# The main loop
if __name__ == "__main__":
    while True:
        result = startup()
        if result == "exit":
            break
        while True:
            alive = explore_floor()
            if alive == "exit":
                print(Fore.YELLOW + "Returning to character select...")
                time.sleep(1.5)
                break  # Break inner loop, go to character select
            elif not alive:
                print(Fore.YELLOW + "Returning to character select...")
                time.sleep(1.5)
                break  # Break inner loop, go to character select
            # Otherwise continue exploring with the same character