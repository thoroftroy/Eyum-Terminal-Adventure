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
    "max_health": 15,
    "health": 15,
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
}

character_skills = {
    "Lucian": {
        "skills": ["Firebolt", "Fireblast"],
        "damage": ["1d4","2d8"],
        "attacks": [2, 1],
        "healing": [0, 0],
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
        "damage": ["1d6", "1d4"],
        "attacks": [1, 4],
        "healing": [0, 0],
        "mana_costs": [2, 7],
    },
}

characters = list(character_skills.keys())
current_save_name = ''
global_save_path = ''
current_monster_group = None  # global variable for active encounter

# === Utility Functions ===
def render_health_bar(current, max_val, length=40, color=Fore.GREEN):
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
def apply_equipment_bonuses():
    # Reset base stats (you can store true base values separately if needed)
    base_stats = {
        "damage": 1,
        "defense": 0,
        "max_health": 15,
        "max_mana": 7,
    }
    player_data.update(base_stats)

    for item in player_data.get("equipped", []):
        effect = item.get("effect", "").lower()
        if "+1 damage" in effect:
            player_data["damage"] += 1
        elif "+3 damage" in effect:
            player_data["damage"] += 3
        elif "+1 defense" in effect:
            player_data["defense"] += 1
        elif "+2 mana" in effect:
            player_data["max_mana"] += 2
        elif "restore" in effect:
            continue  # Potions, not equipment
        elif "+2 dodge" in effect:
            pass  # Not implemented yet
        elif "+5 all stats" in effect:
            player_data["damage"] += 5
            player_data["defense"] += 5
            player_data["max_health"] += 5
            player_data["max_mana"] += 5

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

def open_inventory_menu():
    clear_screen()
    print(Fore.BLUE + "--- Inventory ---")
    if not player_data["inventory"]:
        print("Inventory is empty.")
        press_enter()
        return

    types = ["weapon", "armor", "magic", "relic", "potion"]
    equipped = {item["type"]: item for item in player_data.get("equipped", [])}
    grouped = {t: [] for t in types}

    for item in player_data["inventory"]:
        grouped.setdefault(item["type"], []).append(item)

    for t in types:
        print(Fore.CYAN + f"\n{t.capitalize()}s:")
        if t in equipped:
            print(Fore.YELLOW + f"  Equipped: {equipped[t]['name']} ({equipped[t]['effect']})")
        for i, item in enumerate(grouped[t]):
            print(Fore.WHITE + f"  [{i+1}] {item['name']} - {item['effect']}")

    print(Fore.GREEN + "\nType the item number to equip it or 'exit' to return.")
    choice = input(Fore.GREEN + "> ").strip().lower()

    if choice == "exit":
        return

    try:
        num = int(choice)
        count = 0
        for t in types:
            for item in grouped[t]:
                count += 1
                if count == num:
                    # Equip item
                    old_equipped = [e for e in player_data["equipped"] if e["type"] == item["type"]]
                    for e in old_equipped:
                        player_data["equipped"].remove(e)
                    player_data["equipped"].append(item)
                    print(Fore.YELLOW + f"Equipped {item['name']}")
                    apply_equipment_bonuses()
                    save_to_file()
                    return
        print(Fore.RED + "Invalid number.")
    except:
        print(Fore.RED + "Invalid input.")
    press_enter()

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

