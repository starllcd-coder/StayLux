import re
from collections import Counter
p='c:/Users/LENOVO/Desktop/StayLux/web/locale/ar/LC_MESSAGES/django.po'
with open(p,encoding='utf-8') as f:
    s=f.read()
msgs=re.findall(r'^msgid "(.*)"$',s,flags=re.M)
ctr=Counter(msgs)
dups=[(m,c) for m,c in ctr.items() if c>1]
for m,c in dups:
    print(f"{c}x: {m}")
print('done')
