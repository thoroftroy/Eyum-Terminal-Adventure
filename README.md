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

Eyum uses Python 3.12+ and the `colorama` library.

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
- **Linux**: Works in any terminal with Python 3.9+. Install Python and pip via:

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
