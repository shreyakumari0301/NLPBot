# Fix: Make NLPBot the only folder on GitHub

Your Git repo root is currently **C:\Users\shrey**, so GitHub sees everything under that folder (NLPBot, nppe2, etc.). Do this so **only** the NLPBot project is in the repo.

## Steps (run from WSL or Git Bash)

1. **Go into NLPBot**
   ```bash
   cd /mnt/c/Users/shrey/NLPBot
   ```

2. **Create a new repo here (NLPBot becomes the root)**
   ```bash
   git init
   git add .
   git commit -m "NLPBot: voice bot, LangChain, admin, quotations"
   git branch -M main
   git remote add origin https://github.com/shreyakumari0301/NLPBot.git
   ```

3. **Push and overwrite GitHub with only NLPBot**
   ```bash
   git push -u origin main --force
   ```
   (Use your GitHub username and **Personal Access Token** as password when prompted.)

4. **Optional:** Remove the old repo from your home folder so you don’t use it by mistake:
   ```bash
   rm -rf /mnt/c/Users/shrey/.git
   ```
   Only do this if you don’t need that big repo anymore.

After this, `git rev-parse --show-toplevel` run from inside NLPBot should print `/mnt/c/Users/shrey/NLPBot`, and only NLPBot files will be on GitHub (no nppe2, no extra folders).
