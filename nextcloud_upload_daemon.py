#!/usr/bin/env python3
"""
Nextcloud Upload Daemon

A daemon that monitors local directories for file changes and automatically
uploads modified files to a Nextcloud server. Files are uploaded after 10
seconds of inactivity and deleted locally after 10 minutes of successful upload.
"""

import argparse
import json
import logging
import logging.handlers
import os
import queue
import sys
import threading
import time
from typing import Dict, Optional

import requests
from requests.auth import HTTPBasicAuth
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class NextcloudUploader:
    """Handles uploading files to Nextcloud server"""

    def __init__(self, server_url: str, username: str, password: str):
        """
        Initialize Nextcloud uploader

        Args:
            server_url: Nextcloud server URL
            username: Nextcloud username
            password: Nextcloud password or app password
        """
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.password = password
        self.webdav_url = f"{self.server_url}/remote.php/dav/files/{username}"
        self.auth = HTTPBasicAuth(username, password)

    def test_connection(self) -> bool:
        """Test connection to Nextcloud server"""
        try:
            response = requests.get(self.webdav_url, auth=self.auth, timeout=30)
            return response.status_code in [200, 207]  # WebDAV returns 207 for PROPFIND
        except Exception as e:
            logging.error(f"Failed to connect to Nextcloud server: {e}")
            return False

    def _generate_unique_filename(self, remote_path: str, filename: str) -> str:
        """Generate a unique filename if file already exists"""
        base_name, extension = os.path.splitext(filename)
        counter = 1

        while True:
            if counter == 1:
                test_filename = filename
            else:
                test_filename = f"Copy_{counter}-{base_name}{extension}"

            test_url = f"{self.webdav_url}/{remote_path.strip('/')}/{test_filename}"

            try:
                response = requests.head(test_url, auth=self.auth, timeout=10)
                if response.status_code == 404:
                    return test_filename
                counter += 1
            except Exception as e:
                logging.warning(f"Error checking file existence: {e}")
                return test_filename

    def _ensure_remote_directory(self, remote_path: str):
        """Ensure remote directory exists, create if it doesn't"""
        try:
            # Clean and normalize the path
            clean_path = remote_path.strip("/")
            if not clean_path:
                return  # Root directory always exists

            # Check if directory exists
            dir_url = f"{self.webdav_url}/{clean_path}"
            response = requests.request("PROPFIND", dir_url, auth=self.auth, timeout=30)

            if response.status_code == 207:
                # Directory exists
                logging.debug(f"Directory {remote_path} already exists")
                return
            elif response.status_code == 404:
                # Directory doesn't exist, create it
                logging.info(f"Creating directory {remote_path}")
                print(f"DEBUG: Creating directory {remote_path}")  # Console debug

                create_response = requests.request("MKCOL", dir_url, auth=self.auth, timeout=30)
                if create_response.status_code in [200, 201]:
                    logging.info(f"Successfully created directory {remote_path}")
                    print(f"DEBUG: Successfully created directory {remote_path}")  # Console debug
                else:
                    logging.error(f"Failed to create directory {remote_path}: HTTP {create_response.status_code}")
                    print(
                        f"DEBUG: Failed to create directory {remote_path}: HTTP {create_response.status_code}"
                    )  # Console debug
            else:
                logging.warning(f"Unexpected response when checking directory {remote_path}: HTTP {response.status_code}")
        except Exception as e:
            logging.error(f"Error ensuring remote directory {remote_path}: {e}")
            print(f"DEBUG: Error ensuring remote directory {remote_path}: {e}")  # Console debug

    def upload_file(self, local_file_path: str, remote_path: str) -> Optional[str]:
        """
        Upload file to Nextcloud

        Args:
            local_file_path: Path to local file
            remote_path: Remote directory path on Nextcloud

        Returns:
            The final filename used on the server, or None if upload failed
        """
        try:
            # Ensure remote directory exists
            self._ensure_remote_directory(remote_path)

            filename = os.path.basename(local_file_path)
            unique_filename = self._generate_unique_filename(remote_path, filename)

            remote_url = f"{self.webdav_url}/{remote_path.strip('/')}/{unique_filename}"

            with open(local_file_path, "rb") as file:
                response = requests.put(remote_url, data=file, auth=self.auth, timeout=300)  # 5 minute timeout for large files

            if response.status_code in [200, 201, 204]:
                logging.info(f"Successfully uploaded {local_file_path} as {unique_filename} to {remote_path}")
                print(f"DEBUG: Successfully uploaded {local_file_path} as {unique_filename} to {remote_path}")  # Console debug
                return unique_filename
            else:
                logging.error(f"Failed to upload {local_file_path}: HTTP {response.status_code}")
                print(f"DEBUG: Failed to upload {local_file_path}: HTTP {response.status_code}")  # Console debug
                return None

        except Exception as e:
            logging.error(f"Error uploading file {local_file_path}: {e}")
            return None

    def update_file(self, local_file_path: str, remote_path: str, remote_filename: str) -> bool:
        """
        Update existing file on Nextcloud

        Args:
            local_file_path: Path to local file
            remote_path: Remote directory path on Nextcloud
            remote_filename: Existing filename on server

        Returns:
            True if update successful, False otherwise
        """
        try:
            remote_url = f"{self.webdav_url}/{remote_path.strip('/')}/{remote_filename}"

            with open(local_file_path, "rb") as file:
                response = requests.put(remote_url, data=file, auth=self.auth, timeout=300)

            if response.status_code in [200, 201, 204]:
                logging.info(f"Successfully updated {remote_filename} in {remote_path}")
                return True
            else:
                logging.error(f"Failed to update {remote_filename}: HTTP {response.status_code}")
                return False

        except Exception as e:
            logging.error(f"Error updating file {remote_filename}: {e}")
            return False


