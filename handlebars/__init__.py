import sys
import re
import urllib
import logging
from app import App

from pybars import Compiler

# Helpers (from javascript/shared-package/handlebars-extras.js)

def handlebars_repeat(context, options, count):
    fn = options["fn"]
    ret = ""

    for i in range(0, count):
        ret = ret + u''.join(fn(context))

    return ret

def handlebars_to_login_redirect_href(context, destination):
    redirectParam = "/postlogin?continue=" + destination
    return "/login?continue=" + urllib.quote(redirectParam, '')

def handlebars_commafy(context, number):
    return re.sub(r'(\d)(?=(\d{3})+$)', r'\1,', str(number))

def handlebars_arraylength(context, array):
    return len(array)

handlebars_helpers = {
    "repeat": handlebars_repeat,
    "toLoginRedirectHref": handlebars_to_login_redirect_href,
    "commafy": handlebars_commafy,
    "arrayLength": handlebars_arraylength
}

def handlebars_dynamic_load(package, name):
    """ Dynamically compile a Handlebars template.
        Do not do this in production mode! """

    if not App.is_dev_server:
        return None

    combined_name = "%s_%s" % (package, name)
    if combined_name in handlebars_partials:
        handlebars_partials[combined_name]

    logging.info("Dynamically loading %s-package/%s.handlebars." % (package, name))
    file_name = "clienttemplates/%s-package/%s.handlebars" % (package, name)

    in_file = open(file_name, 'r')
    source = unicode(in_file.read())
    source = source.replace("{{else}}", "{{^}}") # Pybars doesn't handle {{else}} for some reason

    matches = re.search('{{>[\s]*([\w\-_]+)[\s]*}}', source)
    if matches:
        for partial in matches.groups():
            (partial_package, partial_name) = partial.split("_")
            handlebars_dynamic_load(partial_package, partial_name)

    compiler = Compiler()
    function = compiler.compile(source)
    handlebars_partials[combined_name] = function

    return function

def handlebars_template(package, name, params):
    """ Invoke a template and return the output string """

    package_name = package.replace("-", "_")
    function_name = name.replace("-", "_")

    module_name = "compiled_templates.%s_package.%s" % (package_name, function_name)

    function = None

    if not module_name in sys.modules:
        # Dynamically load the module
        try:
            __import__(module_name)
        except ImportError:
            logging.info("Import error!")
            pass

    if module_name in sys.modules:
        function = getattr(sys.modules[module_name], function_name)

    # Fallback is to compile the template dynamically.
    # In production mode, this does nothing.
    if not function:
        function = handlebars_dynamic_load(package, name)

    ret = function(params, helpers=handlebars_helpers, partials=handlebars_partials)
    return u"".join(ret)

def render_from_jinja(package, name, params):
    ret = handlebars_template(package, name, params)
    return ret

try:
    from compiled_templates import handlebars_partials
except:
    handlebars_partials = {}
    pass
