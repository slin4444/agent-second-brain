import shutil, os
src = r'D:\Documents\Obsidian Vault\Second_Brain\03_Knowledge_Base\Sources\YouTube_1FiER-40zng.md'
dest = r'D:\Documents\Obsidian Vault\Second_Brain\01_Inbox\YouTube_1FiER-40zng.md'
if os.path.exists(src):
    shutil.move(src, dest)
    print(f"Moved: {dest}")
else:
    print(f"Not found: {src}")
