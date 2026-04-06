import os

files = [
    r'D:\Documents\Obsidian Vault\Second_Brain\02_AI_Review\Claude_Context_Management.md',
    r'D:\Documents\Obsidian Vault\Second_Brain\02_AI_Review\Daily\Claude_Bonus_Credits_2026-04-05.md',
]

for f in files:
    if os.path.exists(f):
        os.remove(f)
        print(f"Deleted: {f}")
    else:
        print(f"Not found: {f}")

print("Done.")