def open_shop():
    clear_screen()
    print(Fore.BLUE + "--- Merchant's Shop ---")
    print(f"You have {Fore.YELLOW}{player_data['coins']} coins{Style.RESET_ALL}\n")

    # Pick 3 random items
    shop_items = random.choices(drop_table, weights=[i["weight"] for i in drop_table], k=3)

    # 25% chance to add a skill
    skill_offer = None
    if random.random() < 0.25:
        skill_offer = random.choice(skill_table)

    while True:
        print(Fore.GREEN + "Items for sale:")
        for idx, item in enumerate(shop_items):
            print(f"  [{idx+1}] {item['name']} - {item['effect']} - {item['value']} coins")

        if skill_offer:
            print(Fore.MAGENTA + f"  [S] {skill_offer['name']} (Skill) - {20 + (10 - skill_offer['weight']) * 3} coins")

        print(Fore.CYAN + "  [E] Exit shop")
        choice = input(Fore.GREEN + "> ").strip().lower()

        if choice == "e":
            print(Fore.YELLOW + "You leave the shop.")
            return

        if choice in ["s"] and skill_offer:
            price = 20 + (10 - skill_offer["weight"]) * 3
            if player_data["coins"] >= price:
                if skill_offer["name"] in player_data["skills"]:
                    print(Fore.RED + "You already know that skill.")
                else:
                    player_data["coins"] -= price
                    player_data["skills"].append(skill_offer["name"])
                    sd = player_data["skill_data"]
                    sd.setdefault("damage", []).append(skill_offer["damage"])
                    sd.setdefault("attacks", []).append(skill_offer["attacks"])
                    sd.setdefault("healing", []).append(skill_offer["healing"])
                    sd.setdefault("mana_costs", []).append(skill_offer["mana_cost"])
                    print(Fore.MAGENTA + f"You learned {skill_offer['name']}!")
            else:
                print(Fore.RED + "Not enough coins.")
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
            else:
                print(Fore.RED + "Not enough coins.")
        except:
            print(Fore.RED + "Invalid choice.")


def generate_monster_group():
    group = [random.choice(monster_list).copy()]

    if random.random() < 0.30:
        group.append(random.choice(monster_list).copy())
        if random.random() < 0.15:
            group.append(random.choice(monster_list).copy())
            if random.random() < 0.10:
                group.append(random.choice(monster_list).copy())
                if random.random() < 0.05:
                    group.append(random.choice(monster_list).copy())

    for m in group:
        m["max_health"] = m["health"]

    return group

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

        print(Fore.GREEN + "\n[1] Attack  [2] Use Skill  [3] Retreat  [4] Upgrade Menu  [5] Equipment  [6] Exit Game")
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
                    player_data["health"] = min(player_data["health"] + heal, player_data["max_health"])
                    print(Fore.CYAN + f"You heal for {heal} HP.")
            except:
                print(Fore.RED + "Skill failed or canceled.")
                time.sleep(0.5)
                continue

        elif action in ["3", "retreat", "ret", "esc", "escape"]:
            print(Fore.YELLOW + "You fled the battle.")
            return None

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
        global current_monster_group
        current_monster_group = None
        persistent_stats["current_monsters"] = None
        save_to_file()
        # Calculate coin reward
        coin_total = sum((m["damage"] + m["health"] // 2) for m in monsters)
        coin_reward = int(random.uniform(0.75, 1.25) * coin_total)
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

        # 10% chance of entering a shop instead of combat
        if random.random() < 0.10:
            open_shop()
            save_to_file()
            continue  # Do not increment combat or monster

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
    print(f"Boss Encounter! {boss['name']}")
    result = combat(player_data, current_monster_group)

    if result == "exit":
        return "exit"
    elif result is False:
        print("You died to the boss...")
        return False

    # Clean up after boss
    current_monster_group = None
    persistent_stats["current_monsters"] = None
    save_to_file()

    # Backup save
    backup_path = global_save_path.replace(".json", f"_backup_floor{floor}.json")
    with open(backup_path, "w") as f:
        json.dump({"player": player_data, "persistent_stats": persistent_stats}, f, indent=4)

    # Floor complete
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
                # Clear persistent monster group and stats
                global current_monster_group
                current_monster_group = None
                persistent_stats["current_monsters"] = None
                persistent_stats["floor"] = 1
                persistent_stats["room"] = 1
                persistent_stats["is_dead"] = False
                print(Fore.GREEN + "All save data deleted.")
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
                apply_equipment_bonuses()
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

