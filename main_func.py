#!/usr/bin/env python3
# PYTHON_PREAMBLE_START_STANDARD:{{{

# Christopher David Cotton (c)
# http://www.cdcotton.com

# modules needed for preamble
import importlib
import os
from pathlib import Path
import sys

# Get full real filename
__fullrealfile__ = os.path.abspath(__file__)

# Function to get git directory containing this file
def getprojectdir(filename):
    curlevel = filename
    while curlevel is not '/':
        curlevel = os.path.dirname(curlevel)
        if os.path.exists(curlevel + '/.git/'):
            return(curlevel + '/')
    return(None)

# Directory of project
__projectdir__ = Path(getprojectdir(__fullrealfile__))

# Function to call functions from files by their absolute path.
# Imports modules if they've not already been imported
# First argument is filename, second is function name, third is dictionary containing loaded modules.
modulesdict = {}
def importattr(modulefilename, func, modulesdict = modulesdict):
    # get modulefilename as string to prevent problems in <= python3.5 with pathlib -> os
    modulefilename = str(modulefilename)
    # if function in this file
    if modulefilename == __fullrealfile__:
        return(eval(func))
    else:
        # add file to moduledict if not there already
        if modulefilename not in modulesdict:
            # check filename exists
            if not os.path.isfile(modulefilename):
                raise Exception('Module not exists: ' + modulefilename + '. Function: ' + func + '. Filename called from: ' + __fullrealfile__ + '.')
            # add directory to path
            sys.path.append(os.path.dirname(modulefilename))
            # actually add module to moduledict
            modulesdict[modulefilename] = importlib.import_module(''.join(os.path.basename(modulefilename).split('.')[: -1]))

        # get the actual function from the file and return it
        return(getattr(modulesdict[modulefilename], func))

# PYTHON_PREAMBLE_END:}}}

import os
import pexpect
import shutil
import subprocess

# Git Details:{{{1
def getgitdetails(gitlist, addremotelocation = False, addcheckorigin = False, addcheckuncommittedfiles = False):
    import re
    import subprocess

    aheadre = re.compile(r"Your branch is ahead of 'origin/master' by .* commit.?\.")

    gitdetailsdict = {}
    for gitdir in sorted(gitlist):
        gitdetailsdict[gitdir] = {}

        gitdetailsdict[gitdir]['location'] = gitdir

        output = subprocess.check_output(['git', 'status'], cwd = gitdir)
        output = output.decode('latin-1')
        outputlist = output.split('\n')

        # add branch
        # Parsing line 'On branch BRANCH'
        branch = outputlist[0][10:]
        if branch == outputlist[0]:
            print(branch +' not determined correctly')
            sys.exit(1)
        gitdetailsdict[gitdir]['branch'] = branch

        # add whether committed
        # git status used to say working directory clean, now says working tree clean
        if outputlist[-2] == 'nothing to commit, working directory clean' or outputlist[-2] == 'nothing to commit, working tree clean':
            allcommitted = True
        else:
            allcommitted = False
        gitdetailsdict[gitdir]['allcommitted'] = allcommitted
        
        # add details on origin from status
        localvorigin = None
        hasorigin = False
        if outputlist[1] == "Your branch is up-to-date with 'origin/master'.":
            hasorigin = True
            localvorigin = 'uptodate'
        aheadmatch = aheadre.match(outputlist[1])
        if aheadmatch:
            localvorigin = 'ahead'
            hasorigin = True
        gitdetailsdict[gitdir]['localvorigin'] = localvorigin
        gitdetailsdict[gitdir]['hasorigin'] = hasorigin

        # list of uncommitted files:
        if addcheckuncommittedfiles is True:
            gitdetailsdict[gitdir]['uncommittedfiles'] = subprocess.check_output(['git', 'ls-files', '--other', '--exclude-standard'], cwd = gitdir).decode('latin-1').splitlines()
            # gitdetailsdict[gitdir]['uncommittedfiles'] = subprocess.check_output(['git', 'ls-files', '--other', '--directory', '--exclude-standard'], cwd = gitdir).decode('latin-1').splitlines()
            # gitdetailsdict[gitdir]['uncommittedfiles'] = subprocess.check_output(['git', 'diff', '--name-only', '--diff-filter=A', 'HEAD'], cwd = gitdir).decode('latin-1').splitlines()
            # gitdetailsdict[gitdir]['uncommittedfiles'] = subprocess.check_output(['git', 'diff', '--name-only', '--diff-filter=A', 'HEAD'], cwd = gitdir).decode('latin-1').splitlines()

        # check if behind origin (not available on status)
        if addcheckorigin:
            originvlocal = None
            if hasorigin is True:
                gitfetch = subprocess.check_output(['git', 'fetch', '--dry-run'], cwd = gitdir, stderr = subprocess.STDOUT)

                if gitfetch != b'':
                    originvlocal = 'ahead'
                else:
                    originvlocal = 'uptodate'
                
            gitdetailsdict[gitdir]['originvlocal'] = originvlocal
        
        # add origin location
        if addremotelocation:
            try:
                url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url'], cwd = gitdir)
                url = url.decode('latin-1')[:-1]
                gitdetailsdict[gitdir]['remotelocation'] = url
            except Exception:
                gitdetailsdict[gitdir]['remotelocation'] = None
                

    return(gitdetailsdict)
            
