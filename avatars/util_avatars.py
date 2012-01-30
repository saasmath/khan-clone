import layer_cache
from avatars import AvatarPointsCategory, PointsAvatar

@layer_cache.cache()
def all_avatars():
    """ Authoritative list of all avatars available to users. """

    return [
        PointsAvatar("Green Leaf", "/images/avatars/leaf-green.png", 0),
        PointsAvatar("Blue Leaf", "/images/avatars/leaf-blue.png", 0),
        PointsAvatar("Grey Leaf", "/images/avatars/leaf-grey.png", 0),
        PointsAvatar("Red Leaf", "/images/avatars/leaf-red.png", 0),
        PointsAvatar("Orange Leaf", "/images/avatars/leaf-orange.png", 0),
        PointsAvatar("Yellow Leaf", "/images/avatars/leaf-yellow.png", 0),

        PointsAvatar("Spunky Sam", "/images/avatars/spunky-sam.png", 10000),
        PointsAvatar("Marcimus", "/images/avatars/marcimus.png", 10000),
        PointsAvatar("Mr. Pink", "/images/avatars/mr-pink.png", 10000),

        PointsAvatar("Orange Juice Squid", "/images/avatars/orange-juice-squid.png", 50000),
        PointsAvatar("Purple Pi", "/images/avatars/purple-pi.png", 50000),
        
        PointsAvatar("Mr. Pants", "/images/avatars/mr-pants.png", 100000),
        PointsAvatar("Old Spice Man", "/images/avatars/old-spice-man.png", 100000),
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
    
    return avatars["Green Leaf"]

@layer_cache.cache()
def avatars_by_category():
    """ Full list of all avatars available to users segmented by AvatarCategory
    """
    categories = [
        AvatarPointsCategory("Starter", 0, 10000),
        AvatarPointsCategory("Common", 10000, 50000),
        AvatarPointsCategory("Uncommon", 50000, 100000),
        AvatarPointsCategory("Rare", 100000, 250000)
    ]
    full_list = all_avatars()
    for i, category in enumerate(categories):
        categories[i] = {
            'title': category.title,
            'avatars': category.filter_avatars(full_list)
        }
    return categories
