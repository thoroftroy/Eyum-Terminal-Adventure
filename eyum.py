# === Imports ===
import random
import time
from colorama import Fore, Style
import os
import sys
import platform
import json

# === Constants and Globals ===
current_version = "0.1"
save_directory = "eyum/saves"
os.makedirs(save_directory, exist_ok=True)

player_data = {
    "character": "none",
    "level": 1,
    "max_health": 15,
    "health": 15,
    "mana": 7,
    "max_mana": 7,
    "damage": 1,
    "defense": 0,
    "xp": 0,
    "xp_to_next": 10,
    "skill_points": 0,
    "skills": [],
    "skill_data": {},
    "learned_skills": {},
    "inventory": [],
    "equipped": [],
}

monster_list = [
    {"name": "Slime", "health": 6, "damage": 1},
    {"name": "Goblin", "health": 8, "damage": 2},
    {"name": "Wolf", "health": 12, "damage": 3},
    {"name": "Slime 2", "health": 16, "damage": 4},
    {"name": "Goblin 2", "health": 20, "damage": 5},
    {"name": "Wolf 2", "health": 25, "damage": 6},
]

persistent_stats = {
    "current_version": current_version,
    "is_dead": False,
    "floor": 1,
    "room": 1,
    "current_monsters": None,
}

character_skills = {
    "Lucian": {
        "skills": ["Firebolt", "Fireblast"],
        "damage": ["1d6","2d8"],
        "attacks": [2, 1],
        "healing": [0, 1],
        "mana_costs": [3, 7],
    },
    "Ilana": {
        "skills": ["Necro Blast", "Life Drain"],
        "damage": ["1d4", "1d4"],
        "attacks": [1, 2],
        "healing": [1, 4],
        "mana_costs": [4, 6],
    },
    "George": {
        "skills": ["Sword Slash", "Sword Burst"],
        "damage": ["1d8", "1d6"],
        "attacks": [1, 4],
        "healing": [0, 0],
        "mana_costs": [2, 7],
    },
}

characters = list(character_skills.keys())
current_save_name = ''
global_save_path = ''
current_monster_group = None  # global variable for active encounter

skill_table = [
    {"name": "Ember Spark", "damage": "1d4", "attacks": 1, "healing": 0, "mana_cost": 2, "weight": 10},
    {"name": "Piercing Shot", "damage": "1d6", "attacks": 1, "healing": 0, "mana_cost": 3, "weight": 10},
    {"name": "Quick Slash", "damage": "1d4", "attacks": 2, "healing": 0, "mana_cost": 4, "weight": 9},
    {"name": "Healing Pulse", "damage": "0", "attacks": 0, "healing": 2, "mana_cost": 4, "weight": 8},
    {"name": "Frost Needle", "damage": "1d8", "attacks": 1, "healing": 0, "mana_cost": 6, "weight": 8},
    {"name": "Shadow Jab", "damage": "1d6", "attacks": 2, "healing": 0, "mana_cost": 6, "weight": 7},
    {"name": "Radiant Surge", "damage": "1d4", "attacks": 1, "healing": 1, "mana_cost": 5, "weight": 7},
    {"name": "Arcane Burst", "damage": "2d6", "attacks": 1, "healing": 0, "mana_cost": 8, "weight": 6},
    {"name": "Whirlwind", "damage": "1d4", "attacks": 3, "healing": 0, "mana_cost": 7, "weight": 6},
    {"name": "Dark Recovery", "damage": "1d4", "attacks": 1, "healing": 2, "mana_cost": 6, "weight": 5},
]

drop_table = [
    {"name": "Rusty Dagger", "type": "weapon", "effect": "+1 damage", "value": 5, "weight": 10},
    {"name": "Healing Herb", "type": "potion", "effect": "+5 HP", "value": 10, "weight": 10},
    {"name": "Mana Leaf", "type": "potion", "effect": "+5 MP", "value": 12, "weight": 9},
    {"name": "Old Leather Armor", "type": "armor", "effect": "+1 defense", "value": 15, "weight": 9},
    {"name": "Steel Sword", "type": "weapon", "effect": "+3 damage", "value": 30, "weight": 7},
    {"name": "Minor Rune Stone", "type": "magic", "effect": "+2 mana", "value": 20, "weight": 7},
    {"name": "Golden Elixir", "type": "potion", "effect": "Restore all HP", "value": 100, "weight": 3},
    {"name": "Phantom Cloak", "type": "armor", "effect": "+2 dodge", "value": 50, "weight": 2},
    {"name": "Demon Core", "type": "relic", "effect": "+5 all stats", "value": 250, "weight": 1},
]