def printgitdetails(gitlist):
    gitdirsdict = importattr(__projectdir__ / Path('main_func.py'), 'getgitdetails')(gitlist)

    notallcommitted = []
    notonmaster = []
    for gitdir in sorted(gitdirsdict):
        if gitdirsdict[gitdir]['allcommitted'] == False and gitdirsdict[gitdir]['branch'] == 'master':
            notallcommitted.append(gitdir)
        if gitdirsdict[gitdir]['branch'] != 'master':
            notonmaster.append(gitdir)

    if len(notonmaster) > 0:
        print('\nProjects not on the master branch:\n' + '\n'.join(notonmaster))

    if len(notallcommitted) > 0:
        print('\nProjects with uncommitted files on the master branch:\n' + '\n'.join(notallcommitted))

def printgitremote(gitlist):
    gitdirsdict = importattr(__projectdir__ / Path('main_func.py'), 'getgitdetails')(gitlist, addremotelocation = True)

    noremote = []
    github = []
    other = []
    for gitdir in sorted(gitdirsdict):
        if gitdirsdict[gitdir]['remotelocation'] == None:
            noremote.append(gitdir)
        elif gitdirsdict[gitdir]['remotelocation'].startswith('https://github.com/c-d-cotton/'):
            github.append(gitdir)
        else:
            other.append(gitdir)

    if len(github) > 0:
        print('\nGITHUB:\n' + '\n'.join(github))

    if len(other) > 0:
        print('\nOTHER:\n' + '\n'.join(other))

    if len(noremote) > 0:
        print('\nNONE:\n' + '\n'.join(noremote))

