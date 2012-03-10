import sys
import re
import urllib
import logging

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

handlebars_helpers = {
    "repeat": handlebars_repeat,
    "toLoginRedirectHref": handlebars_to_login_redirect_href,
    "commafy": handlebars_commafy
}

# Invoke a template and return the output string
def handlebars_template(package, name, params):
    partials = dict()

    original_file_name = "javascript/%s-package/%s.handlebars" % (package, name)

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

    if not function:
        try:
            in_file = open(original_file_name, 'r')
            source = unicode(in_file.read())
            source = source.replace("{{else}}", "{{^}}") # Pybars doesn't handle {{else}} for some reason

            compiler = Compiler()
            function = compiler.compile(source)
        except:
            logging.info("Compile error!")
            return u""

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
