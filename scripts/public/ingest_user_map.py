from ibl_pipeline import public, reference

users = []
for iuser, user in enumerate(reference.LabMember.fetch('KEY')):
    usermap = dict(**user,
                   pseudo_name='user%03d' % (iuser))

    users.append(usermap)

public.UserMap.insert(users)