# Commit Functions:{{{1
def commitallgit(gitlist, commitmessage, gitdetailsdict = None, addfiles = False, addotherbranches = False, commitnewfiles = False, checkcommitnewfiles = False):
    import subprocess
    import sys

    if commitnewfiles is True:
        addcheckuncommittedfiles = False
    else:
        addcheckuncommittedfiles = True

    if gitdetailsdict is not None:
        gitdetailsdict = importattr(__projectdir__ / Path('main_func.py'), 'getgitdetails')(gitlist, addcheckuncommittedfiles = addcheckuncommittedfiles)    


    notcommitted = [gitdir for gitdir in gitdetailsdict if gitdetailsdict[gitdir]['allcommitted'] == False]

    gitdirsmaster = sorted([gitdir for gitdir in notcommitted if gitdetailsdict[gitdir]['branch'] == 'master'])
    gitdirstest = sorted([gitdir for gitdir in notcommitted if gitdetailsdict[gitdir]['branch'] != 'master'])

    if addotherbranches is True:
        includedbranch = 'ALL BRANCHES'
        tocommit = gitdirsmaster + gitdirstest
    else:
        includedbranch = 'MASTER BRANCH'
        tocommit = gitdirsmaster

    if commitnewfiles is False:
        folderswithnewfiles = sorted([gitdir for gitdir in gitdetailsdict if len(gitdetailsdict[gitdir]['uncommittedfiles']) > 0])
        if checkcommitnewfiles is True:
            removefolders = []
            for gitdir in folderswithnewfiles:
                print(gitdir + ' contains the following new files:')
                print(gitdetailsdict[gitdir]['uncommittedfiles'])
                print('Commit this folder (y/n/q)?')
                inputted = importattr(__projectdir__ / Path('submodules/py-getch/getch/getch.py'), 'getch')()
                if inputted == 'y':
                    removefolders.append(gitdir)
                if inputted == 'q':
                    sys.exit(1)

            folderswithnewfiles = [gitdir for gitdir in folderswithnewfiles if gitdir not in removefolders]
            
        tocommit = [gitdir for gitdir in tocommit if gitdir not in folderswithnewfiles]


    nocommittedlist = []

    print('\nINCLUDED folders to commit on ' + includedbranch + ':')
    print('\n'.join(tocommit))

    if addotherbranches is False:
        print('\nEXCLUDED folders: excluded because on OTHER branches:')
        print('\n'.join(gitdirstest))

    if commitnewfiles is False:
        print('\nEXCLUDED folders: excluded because has new files')
        print('\n'.join(folderswithnewfiles))

    if len(tocommit) > 0:
        importattr(__projectdir__ / Path('submodules/python-pause/pausecall.py'), 'confirm')()


        for gitdir in tocommit:
            subprocess.call(['git', 'add', '.'], cwd = gitdetailsdict[gitdir]['location'])
            subprocess.call(['git', 'commit', '-m', "'" + commitmessage + "'"], cwd = gitdetailsdict[gitdir]['location'])
    else:
        print('all projects fully committed')


def commitallgit_ap(gitlist, checkcommitnewfiles = False):
    import argparse

    # Argparse:{{{
    parser=argparse.ArgumentParser()
    parser.add_argument("commitmessage")
    parser.add_argument("--addfiles", action='store_true')
    parser.add_argument("--noaddfiles", action='store_true')
    parser.add_argument("-a", "--addotherbranches", action='store_true')
    
    
    args=parser.parse_args()
    # End argparse:}}}

    addfiles = False
    if args.addfiles == True:
        addfiles = True
    if args.noaddfiles == False:
        addfiles = False

    importattr(__projectdir__ / Path('main_func.py'), 'commitallgit')(gitlist, args.commitmessage, addfiles, addotherbranches = args.addotherbranches, checkcommitnewfiles = checkcommitnewfiles)

# Git Push/Pull:{{{1
def pushorigingit(gitlist, gitdetailsdict = None):
    import subprocess

    if gitdetailsdict is None:
        gitdetailsdict = importattr(__projectdir__ / Path('main_func.py'), 'getgitdetails')(gitlist)    
        

    pushlist = sorted([gitdir for gitdir in gitdetailsdict if gitdetailsdict[gitdir]['allcommitted'] is True and gitdetailsdict[gitdir]['localvorigin'] == 'ahead'])

    if len(pushlist) > 0:
        print('\nFOLDERS TO PUSH:')
        print('\n'.join(pushlist))

        importattr(__projectdir__ / Path('submodules/python-pause/pausecall.py'), 'confirm')()

        for gitdir in pushlist:
            subprocess.call(['git', 'push', 'origin', 'master'], cwd = gitdetailsdict[gitdir]['location'])
    else:
        print('all masters up-to-date with origin')


