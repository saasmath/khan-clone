import sys
import subprocess
import os
import optparse
import datetime
import urllib2
import webbrowser
import getpass
import re

sys.path.append(os.path.abspath("."))
import compress
import npm

try:
    import secrets
    hipchat_deploy_token = secrets.hipchat_deploy_token
except Exception, e:
    print "Exception raised while trying to import secrets. Attempting to continue..."
    print repr(e)
    hipchat_deploy_token = None

try:
    import secrets_dev
    app_engine_username = getattr(secrets_dev, 'app_engine_username', None)
    app_engine_password = getattr(secrets_dev, 'app_engine_password', None)
except Exception, e:
    app_engine_username, app_engine_password = None, None

if hipchat_deploy_token:
    import hipchat.room
    import hipchat.config
    hipchat.config.manual_init(hipchat_deploy_token)

def popen_results(args):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    return proc.communicate()[0]

def popen_return_code(args, input=None):
    proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    proc.communicate(input)
    return proc.returncode

def get_app_engine_credentials():
    if app_engine_username and app_engine_password:
        print "Using password for %s from secrets.py" % app_engine_username
        return (app_engine_username, app_engine_password)
    else:
        email = app_engine_username or raw_input("App Engine Email: ")
        password = getpass.getpass("Password for %s: " % email)
        return (email, password)

def send_hipchat_deploy_message(version, includes_local_changes, email):
    if hipchat_deploy_token is None:
        return

    app_id = get_app_id()
    if app_id != "khan-academy":
        # Don't notify hipchat about deployments to test apps
        print 'Skipping hipchat notification as %s looks like a test app' % app_id
        return

    url = "http://%s.%s.appspot.com" % (version, app_id)

    hg_id = hg_version()
    hg_msg = hg_changeset_msg(hg_id)
    kiln_url = "https://khanacademy.kilnhg.com/Search?search=%s" % hg_id

    git_id = git_version()
    git_msg = git_revision_msg(git_id)
    github_url = "https://github.com/Khan/khan-exercises/commit/%s" % git_id

    local_changes_warning = " (including uncommitted local changes)" if includes_local_changes else ""
    message_tmpl = """
            %(hg_id)s%(local_changes_warning)s to <a href='%(url)s'>a non-default url</a>. Includes
            website changeset "<a href='%(kiln_url)s'>%(hg_msg)s</a>" and khan-exercises
            revision "<a href='%(github_url)s'>%(git_msg)s</a>."
            """ % {
                "url": url,
                "hg_id": hg_id,
                "kiln_url": kiln_url,
                "hg_msg": hg_msg,
                "github_url": github_url,
                "git_msg": git_msg,
                "local_changes_warning": local_changes_warning,
            }
    public_message = "Just deployed %s" % message_tmpl
    private_message = "%s just deployed %s" % (email, message_tmpl)

    hipchat_message(public_message, ["Exercises"])
    hipchat_message(private_message, ["1s and 0s"])

def hipchat_message(msg, rooms):
    if hipchat_deploy_token is None:
        return

    for room in hipchat.room.Room.list():

        if room.name in rooms:

            result = ""
            msg_dict = {"room_id": room.room_id, "from": "Mr Monkey", "message": msg, "color": "purple"}

            try:
                result = str(hipchat.room.Room.message(**msg_dict))
            except:
                pass

            if "sent" in result:
                print "Notified Hipchat room %s" % room.name
            else:
                print "Failed to send message to Hipchat: %s" % msg

def get_app_id():
    f = open("app.yaml", "r")
    contents = f.read()
    f.close()

    app_re = re.compile("^application:\s+(.+)$", re.MULTILINE)
    match = app_re.search(contents)

    return match.groups()[0]

def hg_st():
    output = popen_results(['hg', 'st', '-mard', '-S'])
    return len(output) > 0

def hg_pull_up():
    # Pull latest
    popen_results(['hg', 'pull'])

    # Hg up and make sure we didn't hit a merge
    output = popen_results(['hg', 'up'])
    lines = output.split("\n")
    if len(lines) != 2 or lines[0].find("files updated") < 0:
        # Ran into merge or other problem
        return -1

    return hg_version()

def hg_version():
    # grab the tip changeset hash
    current_version = popen_results(['hg', 'identify','-i']).strip()
    return current_version or -1

def hg_changeset_msg(changeset_id):
    # grab the summary and date
    output = popen_results(['hg', 'log', '--template','{desc}', '-r', changeset_id])
    return output

def git_version():
    # grab the tip changeset hash
    return popen_results(['git', '--work-tree=khan-exercises/', '--git-dir=khan-exercises/.git', 'rev-parse', 'HEAD']).strip()

def git_revision_msg(revision_id):
    return popen_results(['git', '--work-tree=khan-exercises/', '--git-dir=khan-exercises/.git', 'show', '-s', '--pretty=format:%s', revision_id]).strip()

