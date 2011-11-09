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
        
def collect_files(path, accept):
    """ Collect all files recursively within a specified dir that satisfies
    the given accept method.
    """
    results = []
    for name in [f for f in os.listdir(path) if not f in [".",".."]]:
        file_path = os.path.join(path, name)
        if os.path.isdir(file_path):
            results = results + collect_files(file_path, accept)
        elif accept(name):
            results.append(file_path)
    return results

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
    files = collect_files(root_path, lambda name: name.endswith(".handlebars"))
    for file_path in files:
        compile_template(file_path)

if __name__ == "__main__":
    validate_env()
    compile_templates()
