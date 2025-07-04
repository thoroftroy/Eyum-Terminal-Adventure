# === Imports ===
import random
import time
from colorama import Fore, Style
import os
import sys
import platform
import json

from game_data import drop_table, skill_table, monster_list

# === Constants and Globals ===
current_version = "0.1"
save_directory = "eyum/saves"
os.makedirs(save_directory, exist_ok=True)

player_data = {
    "character": "none",
    "level": 1,
    "max_health": 25,
    "health": 25,
    "mana": 7,
    "max_mana": 7,
    "damage": 1,
    "coins": 0,
    "xp": 0,
    "xp_to_next": 10,
    "skill_points": 0,
    "skills": [],
    "skill_data": {},
    "learned_skills": {},
    "inventory": [],
    "equipped": [],
}

persistent_stats = {
    "current_version": current_version,
    "is_dead": False,
    "floor": 1,
    "room": 1,
    "current_monsters": None,
    "rooms_since_shop": 0,
    "rooms_since_treasure": 0,
    "monster_rotation_index": 0,
}

character_skills = {
    "Lucian": {
        "skills": ["Firebolt", "Fireblast"],
        "damage": ["1d4","2d8"],
        "attacks": [2, 1],
        "healing": [0, 0],
        "mana_costs": [4, 8],
    },
    "Ilana": {
        "skills": ["Necro Blast", "Life Drain"],
        "damage": ["1d4", "1d4"],
        "attacks": [1, 2],
        "healing": [2, 4],
        "mana_costs": [3, 6],
    },
    "George": {
        "skills": ["Sword Slash", "Sword Burst"],
        "damage": ["1d6", "1d4"],
        "attacks": [2, 4],
        "healing": [0, 0],
        "mana_costs": [3, 8],
    },
}

characters = list(character_skills.keys())
current_save_name = ''
global_save_path = ''
current_monster_group = None  # global variable for active encounter

# === Utility Functions ===
def recalculate_all_stats(pdata):
    # If base_stats is missing, initialize it from current values
    if "base_stats" not in pdata:
        pdata["base_stats"] = {
            "damage": pdata.get("damage", 1),
            "max_health": pdata.get("max_health", 25),
            "max_mana": pdata.get("max_mana", 7)
        }

    base = pdata["base_stats"]
    pdata["damage"] = base["damage"]
    pdata["max_health"] = base["max_health"]
    pdata["max_mana"] = base["max_mana"]

def rainbow_text(text):
    colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
    output = ""
    for i, char in enumerate(text):
        output += colors[i % len(colors)] + char
    return output + Style.RESET_ALL

def get_unique_items(owned, count):
    available = [item for item in drop_table if item["name"] not in owned]
    return random.sample(available, min(count, len(available)))

def get_unique_skill(owned):
    available = [skill for skill in skill_table if skill["name"] not in owned]
    return random.choice(available) if available else None

def has_all_items():
    owned_names = [i["name"] for i in player_data["inventory"]]
    return all(item["name"] in owned_names for item in drop_table)

def has_all_skills():
    return all(skill["name"] in player_data["skills"] for skill in skill_table)

def render_health_bar(current, max_val, length=40, color=Fore.GREEN):
    filled_length = int(length * current / max_val)
    empty_length = length - filled_length

    filled_bar = f"{Style.BRIGHT}{color}{'█' * filled_length}"
    empty_bar = f"{Fore.WHITE}{'░' * empty_length}"
    return f"{filled_bar}{empty_bar}{Style.RESET_ALL}"

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
        # Ensure all equipped items have parsed bonuses
        for item in player_data.get("equipped", []):
            if "bonus" not in item and "effect" in item:
                convert_effect_string_to_bonus(item)
        apply_equipment_bonuses_for(player_data)
        return True
    except Exception as e:
        print(Fore.RED + f"Error loading save: {e}")
        press_enter()
        return False

# === Core Functions ===
def convert_effect_string_to_bonus(item):
    effect_str = item.get("effect", "").strip()
    effect_str = effect_str.replace("+", "").lower()

    bonuses = {"damage": 0, "max_health": 0, "max_mana": 0}
    parts = effect_str.replace(" and ", ",").split(",")
    for part in parts:
        words = part.strip().split()
        if len(words) >= 2:
            try:
                val = int(words[0])
                stat = " ".join(words[1:])
                if "damage" in stat:
                    bonuses["damage"] += val
                elif "mana" in stat or "mp" in stat:
                    bonuses["max_mana"] += val
                elif "health" in stat or "hp" in stat:
                    bonuses["max_health"] += val
                elif "all stats" in stat:
                    bonuses["damage"] += val
                    bonuses["max_health"] += val
                    bonuses["max_mana"] += val
            except ValueError:
                continue
    item["bonus"] = bonuses
    return item

def apply_equipment_bonuses_for(pdata):
    """
    Applies equipment bonuses to a given player data dict.
    Recalculates from base stats and applies bonuses from all equipped items.
    """
    base = pdata.get("base_stats", {
        "damage": 1,
        "max_health": 25,
        "max_mana": 7,
    })

    pdata["damage"] = base["damage"]
    pdata["max_health"] = base["max_health"]
    pdata["max_mana"] = base["max_mana"]

    for item in pdata.get("equipped", []):
        if "bonus" not in item and "effect" in item:
            item = convert_effect_string_to_bonus(item)
        bonus = item.get("bonus", {})
        pdata["damage"] += bonus.get("damage", 0)
        pdata["max_health"] += bonus.get("max_health", 0)
        pdata["max_mana"] += bonus.get("max_mana", 0)

    pdata["health"] = min(pdata["health"], pdata["max_health"])
    pdata["mana"] = min(pdata["mana"], pdata["max_mana"])

