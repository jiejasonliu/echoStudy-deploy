import json
import os
import requests
import shutil
import subprocess


GITHUB_API = "https://api.github.com/repos/"
BUILD_DIR_NAME = "build"


class CmdHelper:
    """
    Use of this helper requires the working git dir to be at the root and also checked out on the `main` branch.
    """

    def __init__(self, dir: str, repo: str, github_api_token: str = ""):
        self.change_main_dir(dir)
        self._repo = repo
        self._github_api_req_headers = {
            'Authorization': f'token {github_api_token}'
        }

    def change_main_dir(self, newdir: str):
        self._dir = newdir

    # perf: ~40ms
    def git_local_latest_hash(self) -> str:
        cmd = ['git', 'rev-parse', 'HEAD']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=self._dir)
        first_line = next(iter(proc.stdout.readlines()), '')
        return first_line.decode("utf8").strip()

    # perf: 1000-2000ms
    # def remote_latest_commit_hash(self) -> str:
    #     cmd = ['git', 'ls-remote', 'origin', 'HEAD']
    #     pipe_cmd = ['awk', '{ print $1 }']
    #     proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=self._dir)
    #     first_line = subprocess.check_output(pipe_cmd, stdin=proc.stdout)
    #     return first_line.decode("utf8").strip()

    # perf: ~200-400ms
    def git_remote_latest_hash(self) -> str:
        # GitHub API also tries `main` for backwards compatibility
        url = f'https://api.github.com/repos/{self._repo}/branches/master'
        response = requests.get(url, headers=self._github_api_req_headers)
        obj = json.loads(response.text)
        return obj['commit']['sha']

    def git_check_builds_passing(self, commit_hash) -> bool:
        url = f'https://api.github.com/repos/{self._repo}/commits/{commit_hash}/status'
        response = requests.get(url, headers=self._github_api_req_headers)
        obj = json.loads(response.text)
        return obj['state'] == 'success'

    # perf: n/a
    def git_pull(self) -> int:
        cmd = ['git', 'pull']
        return self._run_for_exit_code(cmd)

    def npm_install(self, clean=False) -> int:
        shell_cmd = 'npm ci' if clean else 'npm i'
        return self._run_shell_for_exit_code(shell_cmd, timeout=300)

    def npm_build(self) -> int:
        shell_cmd = 'npm run build'
        return self._run_shell_for_exit_code(shell_cmd)

    def add_build_version(self, version: str) -> bool:
        print("Adding build version to index.html...")
        index_html_path = os.path.join(self._dir, BUILD_DIR_NAME, 'index.html')
        if os.path.exists(index_html_path):
            # read in index.html
            with open(index_html_path, 'r') as f:
                content = f.read()

            # add versioning comment below <!doctype html>
            with open(index_html_path, 'w') as f:
                doctype = "<!doctype html>"
                build_version = f"<!-- version: {version} -->"
                if content.startswith(doctype) or content.lower().startswith(doctype):
                    new_content = doctype + build_version + content[len(doctype):]
                else:
                    new_content = doctype + build_version + content
                f.write(new_content)
            return True
        else:
            print("Couldn't find 'index.html', try running npm_build() first?")
        return False

    def deploy(self, dest_path: str) -> bool:
        """
        Deploys the currently built files to be served. This method does not automatically build the project.
        Therefore, if `npm_build()` was never ran, we may be serving a stale (or empty) version of the project.

        params:
          dest_path - path where the contents of the built files are; usually 'C:/.../build'

        returns:
          True if build files were successfully deployed, otherwise False
        """

        # create destination folder if it doesn't exist already
        if not os.path.exists(dest_path):
            os.mkdir(dest_path)

        # check if destination is empty (e.g. first time deploy)
        initial_deploy = not os.listdir(dest_path)

        # add certain paths to check for to ensure this is actually a deploy folder
        # we don't want to accidentally typo and remove our entire Windows installation
        index_html_path = os.path.join(dest_path, 'index.html')
        asset_manifest_path = os.path.join(dest_path, 'asset-manifest.json')
        all_paths = [dest_path, index_html_path, asset_manifest_path]

        # replace existing deployment if all paths exist
        if initial_deploy or all([os.path.exists(path) for path in all_paths]):
            shutil.rmtree(dest_path)

            # ensure project distributable exists
            build_dir_path = os.path.join(self._dir, BUILD_DIR_NAME)
            if os.path.exists(build_dir_path):
                shutil.copytree(build_dir_path, dest_path)
                return True
            else:
                print("Tried to deploy but could not find 'build' folder.")
                print("Try running npm_build() first?")

        print("Tried to deploy but failed destination path checks.")
        print("Are you sure you're deploying to the current folder?")
        return False

    def _run_for_exit_code(self, cmd: list, timeout=60):
        print(f"Executing '{' '.join(cmd)}'")
        proc = subprocess.Popen(cmd, cwd=self._dir)
        return proc.wait(timeout)

    def _run_shell_for_exit_code(self, shell_cmd: str, timeout=60):
        print(f"Executing '{shell_cmd}'")
        proc = subprocess.Popen(shell_cmd, shell=True, cwd=self._dir)
        return proc.wait(timeout)