# === Utility Functions ===
def render_health_bar(current, max_val, length=20, color=Fore.GREEN):
    filled_length = int(length * current / max_val)
    bar = f"{color}{'█' * filled_length}{Fore.BLACK}{'█' * (length - filled_length)}{Style.RESET_ALL}"
    return bar

def roll_dice(dice_str):
    try:
        num, sides = map(int, dice_str.lower().split('d'))
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
def list_saved_files():
    dead_count = 0
    print(Fore.CYAN + "Available Characters:")
    for name in characters:
        save_path = os.path.join(save_directory, f"{name}.json")
        if os.path.exists(save_path):
            try:
                with open(save_path, "r") as f:
                    data = json.load(f)
                is_dead = data.get("persistent_stats", {}).get("is_dead", False)
                if is_dead:
                    print(Fore.RED + f"  - {name} (dead)")
                    dead_count += 1
                else:
                    print(Fore.WHITE + f"  - {name}")
            except Exception:
                print(Fore.YELLOW + f"  - {name} (corrupt?)")
        else:
            print(Fore.LIGHTBLACK_EX + f"  - {name} (no save)")
    if dead_count == len(characters):
        print(Fore.MAGENTA + "\nAll characters are dead. Type 'reset' to delete all save files.")

def save_to_file():
    global player_data, persistent_stats, global_save_path
    player_data["name"] = os.path.splitext(current_save_name)[0]
    persistent_stats["current_version"] = current_version
    save_data = {"player": player_data, "persistent_stats": persistent_stats}
    if current_monster_group is not None:
        persistent_stats["current_monsters"] = current_monster_group
    else:
        persistent_stats["current_monsters"] = None
    try:
        with open(global_save_path, "w") as f:
            json.dump(save_data, f, indent=4)
    except PermissionError:
        print(Fore.RED + "[SAVE ERROR] Permission denied.")
        press_enter()
        clear_screen()
        sys.exit(1)

def load_from_file(filename):
    global global_save_path, player_data, persistent_stats, current_monster_group
    global_save_path = os.path.join(save_directory, filename)
    try:
        with open(global_save_path, "r") as f:
            data = json.load(f)
        player_data.update(data.get("player", {}))
        persistent_stats.update(data.get("persistent_stats", {}))
        print(Fore.GREEN + f"Loaded save: {filename}")
        if persistent_stats.get("current_version") != current_version:
            print(Fore.RED + "Version mismatch!")
            press_enter()
        current_monster_group = persistent_stats.get("current_monsters", None)
        return True
    except Exception as e:
        print(Fore.RED + f"Error loading save: {e}")
        press_enter()
        return False

# === Core Functions ===
def gain_xp(amount):
    player_data["xp"] += amount
    print(Fore.CYAN + f"You gained {amount} XP!")
    while player_data["xp"] >= player_data["xp_to_next"]:
        player_data["xp"] -= player_data["xp_to_next"]
        player_data["level"] += 1
        player_data["skill_points"] += 1
        player_data["xp_to_next"] = int(player_data["xp_to_next"] * 1.5)
        # Scale and restore mana
        player_data["max_mana"] = int(player_data["max_mana"] * 1.2)
        player_data["mana"] = player_data["max_mana"]
        print(Fore.YELLOW + f"Level up! Now level {player_data['level']}")
        print(Fore.MAGENTA + f"Skill point earned! Total: {player_data['skill_points']}")
        print(Fore.BLUE + f"Max mana increased to {player_data['max_mana']} and restored to full!")