def gain_xp(amount):
    player_data["xp"] += amount
    print(Fore.CYAN + f"You gained {amount} XP!")

    while player_data["xp"] >= player_data["xp_to_next"]:
        player_data["xp"] -= player_data["xp_to_next"]
        player_data["level"] += 1

        floor = persistent_stats.get("floor", 1)
        earned_points = max(1, floor)  # guarantees at least 1
        player_data["skill_points"] += earned_points

        player_data["xp_to_next"] = int(player_data["xp_to_next"] * 1.5)

        # Scale and restore mana and health
        player_data["max_mana"] = int(player_data["max_mana"] * 1.2)
        player_data["mana"] = player_data["max_mana"]

        player_data["max_health"] = int(player_data["max_health"] * 1.1)
        player_data["health"] = player_data["max_health"]

        player_data["base_stats"] = {
            "damage": player_data["damage"],
            "max_health": player_data["max_health"],
            "max_mana": player_data["max_mana"],
        }

        print(Fore.YELLOW + f"Level up! Now level {player_data['level']}")
        print(Fore.MAGENTA + f"+{earned_points} Skill Point{'s' if earned_points > 1 else ''}! Total: {player_data['skill_points']}")
        print(Fore.BLUE + f"Stats restored to full!")

def reset_game_state():
    """
    Fully clears and resets all runtime globals and deletes all character save files.
    """
    global player_data, persistent_stats, current_monster_group

    for name in characters:
        path = os.path.join(save_directory, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)

    player_data.clear()
    player_data.update({
        "character": "none",
        "level": 1,
        "max_health": 25,
        "health": 25,
        "mana": 7,
        "max_mana": 7,
        "damage": 1,
        "coins": 0,
        "xp": 0,
        "xp_to_next": 10,
        "skill_points": 0,
        "skills": [],
        "skill_data": {},
        "learned_skills": {},
        "inventory": [],
        "equipped": [],
        "upgrade_costs": {
            "max_health": 1,
            "max_mana": 1,
            "damage": 1,
        },
        "skill_upgrade_costs": [],
    })

    persistent_stats.clear()
    persistent_stats.update({
        "current_version": current_version,
        "is_dead": False,
        "floor": 1,
        "room": 1,
        "current_monsters": None,
        "rooms_since_shop": 0,
        "rooms_since_treasure": 0,
        "monster_rotation_index": 0,
    })

    current_monster_group = None

def open_treasure_room():
    persistent_stats["rooms_since_treasure"] = 0
    clear_screen()

    print(Fore.YELLOW + Style.BRIGHT + "\n" + "=" * 50)
    print(Fore.CYAN + Style.BRIGHT + "+++ TREASURE ROOM +++".center(50))
    print("=" * 50 + "\n")
    time.sleep(1)

    coin_reward = random.randint(40, 80)
    player_data["coins"] += coin_reward
    print(Fore.YELLOW + f"You found a stash of {coin_reward} coins!".center(50))
    time.sleep(1)

    # 25% chance of item
    if random.random() < 0.25:
        owned_items = [i["name"] for i in player_data["inventory"]]
        unique_items = get_unique_items(owned_items, 1)
        if unique_items:
            item = unique_items[0]
            player_data["inventory"].append(item)
            bonus = item.get("bonus", {})
            parts = []
            if bonus.get("damage"):
                parts.append(f"+{bonus['damage']} dmg")
            if bonus.get("max_health"):
                parts.append(f"+{bonus['max_health']} HP")
            if bonus.get("max_mana"):
                parts.append(f"+{bonus['max_mana']} MP")
            if item.get("restore_full"):
                parts.append("Restores Full HP/MP")
            effect = ", ".join(parts) if parts else "No effect"
            print(Fore.GREEN + f"You also found an item: {item['name']} ({effect})".center(50))
            time.sleep(1)

    # 10% chance of skill
    if random.random() < 0.10:
        skill = get_unique_skill(player_data["skills"])
        if skill:
            player_data["skills"].append(skill["name"])
            if "skill_upgrade_costs" not in player_data:
                player_data["skill_upgrade_costs"] = []
            player_data["skill_upgrade_costs"].append(1)
            sd = player_data["skill_data"]
            sd.setdefault("damage", []).append(skill["damage"])
            sd.setdefault("attacks", []).append(skill["attacks"])
            sd.setdefault("healing", []).append(skill["healing"])
            sd.setdefault("mana_costs", []).append(skill["mana_cost"])
            print(Fore.MAGENTA + f"You discovered a rare skill: {skill['name']}!".center(50))
        else:
            print(Fore.MAGENTA + "You almost found a skill... but you already knew it.".center(50))
        time.sleep(1)

    print(Style.RESET_ALL)
    save_to_file()
    press_enter()

