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
    {"name": "Slime", "health": 6, "damage": 2},
    {"name": "Goblin", "health": 8, "damage": 3},
    {"name": "Wolf", "health": 12, "damage": 4},
    {"name": "Slime 2", "health": 16, "damage": 5},
    {"name": "Goblin 2", "health": 20, "damage": 6},
    {"name": "Wolf 2", "health": 25, "damage": 7},
]

persistent_stats = {
    "current_version": current_version,
    "is_dead": False,
    "floor": 1,
    "room": 1,
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

# === Utility Functions ===
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
    try:
        with open(global_save_path, "w") as f:
            json.dump(save_data, f, indent=4)
    except PermissionError:
        print(Fore.RED + "[SAVE ERROR] Permission denied.")
        press_enter()
        clear_screen()
        sys.exit(1)

def load_from_file(filename):
    global global_save_path, player_data, persistent_stats
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
            except:
                print("Upgrade failed.")
                continue
        elif choice in ["5", "exit", "leave"]:
            return
        else:
            print("Invalid.")
            continue
        player_data["skill_points"] -= 1

def get_monster_group(floor):
    index = (floor - 1) * 3
    group = monster_list[index:index + 3]
    if len(group) < 3:
        group = (monster_list * 3)[index:index + 3]
    return group

def get_boss(floor):
    index = floor * 3
    return monster_list[min(index, len(monster_list) - 1)]

def rotate_monsters():
    if len(monster_list) > 3:
        monster_list.append(monster_list.pop(0))

def combat(player_data, monster):
    while player_data["health"] > 0 and monster["health"] > 0:
        clear_screen()
        print(Fore.YELLOW + f"--- Combat with {monster['name']} ---")
        xp_bar = f"{Fore.CYAN}{player_data['xp']}{Fore.GREEN}/{Fore.YELLOW}{player_data['xp_to_next']}{Fore.GREEN}"
        print(Fore.GREEN + f"{player_data['character']} (Lv{player_data['level']} {xp_bar}) {Fore.GREEN}HP: {player_data['health']} | Mana: {player_data['mana']}")
        print(Fore.RED + f"{monster['name']} HP: {monster['health']}")
        print(Fore.GREEN + "\n[1] Attack  [2] Use Skill  [3] Retreat  [4] Upgrade Menu  [5] Exit Game")

        action = input(Fore.GREEN + "> ").strip()
        if action in ["1", "atk", "attack"]:
            dmg = int(player_data.get("damage", 1) * random.uniform(0.95, 2))
            monster["health"] -= dmg
            print(Fore.GREEN + f"You dealt {dmg} damage.")
            restore_amount = max(1, player_data["max_mana"] // 10)
            player_data["mana"] = min(player_data["mana"] + restore_amount, player_data["max_mana"])
        elif action in ["2", "skill", "useskill", "useskill", "skl"]:
            skills = player_data.get("skills", [])
            if not skills:
                print(Fore.RED + "No skills available.")
                time.sleep(0.5)
                continue
            for i, skill in enumerate(skills):
                cost = player_data["skill_data"]["mana_costs"][i]
                print(f"  [{i + 1}] {skill} - Mana Cost: {cost}")
            try:
                idx = int(input("> ")) - 1
                skill_name = skills[idx]
                skill_data = player_data["skill_data"]
                mana_cost = skill_data["mana_costs"][idx]
                if player_data["mana"] < mana_cost:
                    print(Fore.RED + "Not enough mana!")
                    time.sleep(0.5)
                    continue
                player_data["mana"] -= mana_cost
                dmg_str = skill_data["damage"][idx]
                attack_count = skill_data["attacks"][idx]
                for _ in range(attack_count):
                    dmg = roll_dice(dmg_str)
                    monster["health"] -= dmg
                    print(Fore.MAGENTA + f"{skill_name} hits for {dmg} damage.")
                healing_amount = skill_data["healing"][idx]
                if healing_amount:
                    heal = roll_dice(f"{healing_amount}d4")
                    player_data["health"] += heal
                    print(Fore.CYAN + f"You heal for {heal} HP!")
            except:
                print(Fore.RED + "Invalid skill.")
                time.sleep(0.5)
                continue
        elif action in ["3", "retreat", "ret", "esc", "escape"]:
            print(Fore.YELLOW + "You fled the battle.")
            return None
        elif action in ["4", "level", "lvl", "upgrade", "xp", "shop"]:
            open_upgrade_menu()
            continue
        elif action in ["5", "exit", "leave"]:
            print(Fore.YELLOW + "Exiting to main menu...")
            save_to_file()
            time.sleep(0.5)
            clear_screen()
            return "exit"
        else:
            print(Fore.RED + "Invalid input.")
            time.sleep(0.6)
            continue

        if monster["health"] > 0:
            player_data["health"] -= monster["damage"]
            print(Fore.RED + f"{monster['name']} hits for {monster['damage']}")

        save_to_file()
        time.sleep(0.5)

    if player_data["health"] > 0:
        xp = int((monster.get("damage", 1) * 2 + 2) * 1.5)
        gain_xp(xp)
        restore_amount = max(1, player_data["max_mana"] // 5)
        player_data["mana"] = min(player_data["mana"] + restore_amount, player_data["max_mana"])
        press_enter()
        return True
    else:
        print(Fore.RED + "You have died.")
        persistent_stats["is_dead"] = True
        save_to_file()
        time.sleep(0.5)
        clear_screen()
        return False

def explore_floor():
    floor = persistent_stats["floor"]
    room = persistent_stats["room"]
    monsters = get_monster_group(floor)
    for i in range(10):
        persistent_stats["room"] += 1
        current_monster = monsters[i % len(monsters)].copy()
        result = combat(player_data, current_monster)
        if result == "exit":
            return "exit"
        elif result is False:
            print("You died...")
            return False
        elif result is None:
            print("You retreated.")
            return True
    boss = get_boss(floor).copy()
    print(f"Boss Encounter! {boss['name']}")
    result = combat(player_data, boss)
    if result == "exit":
        return "exit"
    elif result is False:
        print("You died to the boss...")
        return False

    # === Backup Save ===
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
            sys.exit(0)
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
            press_enter()

if __name__ == "__main__":
    while True:
        startup()  # load character and data
        alive = main()
        if alive == "exit":
            print(Fore.YELLOW + "Returning to character select...")
            time.sleep(1.5)
        elif not alive:
            print(Fore.YELLOW + "Returning to character select...")
            time.sleep(1.5)