def open_upgrade_menu():
    while True:
        clear_screen()
        print(Fore.BLUE + "=== Upgrade Menu ===")
        print(f"Skill Points: {player_data['skill_points']}")
        print("  [1] +5 Max Health")
        print("  [2] +2 Mana")
        print("  [3] +1 Base Damage")
        print("  [4] Upgrade Skill")
        print("  [5] Exit")
        if player_data["skill_points"] <= 0:
            print(Fore.RED + "No skill points.")
            press_enter()
            return
        choice = input(Fore.GREEN + "> ").strip()
        if choice in ["1", "hp", "health"]:
            player_data["health"] += 5
            player_data["max_health"] += 5
        elif choice in ["2", "mana", "man", "mp"]:
            player_data["mana"] += 2
            player_data["max_mana"] += 3
        elif choice in ["3", "dmg", "atk", "damage", "attack"]:
            player_data["damage"] += 1
        elif choice in ["4", "skills", "skill"]:
            skills = player_data.get("skills", [])
            if not skills:
                print("No skills.")
                continue
            print("Choose skill:")
            for i, skill in enumerate(skills):
                print(f"  [{i+1}] {skill}")
            try:
                idx = int(input("> ")) - 1
                dmg_str = player_data["skill_data"]["damage"][idx]
                if not dmg_str.startswith("1d"):
                    print("Unsupported format.")
                    continue
                new_die = int(dmg_str[2:]) + 2
                player_data["skill_data"]["damage"][idx] = f"1d{new_die}"
                player_data["skill_data"]["attacks"][idx] += 1
                print(f"{skills[idx]} upgraded!")
                time.sleep(0.5)
            except:
                print("Upgrade failed.")
                continue
        elif choice in ["5", "exit", "leave"]:
            return
        else:
            print("Invalid.")
            continue
        player_data["skill_points"] -= 1

def generate_monster_group():
    group = [random.choice(monster_list).copy()]
    while len(group) < 5 and random.random() < 0.3:
        group.append(random.choice(monster_list).copy())
    for m in group:
        m["max_health"] = m["health"]
    return group

#def get_monster_group(floor):
#    index = (floor - 1) * 3
#    group = monster_list[index:index + 3]
#    if len(group) < 3:
#        group = (monster_list * 3)[index:index + 3]
#    return group

def get_boss(floor):
    index = floor * 3
    return monster_list[min(index, len(monster_list) - 1)]

def rotate_monsters():
    if len(monster_list) > 3:
        monster_list.append(monster_list.pop(0))

