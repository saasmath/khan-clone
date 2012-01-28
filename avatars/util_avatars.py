import layer_cache
from avatars import AvatarPointsCategory, PointsAvatar

@layer_cache.cache()
def all_avatars():
    """ Authoritative list of all avatars available to users. """

    return [
        PointsAvatar("Spunky Sam", "/images/avatars/spunky-sam.png", 0),
        PointsAvatar("Marcimus", "/images/avatars/marcimus.png", 0),
        PointsAvatar("Mr. Pink", "/images/avatars/mr-pink.png", 0),
        PointsAvatar("Orange Juice Squid", "/images/avatars/orange-juice-squid.png", 5000),

        PointsAvatar("Purple Pi", "/images/avatars/purple-pi.png", 5000),
        PointsAvatar("Mr. Pants", "/images/avatars/mr-pants.png", 50000),

        PointsAvatar("Old Spice Man", "/images/avatars/old-spice-man.png", 50000),
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
    
    return avatars["Spunky Sam"]

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
