#!/usr/bin/env python3
import os
from pathlib import Path
import pexpect
import re
import shutil
import subprocess
import sys
import urllib.request

__projectdir__ = Path(os.path.dirname(os.path.realpath(__file__)) + '/')


# Get List of Github Repositories:{{{1
def getgithubrepositories(username):

    with urllib.request.urlopen("https://api.github.com/users/" + username + "/repos?per_page=1000") as fp:
        mybytes = fp.read()

    text = mybytes.decode("utf8")

    refullname = re.compile('"full_name":"([a-zA-Z0-9/_-]*)"')
    matches = refullname.finditer(text)
    projects = []
    for match in matches:
        projects.append( match.group(1)[len('c-d-cotton/'): ] )

    return(projects)


# Get Details on Git Projects:{{{1
def getgitdetails(gitlist, addremotelocation = False, addcheckorigin = False, addcheckuncommittedfiles = False):
    import re
    import subprocess

    aheadre = re.compile(r"Your branch is ahead of 'origin/master' by .* commit.?\.")

    gitdetailsdict = {}
    notgitlist = []
    for gitdir in sorted(gitlist):
        try:
            output = subprocess.check_output(['git', 'status'], cwd = gitdir)
        except Exception:
            notgitlist.append(gitdir)
            continue
            
        output = output.decode('latin-1')
        outputlist = output.split('\n')

        gitdetailsdict[gitdir] = {}
        gitdetailsdict[gitdir]['location'] = gitdir

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
                
    if len(notgitlist) > 0:
        print('\nProjects that are not a git directory:\n' + '\n'.join(notgitlist))

    return(gitdetailsdict, notgitlist)


def printgitdetails(gitlist):
    gitdirsdict, notgitlist = getgitdetails(gitlist)

    notallcommitted = []
    notonmaster = []
    behindgithub = []
    aheadgithub = []
    for gitdir in sorted(gitdirsdict):
        if gitdirsdict[gitdir]['allcommitted'] == False and gitdirsdict[gitdir]['branch'] == 'master':
            notallcommitted.append(gitdir)
        if gitdirsdict[gitdir]['branch'] != 'master':
            notonmaster.append(gitdir)

        if gitdirsdict[gitdir]['localvorigin'] == 'ahead':
            aheadgithub.append(gitdir)

        if 'originvlocal' in gitdirsdict and gitdirsdict[gitdir]['originvlocal'] == 'ahead':
            behindgithub.append(gitdir)


    if len(notgitlist) > 0:
        print('\nProjects that are not a git directory:\n' + '\n'.join(notgitlist))

    if len(aheadgithub) > 0:
        print('\nProjects that are ahead of github (so may need to do git push):\n' + '\n'.join(aheadgithub))

    if len(behindgithub) > 0:
        print('\nProjects that are behind github (so may need to do git pull):\n' + '\n'.join(behindgithub))

    if len(notonmaster) > 0:
        print('\nProjects not on the master branch:\n' + '\n'.join(notonmaster))

    if len(notallcommitted) > 0:
        print('\nProjects with uncommitted files on the master branch:\n' + '\n'.join(notallcommitted))


# Commit Functions:{{{1
def commitallgit(gitlist, commitmessage, gitdetailsdict = None, addotherbranches = False, commitnewfiles = False, checkcommitnewfiles = False):
    """
    gitlist: list of git folders to commit
    commitmessage: message I commit with for all folders
    gitdetailsdict: I run the gitdetails function to see which files to commit unless it's already specified here
    addotherbranches: commit even when the git project is on another branch
    commitnewfiles: commit projects even where there are files that are not int he previous project version
    checkcommitnewfiles: only commit projects with new files after confirmation y/n
    """

    if commitnewfiles is True:
        addcheckuncommittedfiles = False
    else:
        addcheckuncommittedfiles = True

    if gitdetailsdict is None:
        gitdetailsdict, notgitlist = getgitdetails(gitlist, addcheckuncommittedfiles = addcheckuncommittedfiles)    


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
                sys.path.append(str(__projectdir__ / Path('submodules/py-getch/getch')))
                from getch import getch
                inputted = getch()
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
        sys.path.append(str(__projectdir__ / Path('submodules/python-pause/')))
        from pausecall import confirm
        confirm()


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
    parser.add_argument("-a", "--addotherbranches", action='store_true')
    
    
    args=parser.parse_args()
    # End argparse:}}}

    commitallgit(gitlist, args.commitmessage, addotherbranches = args.addotherbranches, checkcommitnewfiles = checkcommitnewfiles)

