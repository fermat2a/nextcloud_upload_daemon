#!/usr/bin/env python3
"""
System Tests for Nextcloud Upload Daemon

These tests use a real Nextcloud instance to verify end-to-end functionality
including file uploads, WebDAV integration, and daemon behavior.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import requests


class NextcloudSystemTests(unittest.TestCase):
    """System tests using real Nextcloud instance"""

    @classmethod
    def setUpClass(cls):
        """Set up Nextcloud test instance"""
        cls.nextcloud_url = "http://localhost:8080"
        cls.admin_user = "admin"
        cls.admin_password = "admin123"
        cls.test_user = "testuser"
        cls.test_password = "testpass123"

        # Wait for Nextcloud to be ready
        cls._wait_for_nextcloud()

        # Setup test directories
        cls.temp_dir = tempfile.mkdtemp()
        cls.upload_dir = Path(cls.temp_dir) / "upload"
        cls.upload_dir.mkdir()

        print(f"System tests using temp directory: {cls.temp_dir}")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if hasattr(cls, "temp_dir") and os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    @classmethod
    def _wait_for_nextcloud(cls, timeout=120):
        """Wait for Nextcloud to be ready"""
        print("Waiting for Nextcloud to be ready...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Only check basic status, skip WebDAV to avoid rate limiting
                response = requests.get(f"{cls.nextcloud_url}/status.php", timeout=10)
                if response.status_code == 200:
                    status = response.json()
                    if status.get("installed") and status.get("maintenance") is False:
                        print("Nextcloud is ready!")
                        # Wait a bit more for internal initialization
                        time.sleep(10)
                        return
            except requests.exceptions.RequestException:
                pass

            print("Still waiting for Nextcloud...")
            time.sleep(10)

        raise RuntimeError(f"Nextcloud not ready after {timeout} seconds")

    @classmethod
    def _create_test_user(cls):
        """Create test user via OCS API"""
        url = f"{cls.nextcloud_url}/ocs/v1.php/cloud/users"
        data = {"userid": cls.test_user, "password": cls.test_password}

        response = requests.post(url, data=data, auth=(cls.admin_user, cls.admin_password), headers={"OCS-APIRequest": "true"})

        # User might already exist, that's okay
        if response.status_code in [200, 409]:
            print(f"Test user '{cls.test_user}' ready")
        else:
            print(f"Warning: Could not create test user. Status: {response.status_code}")

    def setUp(self):
        """Set up for each test"""
        # Create unique test directory for this test
        self.test_name = self.id().split(".")[-1]
        self.test_upload_dir = self.upload_dir / self.test_name
        self.test_upload_dir.mkdir()

        # Create test configuration - use admin credentials to avoid rate limiting
        self.config_file = self.test_upload_dir / "config.json"
        self.config_data = {
            "nextcloud_server": self.nextcloud_url,
            "username": self.admin_user,
            "password": self.admin_password,
            "directories": [{"local": str(self.test_upload_dir), "remote": f"/test_{self.test_name}"}],
            "upload_delay_seconds": 1,
            "delete_delay_seconds": 3,
        }

        with open(self.config_file, "w") as f:
            json.dump(self.config_data, f, indent=2)

    def tearDown(self):
        """Clean up after each test"""
        # Stop any running daemon processes
        self._stop_daemon_processes()

        # Clean up test files from Nextcloud
        self._cleanup_nextcloud_files()

    def _stop_daemon_processes(self):
        """Stop any running daemon processes"""
        try:
            # Find and kill any running daemon processes
            result = subprocess.run(["pgrep", "-f", "nextcloud_upload_daemon.py"], capture_output=True, text=True)

            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    if pid:
                        subprocess.run(["kill", pid], capture_output=True)
                        time.sleep(0.5)
        except Exception as e:
            print(f"Warning: Could not stop daemon processes: {e}")

    def _cleanup_nextcloud_files(self):
        """Clean up test files from Nextcloud"""
        try:
            # Delete test directory from Nextcloud
            webdav_url = f"{self.nextcloud_url}/remote.php/dav/files/{self.admin_user}/test_{self.test_name}"
            requests.delete(webdav_url, auth=(self.admin_user, self.admin_password), timeout=10)
        except Exception as e:
            print(f"Warning: Could not clean up Nextcloud files: {e}")

    def _run_daemon(self, timeout=15):
        """Run the daemon for a specified time"""
        daemon_script = Path(__file__).parent / "nextcloud_upload_daemon.py"

        # Use Python from virtual environment if available
        python_executable = sys.executable if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else "python3"

        # Run daemon in background
        with subprocess.Popen(
            [python_executable, str(daemon_script), "--config", str(self.config_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:
            # Let it run for the specified time
            time.sleep(timeout)

            # Stop the daemon gracefully
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if still running
                process.kill()
                stdout, stderr = process.communicate(timeout=2)

            # Print daemon output for debugging
            print(f"Daemon returncode: {process.returncode}")
            if stdout:
                print(f"Daemon stdout: {stdout}")
            if stderr:
                print(f"Daemon stderr: {stderr}")

            return process.returncode

    def _run_daemon_with_file_creation(self, filename, content, timeout=15):
        """Run daemon and create file after daemon starts to trigger watchdog events"""
        daemon_script = Path(__file__).parent / "nextcloud_upload_daemon.py"

        # Use Python from virtual environment if available
        python_executable = sys.executable if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else "python3"
        
        with subprocess.Popen(
            [python_executable, str(daemon_script), "--config", str(self.config_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:
            # Give daemon time to start and setup file watching
            time.sleep(3)

            # Create test file AFTER daemon is running to trigger watchdog event
            file_path = self.test_upload_dir / filename
            with open(file_path, "w") as f:
                f.write(content)

            # Wait for upload processing (upload_delay + processing time)
            time.sleep(timeout - 3)

            # Stop daemon
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=2)

            # Print daemon output for debugging
            print(f"Daemon returncode: {process.returncode}")
            if stdout:
                print(f"Daemon stdout: {stdout}")
            if stderr:
                print(f"Daemon stderr: {stderr}")

            return process.returncode

    def _create_test_file(self, filename, content="Test file content"):
        """Create a test file in the upload directory"""
        file_path = self.test_upload_dir / filename
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def _check_file_in_nextcloud(self, filename):
        """Check if file exists in Nextcloud"""
        webdav_url = f"{self.nextcloud_url}/remote.php/dav/files/{self.admin_user}/test_{self.test_name}/{filename}"

        response = requests.request("PROPFIND", webdav_url, auth=(self.admin_user, self.admin_password), timeout=10)

        return response.status_code == 207

    def _get_file_content_from_nextcloud(self, filename):
        """Get file content from Nextcloud"""
        webdav_url = f"{self.nextcloud_url}/remote.php/dav/files/{self.admin_user}/test_{self.test_name}/{filename}"

        response = requests.get(webdav_url, auth=(self.admin_user, self.admin_password), timeout=10)

        if response.status_code == 200:
            return response.text
        return None

    def test_basic_file_upload(self):
        """Test basic file upload functionality"""
        test_content = "Hello Nextcloud System Test!"

        # Use modified run method that creates file after daemon starts
        self._run_daemon_with_file_creation("test_upload.txt", test_content, timeout=15)

        # Check if file was uploaded
        self.assertTrue(self._check_file_in_nextcloud("test_upload.txt"), "File should be uploaded to Nextcloud")

        # Verify content
        uploaded_content = self._get_file_content_from_nextcloud("test_upload.txt")
        self.assertEqual(uploaded_content, test_content, "Uploaded content should match original")

    def test_file_modification_update(self):
        """Test that modified files are updated in Nextcloud"""
        original_content = "Original content"
        modified_content = "Modified content - updated!"
        
        # Start daemon first
        daemon_script = Path(__file__).parent / "nextcloud_upload_daemon.py"
        python_executable = sys.executable if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else "python3"
        
        with subprocess.Popen(
            [python_executable, str(daemon_script), "--config", str(self.config_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:
            # Give daemon time to start and setup file watching
            time.sleep(3)

            # Create initial file AFTER daemon is running
            file_path = self.test_upload_dir / "test_modify.txt"
            with open(file_path, "w") as f:
                f.write(original_content)

            # Wait for initial upload but not deletion (shorter timeout)
            time.sleep(5)
            
            # Verify initial upload 
            self.assertTrue(self._check_file_in_nextcloud("test_modify.txt"))

            # Modify the file while daemon is still running
            with open(file_path, "w") as f:
                f.write(modified_content)

            # Wait for update processing
            time.sleep(8)

            # Stop daemon
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=2)

            # Print daemon output for debugging
            print(f"Daemon returncode: {process.returncode}")
            if stdout:
                print(f"Daemon stdout: {stdout}")
            if stderr:
                print(f"Daemon stderr: {stderr}")

        # Verify update
        uploaded_content = self._get_file_content_from_nextcloud("test_modify.txt")
        self.assertEqual(uploaded_content, modified_content, "Updated content should be reflected in Nextcloud")

    def test_file_deletion_after_upload(self):
        """Test that files are deleted locally after successful upload"""
        # Run daemon and create file after it starts to trigger watchdog
        self._run_daemon_with_file_creation("test_delete.txt", "Delete me after upload", timeout=15)

        # Check upload happened
        self.assertTrue(self._check_file_in_nextcloud("test_delete.txt"), "File should be uploaded to Nextcloud")

        # Check local deletion happened 
        file_path = self.test_upload_dir / "test_delete.txt"
        self.assertFalse(file_path.exists(), "File should be deleted locally after upload")

    def test_conflict_resolution(self):
        """Test filename conflict resolution"""
        content1 = "First file content"
        
        # Create first file after daemon starts
        self._run_daemon_with_file_creation("common_name.txt", content1, timeout=12)

        # Verify upload
        self.assertTrue(self._check_file_in_nextcloud("common_name.txt"))

        # Create another file with same name (after first is deleted) 
        time.sleep(1)  # Ensure different timestamp
        content2 = "Second file content with different data"
        
        # Create second file and run daemon again
        self._run_daemon_with_file_creation("common_name.txt", content2, timeout=12)

        # Check that both files exist (second should be renamed)
        self.assertTrue(self._check_file_in_nextcloud("common_name.txt"))
        # Should have a copy with different name
        self.assertTrue(
            self._check_file_in_nextcloud("Copy_1-common_name.txt") or self._check_file_in_nextcloud("Copy_2-common_name.txt"),
            "Conflicting file should be renamed with Copy_ prefix",
        )

    def test_multiple_files_upload(self):
        """Test uploading multiple files simultaneously"""
        files_data = {
            "file1.txt": "Content of file 1",
            "file2.txt": "Content of file 2", 
            "file3.txt": "Content of file 3",
            "subdoc.md": "# Markdown Document\nThis is a test.",
        }

        # Start daemon first, then create all files to trigger watchdog
        daemon_script = Path(__file__).parent / "nextcloud_upload_daemon.py"
        python_executable = sys.executable if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else "python3"
        
        with subprocess.Popen(
            [python_executable, str(daemon_script), "--config", str(self.config_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:
            # Give daemon time to start and setup file watching
            time.sleep(3)

            # Create all test files AFTER daemon is running
            for filename, content in files_data.items():
                file_path = self.test_upload_dir / filename
                with open(file_path, "w") as f:
                    f.write(content)

            # Wait for upload processing
            time.sleep(15)

            # Stop daemon
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=2)

            # Print daemon output for debugging
            print(f"Daemon returncode: {process.returncode}")
            if stdout:
                print(f"Daemon stdout: {stdout}")
            if stderr:
                print(f"Daemon stderr: {stderr}")

        # Check all files were uploaded
        for filename, expected_content in files_data.items():
            self.assertTrue(self._check_file_in_nextcloud(filename), f"File {filename} should be uploaded")

            uploaded_content = self._get_file_content_from_nextcloud(filename)
            self.assertEqual(uploaded_content, expected_content, f"Content of {filename} should match")

    def test_daemon_connection_failure_handling(self):
        """Test daemon behavior when Nextcloud is unavailable"""
        # Create test file
        file_path = self._create_test_file("test_connection.txt", "Test connection failure")

        # Use invalid configuration
        invalid_config = self.config_data.copy()
        invalid_config["nextcloud_server"] = "http://invalid-server:9999"

        invalid_config_file = self.test_upload_dir / "invalid_config.json"
        with open(invalid_config_file, "w") as f:
            json.dump(invalid_config, f, indent=2)

        # Run daemon with invalid config (should not crash)
        daemon_script = Path(__file__).parent / "nextcloud_upload_daemon.py"

        process = subprocess.Popen(
            ["python3", str(daemon_script), "--config", str(invalid_config_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Let it run briefly
        time.sleep(5)
        process.terminate()
        stdout, stderr = process.communicate()

        # File should still exist (not uploaded due to connection failure)
        self.assertTrue(file_path.exists(), "File should remain when connection fails")

        # Should have logged connection errors
        self.assertIn(b"Failed to connect" or b"Connection error", stderr, "Should log connection errors")

    def test_webdav_authentication(self):
        """Test WebDAV authentication with Nextcloud"""
        from nextcloud_upload_daemon import NextcloudUploader

        # Test valid credentials
        uploader = NextcloudUploader(self.nextcloud_url, self.admin_user, self.admin_password)

        self.assertTrue(uploader.test_connection(), "Should connect with valid credentials")

        # Test invalid credentials
        invalid_uploader = NextcloudUploader(self.nextcloud_url, "invalid_user", "invalid_password")

        self.assertFalse(invalid_uploader.test_connection(), "Should fail with invalid credentials")


if __name__ == "__main__":
    # Check if we're running in CI or need to start Nextcloud
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        print("Running in CI environment - assuming Nextcloud is already started")
    else:
        print("Running locally - please ensure Nextcloud is running with: docker compose -f docker-compose.test.yml up -d")

        # Optionally auto-start docker compose
        response = input("Start Nextcloud automatically? (y/n): ").lower()
        if response == "y":
            print("Starting Nextcloud...")
            subprocess.run(["docker", "compose", "-f", "docker-compose.test.yml", "up", "-d"])
            time.sleep(10)  # Give it time to start

    unittest.main(verbosity=2)
