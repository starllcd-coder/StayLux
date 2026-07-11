from pathlib import Path
p=Path('c:/Users/LENOVO/Desktop/StayLux/web/locale/ar/LC_MESSAGES/django.po')
text=p.read_text(encoding='utf-8')
# split blocks by blank line
blocks=[]
cur=[]
for line in text.splitlines():
    if line.strip()=='' and cur:
        blocks.append('\n'.join(cur))
        cur=[]
    else:
        cur.append(line)
if cur:
    blocks.append('\n'.join(cur))
seen=set()
out=[]
for b in blocks:
    # find first msgid in block
    import re
    m=re.search(r'^msgid\s+"(.*)"', b, flags=re.M)
    if not m:
        out.append(b)
    else:
        key=m.group(1)
        if key in seen:
            # skip duplicate block
            continue
        seen.add(key)
        out.append(b)
# write backup
bak=p.with_suffix('.po.bak')
if not bak.exists():
    p.replace(bak)
# write cleaned
p.write_text('\n\n'.join(out)+"\n", encoding='utf-8')
print('cleaned')
