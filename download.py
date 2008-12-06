#! /usr/bin/env python
import subprocess
import sys
from optparse import OptionParser
import os
import shutil
import urllib
from util import run_command, fatal, CommandError

import constants
    

def main(argv):
    parser = OptionParser()
    parser.add_option("-n", "--ns3-branch", dest="ns3_branch", default="ns-3-dev",
                      help="Name of the NS-3 version", metavar="BRANCH_NAME")
    (options, args) = parser.parse_args()

    # first of all, change to the directory of the script
    os.chdir(os.path.dirname(__file__))




    #
    # Get NS-3
    #
    ns3_dir = options.ns3_branch
    ns3_branch_url = constants.NSNAM_CODE_BASE_URL + options.ns3_branch

    if not os.path.exists(ns3_dir):
        print "Cloning ns-3 branch"
        run_command(['hg', 'clone', ns3_branch_url, ns3_dir])
    else:
        print "Updating ns-3 branch"
        run_command(['hg', '--cwd', ns3_dir, 'pull', '-u'])

    # For future reference (e.g. build.py script), the downloaded ns3 version becomes our version
    f = file("BRANCH", "wt")
    f.write("%s\n" % options.ns3_branch)
    f.close()

    #
    # Get the regression traces
    # 
    regression_traces_dir_name = ns3_dir + constants.REGRESSION_SUFFIX
    print "Synchronizing reference traces using Mercurial."
    try:
        if not os.path.exists(regression_traces_dir_name):
            run_command(["hg", "clone", constants.REGRESSION_TRACES_REPO + regression_traces_dir_name, regression_traces_dir_name])
        else:
            run_command(["hg", "-q", "pull", "--cwd", regression_traces_dir_name,
                         constants.REGRESSION_TRACES_REPO + regression_traces_dir_name])
            run_command(["hg", "-q", "update", "--cwd", regression_traces_dir_name])
    except OSError: # this exception normally means mercurial is not found
        if not os.path.exists(regression_traces_dir_name):
            traceball = regression_traces_dir_name + constants.TRACEBALL_SUFFIX
            print "Retrieving " + traceball + " from web."
            urllib.urlretrieve(constants.REGRESSION_TRACES_URL + traceball, traceball)
            run_command(["tar", "-xjf", traceball])
            print "Done."



    #
    # Get PyBindGen
    #
    # (peek into the ns-3 wscript and extract the required pybindgen version)
    ns3_python_wscript = open(os.path.join(ns3_dir, "bindings", "python", "wscript"), "rt")
    required_pybindgen_version = None
    for line in ns3_python_wscript:
        if 'REQUIRED_PYBINDGEN_VERSION' in line:
            required_pybindgen_version = eval(line.split('=')[1].strip())
            ns3_python_wscript.close()
            break
    if required_pybindgen_version is None:
        fatal("Unable to detect pybindgen required version")
    print "Required pybindgen version: ", '.'.join([str(x) for x in required_pybindgen_version])

    # work around http_proxy handling bug in bzr
    if 'http_proxy' in os.environ and 'https_proxy' not in os.environ:
        os.environ['https_proxy'] = os.environ['http_proxy']
 
    if len(required_pybindgen_version) == 4:
        rev = "-rrevno:%i" % required_pybindgen_version[3]
    else:
        rev = "-rtag:%s" % '.'.join([str(x) for x in required_pybindgen_version])
        
    if os.path.exists(constants.LOCAL_PYBINDGEN_PATH):
        print "Trying to update pybindgen; this will fail if no network connection is available.  Hit Ctrl-C to skip."

        try:
            run_command(["bzr", "pull", rev, "-d", constants.LOCAL_PYBINDGEN_PATH, constants.PYBINDGEN_BRANCH])
        except KeyboardInterrupt:
            print "Interrupted; Python bindings will be disabled."
        else:
            print "Update was successful."
    else:
        print "Trying to fetch pybindgen; this will fail if no network connection is available.  Hit Ctrl-C to skip."
        try:
            run_command(["bzr", "checkout", rev, constants.PYBINDGEN_BRANCH, constants.LOCAL_PYBINDGEN_PATH])
        except KeyboardInterrupt:
            print "Interrupted; Python bindings will be disabled."
            shutil.rmtree(constants.LOCAL_PYBINDGEN_PATH, True)
            return False
        print "Fetch was successful."

    ## generate a fake version.py file in pybindgen it's safer this
    ## way, since the normal version generation process requires
    ## bazaar python bindings, which may not be available.
    vfile = open(os.path.join(constants.LOCAL_PYBINDGEN_PATH, "pybindgen", "version.py"), "wt")
    vfile.write("""
# (fake version generated by ns-3)
__version__ = %r
""" % list(required_pybindgen_version))
    vfile.close()





    

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))