class FileWatcher(FileSystemEventHandler):
    """Handles file system events for monitoring directories"""

    def __init__(self, uploader: NextcloudUploader, local_dir: str, remote_dir: str, event_queue: queue.Queue):
        """
        Initialize file watcher

        Args:
            uploader: NextcloudUploader instance
            local_dir: Local directory to monitor
            remote_dir: Corresponding remote directory
            event_queue: Queue for file events
        """
        super().__init__()
        self.uploader = uploader
        self.local_dir = local_dir
        self.remote_dir = remote_dir
        self.event_queue = event_queue

    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory:
            self.event_queue.put(("modified", event.src_path))

    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory:
            self.event_queue.put(("created", event.src_path))


class FileProcessor:
    """Processes file events with appropriate delays"""

    def __init__(self, uploader: NextcloudUploader, upload_delay_seconds: int = 10, delete_delay_seconds: int = 600):
        """
        Initialize file processor

        Args:
            uploader: NextcloudUploader instance
            upload_delay_seconds: Seconds to wait before uploading after file modification
            delete_delay_seconds: Seconds to wait before deleting after successful upload
        """
        self.uploader = uploader
        self.upload_delay = upload_delay_seconds
        self.delete_delay = delete_delay_seconds
        self.file_states = {}  # filepath -> {'last_modified': time, 'remote_filename': str, 'remote_path': str}
        self.lock = threading.Lock()

    def process_file_event(self, event_type: str, file_path: str, remote_path: str):
        """
        Process a file event

        Args:
            event_type: 'created' or 'modified'
            file_path: Path to the local file
            remote_path: Remote directory path
        """
        if not os.path.exists(file_path):
            return

        with self.lock:
            current_time = time.time()

            # Update file state
            if file_path not in self.file_states:
                self.file_states[file_path] = {
                    "last_modified": current_time,
                    "remote_filename": None,
                    "remote_path": remote_path,
                    "upload_scheduled": False,
                }
            else:
                self.file_states[file_path]["last_modified"] = current_time

            # Schedule upload if not already scheduled
            if not self.file_states[file_path]["upload_scheduled"]:
                self.file_states[file_path]["upload_scheduled"] = True
                threading.Timer(self.upload_delay, self._upload_file_if_stable, [file_path]).start()

    def _upload_file_if_stable(self, file_path: str):
        """Upload file if it hasn't been modified in the configured upload delay"""
        with self.lock:
            if file_path not in self.file_states:
                return

            file_state = self.file_states[file_path]
            current_time = time.time()

            # Check if file is stable (no modifications in the configured upload delay)
            if current_time - file_state["last_modified"] >= self.upload_delay:
                if os.path.exists(file_path):
                    remote_path = file_state["remote_path"]

                    if file_state["remote_filename"] is None:
                        # First upload
                        remote_filename = self.uploader.upload_file(file_path, remote_path)
                        if remote_filename:
                            file_state["remote_filename"] = remote_filename
                            # Schedule deletion after configured delay
                            threading.Timer(self.delete_delay, self._delete_file_if_stable, [file_path]).start()
                            # Schedule deletion after 10 minutes
                            threading.Timer(600.0, self._delete_file_if_stable, [file_path]).start()
                    else:
                        # Update existing file
                        self.uploader.update_file(file_path, remote_path, file_state["remote_filename"])
                        # Reset deletion timer
                        threading.Timer(self.delete_delay, self._delete_file_if_stable, [file_path]).start()

                file_state["upload_scheduled"] = False
            else:
                # File was modified, reschedule upload
                threading.Timer(self.upload_delay, self._upload_file_if_stable, [file_path]).start()

    def _delete_file_if_stable(self, file_path: str):
        """Delete local file if it hasn't been modified in the configured delete delay and was uploaded successfully"""
        with self.lock:
            if file_path not in self.file_states:
                return

            file_state = self.file_states[file_path]
            current_time = time.time()

            # Check if file is stable for the configured delete delay and was uploaded
            if (
                current_time - file_state["last_modified"] >= self.delete_delay
                and file_state["remote_filename"] is not None
                and os.path.exists(file_path)
            ):

                try:
                    os.remove(file_path)
                    logging.info(f"Deleted local file {file_path} after successful upload")
                    del self.file_states[file_path]
                except Exception as e:
                    logging.error(f"Failed to delete local file {file_path}: {e}")
            elif file_state["remote_filename"] is not None:
                # Reschedule deletion if file was uploaded but still being modified
                threading.Timer(self.delete_delay, self._delete_file_if_stable, [file_path]).start()


