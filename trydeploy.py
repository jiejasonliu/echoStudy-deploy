import argparse
import sys
import time
import yaml

from cmdhelper import *
from datetime import datetime
from pytz import timezone

############################################################
# create a file with _deploy.yml with the schema below
DEPLOY_CONFIG = "_deploy.yml"

# yml schema
MAIN_DIR = ""           # path where the repository lives
FRONTEND_DEST_DIR = ""  # path where the frontend is served
PUBLIC_AUTHOR_REPO = ""  # format of <author>/<repository-name>
ACCESS_TOKEN = ""       # see: https://github.com/settings/tokens
###########################################################


def exit_non_zero(return_code, name):
    if return_code == 0:
        print("> done.", '\n')
        return

    print(f"'{name}' failed to run; with exit code {return_code}\n")
    sys.exit(return_code)


def exit_non_success(success, name):
    if success:
        print("> done.", '\n')
        return

    print(f"'{name}' was not successful")
    sys.exit(1)


def try_deploy(cmd: CmdHelper, args) -> bool:
    try:
        local_hash = cmd.git_local_latest_hash()
        remote_hash = cmd.git_remote_latest_hash()

        # only if there are new commits on `main` or forced
        if (local_hash != remote_hash or args.force):
            print(f'comparing: remote {remote_hash} <--> local {local_hash}')

            # check if all builds pass (not pending/failing) or forced
            if not args.force:
                passing = cmd.git_check_builds_passing(remote_hash)
                exit_non_success(passing, "check CircleCI builds all passing")
            else:
                print('Skipping build pass check due to --force flag.')
            print("--------")

            # update branch
            return_code = cmd.git_pull()
            exit_non_zero(return_code, 'git pull')

            # update npm deps
            clean_install = not args.fast
            return_code = cmd.npm_install(clean=clean_install)
            exit_non_zero(return_code, 'npm ci' if clean_install else 'npm i')

            # build project distributable
            return_code = cmd.npm_build()
            exit_non_zero(return_code, 'npm run build')

            # modify project to add meta versioning before deploying
            now = datetime.now(timezone('US/Mountain'))
            version_text = f"{remote_hash} (built on {now})"
            success = cmd.add_build_version(version=version_text)
            exit_non_success(success, 'add meta build versioning')

            # deploy!
            return cmd.deploy(FRONTEND_DEST_DIR)
        else:
            print('Project is already up to date!')

    except KeyboardInterrupt:
        print('-- Exited due to keyboard interruption --')
        sys.exit(0)
    except Exception as e:
        print('An unknown error occured', e)
        return False


def parse_deploy_config():
    try:
        with open(DEPLOY_CONFIG, 'r') as f:
            doc = yaml.safe_load(f)
            global MAIN_DIR, FRONTEND_DEST_DIR, PUBLIC_AUTHOR_REPO, ACCESS_TOKEN
            MAIN_DIR = doc['MAIN_DIR']
            FRONTEND_DEST_DIR = doc['FRONTEND_DEST_DIR']
            PUBLIC_AUTHOR_REPO = doc['PUBLIC_AUTHOR_REPO']
            ACCESS_TOKEN = doc['ACCESS_TOKEN']

    except Exception as e:
        print(f'Failed to parse deploy config ({DEPLOY_CONFIG})', e)
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Deploy script for echoStudy")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force deploy regardless if already up to date or there are failing builds",
        dest="force"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="An optimized deploy; instead of a clean install, we run a simple revision install",
        dest="fast"
    )
    args = parser.parse_args()

    print('Running deployment script...')
    start = time.time()
    ###
    parse_deploy_config()
    cmd = CmdHelper(
        dir=MAIN_DIR,
        repo=PUBLIC_AUTHOR_REPO,
        github_api_token=ACCESS_TOKEN
    )
    deployed = try_deploy(cmd, args)
    ###
    end = time.time()

    if deployed:
        runtime = round(end-start, 2)
        print(f'Successfully deployed frontend; took {runtime} secs.')