def combat(player_data, monsters):
    while player_data["health"] > 0 and any(m["health"] > 0 for m in monsters):
        clear_screen()
        # UI Display
        xp_bar = f"{Fore.CYAN}{player_data['xp']}{Fore.GREEN}/{Fore.YELLOW}{player_data['xp_to_next']}{Fore.GREEN}"
        player_bar = render_health_bar(player_data["health"], player_data["max_health"], color=Fore.GREEN)
        mana_bar = render_health_bar(player_data["mana"], player_data["max_mana"], color=Fore.BLUE)
        print(Fore.GREEN + f"{player_data['character']} (Lv{player_data['level']} {xp_bar})")
        print(f"HP: {player_data['health']} / {player_data['max_health']}  {player_bar}")
        print(f"{Fore.BLUE}MP: {player_data['mana']} / {player_data['max_mana']}  {mana_bar}")

        print(Fore.RED + "\n--- Monsters ---")
        for idx, m in enumerate(monsters):
            if m["health"] <= 0:
                bar = render_health_bar(0, m["max_health"], color=Fore.BLACK)
                print(Fore.RED + f"[{idx+1}] {m['name']} (defeated)")
                print(bar)
            else:
                bar = render_health_bar(m["health"], m["max_health"], color=Fore.RED)
                print(Fore.RED + f"[{idx+1}] {m['name']} HP: {m['health']} / {m['max_health']}")
                print(bar)

        print(Fore.GREEN + "\n[1] Attack  [2] Use Skill  [3] Retreat  [4] Upgrade Menu  [5] Exit Game")
        action = input(Fore.GREEN + "> ").strip().lower()

        if action in ["1", "atk", "attack"]:
            targets = [i for i, m in enumerate(monsters) if m["health"] > 0]
            print("Choose target:")
            for i in targets:
                print(Fore.RED + f"  [{i + 1}] {monsters[i]['name']} ({monsters[i]['health']} HP)")
            try:
                choice = int(input("> ")) - 1
                if choice not in targets:
                    print(Fore.RED + "Invalid target.")
                    time.sleep(0.5)
                    continue
                dmg = int(player_data.get("damage", 1) * random.uniform(0.95, 2))
                monsters[choice]["health"] -= dmg
                print(Fore.GREEN + f"You dealt {dmg} damage to {monsters[choice]['name']}.")
                restore_amount = max(1, player_data["max_mana"] // 10)
                player_data["mana"] = min(player_data["mana"] + restore_amount, player_data["max_mana"])
            except:
                print(Fore.RED + "Invalid input.")
                time.sleep(0.5)
                continue

        elif action in ["2", "skill", "useskill", "skl"]:
            skills = player_data.get("skills", [])
            if not skills:
                print(Fore.RED + "No skills available.")
                time.sleep(0.5)
                continue
            for i, skill in enumerate(skills):
                print(f"  [{i + 1}] {skill} - Mana Cost: {player_data['skill_data']['mana_costs'][i]}")
            try:
                idx = int(input("> ")) - 1
                if idx < 0 or idx >= len(skills):
                    raise ValueError
                skill_name = skills[idx]
                sd = player_data["skill_data"]
                cost = sd["mana_costs"][idx]
                if player_data["mana"] < cost:
                    print(Fore.RED + "Not enough mana.")
                    time.sleep(0.5)
                    continue
                player_data["mana"] -= cost
                attacks = sd["attacks"][idx]
                dmg_str = sd["damage"][idx]

                if attacks == 1:
                    # Single target skill
                    targets = [i for i, m in enumerate(monsters) if m["health"] > 0]
                    print("Choose target:")
                    for i in targets:
                        print(f"  [{i+1}] {monsters[i]['name']} ({monsters[i]['health']} HP)")
                    target_idx = int(input("> ")) - 1
                    if target_idx not in targets:
                        print("Invalid target.")
                        continue
                    dmg = roll_dice(dmg_str)
                    monsters[target_idx]["health"] -= dmg
                    print(Fore.MAGENTA + f"{skill_name} hits {monsters[target_idx]['name']} for {dmg} damage.")
                else:
                    # Multi-target skill hits randomly
                    for _ in range(attacks):
                        valid_targets = [m for m in monsters if m["health"] > 0]
                        if not valid_targets:
                            break
                        target = random.choice(valid_targets)
                        dmg = roll_dice(dmg_str)
                        target["health"] -= dmg
                        print(Fore.MAGENTA + f"{skill_name} hits {target['name']} for {dmg} damage.")

                healing = sd["healing"][idx]
                if healing:
                    heal = roll_dice(f"{healing}d4")
                    player_data["health"] = min(player_data["health"] + heal, player_data["max_health"])
                    print(Fore.CYAN + f"You heal for {heal} HP.")
            except:
                print(Fore.RED + "Skill failed.")
                time.sleep(0.5)
                continue

        elif action in ["3", "retreat", "ret", "esc", "escape"]:
            print(Fore.YELLOW + "You fled the battle.")
            return None

        elif action in ["4", "level", "upgrade", "xp"]:
            open_upgrade_menu()
            continue

        elif action in ["5", "exit", "leave"]:
            print(Fore.YELLOW + "Exiting to main menu...")
            save_to_file()
            time.sleep(0.5)
            clear_screen()
            return "exit"

        else:
            print(Fore.RED + "Invalid action.")
            time.sleep(0.5)
            continue

        # Enemy Turn
        for m in monsters:
            if m["health"] > 0:
                player_data["health"] -= m["damage"]
                print(Fore.RED + f"{m['name']} hits you for {m['damage']}")
        save_to_file()
        time.sleep(0.5)

    if player_data["health"] <= 0:
        print(Fore.RED + "You have died.")
        persistent_stats["is_dead"] = True
        save_to_file()
        time.sleep(0.5)
        clear_screen()
        return False
    else:
        global current_monster_group
        current_monster_group = None
        persistent_stats["current_monsters"] = None
        save_to_file()

        xp_total = sum((m["damage"] * 2 + 2) for m in monsters)
        gain_xp(int(xp_total * 1.5))
        press_enter()
        return True

def explore_floor():
    global current_monster_group
    floor = persistent_stats["floor"]
    room = persistent_stats["room"]

    # Handle active combat if it exists
    if current_monster_group is not None:
        result = combat(player_data, current_monster_group)
        if result == "exit":
            return "exit"
        elif result is False:
            print("You died...")
            return False
        elif result is None:
            print("You retreated.")
            return True

    # Regular rooms
    for _ in range(10):
        persistent_stats["room"] += 1
        current_monster_group = generate_monster_group()
        result = combat(player_data, current_monster_group)
        if result == "exit":
            return "exit"
        elif result is False:
            print("You died...")
            return False
        elif result is None:
            print("You retreated.")
            return True
        current_monster_group = None
        persistent_stats["current_monsters"] = None
        save_to_file()

    # Boss encounter
    boss = get_boss(floor).copy()
    boss["max_health"] = boss["health"]
    current_monster_group = [boss]
    result = combat(player_data, current_monster_group)
    print(f"Boss Encounter! {boss['name']}")
    if result == "exit":
        return "exit"
    elif result is False:
        print("You died to the boss...")
        return False

    current_monster_group = None
    persistent_stats["current_monsters"] = None
    save_to_file()

    # Backup save
    backup_path = global_save_path.replace(".json", f"_backup_floor{floor}.json")
    with open(backup_path, "w") as f:
        json.dump({"player": player_data, "persistent_stats": persistent_stats}, f, indent=4)

    rotate_monsters()
    persistent_stats["floor"] += 1
    persistent_stats["room"] = 1
    return True

def main():
    return explore_floor()

def startup():
    global current_save_name, global_save_path
    while True:
        clear_screen()
        print(Fore.YELLOW + f"Eyum Terminal Adventure v{current_version}")
        print(Fore.BLUE + "Choose your character or type 'exit' to quit:")
        list_saved_files()
        choice = input(Fore.GREEN + "> ").strip().capitalize()
        if choice.lower() == "exit":
            print(Fore.RED + "Exiting...")
            time.sleep(0.5)
            clear_screen()
            return "exit"
        if choice.lower() == "reset":
            confirm = input(
                Fore.RED + "Are you sure? This will delete all character saves. Type 'yes' to confirm: ").strip().lower()
            if confirm == "yes":
                for name in characters:
                    save_path = os.path.join(save_directory, f"{name}.json")
                    if os.path.exists(save_path):
                        os.remove(save_path)
                print(Fore.GREEN + "All saves deleted.")
                time.sleep(1)
                clear_screen()
                continue
            else:
                print("Reset cancelled.")
                time.sleep(1)
                clear_screen()
                continue
        if choice in characters:
            current_save_name = f"{choice}.json"
            global_save_path = os.path.join(save_directory, current_save_name)
            if os.path.exists(global_save_path):
                if not load_from_file(current_save_name):
                    print(f"{Fore.RED}Failed to load.")
                    time.sleep(0.5)
                    clear_screen()
                    sys.exit()
                if persistent_stats.get("is_dead", False):
                    print(f"{Fore.YELLOW}Character is dead. Delete save to retry by typing reset {Fore.RED}(THIS WILL RESET ALL CHARACTERS).")
                    press_enter()
                    continue
            else:
                print(f"Creating new save for {choice}")
                base = character_skills[choice]
                player_data.update({
                    "character": choice,
                    "level": 1,
                    "xp": 0,
                    "xp_to_next": 10,
                    "skill_points": 0,
                    "max_health": 15,
                    "health": 15,
                    "mana": 7,
                    "max_mana": 7,
                    "damage": 1,
                    "defense": 0,
                    "skills": base["skills"],
                    "skill_data": {
                        "damage": base["damage"],
                        "attacks": base["attacks"],
                        "healing": base["healing"],
                        "mana_costs": base["mana_costs"]
                    },
                    "learned_skills": {},
                    "inventory": [],
                    "equipped": [],
                })
                persistent_stats.update({
                    "is_dead": False,
                    "floor": 1,
                    "room": 1,
                })
                save_to_file()
            break
        else:
            print("Invalid character.")
            time.sleep(0.5)

if __name__ == "__main__":
    while True:
        result = startup()
        if result == "exit":
            break
        alive = main()
        if alive == "exit":
            print(Fore.YELLOW + "Returning to character select...")
            time.sleep(1.5)
        elif not alive:
            print(Fore.YELLOW + "Returning to character select...")
            time.sleep(1.5)