def check_secrets():
    try:
        import secrets
    except ImportError, e:
        return False

    if not hasattr(secrets, 'verify_secrets_is_up_to_date'):
        print "Your secrets is too old; update it using the instructions in"
        print "password_for_secrets_py_cast5.txt at:"
        print "  https://www.dropbox.com/home/Khan%20Academy%20All%20Staff/Secrets"
        print
        return False

    fb_secret = getattr(secrets, 'facebook_app_secret', '')
    return fb_secret.startswith('050c')

def check_deps():
    """Check if npm and friends are installed"""
    return npm.check_dependencies()

def compile_handlebar_templates():
    print "Compiling handlebar templates"
    return 0 == popen_return_code([sys.executable,
                                   'deploy/compile_handlebar_templates.py'])

def compile_less_stylesheets():
    print "Compiling less stylesheets"
    return 0 == popen_return_code([sys.executable,
                                   'deploy/compile_less.py'])
def compress_js():
    print "Compressing javascript"
    compress.compress_all_javascript()

def compress_css():
    print "Compressing stylesheets"
    compress.compress_all_stylesheets()

def compress_exercises():
    print "Compressing exercises"
    subprocess.check_call(["ruby", "khan-exercises/build/pack.rb"])

def compile_templates():
    print "Compiling jinja templates"
    return 0 == popen_return_code([sys.executable, 'deploy/compile_templates.py'])

def prime_cache(version):
    try:
        resp = urllib2.urlopen("http://%s.%s.appspot.com/api/v1/autocomplete?q=calc" % (version, get_app_id()))
        resp.read()
        resp = urllib2.urlopen("http://%s.%s.appspot.com/api/v1/topics/library/compact" % (version, get_app_id()))
        resp.read()
        print "Primed cache"
    except:
        print "Error when priming cache"

def open_browser_to_ka_version(version):
    webbrowser.open("http://%s.%s.appspot.com" % (version, get_app_id()))

def deploy(version, email, password):
    print "Deploying version " + str(version)
    return 0 == popen_return_code(['appcfg.py', '-V', str(version), "-e", email, "--passin", "update", "."], "%s\n" % password)

def main():

    start = datetime.datetime.now()

    parser = optparse.OptionParser()

    parser.add_option('-f', '--force',
        action="store_true", dest="force",
        help="Force deploy even with local changes", default=False)

    parser.add_option('-v', '--version',
        action="store", dest="version",
        help="Override the deployed version identifier", default="")

    parser.add_option('-x', '--no-up',
        action="store_true", dest="noup",
        help="Don't hg pull/up before deploy", default="")

    parser.add_option('-s', '--no-secrets',
        action="store_true", dest="nosecrets",
        help="Don't check for production secrets.py file before deploying", default="")

    parser.add_option('-d', '--dryrun',
        action="store_true", dest="dryrun",
        help="Dry run without the final deploy-to-App-Engine step", default=False)

    parser.add_option('-r', '--report',
        action="store_true", dest="report",
        help="Generate a report that displays minified, gzipped file size for each package element",
            default=False)

    parser.add_option('-n', '--no-npm',
        action="store_false", dest="node",
        help="Don't check for local npm modules and don't install/update them",
        default=True)

    options, args = parser.parse_args()

    if options.node:
        print "Checking for node and dependencies"
        if not check_deps():
            return

    if options.report:
        print "Generating file size report"
        compile_handlebar_templates()
        compress.file_size_report()
        return

    includes_local_changes = hg_st()
    if not options.force and includes_local_changes:
        print "Local changes found in this directory, canceling deploy."
        return

    version = -1

    if not options.noup:
        version = hg_pull_up()
        if version <= 0:
            print "Could not find version after 'hg pull', 'hg up', 'hg tip'."
            return

    if not options.nosecrets:
        if not check_secrets():
            print "Stopping deploy. It doesn't look like you're deploying from a directory with"
            print "the appropriate secrets.py."
            return

    if not compile_templates():
        print "Failed to compile jinja templates, bailing."
        return

    if not compile_handlebar_templates():
        print "Failed to compile handlebars templates, bailing."
        return

    if not compile_less_stylesheets():
        print "Failed to compile less stylesheets, bailing."
        return

    compress_js()
    compress_css()
    compress_exercises()

    if not options.dryrun:
        if options.version:
            version = options.version
        elif options.noup:
            print 'You must supply a version when deploying with --no-up'
            return

        print "Deploying version " + str(version)

        (email, password) = get_app_engine_credentials()
        success = deploy(version, email, password)
        if success:
            send_hipchat_deploy_message(version, includes_local_changes, email)
            open_browser_to_ka_version(version)
            prime_cache(version)

    end = datetime.datetime.now()
    print "Done. Duration: %s" % (end - start)

if __name__ == "__main__":
    main()
