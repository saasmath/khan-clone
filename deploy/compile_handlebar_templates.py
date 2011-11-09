# -*- coding: utf-8 -*-
import os
import subprocess
import sys

def validate_env():
    """ Ensures that pre-requisites are met for compiling handlebar templates.
    
    TODO: point to documents when they're made.
    Handlebars doc: https://github.com/wycats/handlebars.js/
    """
    try:
        subprocess.call(["handlebars"],
                        stderr=subprocess.STDOUT,
                        stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        sys.exit("Can't find handlebars. Did you install it?")
        
def compile_template(file_path):
    """ Compiles a single template. """
    try:
        # Append ".js" to the template name.
        output_path = "%s/%s.js" % (os.path.dirname(file_path),
                                    os.path.basename(file_path))
        subprocess.call(["handlebars", "-m", "-f", output_path, file_path],
                        stderr=subprocess.STDOUT,
                        stdout=subprocess.PIPE)
        print "Compiled to %s" % output_path
    except subprocess.CalledProcessError:
        sys.exit("Error compiling %s" % file_path)

def compile_templates():
    root_path = os.path.join("..", "javascript")
    for dir_path, dir_names, file_names in os.walk(root_path):
        for file_name in file_names:
            print file_name
            if file_name.endswith(".handlebars"):
                compile_template(os.path.join(dir_path, file_name))

if __name__ == "__main__":
    validate_env()
    compile_templates()