def open_inventory_menu():
    def remove_item_from_all_characters(item_name):
        for name in characters:
            path = os.path.join(save_directory, f"{name}.json")
            if not os.path.exists(path):
                continue
            with open(path, "r") as f:
                data = json.load(f)
            pdata = data["player"]
            pdata["inventory"] = [i for i in pdata.get("inventory", []) if i["name"] != item_name]
            pdata["equipped"] = [i for i in pdata.get("equipped", []) if i["name"] != item_name]
            data["player"] = pdata
            with open(path, "w") as f:
                json.dump(data, f, indent=4)

    while True:
        clear_screen()
        print(Fore.BLUE + "--- Party Inventory & Equipment ---")

        all_items = []
        index_map = []
        for char_name in characters:
            path = os.path.join(save_directory, f"{char_name}.json")
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                pdata = data["player"]
                equipped = {item["type"]: item for item in pdata.get("equipped", [])}
                inventory = pdata.get("inventory", [])
                types = ["weapon", "armor", "magic", "relic", "potion"]
                print(Fore.CYAN + f"\n== {char_name}'s Inventory ==")
                for t in types:
                    print(Fore.LIGHTBLACK_EX + f"\n  {t.capitalize()}:")

                    if t in equipped:
                        eq = equipped[t]
                        bonus = eq.get("bonus", {})
                        parts = []
                        if bonus.get("damage"):
                            parts.append(f"+{bonus['damage']} dmg")
                        if bonus.get("max_health"):
                            parts.append(f"+{bonus['max_health']} HP")
                        if bonus.get("max_mana"):
                            parts.append(f"+{bonus['max_mana']} MP")
                        if eq.get("restore_full"):
                            parts.append("Restores Full HP/MP")
                        bonus_text = ", ".join(parts) if parts else "No effect"
                        print(Fore.YELLOW + f"    Equipped: {eq['name']}".ljust(40) + f"({bonus_text})")
                        index_map.append((char_name, {"type": t, "unequip": True}))
                        print(Fore.LIGHTBLACK_EX + f"    [{len(index_map)}] Unequip")

                    for item in inventory:
                        if item["type"] == t and item["name"] != equipped.get(t, {}).get("name"):
                            bonus = item.get("bonus", {})
                            parts = []
                            if bonus.get("damage"):
                                parts.append(f"+{bonus['damage']} dmg")
                            if bonus.get("max_health"):
                                parts.append(f"+{bonus['max_health']} HP")
                            if bonus.get("max_mana"):
                                parts.append(f"+{bonus['max_mana']} MP")
                            if item.get("restore_full"):
                                parts.append("Restores Full HP/MP")
                            bonus_text = ", ".join(parts) if parts else "No effect"
                            index_map.append((char_name, item))
                            print(Fore.WHITE + f"    [{len(index_map)}] {item['name']}".ljust(40) + f"({bonus_text})")
            except Exception as e:
                print(Fore.RED + f"[ERROR] {char_name}: {e}")

        print(Fore.GREEN + "\nType the item number to equip it, or 'exit' to go back.")
        choice = input(Fore.GREEN + "> ").strip().lower()
        if choice == "exit":
            return
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(index_map):
                raise ValueError
            source_name, item = index_map[idx]
            unequip = item.get("unequip", False)
            if unequip:
                path = os.path.join(save_directory, f"{source_name}.json")
                with open(path, "r") as f:
                    data = json.load(f)
                pdata = data["player"]
                pdata["equipped"] = [e for e in pdata["equipped"] if e["type"] != item["type"]]
                recalculate_all_stats(pdata)
                if pdata["character"] == player_data["character"]:
                    player_data.update(pdata)
                    apply_equipment_bonuses_for(player_data)
                data["player"] = pdata
                with open(path, "w") as f:
                    json.dump(data, f, indent=4)
                print(Fore.YELLOW + f"Unequipped {item['type']} from {source_name}.")
                press_enter()
                continue

            print(Fore.CYAN + f"Who should equip {item['name']}? (Lucian, Ilana, George)")
            target_name = input(Fore.GREEN + "> ").strip().capitalize()
            if target_name not in characters:
                print(Fore.RED + "Invalid character.")
                time.sleep(1)
                continue

            remove_item_from_all_characters(item["name"])
            # Also remove from source character's inventory if needed
            if source_name != target_name:
                source_path = os.path.join(save_directory, f"{source_name}.json")
                if os.path.exists(source_path):
                    with open(source_path, "r") as f:
                        source_data = json.load(f)
                    source_pdata = source_data["player"]
                    source_pdata["inventory"] = [i for i in source_pdata["inventory"] if i["name"] != item["name"]]
                    source_data["player"] = source_pdata
                    with open(source_path, "w") as f:
                        json.dump(source_data, f, indent=4)

            path = os.path.join(save_directory, f"{target_name}.json")
            with open(path, "r") as f:
                data = json.load(f)
            pdata = data["player"]
            pdata["equipped"] = [e for e in pdata["equipped"] if e["type"] != item["type"]]
            pdata["equipped"].append(item)
            if "bonus" not in item and "effect" in item:
                convert_effect_string_to_bonus(item)
            apply_equipment_bonuses_for(pdata)
            pdata["health"] = min(pdata["health"], pdata["max_health"])
            pdata["mana"] = min(pdata["mana"], pdata["max_mana"])
            if pdata["character"] == player_data["character"]:
                player_data.update(pdata)
            data["player"] = pdata
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
            print(Fore.YELLOW + f"Equipped {item['name']} on {target_name}")
            press_enter()
        except:
            print(Fore.RED + "Invalid input.")
            time.sleep(0.5)

