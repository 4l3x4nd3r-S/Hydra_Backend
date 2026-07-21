import os
import re

versions_dir = r"C:\Users\ALEXANDER_SUNI\Documents\ALEXANDERSUNI\PROYECTS\HYDRA\Hydra_Backend\alembic\versions"
files = [f for f in os.listdir(versions_dir) if f.endswith('.py')]

revisions = set()
down_revisions = set()

for f in files:
    with open(os.path.join(versions_dir, f), 'r', encoding='utf-8') as file:
        content = file.read()
        rev_match = re.search(r"revision:\s*str\s*=\s*['\"]([^'\"]+)['\"]", content)
        down_rev_match = re.search(r"down_revision:\s*(?:Union\[str,\s*None\]|str)\s*=\s*['\"]([^'\"]+)['\"]", content)
        if rev_match:
            revisions.add(rev_match.group(1))
        if down_rev_match:
            down_revisions.add(down_rev_match.group(1))

heads = revisions - down_revisions
print("Heads:", heads)
