# echoStudy Deploy Script

Windows deploy script for echoStudy's server instance.

### Synopsis
  ```bash
  py trydeploy.py [-f | --flags] [-h | --help]
  ```

### Flags
  * `--force`   - try deploying even if local is up-to-date or builds aren't passing
  * `--fast`    - run an incremental install instead of a clean one for npm dependencies
  * `--legacy`  - pass `--legacy-peer-deps` when running `npm [i | ci]`

### Deploy configuration
A deploy configuration file is required for the script to work. 
You can change the file name and look at the schema at the top of `trydeploy.py`.
  * (e.g.) `_deploy.yml`:
    ```yml
    MAIN_DIR: "C:\\my-app"
    FRONTEND_DEST_DIR: "C:\\deploy\\my-app\\build"
    PUBLIC_AUTHOR_REPO: "jiejasonliu/my-repo-name"
    ACCESS_TOKEN: "ghp_***"
    ```

### Windows Task Scheduler
  * It's recommended that this script be added as a task to be run every `X` unit of time.
  * [More resources in doing so can be found here.](https://www.jcchouinard.com/python-automation-using-task-scheduler/)