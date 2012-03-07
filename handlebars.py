import sys
import unittest2 as unittest
import fnmatch
import os
import re
import simplejson
import subprocess
import tempfile

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

            # Run Python template (append extra newline to make comparison with JS easier)
            python_output = str(handlebars_template(package, template_name, test_data)) + "\n"

            # Run JS template in node.js
            tmp = tempfile.TemporaryFile()
            subprocess.call(["node", "javascript/test/handlebars-test.js", handlebars_file, test_file], stdout=tmp)
            tmp.seek(0, 0)
            js_output = str(tmp.read())

            if js_output != python_output:
                open("python.txt", "w").write(python_output)
                print "PYTHON:"
                print python_output

                open("js.txt", "w").write(js_output)
                print "JS:"
                print js_output

            self.assertEqual(js_output, python_output)
