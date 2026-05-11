import os
import sys
import logging
import subprocess
from datetime import datetime
from typing import List, Tuple
import dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import WriteMode, FileMetadata

logger = logging.getLogger(__name__)

class DropboxSync:
    """Handles synchronization logic between local git repository and Dropbox."""

    def __init__(self, refresh_token: str, app_key: str, app_secret: str, base_path: str):
        self.base_path = base_path.strip("/")
        try:
            self.dbx = dropbox.Dropbox(
                oauth2_refresh_token=refresh_token,
                app_key=app_key,
                app_secret=app_secret
            )
            self.dbx.users_get_current_account()
            logger.debug("Successfully authenticated with Dropbox.")
        except AuthError as e:
            logger.error(f"Authentication failed: {e}")
            sys.exit(1)

    def _format_dropbox_path(self, local_path: str, branch_folder: str) -> str:
        """Converts local file path to Dropbox-compatible path."""
        clean_path = local_path.replace(os.sep, "/")
        return f"/{self.base_path}/{branch_folder}/{clean_path}".replace("//", "/")

    def _format_local_path(self, dbx_path: str, branch_folder: str) -> str:
        """Converts Dropbox path back to local file path."""
        prefix = f"/{self.base_path}/{branch_folder}/".replace("//", "/")
        if dbx_path.startswith(prefix):
            return dbx_path[len(prefix):].replace("/", os.sep)
        return dbx_path.replace("/", os.sep)

    def folder_exists(self, folder_name: str) -> bool:
        """Checks if a folder exists in Dropbox."""
        dbx_path = f"/{self.base_path}/{folder_name}".replace("//", "/")
        try:
            self.dbx.files_get_metadata(dbx_path)
            return True
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                return False
            return False

    def upload_file(self, local_path: str, branch_folder: str):
        """Uploads or overwrites a file on Dropbox."""
        if local_path == ".env":
            return

        dbx_path = self._format_dropbox_path(local_path, branch_folder)
        
        if not os.path.exists(local_path):
            logger.warning(f"File {local_path} does not exist locally. Skipping.")
            return

        try:
            with open(local_path, "rb") as f:
                data = f.read()
                self.dbx.files_upload(data, dbx_path, mode=WriteMode.overwrite)
                logger.info(f"Uploaded: {local_path} -> {dbx_path}")
        except ApiError as e:
            logger.error(f"Failed to upload {local_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error uploading {local_path}: {e}")

    def download_file(self, dbx_path: str, local_path: str):
        """Downloads a file from Dropbox to local disk."""
        try:
            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.dbx.files_download_to_file(local_path, dbx_path)
            logger.info(f"Downloaded: {dbx_path} -> {local_path}")
        except ApiError as e:
            logger.error(f"Failed to download {dbx_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error downloading {dbx_path}: {e}")

    def delete_file(self, local_path: str, branch_folder: str):
        """Deletes a file or folder from Dropbox."""
        dbx_path = self._format_dropbox_path(local_path, branch_folder)
        try:
            self.dbx.files_delete_v2(dbx_path)
            logger.info(f"Deleted from Dropbox: {dbx_path}")
        except ApiError as e:
            if not (e.error.is_path() and e.error.get_path().is_not_found()):
                logger.error(f"Failed to delete {dbx_path}: {e}")

    def sync_push(self, branch_folder: str, changed_files: List[Tuple[str, str]]):
        """Processes a list of changed files and their status codes (Local -> Dropbox)."""
        for status, path in changed_files:
            if status.startswith("A") or status.startswith("M"):
                self.upload_file(path, branch_folder)
            elif status.startswith("D"):
                self.delete_file(path, branch_folder)
            elif status.startswith("R"):
                parts = path.split("\t")
                if len(parts) == 2:
                    old_p, new_p = parts
                    self.delete_file(old_p, branch_folder)
                    self.upload_file(new_p, branch_folder)

    def sync_pull(self, branch_folder: str):
        """Pulls changes from Dropbox to Local (Dropbox -> Local)."""
        dbx_base = f"/{self.base_path}/{branch_folder}".replace("//", "/")
        
        try:
            result = self.dbx.files_list_folder(dbx_base, recursive=True)
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, FileMetadata):
                        local_path = self._format_local_path(entry.path_display, branch_folder)
                        
                        # Smart Sync logic: Compare modification times
                        remote_time = entry.server_modified
                        local_exists = os.path.exists(local_path)
                        
                        should_download = False
                        if not local_exists:
                            should_download = True
                        else:
                            local_time = datetime.fromtimestamp(os.path.getmtime(local_path))
                            # server_modified is UTC, let's assume local is same for simplicity or comparison
                            if remote_time > local_time:
                                should_download = True
                        
                        if should_download:
                            self.download_file(entry.path_display, local_path)
                        else:
                            logger.debug(f"Skipping {local_path} (local is up to date)")

            process_entries(result.entries)
            
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                process_entries(result.entries)
                
        except ApiError as e:
            logger.error(f"Failed to list Dropbox folder: {e}")

def get_current_branch() -> str:
    """Gets the name of the current Git branch."""
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
            text=True
        ).strip()
        return branch
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get current branch: {e}")
        sys.exit(1)

def get_git_changes(before: str = None, after: str = None) -> List[Tuple[str, str]]:
    """Retrieves changed files. If before/after are none, returns all tracked files."""
    if before and after:
        try:
            cmd = ["git", "diff", "--name-status", before, after]
            output = subprocess.check_output(cmd, text=True).strip()
            if not output: return []
            
            changes = []
            for line in output.split("\n"):
                parts = line.split("\t")
                if len(parts) >= 2:
                    changes.append((parts[0], "\t".join(parts[1:])))
            return changes
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running git diff: {e}")
            return []
    else:
        try:
            output = subprocess.check_output(["git", "ls-files"], text=True).strip()
            if not output: return []
            return [("A", f) for f in output.split("\n")]
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running git ls-files: {e}")
            return []
