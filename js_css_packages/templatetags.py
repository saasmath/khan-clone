import os
import cgi

from app import App
from js_css_packages import packages
import request_cache
import util

# Attempt to load compressed packages (may not exist in dev mode)
try:
    from js_css_packages import packages_compressed
except Exception:
    pass

@request_cache.cache()
def use_compressed_packages():
    qs = os.environ.get("QUERY_STRING")
    dict_qs = cgi.parse_qs(qs)

    if App.is_dev_server and ["1"] != dict_qs.get("compressed_packages"):
        return False

    if ["1"] == dict_qs.get("uncompressed_packages"):
        return False

    return True

def js_package(package_name):

    if not use_compressed_packages():
        package = packages.javascript[package_name]
        base_url = package.get("base_url") or "/javascript/%s-package" % package_name
        list_js = []
        for filename in package["files"]:
            list_js.append("<script type='text/javascript' src='%s/%s'></script>" % (base_url, filename))
        return "".join(list_js)
    else:
        package = packages_compressed.compressed_javascript[package_name]
        base_url = package.get("base_url") or "/javascript/%s-package" % package_name
        return "<script type='text/javascript' src='%s/%s'></script>" % (util.static_url(base_url), package["hashed-filename"])

def css_package(package_name):

    if not use_compressed_packages():
        package = packages.stylesheets[package_name]
    else:
        package = packages_compressed.compressed_stylesheets[package_name]
    base_url = package.get("base_url") or "/stylesheets/%s-package" % package_name

    list_css = []
    if not use_compressed_packages():
        for filename in package["files"]:
            list_css.append("<link rel='stylesheet' type='text/css' href='%s/%s'/>" \
                % (base_url, filename))
    elif package_name+'-non-ie' not in packages.stylesheets:
        list_css.append("<link rel='stylesheet' type='text/css' href='%s/%s'/>" \
            % (util.static_url(base_url), package["hashed-filename"]))
    else:
        # Thank you Jammit (https://github.com/documentcloud/jammit) for the
        # conditional comments.
        non_ie_package = packages.stylesheets[package_name+'-non-ie']

        list_css.append("<!--[if (!IE)|(gte IE 8)]><!-->")

        # Stylesheets using data-uris
        list_css.append("<link rel='stylesheet' type='text/css' href='%s/%s'/>" \
            % (util.static_url(base_url), non_ie_package["hashed-filename"]))

        list_css.append("<!--<![endif]-->")
        list_css.append("<!--[if lte IE 7]>")

        # Without data-uris, for IE <= 7
        list_css.append("<link rel='stylesheet' type='text/css' href='%s/%s'/>" \
            % (util.static_url(base_url), package["hashed-filename"]))

        list_css.append("<![endif]-->")

    return "".join(list_css)
