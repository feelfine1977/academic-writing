# Publish the app to GitHub

Publish from the prepared public source folder. It contains the app and general exercises. Keep your Obsidian vault, private development repository and their histories separate.

## Guided update of an existing public clone

Use this route if your prepared public app folder already contains its own `.git` directory and is connected to your GitHub repository.

1. Open GitHub Desktop. Choose **File → Add Local Repository**, then select the existing public clone. Do not select your private development folder.
2. Check **Current branch** and the repository's remote in **Repository Settings**. Use your intended repository and branch.
3. Review **Changes**. Expect app code, general lessons, tests, blank templates and documentation. Private drafts, recordings, transcripts, local databases and Obsidian folders do not belong here.
4. Check your commit name and email in Desktop's Git settings. Enter a Summary describing the update and click **Commit to main** (or the branch shown).
5. Click **Push origin**. Check the latest commit and README on GitHub. A commit is local; pushing publishes it.
6. Open **Actions → Portable application checks** and inspect the run for this commit. Wait for both Windows and macOS jobs to pass. [Reading workflow results](https://docs.github.com/en/actions/how-tos/monitor-workflows/view-workflow-run-history).

**Next:** follow the [Windows setup checklist](windows-setup.md), connect the already-synced Obsidian vault and select a local Ollama model. Application updates come through Git; your manuscript and saved practice come through Obsidian.

If Desktop asks you to pull or resolve a conflict, inspect the incoming changes first. Do not force-push or discard changes to bypass the message. [Add an existing local repository](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-a-repository-from-your-local-computer-to-github-desktop).

## First publication into a newly cloned repository

This works on Mac and Windows and also preserves any files already in the GitHub repository.

1. Install [GitHub Desktop](https://desktop.github.com/) and sign in to your account.
2. Choose **File → Clone repository → URL**. Paste your existing repository URL and choose a new local folder outside your Obsidian vault.
3. Copy the contents of the prepared public source folder into that clone. Include `.gitignore`; exclude `.git`, `.venv`, `__pycache__` and `.pytest_cache`. On Mac, Command + Shift + . shows hidden files in Finder. Keep the clone's own `.git` folder.
4. Review the changed files in GitHub Desktop. They should contain application files, documentation, templates and general exercises. Paper folders, databases, transcripts and personal backups belong in your vault.
5. Enter a summary such as **Add Academic Writing Lab** and click **Commit to main** (or the branch displayed in your clone).
6. Click **Push origin**. Open the repository in your browser to check that the README and installation scripts are there.

GitHub supports publishing local code through either Desktop or the command line. [GitHub's publishing guide](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)

## Terminal — first push to an empty repository

Open Terminal on Mac or PowerShell/Git Bash on Windows, then change into the prepared public source folder. Replace `YOUR-ACCOUNT` below with your account name. Use these initialisation steps only when that folder has no Git repository and the destination repository is empty.

```sh
git init -b main
git config --get user.name
git config --get user.email
```

If your name or email is missing or incorrect, set it for this repository. Replace both example values with your details. You may use the private commit email shown in your GitHub email settings.

```sh
git config user.name "Your name"
git config user.email "YOUR-COMMIT-EMAIL"
```

Prepare the files and inspect the list before creating your commit:

```sh
git add .
git diff --cached --name-only
```

Then create your first commit and connect it to the existing GitHub repository:

```sh
git commit -m "Add Academic Writing Lab"
git remote add origin https://github.com/YOUR-ACCOUNT/academic-writing.git
git remote -v
git push -u origin main
```

`commit` saves a local version. `push` uploads that version to GitHub. The commands follow [GitHub's local repository instructions](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).

## Signing in

Git commit identity and GitHub login are separate. HTTPS Git authentication uses a supported credential helper or token, rather than your normal account password. GitHub Desktop handles sign-in through its interface. [GitHub authentication](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github)

For Terminal, an option is to install [GitHub CLI](https://cli.github.com/) and run:

```sh
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git --hostname github.com
```

Complete the browser sign-in, then retry `git push -u origin main`. See the official [login](https://cli.github.com/manual/gh_auth_login) and [Git credential setup](https://cli.github.com/manual/gh_auth_setup-git) instructions. Enter credentials only in the authentication interface, not in a source file or commit.

## Common messages

- **“remote origin already exists”:** run `git remote -v`. If it already points to your repository, skip `git remote add`. If it points elsewhere, confirm the intended destination before changing it.
- **“Author identity unknown”:** set your commit name and email as above, then retry the commit.
- **“Authentication failed” / “Repository not found”:** check the repository URL and signed-in account, then complete authentication.
- **“fetch first” / “non-fast-forward”:** the remote contains commits you do not have. Use the Desktop clone-and-copy method above to retain that history. Do not force-push over it.
- **“nothing to commit”:** there are no new file changes to commit. Check `git status`; an existing local commit may still need pushing.

## Later updates

Keep using the same public clone and its `.git` folder. Before copying a new release into a clean clone, run `git pull --ff-only` to bring it up to date. Copy only the prepared public release files, review additions and removals, then:

```sh
git add .
git diff --cached --stat
git commit -m "Update Academic Writing Lab"
git push
```

The release builder creates a new folder; it does not overwrite an existing public clone. Keep its Git history when transferring subsequent releases.

## Install from GitHub on another computer

Clone the repository with GitHub Desktop or Git to support **Update on Windows.cmd** and **Update on Mac.command**. A ZIP download also installs, but later updates require a fresh download because it has no Git history. Use a permanent folder outside the vault and follow the [installation guide](portable-user-guide.md). Run **Install on Windows.cmd** or **Install on Mac.command**, then choose your local synced Obsidian vault in **Papers**. Your paper data travels through Obsidian Sync separately from GitHub. Follow the [two-computer guide](portable-sync.md) before changing devices.
