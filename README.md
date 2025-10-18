# Nextcloud Upload Daemon

A Python daemon that monitors local directories for file changes and automatically uploads modified files to a Nextcloud server. Files are uploaded after 10 seconds of inactivity and automatically deleted from the local system after 10 minutes of successful upload.

## What the Program Does

The Nextcloud Upload Daemon provides the following functionality:

- **Automatic File Monitoring**: Watches specified local directories for new files and modifications
- **Smart Upload Logic**: Uploads files to Nextcloud after 10 seconds of inactivity to avoid uploading partially written files
- **Conflict Resolution**: If a file with the same name already exists on the server, it automatically renames the file with a "Copy_X-" prefix
- **File Updates**: If a local file is modified after being uploaded, the daemon updates the file on the server
- **Automatic Cleanup**: Deletes local files 10 minutes after successful upload if they haven't been modified
- **Logging**: Comprehensive logging to syslog for monitoring and troubleshooting

## Usage

### Basic Usage

```bash
# Use default configuration file (/etc/nextcloud_upload_daemon.json)
./run.sh

# Use custom configuration file
./run.sh --config /path/to/your/config.json
./run.sh -c /path/to/your/config.json
```

### Direct Python Execution

```bash
# After setting up the virtual environment
source venv/bin/activate
python3 nextcloud_upload_daemon.py --config /path/to/config.json
```

## Configuration File

The daemon requires a JSON configuration file with the following structure:

```json
{
  "nextcloud_server": "https://your-nextcloud-server.com",
  "username": "your-username",
  "password": "your-app-password-or-password",
  "directories": [
    {
      "local": "/home/user/documents/sync",
      "remote": "/Documents/Sync"
    },
    {
      "local": "/home/user/photos/upload",
      "remote": "/Photos/Upload"
    }
  ]
}
```

### Configuration Parameters

