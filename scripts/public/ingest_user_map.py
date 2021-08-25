from ibl_pipeline import public
from ibl_pipeline.ingest import alyxraw

users = alyxraw.AlyxRaw.Field & \
        (alyxraw.AlyxRaw & 'model="misc.labmember"') & \
        'fname="username"'
original_users = public.UserMap.proj(fvalue='user_name')

new_users = []
for iuser, user in enumerate(
        (users - original_users).fetch()):
    usermap = dict(
        user_name=user['fvalue'],
        pseudo_name='user%03d' % (iuser + len(original_users)))

    new_users.append(usermap)

public.UserMap.insert(new_users)
