# sdb (Simple Dropbox Sync)

`sdb` is a lightweight CLI tool designed for developers who work across GitHub and Dropbox. It bridges the gap by allowing you to synchronize your Git branches directly to Dropbox folders with a single command.

Ideal for scenarios where you need to share code with collaborators who use Dropbox for privacy or convenience, while you maintain your workflow in Git.

## 🚀 Features

- **Branch-Specific Syncing:** Automatically detects your current Git branch and syncs it to a corresponding `.<branch_name>` folder in Dropbox.
- **Delta Sync (Push):** By default, only uploads changes since your last commit to save bandwidth and time.
- **Smart Pull:** Downloads files from Dropbox only if they are newer than your local copies.
- **Full Sync Support:** Automatically performs a full upload if a branch folder doesn't yet exist on Dropbox.
- **Simple CLI:** Clean commands (`sdb push`, `sdb pull`) for a seamless workflow.

## 🛠 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/dropbox-sync.git
   cd dropbox-sync
   ```

2. **Install the package:**
   ```bash
   pip install -e .
   ```

3. **Configure your environment:**
   Create a `.env` file in the root directory:
   ```env
   DROPBOX_APP_KEY=your_app_key
   DROPBOX_APP_SECRET=your_app_secret
   DROPBOX_REFRESH_TOKEN=your_refresh_token
   DROPBOX_BASE_DIR=my_project_sync
   ```

## 📖 Usage

### Push to Dropbox
Sync local changes from the current branch to Dropbox:
```bash
sdb push
```
*Note: This defaults to syncing `HEAD~1..HEAD`. To sync a specific range:*
```bash
sdb push <start_commit> <end_commit>
```

### Pull from Dropbox
Download newer files from the corresponding branch folder in Dropbox:
```bash
sdb pull
```

## 🔑 Dropbox Setup

To use this tool, you need a Dropbox Scoped App:

1. Create an app in the [Dropbox App Console](https://www.dropbox.com/developers/apps).
2. **Permissions:** Enable `files.content.write`, `files.content.read`, `files.metadata.write`, and `files.metadata.read`.
3. **Refresh Token:** Since access tokens expire, you must generate a long-lived refresh token.
   - Use the OAuth2 flow to get an authorization code.
   - Exchange the code for a `refresh_token` using the `/oauth2/token` endpoint with `token_access_type=offline`.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