- **nextcloud_server**: The URL of your Nextcloud server (including https://)
- **username**: Your Nextcloud username
- **password**: Your Nextcloud password or app password (app passwords are recommended for security)
- **directories**: An array of directory mappings, each containing:
  - **local**: Absolute path to the local directory to monitor
  - **remote**: Path on the Nextcloud server where files should be uploaded (relative to the user's root)

### Default Configuration Location

If no configuration file is specified, the daemon looks for `/etc/nextcloud_upload_daemon.json`.

## Installation as systemd Service

Follow these steps to install the daemon as a system service that runs automatically:

### 1. Create System User

```bash
sudo useradd --system --home /opt/nextcloud_upload_daemon --shell /bin/false nextcloud-daemon
```

### 2. Install Files

```bash
# Create installation directory
sudo mkdir -p /opt/nextcloud_upload_daemon

# Copy program files
sudo cp nextcloud_upload_daemon.py /opt/nextcloud_upload_daemon/
sudo cp run.sh /opt/nextcloud_upload_daemon/
sudo cp requirements.txt /opt/nextcloud_upload_daemon/
sudo cp config.json.example /opt/nextcloud_upload_daemon/

# Set permissions
sudo chown -R nextcloud-daemon:nextcloud-daemon /opt/nextcloud_upload_daemon
sudo chmod +x /opt/nextcloud_upload_daemon/run.sh
```

### 3. Create Configuration File

```bash
# Copy and edit the configuration file
sudo cp /opt/nextcloud_upload_daemon/config.json.example /etc/nextcloud_upload_daemon.json
sudo nano /etc/nextcloud_upload_daemon.json

# Set secure permissions
sudo chown nextcloud-daemon:nextcloud-daemon /etc/nextcloud_upload_daemon.json
sudo chmod 600 /etc/nextcloud_upload_daemon.json
```

### 4. Install systemd Service

```bash
# Copy service file
sudo cp nextcloud-upload-daemon.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable nextcloud-upload-daemon
sudo systemctl start nextcloud-upload-daemon
```

### 5. Verify Installation

```bash
# Check service status
sudo systemctl status nextcloud-upload-daemon

# View logs
sudo journalctl -u nextcloud-upload-daemon -f

# Check syslog
sudo tail -f /var/log/syslog | grep nextcloud_upload_daemon
```

## Service Management

```bash
# Start the service
sudo systemctl start nextcloud-upload-daemon

# Stop the service
sudo systemctl stop nextcloud-upload-daemon

# Restart the service
sudo systemctl restart nextcloud-upload-daemon

# Enable automatic startup
sudo systemctl enable nextcloud-upload-daemon

# Disable automatic startup
sudo systemctl disable nextcloud-upload-daemon

# View service logs
sudo journalctl -u nextcloud-upload-daemon
```

## Syslog Messages and Troubleshooting

The daemon logs all activities to syslog. You can monitor the logs with:

```bash
sudo tail -f /var/log/syslog | grep nextcloud_upload_daemon
```

### Common Log Messages

#### Normal Operation

- `Starting Nextcloud Upload Daemon` - Daemon is starting up
- `Successfully connected to Nextcloud server` - Connection to Nextcloud established
- `Monitoring directory: /path/to/local -> /remote/path` - Directory monitoring started
- `Successfully uploaded /path/to/file as filename.ext to /remote/path` - File uploaded successfully
- `Successfully updated filename.ext in /remote/path` - Existing file updated
- `Deleted local file /path/to/file after successful upload` - Local file cleaned up

#### Common User Errors and Solutions

**Configuration File Errors:**

- `Configuration file not found: /path/to/config.json`
  - **Solution**: Create the configuration file or specify the correct path with `--config`
  - **Command**: `sudo touch /etc/nextcloud_upload_daemon.json && sudo nano /etc/nextcloud_upload_daemon.json`

- `Invalid JSON in config file`
  - **Solution**: Check JSON syntax, ensure all brackets and quotes are properly closed
  - **Command**: `sudo python3 -m json.tool /etc/nextcloud_upload_daemon.json`

- `Missing required field in config: fieldname`
  - **Solution**: Add the missing field to your configuration file (nextcloud_server, username, password, or directories)

**Connection Errors:**

- `Failed to connect to Nextcloud server`
  - **Possible causes**:
    - Incorrect server URL
    - Wrong username or password
    - Network connectivity issues
    - Server is down
  - **Solutions**:
    - Verify server URL is correct and includes `https://`
    - Test credentials by logging into Nextcloud web interface
    - Check network connectivity: `ping your-nextcloud-server.com`
    - Consider using an app password instead of regular password

**Directory Errors:**

- `Local directory does not exist: /path/to/directory`
  - **Solution**: Create the directory or fix the path in configuration
  - **Command**: `sudo mkdir -p /path/to/directory`

- `Local path is not a directory: /path/to/file`
  - **Solution**: Ensure the local path points to a directory, not a file

- `No valid directories to monitor`
  - **Solution**: Ensure at least one local directory in the configuration exists and is accessible

**Permission Errors:**

- `Permission denied` errors when accessing files
  - **Solution**: Ensure the daemon user has read access to monitored directories
  - **Command**: `sudo chown -R nextcloud-daemon:nextcloud-daemon /path/to/monitored/directory`

**Upload Errors:**

- `Failed to upload /path/to/file: HTTP 401`
  - **Solution**: Check username and password, consider using app password

- `Failed to upload /path/to/file: HTTP 403`
  - **Solution**: Check if user has write permissions to the remote directory

- `Failed to upload /path/to/file: HTTP 507`
  - **Solution**: Nextcloud server storage is full

### Debugging Tips

1. **Test Configuration**: Run the daemon manually to see immediate error output:
   ```bash
   cd /opt/nextcloud_upload_daemon
   sudo -u nextcloud-daemon ./run.sh --config /etc/nextcloud_upload_daemon.json
   ```

2. **Check Network Connectivity**: Test connection to your Nextcloud server:
   ```bash
   curl -I https://your-nextcloud-server.com
   ```

3. **Validate JSON Configuration**:
   ```bash
   python3 -m json.tool /etc/nextcloud_upload_daemon.json
   ```

4. **Monitor File System Events**: Check if the daemon detects file changes:
   ```bash
   # Create a test file in a monitored directory
   echo "test" > /path/to/monitored/directory/test.txt
   # Then check the logs for upload activity
   ```

## Requirements

- Python 3.7 or higher
- pip (Python package manager)
- Internet connection to Nextcloud server
- Write access to monitored local directories
- Valid Nextcloud account with appropriate permissions

## Dependencies

The daemon uses the following Python packages (automatically installed by `run.sh`):

- `watchdog>=3.0.0` - For file system monitoring
- `requests>=2.31.0` - For HTTP communication with Nextcloud

## Security Considerations

1. **Use App Passwords**: Instead of your main Nextcloud password, create and use app-specific passwords
2. **Secure Configuration**: The configuration file contains credentials, so ensure it has restrictive permissions (600)
3. **Dedicated User**: Run the daemon as a dedicated system user with minimal privileges
4. **Network Security**: Use HTTPS for Nextcloud server communication
5. **Log Monitoring**: Regularly monitor logs for suspicious activity

## License

This project is open source. Please check the repository for license details.