def load_config(config_path: str) -> Dict:
    """
    Load configuration from JSON file

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary

    Raises:
        SystemExit: If config file doesn't exist or is invalid
    """
    if not os.path.exists(config_path):
        logging.error(f"Configuration file not found: {config_path}")
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        # Validate required fields
        required_fields = ["nextcloud_server", "username", "password", "directories"]
        for field in required_fields:
            if field not in config:
                logging.error(f"Missing required field in config: {field}")
                print(f"Error: Missing required field in config: {field}", file=sys.stderr)
                sys.exit(1)

        # Set default values for optional timing fields
        if "upload_delay_seconds" not in config:
            config["upload_delay_seconds"] = 10
            logging.info("Using default upload delay: 10 seconds")

        if "delete_delay_seconds" not in config:
            config["delete_delay_seconds"] = 600
            logging.info("Using default delete delay: 600 seconds (10 minutes)")

        # Validate directories format
        if not isinstance(config["directories"], list):
            logging.error("'directories' field must be a list")
            print("Error: 'directories' field must be a list", file=sys.stderr)
            sys.exit(1)

        for i, directory in enumerate(config["directories"]):
            if not isinstance(directory, dict) or "local" not in directory or "remote" not in directory:
                logging.error(f"Invalid directory entry at index {i}: must contain 'local' and 'remote' fields")
                print(
                    f"Error: Invalid directory entry at index {i}: must contain 'local' and 'remote' fields",
                    file=sys.stderr,
                )
                sys.exit(1)

        return config

    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in config file: {e}")
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error loading config file: {e}")
        print(f"Error: Error loading config file: {e}", file=sys.stderr)
        sys.exit(1)


