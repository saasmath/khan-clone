import layer_cache
from avatars import AvatarPointsCategory, PointsAvatar

@layer_cache.cache()
def all_avatars():
    """ Authoritative list of all avatars available to users. """

    return [
        PointsAvatar("darth", "/images/darth.png", 0),
        PointsAvatar("warp_ray", "http://www.trinigamers.com/forums/images/avatars/warp_ray_128.gif", 0),
        PointsAvatar("raynor", "http://www.trinigamers.com/forums/images/avatars/raynor1_128.gif", 0),

        PointsAvatar("marine", "http://www.trinigamers.com/forums/images/avatars/findlay1_128.gif", 5000),
        PointsAvatar("protoss", "http://www.trinigamers.com/forums/images/avatars/selendis_128.gif", 5000),

        PointsAvatar("zergling", "http://www.trinigamers.com/forums/images/avatars/zergling_128.gif", 50000),
    ]

@layer_cache.cache()
def avatars_by_name():
    """ Full list of avatars in a dict, keyed by their unique names """
    return dict([(avatar.name, avatar) for avatar in all_avatars()])

def avatar_for_name(name):
    """ Returns the avatar for the specified name.

    If name is None or an invalid avatar, defaults to the "default" avatar.
    """
    avatars = avatars_by_name()
    if name in avatars:
        return avatars[name]
    
    return avatars["darth"]

@layer_cache.cache()
def avatars_by_category():
    """ Full list of all avatars available to users segmented by AvatarCategory
    """
    categories = [
        AvatarPointsCategory("Easy", 0, 5000),
        AvatarPointsCategory("Coolsville", 5000, 50000),
        AvatarPointsCategory("Epic", 50000)
    ]
    full_list = all_avatars()
    for i, category in enumerate(categories):
        categories[i] = {
            'title': category.title,
            'avatars': category.filter_avatars(full_list)
        }
    return categories