def open_upgrade_menu():
    # initialize upgrade cost trackers if not present
    if "upgrade_costs" not in player_data:
        player_data["upgrade_costs"] = {
            "max_health": 1,
            "max_mana": 1,
            "damage": 1
        }
    if "skill_upgrade_costs" not in player_data:
        player_data["skill_upgrade_costs"] = [1 for _ in player_data["skills"]]

    def save_stats():
        player_data["base_stats"] = {
            "damage": player_data["damage"],
            "max_health": player_data["max_health"],
            "max_mana": player_data["max_mana"]
        }

    while True:
        clear_screen()
        print(f"{Fore.BLUE}Skill Points: {player_data['skill_points']}  |  XP: {player_data['xp']}  |  Hp: {player_data['health']}/{player_data['max_health']}")

        # Grab current costs
        costs = player_data["upgrade_costs"]
        hp_cost = costs["max_health"]
        mana_cost = costs["max_mana"]
        dmg_cost = costs["damage"]

        # Color options based on affordability
        hp_color = Fore.GREEN if player_data["skill_points"] >= hp_cost else Fore.RED
        mana_color = Fore.GREEN if player_data["skill_points"] >= mana_cost else Fore.RED
        dmg_color = Fore.GREEN if player_data["skill_points"] >= dmg_cost else Fore.RED

        print(f"{hp_color}  [1] +5 Max Health ({hp_cost} pts)")
        print(f"{mana_color}  [2] +2 Mana ({mana_cost} pts)")
        print(f"{dmg_color}  [3] +1 Base Damage ({dmg_cost} pts)")
        print(Fore.CYAN + "  [4] Upgrade Skill")
        floor = persistent_stats.get("floor", 1)
        min_cost = (floor + 1) * 10
        xp_cost = max(min_cost, int(player_data["xp"] * 0.25))
        heal_color = Fore.GREEN if player_data["xp"] >= xp_cost else Fore.RED
        print(f"{heal_color}  [5] Heal 10% HP (costs 25% XP)")
        print(Fore.CYAN + "  [6] Exit")

        if player_data["skill_points"] <= 0:
            print(Fore.RED + "No skill points.")

        choice = input(Fore.GREEN + "> ").strip()
        if choice == "1":
            cost = player_data["upgrade_costs"]["max_health"]
            if player_data["skill_points"] < cost:
                print(Fore.RED + f"Not enough points (cost: {cost})")
                time.sleep(1)
                continue
            player_data["max_health"] += 5
            player_data["health"] += 5
            player_data["skill_points"] -= cost
            save_stats()
            player_data["upgrade_costs"]["max_health"] = max(int(cost * 1.2), cost + 1)

        elif choice == "2":
            cost = player_data["upgrade_costs"]["max_mana"]
            if player_data["skill_points"] < cost:
                print(Fore.RED + f"Not enough points (cost: {cost})")
                time.sleep(1)
                continue
            player_data["max_mana"] += 3
            player_data["mana"] += 2
            player_data["skill_points"] -= cost
            save_stats()
            player_data["upgrade_costs"]["max_mana"] = max(int(cost * 1.2), cost + 1)

        elif choice == "3":
            cost = player_data["upgrade_costs"]["damage"]
            if player_data["skill_points"] < cost:
                print(Fore.RED + f"Not enough points (cost: {cost})")
                time.sleep(1)
                continue
            player_data["damage"] += 1
            player_data["skill_points"] -= cost
            save_stats()
            player_data["upgrade_costs"]["damage"] = max(int(cost * 1.2), cost + 1)

        elif choice == "4":
            skills = player_data.get("skills", [])
            if not skills:
                print("No skills.")
                press_enter()
                continue

            print("choose skill:")
            # Ensure skill_upgrade_costs list is the same length as skills
            if len(player_data["skill_upgrade_costs"]) < len(player_data["skills"]):
                missing = len(player_data["skills"]) - len(player_data["skill_upgrade_costs"])
                player_data["skill_upgrade_costs"].extend([1] * missing)
            for i, skill in enumerate(skills):
                cost = player_data["skill_upgrade_costs"][i]
                color = Fore.GREEN if player_data["skill_points"] >= cost else Fore.RED
                print(f"{color}  [{i + 1}] {skill} (cost: {cost})")

            try:
                idx = int(input("> ")) - 1
                if idx < 0 or idx >= len(skills):
                    raise ValueError

                cost = player_data["skill_upgrade_costs"][idx]
                if player_data["skill_points"] < cost:
                    print(Fore.RED + f"Not enough points (cost: {cost})")
                    time.sleep(1)
                    continue

                dmg_str = player_data["skill_data"]["damage"][idx]
                if not dmg_str.startswith("1d"):
                    print("Unsupported Format.")
                    continue

                new_die = int(dmg_str[2:]) + 2
                player_data["skill_data"]["damage"][idx] = f"1d{new_die}"
                player_data["skill_data"]["attacks"][idx] += 1
                player_data["skill_points"] -= cost
                save_stats()
                player_data["skill_upgrade_costs"][idx] = max(cost * 2, cost + 1)

                print(f"{skills[idx]} upgraded!")
                time.sleep(0.5)
            except:
                print("Upgrade failed or was exited.")
                time.sleep(1)
                continue

        elif choice == "5":
            if player_data["health"] >= player_data["max_health"]:
                print(Fore.YELLOW + "You're already at full health.")
                time.sleep(1)
                continue

            floor = persistent_stats.get("floor", 1)
            min_cost = (floor + 1) * 10
            xp_cost = max(min_cost, int(player_data["xp"] * 0.25))

            if player_data["xp"] < xp_cost:
                print(Fore.RED + f"Not enough XP. Heal costs {xp_cost} XP (minimum {min_cost}).")
                time.sleep(1)
                continue

            heal_amount = max(1, int(player_data["max_health"] * 0.1))
            player_data["xp"] -= xp_cost
            player_data["health"] = min(player_data["health"] + heal_amount, player_data["max_health"])
            print(Fore.CYAN + f"You spent {xp_cost} XP and healed {heal_amount} HP!")
            time.sleep(1)

        elif choice in ["6", "exit", "leave"]:
            return
        else:
            print("Invalid.")
            time.sleep(1)

