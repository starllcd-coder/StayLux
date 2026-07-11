import gettext, os
locale_dir=r'c:/Users/LENOVO/Desktop/StayLux/web/locale'
try:
    t = gettext.translation('django', locale_dir, languages=['ar'])
    _ = t.gettext
    for s in ['Unit List','Units','Unit','Manage rooms and units, pricing, and amenities.']:
        print(s, '->', _(s))
except Exception as e:
    print('error',e)
