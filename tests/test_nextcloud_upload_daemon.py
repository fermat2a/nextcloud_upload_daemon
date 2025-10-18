#!/usr/bin/env python3
"""
Unit tests for Nextcloud Upload Daemon

Tests the core functionality of the daemon including configuration loading,
Nextcloud integration, file processing, and event handling.
"""

import unittest
import tempfile
import os
import json
import time
import threading
import shutil
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys

# Add the parent directory to the path to import the main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nextcloud_upload_daemon import (
    NextcloudUploader,
    FileProcessor,
    FileWatcher,
    load_config,
    setup_logging
)


class TestNextcloudUploader(unittest.TestCase):
    """Test cases for NextcloudUploader class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.server_url = "https://test-nextcloud.com"
        self.username = "testuser"
        self.password = "testpass"
        self.uploader = NextcloudUploader(self.server_url, self.username, self.password)
    
    def test_init(self):
        """Test NextcloudUploader initialization"""
        self.assertEqual(self.uploader.server_url, self.server_url)
        self.assertEqual(self.uploader.username, self.username)
        self.assertEqual(self.uploader.password, self.password)
        self.assertEqual(self.uploader.webdav_url, f"{self.server_url}/remote.php/dav/files/{self.username}")
    
    @patch('nextcloud_upload_daemon.requests.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection test"""
        mock_response = Mock()
        mock_response.status_code = 207
        mock_get.return_value = mock_response
        
        result = self.uploader.test_connection()
        self.assertTrue(result)
        mock_get.assert_called_once()
    
    @patch('nextcloud_upload_daemon.requests.get')
    def test_test_connection_failure(self, mock_get):
        """Test failed connection test"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        result = self.uploader.test_connection()
        self.assertFalse(result)
    
    @patch('nextcloud_upload_daemon.requests.get')
    def test_test_connection_exception(self, mock_get):
        """Test connection test with exception"""
        mock_get.side_effect = Exception("Connection error")
        
        result = self.uploader.test_connection()
        self.assertFalse(result)
    
    @patch('nextcloud_upload_daemon.requests.head')
    def test_generate_unique_filename_no_conflict(self, mock_head):
        """Test filename generation when no conflict exists"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response
        
        result = self.uploader._generate_unique_filename("/test", "file.txt")
        self.assertEqual(result, "file.txt")
    
    @patch('nextcloud_upload_daemon.requests.head')
    def test_generate_unique_filename_with_conflict(self, mock_head):
        """Test filename generation when conflict exists"""
        # First call returns 200 (file exists), second call returns 404 (unique name found)
        mock_responses = [Mock(status_code=200), Mock(status_code=404)]
        mock_head.side_effect = mock_responses
        
        result = self.uploader._generate_unique_filename("/test", "file.txt")
        self.assertEqual(result, "Copy_2-file.txt")
    
    @patch('nextcloud_upload_daemon.requests.put')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_upload_file_success(self, mock_file, mock_put):
        """Test successful file upload"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_put.return_value = mock_response
        
        with patch.object(self.uploader, '_generate_unique_filename', return_value="test.txt"):
            result = self.uploader.upload_file("/path/to/test.txt", "/remote/path")
        
        self.assertEqual(result, "test.txt")
        mock_put.assert_called_once()
    
    @patch('nextcloud_upload_daemon.requests.put')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_upload_file_failure(self, mock_file, mock_put):
        """Test failed file upload"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_put.return_value = mock_response
        
        with patch.object(self.uploader, '_generate_unique_filename', return_value="test.txt"):
            result = self.uploader.upload_file("/path/to/test.txt", "/remote/path")
        
        self.assertIsNone(result)
    
    @patch('nextcloud_upload_daemon.requests.put')
    @patch('builtins.open', new_callable=mock_open, read_data=b"updated content")
    def test_update_file_success(self, mock_file, mock_put):
        """Test successful file update"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response
        
        result = self.uploader.update_file("/path/to/test.txt", "/remote/path", "test.txt")
        
        self.assertTrue(result)
        mock_put.assert_called_once()


class TestFileProcessor(unittest.TestCase):
    """Test cases for FileProcessor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_uploader = Mock()
        self.processor = FileProcessor(self.mock_uploader, upload_delay_seconds=1, delete_delay_seconds=2)
    
    def test_init(self):
        """Test FileProcessor initialization"""
        self.assertEqual(self.processor.uploader, self.mock_uploader)
        self.assertEqual(self.processor.upload_delay, 1)
        self.assertEqual(self.processor.delete_delay, 2)
        self.assertEqual(self.processor.file_states, {})
    
    def test_process_file_event_new_file(self):
        """Test processing event for new file"""
        with patch('os.path.exists', return_value=True):
            with patch('time.time', return_value=1000.0):
                self.processor.process_file_event('created', '/test/file.txt', '/remote')
        
        self.assertIn('/test/file.txt', self.processor.file_states)
        file_state = self.processor.file_states['/test/file.txt']
        self.assertEqual(file_state['last_modified'], 1000.0)
        self.assertEqual(file_state['remote_path'], '/remote')
        self.assertIsNone(file_state['remote_filename'])
        self.assertTrue(file_state['upload_scheduled'])
    
    def test_process_file_event_existing_file(self):
        """Test processing event for existing file"""
        # Setup existing file state
        self.processor.file_states['/test/file.txt'] = {
            'last_modified': 1000.0,
            'remote_filename': 'existing.txt',
            'remote_path': '/remote',
            'upload_scheduled': False
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('time.time', return_value=1001.0):
                self.processor.process_file_event('modified', '/test/file.txt', '/remote')
        
        file_state = self.processor.file_states['/test/file.txt']
        self.assertEqual(file_state['last_modified'], 1001.0)
        self.assertTrue(file_state['upload_scheduled'])
    
    def test_process_file_event_nonexistent_file(self):
        """Test processing event for non-existent file"""
        with patch('os.path.exists', return_value=False):
            self.processor.process_file_event('created', '/test/nonexistent.txt', '/remote')
        
        self.assertNotIn('/test/nonexistent.txt', self.processor.file_states)


class TestFileWatcher(unittest.TestCase):
    """Test cases for FileWatcher class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_uploader = Mock()
        self.mock_queue = Mock()
        self.watcher = FileWatcher(
            self.mock_uploader,
            '/local/path',
            '/remote/path',
            self.mock_queue
        )
    
    def test_init(self):
        """Test FileWatcher initialization"""
        self.assertEqual(self.watcher.uploader, self.mock_uploader)
        self.assertEqual(self.watcher.local_dir, '/local/path')
        self.assertEqual(self.watcher.remote_dir, '/remote/path')
        self.assertEqual(self.watcher.event_queue, self.mock_queue)
    
    def test_on_modified_file(self):
        """Test handling file modification event"""
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = '/test/file.txt'
        
        self.watcher.on_modified(mock_event)
        
        self.mock_queue.put.assert_called_once_with(('modified', '/test/file.txt'))
    
    def test_on_modified_directory(self):
        """Test handling directory modification event (should be ignored)"""
        mock_event = Mock()
        mock_event.is_directory = True
        mock_event.src_path = '/test/directory'
        
        self.watcher.on_modified(mock_event)
        
        self.mock_queue.put.assert_not_called()
    
    def test_on_created_file(self):
        """Test handling file creation event"""
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = '/test/newfile.txt'
        
        self.watcher.on_created(mock_event)
        
        self.mock_queue.put.assert_called_once_with(('created', '/test/newfile.txt'))


class TestConfigLoading(unittest.TestCase):
    """Test cases for configuration loading"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_load_valid_config(self):
        """Test loading valid configuration"""
        config_data = {
            "nextcloud_server": "https://test.com",
            "username": "user",
            "password": "pass",
            "upload_delay_seconds": 15,
            "delete_delay_seconds": 900,
            "directories": [
                {"local": "/local1", "remote": "/remote1"},
                {"local": "/local2", "remote": "/remote2"}
            ]
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = load_config(self.config_file)
        
        self.assertEqual(config['nextcloud_server'], "https://test.com")
        self.assertEqual(config['username'], "user")
        self.assertEqual(config['password'], "pass")
        self.assertEqual(config['upload_delay_seconds'], 15)
        self.assertEqual(config['delete_delay_seconds'], 900)
        self.assertEqual(len(config['directories']), 2)
    
    def test_load_config_with_defaults(self):
        """Test loading configuration with default timing values"""
        config_data = {
            "nextcloud_server": "https://test.com",
            "username": "user",
            "password": "pass",
            "directories": [
                {"local": "/local1", "remote": "/remote1"}
            ]
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = load_config(self.config_file)
        
        self.assertEqual(config['upload_delay_seconds'], 10)
        self.assertEqual(config['delete_delay_seconds'], 600)
    
    def test_load_config_missing_file(self):
        """Test loading non-existent configuration file"""
        with self.assertRaises(SystemExit):
            load_config('/nonexistent/config.json')
    
    def test_load_config_invalid_json(self):
        """Test loading invalid JSON configuration"""
        with open(self.config_file, 'w') as f:
            f.write('invalid json content')
        
        with self.assertRaises(SystemExit):
            load_config(self.config_file)
    
    def test_load_config_missing_required_fields(self):
        """Test loading configuration with missing required fields"""
        config_data = {
            "nextcloud_server": "https://test.com",
            "username": "user"
            # Missing password and directories
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
        
        with self.assertRaises(SystemExit):
            load_config(self.config_file)
    
    def test_load_config_invalid_directories(self):
        """Test loading configuration with invalid directories format"""
        config_data = {
            "nextcloud_server": "https://test.com",
            "username": "user",
            "password": "pass",
            "directories": "invalid_format"  # Should be a list
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
        
        with self.assertRaises(SystemExit):
            load_config(self.config_file)
    
    def test_load_config_invalid_directory_entry(self):
        """Test loading configuration with invalid directory entry"""
        config_data = {
            "nextcloud_server": "https://test.com",
            "username": "user",
            "password": "pass",
            "directories": [
                {"local": "/local1"}  # Missing remote field
            ]
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
        
        with self.assertRaises(SystemExit):
            load_config(self.config_file)


class TestLoggingSetup(unittest.TestCase):
    """Test cases for logging setup"""
    
    @patch('nextcloud_upload_daemon.logging.handlers.SysLogHandler')
    @patch('nextcloud_upload_daemon.logging.getLogger')
    def test_setup_logging(self, mock_get_logger, mock_syslog_handler):
        """Test logging setup"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_handler = Mock()
        mock_syslog_handler.return_value = mock_handler
        
        setup_logging()
        
        mock_logger.setLevel.assert_called_once()
        mock_logger.addHandler.assert_called_once_with(mock_handler)
        mock_syslog_handler.assert_called_once()


class TestIntegration(unittest.TestCase):
    """Integration tests for the daemon components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        self.test_file = os.path.join(self.temp_dir, 'test_file.txt')
        
        # Create test configuration
        config_data = {
            "nextcloud_server": "https://test.com",
            "username": "user",
            "password": "pass",
            "upload_delay_seconds": 1,
            "delete_delay_seconds": 2,
            "directories": [
                {"local": self.temp_dir, "remote": "/remote"}
            ]
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_config_and_processor_integration(self):
        """Test integration between configuration loading and file processor"""
        config = load_config(self.config_file)
        mock_uploader = Mock()
        
        processor = FileProcessor(
            mock_uploader,
            config['upload_delay_seconds'],
            config['delete_delay_seconds']
        )
        
        self.assertEqual(processor.upload_delay, 1)
        self.assertEqual(processor.delete_delay, 2)
    
    @patch('nextcloud_upload_daemon.queue.Queue')
    def test_watcher_and_processor_integration(self, mock_queue_class):
        """Test integration between file watcher and processor"""
        mock_queue = Mock()
        mock_queue_class.return_value = mock_queue
        mock_uploader = Mock()
        
        processor = FileProcessor(mock_uploader, 1, 2)
        watcher = FileWatcher(mock_uploader, self.temp_dir, "/remote", mock_queue)
        
        # Simulate file creation event
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = self.test_file
        
        watcher.on_created(mock_event)
        
        mock_queue.put.assert_called_once_with(('created', self.test_file))


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)