# Eyum Terminal Adventure

Eyum Terminal Adventure is a turn-based roguelike RPG played entirely in the terminal.

---

## How to Run

### 1. Clone the Repository

```bash
git clone https://github.com/thoroftroy/Eyum-Terminal-Adventure.git
cd eyum-terminal-adventure
```

### 2. Install Python Requirements

Eyum uses Python 3+ and the `colorama` library.

```bash
pip install colorama
```

### 3. Run the Game

```bash
python main.py
```

---

## Platform Notes

- **Windows**: Run in Command Prompt or PowerShell.
- **macOS**: Use Terminal. Ensure Python 3 is installed (`brew install python`).
- **Linux**: Works in any terminal with Python 3+. Install Python and pip via:

```bash
sudo apt install python3 python3-pip
```

---

## Saves

- Saves are stored in `eyum/saves/` as `.json` files (one per character)
- On death, saves are flagged but not deleted
- Use `reset` on the title screen to delete all character saves and start fresh

---

## License

MIT — use, modify, and share freely.

---

## Known Issues/Planned Features
Currently the game is unbeatable, not only can you not scale fast enough but there is litteraly no ending. Also the begining is too easy, and the backups aren't great beacuse it only backs up the current character you have selected not everyone. I haven't play tested much beacuse I am still adding in basic functionality. 

Currently I plan to add the following

 -More room types to stumble on
 
 -Minigames
 
 -More allies (unlocked as you play)
 
 -A story line, each floor will reveal more
 
 -An actual freaking ending
 