def open_shop():
    persistent_stats["rooms_since_shop"] = 0
    owned_items = [i["name"] for i in player_data["inventory"]]
    owned_skills = player_data["skills"]

    all_items_owned = has_all_items()
    all_skills_owned = has_all_skills()

    shop_items = []
    if not all_items_owned:
        shop_items = get_unique_items(owned_items, 3)

    # Force a skill to show if any are left
    skill_offer = get_unique_skill(owned_skills) if not all_skills_owned else None

    # Abort shop if everything is already owned
    if all_items_owned and all_skills_owned:
        print(Fore.YELLOW + "The merchant has nothing new to offer you.")
        time.sleep(1.5)
        return

    floor_multiplier = 1 + (persistent_stats["floor"] - 1) * 0.1  # 10% more per floor

    while True:
        clear_screen()
        print(Fore.BLUE + "--- Merchant's Shop ---")
        print(Fore.MAGENTA + f"You can buy {Fore.RED}1{Fore.MAGENTA} item, choose wisely")
        print(f"You have {Fore.YELLOW}{player_data['coins']} coins{Style.RESET_ALL}\n")
        print(Fore.GREEN + "Items for sale:")
        for idx, item in enumerate(shop_items):
            price = int(item["value"] * floor_multiplier)
            affordable = player_data["coins"] >= price
            color = Fore.GREEN if affordable else Fore.RED
            bonus = item.get("bonus", {})
            bonus_parts = []
            if bonus.get("damage"):
                bonus_parts.append(f"+{bonus['damage']} dmg")
            if bonus.get("max_health"):
                bonus_parts.append(f"+{bonus['max_health']} HP")
            if bonus.get("max_mana"):
                bonus_parts.append(f"+{bonus['max_mana']} MP")
            if item.get("restore_full"):
                bonus_parts.append("Restores Full HP/MP")
            effect = ", ".join(bonus_parts) if bonus_parts else "No effect"

            print(f"{color}  [{idx + 1}] {item['name']} ({price} coins) - {effect}")

        if skill_offer:
            base_price = 20 + (10 - skill_offer["weight"]) * 3
            skill_price = int(base_price * floor_multiplier)
            skill_color = Fore.GREEN if player_data["coins"] >= skill_price else Fore.RED
            effect = skill_offer.get("effect",f"{skill_offer['damage']} dmg, {skill_offer['attacks']} hit(s), costs {skill_offer['mana_cost']} MP")
            print(f"{skill_color}  [S] {skill_offer['name']} ({skill_price} coins) (Skill) - {effect}")

        print(Fore.CYAN + "  [E] Exit shop")
        choice = input(Fore.GREEN + "> ").strip().lower()

        if choice in ["e", "exit", "leave"]:
            print(Fore.YELLOW + "You leave the shop.")
            return

        if choice in ["s"] and skill_offer:
            price = 20 + (10 - skill_offer["weight"]) * 3
            if player_data["coins"] >= price:
                if skill_offer["name"] in player_data["skills"]:
                    print(Fore.RED + "You already know that skill.")
                    time.sleep(1)
                else:
                    player_data["coins"] -= price
                    player_data["skills"].append(skill_offer["name"])
                    if "skill_upgrade_costs" not in player_data:
                        player_data["skill_upgrade_costs"] = []
                    player_data["skill_upgrade_costs"].append(1)
                    sd = player_data["skill_data"]
                    sd.setdefault("damage", []).append(skill_offer["damage"])
                    sd.setdefault("attacks", []).append(skill_offer["attacks"])
                    sd.setdefault("healing", []).append(skill_offer["healing"])
                    sd.setdefault("mana_costs", []).append(skill_offer["mana_cost"])
                    print(Fore.MAGENTA + f"You learned {skill_offer['name']}!")
                    save_to_file()
                    time.sleep(1)
                    return  # Exit after purchase
            else:
                print(Fore.RED + "Not enough coins.")
                time.sleep(1)
            continue

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(shop_items):
                raise ValueError
            item = shop_items[idx]
            if player_data["coins"] >= item["value"]:
                player_data["coins"] -= item["value"]
                player_data["inventory"].append(item)
                print(Fore.YELLOW + f"Purchased {item['name']}")
                save_to_file()
                time.sleep(1)
                return  # Exit after purchase
            else:
                print(Fore.RED + "Not enough coins.")
                time.sleep(1)
        except:
            print(Fore.RED + "Invalid choice.")
            time.sleep(1)

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

def heal_other_characters(overflow_heal, exclude_name):
    for name in characters:
        if name == exclude_name:
            continue
        path = os.path.join(save_directory, f"{name}.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r") as f:
                data = json.load(f)
            pdata = data.get("player", {})
            pstats = data.get("persistent_stats", {})
            if pstats.get("is_dead"):
                continue
            if pdata["health"] < pdata["max_health"]:
                needed = pdata["max_health"] - pdata["health"]
                healed = min(overflow_heal, needed)
                pdata["health"] += healed
                overflow_heal -= healed
                print(Fore.CYAN + f"{name} is healed for {healed} HP.")
                with open(path, "w") as f:
                    json.dump(data, f, indent=4)
                if overflow_heal <= 0:
                    break
        except Exception as e:
            print(Fore.RED + f"[ERROR] Healing {name}: {e}")