def setup_logging():
    """Setup logging to syslog or stdout based on environment variable"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Check environment variable to determine logging destination
    log_to_stdout = os.environ.get("NEXTCLOUD_DAEMON_LOG_STDOUT", "").lower() in ("1", "true", "yes")

    if log_to_stdout:
        # Create console handler for stdout
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - nextcloud_upload_daemon[%(process)d]: %(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    else:
        # Create syslog handler (default)
        syslog_handler = logging.handlers.SysLogHandler(address="/dev/log")
        formatter = logging.Formatter("nextcloud_upload_daemon[%(process)d]: %(levelname)s - %(message)s")
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Nextcloud Upload Daemon")
    parser.add_argument(
        "--config",
        "-c",
        default="/etc/nextcloud_upload_daemon.json",
        help="Configuration file path (default: /etc/nextcloud_upload_daemon.json)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    logging.info("Starting Nextcloud Upload Daemon")

    # Load configuration
    config = load_config(args.config)

    # Initialize Nextcloud uploader
    uploader = NextcloudUploader(config["nextcloud_server"], config["username"], config["password"])

    # Test connection
    if not uploader.test_connection():
        logging.error("Failed to connect to Nextcloud server")
        print("Error: Failed to connect to Nextcloud server", file=sys.stderr)
        sys.exit(1)

    logging.info("Successfully connected to Nextcloud server")

    # Initialize file processor with configured delays
    file_processor = FileProcessor(uploader, config["upload_delay_seconds"], config["delete_delay_seconds"])

    logging.info(f"Using upload delay: {config['upload_delay_seconds']} seconds")
    logging.info(f"Using delete delay: {config['delete_delay_seconds']} seconds")

    # Setup file watchers
    observers = []
    event_queue = queue.Queue()

    for directory_config in config["directories"]:
        local_dir = directory_config["local"]
        remote_dir = directory_config["remote"]

        if not os.path.exists(local_dir):
            logging.warning(f"Local directory does not exist: {local_dir}")
            continue

        if not os.path.isdir(local_dir):
            logging.warning(f"Local path is not a directory: {local_dir}")
            continue

        logging.info(f"Monitoring directory: {local_dir} -> {remote_dir}")

        event_handler = FileWatcher(uploader, local_dir, remote_dir, event_queue)
        observer = Observer()
        observer.schedule(event_handler, local_dir, recursive=True)
        observer.start()
        observers.append(observer)

    if not observers:
        logging.error("No valid directories to monitor")
        print("Error: No valid directories to monitor", file=sys.stderr)
        sys.exit(1)

    # Process events from queue
    def process_events():
        while True:
            try:
                event_type, file_path = event_queue.get(timeout=1.0)

                # Find corresponding remote directory
                for directory_config in config["directories"]:
                    local_dir = os.path.abspath(directory_config["local"])
                    file_abs_path = os.path.abspath(file_path)

                    if file_abs_path.startswith(local_dir + os.sep) or file_abs_path == local_dir:
                        remote_dir = directory_config["remote"]
                        file_processor.process_file_event(event_type, file_path, remote_dir)
                        break

            except queue.Empty:
                continue
            except KeyboardInterrupt:
                break

    # Start event processing thread
    event_thread = threading.Thread(target=process_events, daemon=True)
    event_thread.start()

    try:
        logging.info("Nextcloud Upload Daemon started successfully")
        print("Nextcloud Upload Daemon started. Press Ctrl+C to stop.")

        # Keep the main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Received interrupt signal, shutting down")
        print("\nShutting down...")

        # Stop observers
        for observer in observers:
            observer.stop()
            observer.join()

        logging.info("Nextcloud Upload Daemon stopped")


if __name__ == "__main__":
    main()