def pushorigingit_github(githubuserhome, username, gitlist, gitdetailsdict = None, githubpwd = None, skipnonme = False, force = False):
    """
    Calls pushorigingit but for github
    """

    if gitdetailsdict is None:
        gitdetailsdict = importattr(__projectdir__ / Path('main_func.py'), 'getgitdetails')(gitlist, addremotelocation = True)    

    pushlist_all = sorted([gitdir for gitdir in gitdetailsdict if gitdetailsdict[gitdir]['allcommitted'] is True and gitdetailsdict[gitdir]['remotelocation'] is not None and (force is True or gitdetailsdict[gitdir]['localvorigin'] == 'ahead')])
    pushlist_committed = [gitdir for gitdir in pushlist_all if gitdetailsdict[gitdir]['allcommitted'] is True]
    pushlist_notcommitted = [gitdir for gitdir in pushlist_all if gitdetailsdict[gitdir]['allcommitted'] is False]

    if len(pushlist_notcommitted) > 0:
        print('\nFOLDERS NOT COMMITTED:')
        print('\n'.join(pushlist_notcommitted))
        print('\nWAIT!!! FOLDERS NOT COMMITTED!:')
        importattr(__projectdir__ / Path('submodules/python-pause/pausecall.py'), 'confirm')()


    if len(pushlist_committed) > 0:
        print('\nFOLDERS TO PUSH:')
        print('\n'.join(pushlist_committed))

        importattr(__projectdir__ / Path('submodules/python-pause/pausecall.py'), 'confirm')()

        if force is True:
            forcestring = ' -f'
        else:
            forcestring = ''

        if githubuserhome[-1] != '/':
            githubuserhome = githubuserhome + '/' 
        for gitdir in pushlist_committed:
            print('Parsing: ' + gitdir)
            if gitdetailsdict[gitdir]['remotelocation'].startswith(githubuserhome):
                child = pexpect.spawn('git push' + forcestring + ' origin master', cwd = gitdetailsdict[gitdir]['location'])
                child.expect('Username for ', timeout = 20)
                child.sendline(username)
                child.expect('Password for ', timeout = 20)
                child.sendline(githubpwd)

                print('\n'.join(child.read().decode('latin-1').splitlines()))
                print('')
            else:
                subprocess.call(['git', 'push', 'origin', 'master'], cwd = gitdetailsdict[gitdir]['location'])
    else:
        print('all masters up-to-date with origin')


def pullorigingit(gitlist, gitdetailsdict = None):
    """
    If input gitdetailsdict, needs to be run with option addcheckorigin
    """
    import subprocess

    if gitdetailsdict is None:
        print('Getting list for whether pull is ahead of current or not')
        gitdetailsdict = importattr(__projectdir__ / Path('main_func.py'), 'getgitdetails')(gitlist, addcheckorigin = True)    

    pulllist = sorted([gitdir for gitdir in gitdetailsdict if gitdetailsdict[gitdir]['allcommitted'] is True and gitdetailsdict[gitdir]['originvlocal'] == 'ahead'])

    if len(pulllist) > 0:
        print('\nFOLDERS TO PULL:')
        print('\n'.join(pulllist))

        importattr(__projectdir__ / Path('submodules/python-pause/pausecall.py'), 'confirm')()

        for gitdir in pulllist:
            print('Pulling ' + gitdir + '.')
            subprocess.call(['git', 'pull', 'origin', 'master'], cwd = gitdetailsdict[gitdir]['location'])
    else:
        print('all origins up-to-date')


# Empty Repository:{{{1
def emptyrepository(gitlist, gitdetailsdict = None):
    if gitdetailsdict is None:
        gitdetailsdict = importattr(__projectdir__ / Path('main_func.py'), 'getgitdetails')(gitlist, addremotelocation = True)    

    print('\nFOLDERS WHERE DELETE .git/ folder and replace with empty .git/:')
    print('\n'.join(gitdetailsdict))
    print('\nGOING TO DELETE .git')
    print('IRREVERSIBLE!!!')
    print('MAKE SURE NO MISTAKE i.e. commit all first')

    importattr(__projectdir__ / Path('submodules/python-pause/pausecall.py'), 'confirm')()

    for gitdir in gitlist:
        # remove folder
        # need to change permissions due to read-only .git folder
        importattr(__projectdir__ / Path('submodules/python-general-func/main.py'), 'chmodrecursive')(gitdir, 0o755)
        shutil.rmtree(os.path.join(gitdir, '.git'))

        subprocess.call(['git', 'init'], cwd = gitdir)
        subprocess.call(['git', 'add', '.'], cwd = gitdir)
        subprocess.call(['git', 'commit', '-m', 'Initial commit'], cwd = gitdir)

        if gitdetailsdict[gitdir]['remotelocation'] is not None:
            subprocess.call(['git', 'remote', 'add', 'origin', gitdetailsdict[gitdir]['remotelocation']], cwd = gitdir)



        