def apply_party_idle_effects(active_name, monsters):
    for name in characters:
        if name == active_name:
            continue  # skip current character
        path = os.path.join(save_directory, f"{name}.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r") as f:
                data = json.load(f)
            pdata = data.get("player", {})
            pstats = data.get("persistent_stats", {})
            if pstats.get("is_dead"):
                continue

            level = pdata.get("level", 1)
            if name == "George":
                dice_str = f"{level}d4"
                targetable = [m for m in monsters if m["health"] > 0]
                if targetable:
                    target = random.choice(targetable)
                    dmg = roll_dice(dice_str)
                    target["health"] -= dmg
                    print(Fore.YELLOW + f"George strikes {target['name']} for {dmg} damage.")
            elif name == "Lucian":
                dice_str = f"{level}d2"
                dmg = roll_dice(dice_str)
                for m in monsters:
                    if m["health"] > 0:
                        m["health"] -= dmg
                print(Fore.YELLOW + f"Lucian hits all enemies for {dmg} damage.")
            elif name == "Ilana":
                dice_str = f"{level}d2"
                heal = roll_dice(dice_str)
                for ally in characters:
                    apath = os.path.join(save_directory, f"{ally}.json")
                    if not os.path.exists(apath):
                        continue
                    with open(apath, "r") as af:
                        adata = json.load(af)
                    ap = adata["player"]
                    apstats = adata["persistent_stats"]
                    if apstats.get("is_dead"):
                        continue
                    old = ap["health"]
                    ap["health"] = min(ap["max_health"], ap["health"] + heal)
                    healed = ap["health"] - old
                    if healed > 0:
                        print(Fore.CYAN + f"Ilana heals {ally} for {healed} HP.")
                    with open(apath, "w") as af:
                        json.dump(adata, af, indent=4)
        except Exception as e:
            print(Fore.RED + f"[ERROR] Ally effect for {name}: {e}")

