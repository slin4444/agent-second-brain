import os, shutil

# Rename the existing LightRAG video note to a cleaner name matching the real video title
src = r'D:\Documents\Obsidian Vault\Second_Brain\03_Knowledge_Base\Sources\Я_подключил_своим_агентам_МОЗГ._Вот_что_изменилось.md'
dest = r'D:\Documents\Obsidian Vault\Second_Brain\03_Knowledge_Base\Sources\Подключил_агентам_МОЗГ_LightRAG_Claude_Code_OpenClaw.md'

if os.path.exists(src):
    shutil.move(src, dest)
    print(f"OK: {os.path.basename(dest)}")
else:
    print(f"Not found: {src}")
    # List what's there
    folder = r'D:\Documents\Obsidian Vault\Second_Brain\03_Knowledge_Base\Sources'
    print("Files in Sources:", os.listdir(folder))
