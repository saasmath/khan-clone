import sys
import unittest2 as unittest
import fnmatch
import os
import re
import simplejson
import subprocess
import tempfile
import urllib

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
    ret = function(params, helpers=handlebars_helpers, partials=handlebars_partials)
    return u"".join(ret)

# Unit test to ensure that Python & JS outputs match
class HandlebarsTest(unittest.TestCase):
    def test_handlebars_templates(self):
        matches = []
        for root, dirnames, filenames in os.walk('javascript'):
            for filename in fnmatch.filter(filenames, '*.handlebars.json'):
                package = re.match('javascript/([^-]+)-package', root).group(1);
                matches.append((package, root, filename))

        for match in matches:
            package = match[0]
            template_name = re.sub('\.handlebars\.json$', '', match[2])
            test_file = os.path.join(match[1], match[2])
            handlebars_file = re.sub('handlebars\.json$', 'handlebars', test_file)

            # Load test file data
            in_file = open(test_file, 'r')
            source = in_file.read()
            test_data = simplejson.loads(source)

            print "Testing %s..." % handlebars_file

            # Run Python template (append extra newline to make comparison with JS easier)
            python_output = str(handlebars_template(package, template_name, test_data)) + "\n"

            # Run JS template in node.js
            tmp = tempfile.TemporaryFile()
            subprocess.call(["node", "javascript/test/handlebars-test.js", handlebars_file, test_file], stdout=tmp)
            tmp.seek(0, 0)
            js_output = str(tmp.read())

            if js_output != python_output:
                open("python.txt", "w").write(python_output)
                #print "PYTHON:"
                #print python_output

                open("js.txt", "w").write(js_output)
                #print "JS:"
                #print js_output

            self.assertEqual(js_output, python_output)

from compiled_templates import handlebars_partials