# Git Push/Pull:{{{1
def pullorigingit(gitlist):
    """
    Just git pull for every folder in a list
    """

    pwd = os.getcwd()

    badprojects = []
    for gitdir in gitlist:
        os.chdir(gitdir)

        print('\ngit pull starting for ' + gitdir + '.')
        try:
            subprocess.check_output(['git', 'pull'])
            print('git pull succeeded for: ' + gitdir + '.')
        except subprocess.CalledProcessError as e:
            badprojects.append(gitdir)
            print('git pull failed for: ' + gitdir + '.')
            print(e.output)

    if len(badprojects) > 0:
        print('\nGIT PULL FAILED for following projects:')
        print('\n'.join(badprojects))

    os.chdir(pwd)


def pullorigingit_dict(gitlist, gitdetailsdict = None):
    """
    Select which repositories to pull using my git details function
    Possibly quicker but doesn't always correctly identify whether needs to be pulled (if for some reason the github and local versions don't line up)
    I normally just use pullorigingit() instead

    If input gitdetailsdict, needs to be run with option addcheckorigin
    """

    if gitdetailsdict is None:
        print('Getting list for whether pull is ahead of current or not')
        gitdetailsdict, nogitlist = getgitdetails(gitlist, addcheckorigin = True)    

    pulllist = sorted([gitdir for gitdir in gitdetailsdict if gitdetailsdict[gitdir]['allcommitted'] is True and gitdetailsdict[gitdir]['originvlocal'] == 'ahead'])

    if len(pulllist) > 0:
        print('\nFOLDERS TO PULL:')
        print('\n'.join(pulllist))

        sys.path.append(str(__projectdir__ / Path('submodules/python-pause/')))
        from pausecall import confirm
        confirm()

        for gitdir in pulllist:
            print('Pulling ' + gitdir + '.')
            subprocess.call(['git', 'pull', 'origin', 'master'], cwd = gitdetailsdict[gitdir]['location'])
    else:
        print('all origins up-to-date')


def pushorigingit(gitlist):
    """
    Just git push for every folder in a list
    """

    pwd = os.getcwd()

    badprojects = []
    for gitdir in gitlist:
        os.chdir(gitdir)

        print('\ngit push starting for ' + gitdir + '.')
        try:
            subprocess.check_output(['git', 'push'])
            print('git push succeeded for: ' + gitdir + '.')
        except subprocess.CalledProcessError as e:
            badprojects.append(gitdir)
            print('git push failed for: ' + gitdir + '.')
            print(e.output)

    if len(badprojects) > 0:
        print('\nGIT PUSH FAILED for following projects:')
        print('\n'.join(badprojects))

    os.chdir(pwd)


def pushorigingit_dict(gitlist, gitdetailsdict = None):
    """
    Select which repositories to push using my git details function
    Possibly quicker but doesn't always correctly identify whether needs to be pushed (if for some reason the github and local versions don't line up)
    I normally just use pushorigingit() instead
    """

    if gitdetailsdict is None:
        gitdetailsdict, notgitlist = getgitdetails(gitlist)    
        

    pushlist = sorted([gitdir for gitdir in gitdetailsdict if gitdetailsdict[gitdir]['allcommitted'] is True and gitdetailsdict[gitdir]['localvorigin'] == 'ahead'])

    if len(pushlist) > 0:
        print('\nFOLDERS TO PUSH:')
        print('\n'.join(pushlist))

        sys.path.append(str(__projectdir__ / Path('submodules/python-pause/')))
        from pausecall import confirm
        confirm()

        for gitdir in pushlist:
            subprocess.call(['git', 'push', 'origin', 'master'], cwd = gitdetailsdict[gitdir]['location'])
    else:
        print('all masters up-to-date with origin')


# Empty .git Folders:{{{1
def emptyrepository(gitlist, gitdetailsdict = None):
    """
    Replaces all .git folders in gitlist with an empty folder
    """
    if gitdetailsdict is None:
        gitdetailsdict, notgitlist = getgitdetails(gitlist, addremotelocation = True)    

    print('\nFOLDERS WHERE DELETE .git/ folder and replace with empty .git/:')
    print('\n'.join(gitdetailsdict))
    print('\nGOING TO DELETE .git')
    print('IRREVERSIBLE!!!')
    print('MAKE SURE NO MISTAKE i.e. commit all first')

    sys.path.append(str(__projectdir__ / Path('submodules/python-pause/')))
    from pausecall import confirm
    confirm()

    for gitdir in gitlist:
        # remove folder
        # need to change permissions due to read-only .git folder
        sys.path.append(str(__projectdir__ / Path('submodules/python-general-func/')))
        from main import chmodrecursive
        chmodrecursive(gitdir, 0o755)
        shutil.rmtree(os.path.join(gitdir, '.git'))

        subprocess.call(['git', 'init'], cwd = gitdir)
        subprocess.call(['git', 'add', '.'], cwd = gitdir)
        subprocess.call(['git', 'commit', '-m', 'Initial commit'], cwd = gitdir)

        if gitdetailsdict[gitdir]['remotelocation'] is not None:
            subprocess.call(['git', 'remote', 'add', 'origin', gitdetailsdict[gitdir]['remotelocation']], cwd = gitdir)



        

