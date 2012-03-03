import sys

def handlebars_template(package, name, params):
    package_name = package.replace("-", "_")
    function_name = name.replace("-", "_")

    module_name = "compiled_templates.%s_package.%s" % (package_name, function_name)

    if not module_name in sys.modules:
        # Dynamically load the module
        try:
            __import__(module_name)
        except ImportError:
            return u""

    function = getattr(sys.modules[module_name], function_name)
    ret = function(params)
    return u"".join(ret)

