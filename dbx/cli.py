import os
import sys
import argparse
import logging
from dotenv import load_dotenv
from .core import DropboxSync, get_current_branch, get_git_changes

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def main():
    parser = argparse.ArgumentParser(description="dbx: Git-to-Dropbox Synchronization Tool")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Push Command
    push_parser = subparsers.add_parser("push", help="Push local changes to Dropbox")
    push_parser.add_argument("before", nargs="?", default="HEAD~1", help="Start commit for delta sync")
    push_parser.add_argument("after", nargs="?", default="HEAD", help="End commit for delta sync")

    # Pull Command
    subparsers.add_parser("pull", help="Pull changes from Dropbox to local")

    args = parser.parse_args()
    setup_logging(args.verbose)
    load_dotenv()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Load credentials
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")
    base_dir = os.getenv("DROPBOX_BASE_DIR", "github_sync")

    if not all([refresh_token, app_key, app_secret]):
        print("Error: Missing Dropbox credentials. Please check your .env file.")
        sys.exit(1)

    branch = get_current_branch()
    branch_folder = f".{branch}"
    sync_engine = DropboxSync(refresh_token, app_key, app_secret, base_dir)

    if args.command == "push":
        if not sync_engine.folder_exists(branch_folder):
            print(f"Branch folder '{branch_folder}' not found on Dropbox. Performing full sync...")
            changes = get_git_changes()
        else:
            print(f"Performing delta sync: {args.before} -> {args.after}")
            changes = get_git_changes(args.before, args.after)

        if not changes:
            print("No changes to sync.")
            return

        sync_engine.sync_push(branch_folder, changes)
        print("Push complete.")

    elif args.command == "pull":
        if not sync_engine.folder_exists(branch_folder):
            print(f"Error: Branch folder '{branch_folder}' does not exist on Dropbox. Nothing to pull.")
            sys.exit(1)
        
        print(f"Pulling changes from Dropbox (branch: {branch})...")
        sync_engine.sync_pull(branch_folder)
        print("Pull complete.")

if __name__ == "__main__":
    main()