def combat(player_data, monsters):
    global current_monster_group
    while player_data["health"] > 0 and any(m["health"] > 0 for m in monsters):
        clear_screen()
        # UI Display
        xp_bar = f"{Fore.CYAN}{player_data['xp']}{Fore.GREEN}/{Fore.YELLOW}{player_data['xp_to_next']}{Fore.GREEN}"
        player_bar = render_health_bar(player_data["health"], player_data["max_health"], color=Fore.GREEN)
        mana_bar = render_health_bar(player_data["mana"], player_data["max_mana"], color=Fore.BLUE)

        print(Fore.GREEN + f"{player_data['character']} (Lv{player_data['level']} {xp_bar})")
        print(Fore.LIGHTBLACK_EX + f"Floor {persistent_stats['floor']} - Room {persistent_stats['room']}\n")

        # Show other characters' status
        print(Fore.LIGHTBLACK_EX + "--- Allies ---")
        for name in characters:
            if name == player_data["character"]:
                continue
            path = os.path.join(save_directory, f"{name}.json")
            if not os.path.exists(path):
                print(Fore.LIGHTBLACK_EX + f"{name}: (hasn't joined the battle)")
                continue
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                stats = data.get("player", {})
                dead = data.get("persistent_stats", {}).get("is_dead", False)
                if dead:
                    print(Fore.LIGHTBLACK_EX + f"{name}: (dead)")
                else:
                    hp = stats.get("health", 0)
                    max_hp = stats.get("max_health", 0)
                    print(Fore.LIGHTBLACK_EX + f"{name}: {hp} / {max_hp} HP")
            except:
                print(Fore.LIGHTBLACK_EX + f"{name}: (unreadable save)")
        print("\n")
        hp_text = f"{Fore.GREEN}HP: {player_data['health']} / {player_data['max_health']}"
        mp_text = f"{Fore.BLUE}MP: {player_data['mana']} / {player_data['max_mana']}"
        hp_bar = player_bar
        mp_bar = mana_bar

        # Align both bar labels
        print(hp_text)
        print(hp_bar)
        print(mp_text)
        print(mp_bar)

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

        print(Fore.GREEN + "\n[1] Attack  [2] Use Skill  [3] Retreat  [4] Upgrade Menu  [5] Equipment  [6] Character Selection")
        action = input(Fore.GREEN + "> ").strip().lower()

        if action in ["1", "atk", "attack"]:
            targets = [i for i, m in enumerate(monsters) if m["health"] > 0]

            if len(targets) == 1:
                choice = targets[0]
            else:
                print("Choose target:")
                for i in targets:
                    print(Fore.RED + f"  [{i + 1}] {monsters[i]['name']} ({monsters[i]['health']} HP)")
                try:
                    choice = int(input("> ")) - 1
                    if choice not in targets:
                        print(Fore.RED + "Invalid target.")
                        time.sleep(0.5)
                        continue
                except:
                    print(Fore.RED + "Invalid input.")
                    time.sleep(0.5)
                    continue

            dmg = sum(random.randint(1, 2) for _ in range(player_data.get("damage", 1)))  # Roll a bunch of d2's
            dmg = int(dmg * random.uniform(0.9, 1.2))  # then randomize it even more!
            monsters[choice]["health"] -= dmg
            print(Fore.GREEN + f"You dealt {dmg} damage to {monsters[choice]['name']}.")
            restore_amount = max(1, player_data["max_mana"] // 10)
            player_data["mana"] = min(player_data["mana"] + restore_amount, player_data["max_mana"])
            apply_party_idle_effects(player_data["character"], monsters)

        elif action in ["2", "skill", "useskill", "skl"]:
            skills = player_data.get("skills", [])
            if not skills:
                print(Fore.RED + "No skills available.")
                time.sleep(0.5)
                continue
            for i, skill in enumerate(skills):
                cost = player_data["skill_data"]["mana_costs"][i]
                color = Fore.GREEN if player_data["mana"] >= cost else Fore.RED
                print(f"{color}  [{i + 1}] {skill} - Mana Cost: {cost}")
            print(Fore.CYAN + "Type a number to use a skill or type 'cancel' to go back.")
            skill_choice = input(Fore.GREEN + "> ").strip().lower()

            if skill_choice in ["cancel", "exit", "back"]:
                continue

            try:
                idx = int(skill_choice) - 1
                if idx < 0 or idx >= len(skills):
                    raise ValueError
                skill_name = skills[idx]
                sd = player_data["skill_data"]
                cost = sd["mana_costs"][idx]

                if player_data["mana"] < cost:
                    print(Fore.RED + "Not enough mana.")
                    time.sleep(0.5)
                    continue

                # Now consume mana only after this point
                targets = [i for i, m in enumerate(monsters) if m["health"] > 0]
                if not targets:
                    print(Fore.YELLOW + "No valid targets.")
                    continue

                player_data["mana"] -= cost
                attacks = sd["attacks"][idx]
                dmg_str = sd["damage"][idx]

                if attacks == 1:
                    print("Choose target:")
                    for i in targets:
                        print(f"  [{i + 1}] {monsters[i]['name']} ({monsters[i]['health']} HP)")
                    try:
                        target_idx = int(input("> ")) - 1
                        if target_idx not in targets:
                            print(Fore.RED + "Invalid target.")
                            player_data["mana"] += cost  # Refund mana
                            continue
                        dmg = roll_dice(dmg_str)
                        monsters[target_idx]["health"] -= dmg
                        print(Fore.MAGENTA + f"{skill_name} hits {monsters[target_idx]['name']} for {dmg} damage.")
                    except:
                        print(Fore.RED + "Skill cancelled.")
                        player_data["mana"] += cost
                        continue
                else:
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
                    pre_heal = player_data["health"]
                    player_data["health"] = min(player_data["health"] + heal, player_data["max_health"])
                    used = player_data["health"] - pre_heal
                    overflow = heal - used
                    print(Fore.CYAN + f"You heal for {used} HP.")
                    if overflow > 0:
                        print(Fore.CYAN + f"{overflow} HP overflowed to allies.")
                        heal_other_characters(overflow, player_data["character"])
                        time.sleep(1)
            except:
                print(Fore.RED + "Skill failed or canceled.")
                time.sleep(0.5)
                continue

        elif action in ["3", "retreat", "ret", "esc", "escape"]:
            if random.random() < 0.75:
                print(Fore.YELLOW + "You successfully fled the battle!")
                current_monster_group = None
                persistent_stats["current_monsters"] = None
                save_to_file()
                time.sleep(0.5)
                clear_screen()
                return True  # Acts like a victory, but no rewards
            else:
                print(Fore.RED + "Retreat failed! The monsters attack!")
                for m in monsters:
                    if m["health"] > 0:
                        player_data["health"] -= m["damage"]
                        print(Fore.RED + f"{m['name']} hits you for {m['damage']}")
                save_to_file()
                time.sleep(1)
                continue

        elif action in ["4", "level", "upgrade", "xp"]:
            open_upgrade_menu()
            continue

        elif action in ["5", "inventory", "inv"]:
            open_inventory_menu()
            continue

        elif action in ["6", "exit", "leave"]:
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
        time.sleep(1)

    if player_data["health"] <= 0:
        print(Fore.RED + "You have died.")
        persistent_stats["is_dead"] = True
        save_to_file()
        time.sleep(0.5)
        clear_screen()
        return False
    else:
        current_monster_group = None
        persistent_stats["current_monsters"] = None
        save_to_file()
        # Calculate coin reward
        min_reward = 5 + persistent_stats["floor"]  # e.g. floor 3 = min 8 coins
        coin_total = sum((m["damage"] + m["health"] // 2) for m in monsters)
        coin_reward = max(min_reward, int(random.uniform(0.75, 1.25) * coin_total))
        player_data["coins"] += coin_reward
        print(Fore.YELLOW + f"You found {coin_reward} coins!")
        # Grant Xp
        xp_total = sum((m["damage"] * 2 + 2) for m in monsters)
        gain_xp(int(xp_total * 1.5))
        press_enter()
        return True

def explore_floor():
    global current_monster_group
    floor = persistent_stats["floor"]
    room = persistent_stats["room"]

    # === Forced boss fight if room exceeds 10 ===
    # === Boss chance after room 10 ===
    if room > 10 and random.random() < 0.40:
        print(Fore.RED + "A powerful enemy blocks your path!")
        boss = get_boss(floor).copy()
        boss["max_health"] = boss["health"]
        current_monster_group = [boss]
        clear_screen()
        print(Fore.RED + Style.BRIGHT + "\n" + "=" * 50)
        print(Fore.MAGENTA + Style.BRIGHT + "!!! RANDOM BOSS ENCOUNTER !!!".center(50))
        print("=" * 50)
        print("\n" + rainbow_text(boss["name"].center(50)))
        print("=" * 50 + "\n")
        time.sleep(3)
        result = combat(player_data, current_monster_group)

        if result == "exit":
            return "exit"
        elif result is False:
            print("You died to the boss...")
            return False

        print(Fore.GREEN + Style.BRIGHT + "\n=== BOSS DEFEATED! FLOOR ADVANCED! ===")
        time.sleep(1)
        persistent_stats["room"] = 1
        persistent_stats["floor"] += 1
        rotate_monsters()

        current_monster_group = None
        persistent_stats["current_monsters"] = None

        save_to_file()
        backup_path = global_save_path.replace(".json", f"_backup_floor{floor}.json")
        with open(backup_path, "w") as f:
            json.dump({"player": player_data, "persistent_stats": persistent_stats}, f, indent=4)

        return True

    # Handle active combat if it exists (from a saved battle)
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

    # Regular rooms (10 per floor)
    for _ in range(10):
        persistent_stats["room"] += 1

        # Guaranteed room logic
        guaranteed_shop = persistent_stats.get("rooms_since_shop", 0) >= 10
        guaranteed_treasure = persistent_stats.get("rooms_since_treasure", 0) >= 20

        rand = random.random()
        shop_trigger = rand < 0.10 or guaranteed_shop
        treasure_trigger = rand < 0.15 or guaranteed_treasure

        if shop_trigger and player_data.get("coins", 0) > 0:
            open_shop()
            persistent_stats["rooms_since_shop"] = 0
            save_to_file()
            continue
        elif treasure_trigger:
            open_treasure_room()
            persistent_stats["rooms_since_treasure"] = 0
            save_to_file()
            continue

        persistent_stats["rooms_since_shop"] += 1
        persistent_stats["rooms_since_treasure"] += 1

        # Generate new monster group and fight
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

        # Clear monster state after successful combat
        current_monster_group = None
        persistent_stats["current_monsters"] = None
        save_to_file()

    # Boss encounter
    boss = get_boss(floor).copy()
    boss["max_health"] = boss["health"]
    current_monster_group = [boss]
    clear_screen()
    print(Fore.RED + Style.BRIGHT + "\n" + "=" * 50)
    print(Fore.MAGENTA + Style.BRIGHT + "!!! BOSS ENCOUNTER !!!".center(50))
    print("=" * 50)
    print("\n" + rainbow_text(boss["name"].center(50)))
    print("=" * 50 + "\n")
    time.sleep(2)
    result = combat(player_data, current_monster_group)

    if result == "exit":
        return "exit"
    elif result is False:
        print("You died to the boss...")
        return False

    # Boss defeated — reset room, advance floor, rotate monsters
    print(Fore.GREEN + Style.BRIGHT + "\n=== BOSS DEFEATED! FLOOR COMPLETE! ===")
    time.sleep(1)
    persistent_stats["room"] = 1
    persistent_stats["floor"] += 1
    rotate_monsters()

    # Clear any remaining monster state
    current_monster_group = None
    persistent_stats["current_monsters"] = None

    # Save and backup
    save_to_file()
    backup_path = global_save_path.replace(".json", f"_backup_floor{floor}.json")
    with open(backup_path, "w") as f:
        json.dump({"player": player_data, "persistent_stats": persistent_stats}, f, indent=4)

    return True

def main():
    return explore_floor()

def startup():
    global current_save_name, global_save_path
    while True:
        clear_screen()
        print(Fore.YELLOW + f"Eyum Terminal Adventure v{current_version}")
        print(Fore.BLUE + "Choose your character or type 'exit' to quit:")
        print(Fore.CYAN + "\nYou will control one character, but the others will act with you in battle.")
        print(Fore.CYAN + "Lucian deals AoE damage, George hits a random enemy, Ilana heals everyone.\n")
        # Create missing saves on boot
        for name in characters:
            save_path = os.path.join(save_directory, f"{name}.json")
            if not os.path.exists(save_path):
                current_save_name = f"{name}.json"
                global_save_path = save_path
                base_stats = {
                    "max_health": 25,
                    "health": 25,
                    "mana": 7,
                    "max_mana": 7,
                    "damage": 1,
                }
                if name == "Lucian":
                    base_stats["mana"] += 3
                    base_stats["max_mana"] += 3
                elif name == "Ilana":
                    base_stats["health"] += 5
                    base_stats["max_health"] += 5
                elif name == "George":
                    base_stats["damage"] += 1

                base = character_skills[name]
                player_data.update({
                    "character": name,
                    "level": 1,
                    "xp": 0,
                    "xp_to_next": 10,
                    "skill_points": 0,
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
                player_data["base_stats"] = base_stats.copy()
                player_data.update(base_stats)
                persistent_stats.update({
                    "is_dead": False,
                    "floor": 1,
                    "room": 1,
                })
                apply_equipment_bonuses_for(player_data)
                save_to_file()
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
                reset_game_state()
                print(Fore.GREEN + "All save data deleted. Reinitializing...")
                time.sleep(1)
                return startup()
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
                base_stats = {
                    "max_health": 25,
                    "health": 25,
                    "mana": 7,
                    "max_mana": 7,
                    "damage": 1,
                }

                # Apply character-specific bonuses
                if choice == "Lucian":
                    base_stats["mana"] += 3
                    base_stats["max_mana"] += 3
                elif choice == "Ilana":
                    base_stats["health"] += 5
                    base_stats["max_health"] += 5
                elif choice == "George":
                    base_stats["damage"] += 1

                base = character_skills[choice]
                player_data.update({
                    "character": choice,
                    "level": 1,
                    "xp": 0,
                    "xp_to_next": 10,
                    "skill_points": 0,
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
                player_data["base_stats"] = base_stats.copy()
                player_data.update(base_stats)
                persistent_stats.update({
                    "is_dead": False,
                    "floor": 1,
                    "room": 1,
                })
                apply_equipment_bonuses_for(player_data)
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
        while True:
            alive = main()
            if alive == "exit":
                print(Fore.YELLOW + "Returning to character select...")
                time.sleep(1.5)
                break  # Break inner loop, go to character select
            elif not alive:
                print(Fore.YELLOW + "Returning to character select...")
                time.sleep(1.5)
                break  # Break inner loop, go to character select
            # Otherwise continue exploring with the same character
