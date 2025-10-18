# Developer Documentation

## Overview

This document provides technical documentation for developers working on the Nextcloud Upload Daemon project. It covers the code architecture, development setup, testing procedures, and contribution guidelines.

## Project Structure

```
nextcloud_upload_daemon/
├── nextcloud_upload_daemon.py    # Main daemon implementation
├── config.json.example           # Example configuration file
├── requirements.txt               # Python dependencies
├── run.sh                        # Production startup script
├── test_runner.sh                # Test execution script
├── nextcloud-upload-daemon.service # systemd service file
├── tests/                        # Unit tests directory
│   ├── __init__.py               # Python package marker
│   └── test_nextcloud_upload_daemon.py # Main test suite
├── README.md                     # User documentation
├── DEVELOPER.md                  # This file
├── license.txt                   # GPL v2 license
└── .gitignore                    # Git ignore rules
```

## Code Architecture

### Core Components

The Nextcloud Upload Daemon is built using a modular architecture with the following main components:

#### 1. NextcloudUploader Class

**Purpose**: Handles all communication with the Nextcloud server via WebDAV protocol.

**Key Methods**:
- `__init__(server_url, username, password)`: Initialize connection parameters
- `test_connection()`: Verify server connectivity and authentication
- `upload_file(local_path, remote_path)`: Upload a new file to Nextcloud
- `update_file(local_path, remote_path, remote_filename)`: Update existing file
- `_generate_unique_filename(remote_path, filename)`: Handle filename conflicts

**Dependencies**: `requests` library for HTTP/WebDAV communication

#### 2. FileProcessor Class

**Purpose**: Manages file state tracking, upload scheduling, and cleanup operations.

**Key Methods**:
- `__init__(uploader, upload_delay_seconds, delete_delay_seconds)`: Initialize with configurable timing
- `process_file_event(event_type, file_path, remote_path)`: Handle file system events
- `_upload_file_if_stable(file_path)`: Upload files after stability period
- `_delete_file_if_stable(file_path)`: Delete local files after successful upload

**State Management**: Tracks file modification times, upload status, and remote filenames using thread-safe operations.

#### 3. FileWatcher Class

**Purpose**: Monitors file system events and forwards them to the event queue.

**Inheritance**: Extends `watchdog.events.FileSystemEventHandler`

**Key Methods**:
- `on_modified(event)`: Handle file modification events
- `on_created(event)`: Handle file creation events

**Threading**: Operates in separate thread via `watchdog.observers.Observer`

#### 4. Configuration Management

**Function**: `load_config(config_path)`

**Purpose**: Load and validate JSON configuration with proper error handling.

**Validation**:
- Required fields: `nextcloud_server`, `username`, `password`, `directories`
- Optional fields: `upload_delay_seconds`, `delete_delay_seconds`
- Directory structure validation
- Default value assignment

### Data Flow

1. **Initialization**:
   - Load configuration from JSON file
   - Initialize NextcloudUploader with server credentials
   - Create FileProcessor with configured timing parameters
   - Set up FileWatcher instances for each monitored directory

2. **File Monitoring**:
   - FileWatcher detects file system events
   - Events are queued for processing
   - FileProcessor handles queued events

3. **Upload Process**:
   - File events trigger stability tracking
   - After configured delay, stable files are uploaded
   - Filename conflicts are resolved automatically
   - Upload success triggers deletion timer

4. **Cleanup**:
   - Successfully uploaded files are deleted after configured delay
   - File state is maintained until cleanup completion

### Threading Model

The daemon uses multiple threads for non-blocking operation:

- **Main Thread**: Configuration, setup, and coordination
- **Observer Threads**: File system monitoring (one per directory)
- **Event Processing Thread**: Handles queued file events
- **Timer Threads**: Handle delayed upload and deletion operations

### Error Handling

- **Configuration Errors**: Immediate termination with clear error messages
- **Network Errors**: Logged and retried on subsequent file modifications
- **File System Errors**: Logged with appropriate error levels
- **Upload Failures**: Logged but do not prevent future operations

## Development Setup

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)
- Git for version control

### Local Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/fermat2a/nextcloud_upload_daemon.git
   cd nextcloud_upload_daemon
   ```

2. **Set up virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install coverage pytest pytest-cov  # For testing
   ```

4. **Create test configuration**:
   ```bash
   cp config.json.example config.json
   # Edit config.json with your test Nextcloud server details
   ```

## Testing

### Test Suite Overview

The project includes comprehensive unit tests covering:

- **NextcloudUploader**: Server communication, file uploads, error handling
- **FileProcessor**: Event processing, state management, timing logic
- **FileWatcher**: File system event handling
- **Configuration**: JSON loading, validation, error cases
- **Integration**: Component interaction testing

### Running Tests

#### Basic Test Execution

```bash
# Run all tests
./test_runner.sh

# Run tests with verbose output
./test_runner.sh --verbose

# Run specific test pattern
./test_runner.sh --pattern "test_config*"
```

#### Coverage Analysis

```bash
# Run tests with coverage analysis
./test_runner.sh --coverage

# View detailed coverage report
open htmlcov/index.html  # Opens coverage report in browser
```

#### Alternative Test Execution

You can also run tests directly with Python:

```bash
# Using unittest
python -m unittest discover -s tests -v

# Using pytest (if installed)
pytest tests/ -v

# With coverage
pytest tests/ --cov=nextcloud_upload_daemon --cov-report=html
```

### Test Structure

Tests are organized by component:

- `TestNextcloudUploader`: Tests for Nextcloud server interaction
- `TestFileProcessor`: Tests for file processing logic
- `TestFileWatcher`: Tests for file system monitoring
- `TestConfigLoading`: Tests for configuration management
- `TestLoggingSetup`: Tests for logging initialization
- `TestIntegration`: Integration tests for component interaction

### Mocking Strategy

Tests use extensive mocking to:
- Avoid real network requests to Nextcloud servers
- Simulate file system operations without actual file creation
- Control timing for deterministic test execution
- Test error conditions safely

### System Tests

System tests provide end-to-end validation using a real Nextcloud instance:

```bash
# Run system tests (requires Docker)
./run_system_tests.sh

# Or run manually with existing Nextcloud
python system_tests.py -v
```

**System Test Features:**
- Real Nextcloud server integration using Docker
- File upload and modification testing
- Conflict resolution verification
- Authentication and WebDAV protocol testing
- Daemon lifecycle and error handling validation
- Multi-file upload scenarios

**System Test Requirements:**
- Docker and Docker Compose installed
- Available ports 8080 (Nextcloud) and 3306 (MySQL)
- At least 2GB RAM for Docker containers
- Internet connection for downloading Docker images

**System Test Architecture:**
- `docker-compose.test.yml`: Nextcloud + MySQL test environment
- `system_tests.py`: Comprehensive integration test suite
- `run_system_tests.sh`: Automated test runner with Docker orchestration

The system tests create a complete Nextcloud environment and validate:
- WebDAV connectivity and authentication
- File upload operations
- File modification and updates
- Conflict resolution with duplicate filenames
- Large file handling
- Directory and folder management

## Code Quality Standards

### Code Style

- Follow PEP 8 Python style guidelines
- Use descriptive variable and function names
- Include comprehensive docstrings for all classes and functions
- Comment complex logic and business rules

### Documentation Requirements

- All public methods must have docstrings
- Complex algorithms should include inline comments
- Update this developer documentation for architectural changes
- Maintain user documentation in README.md

### Error Handling

- Use appropriate exception types
- Log errors with sufficient context
- Provide user-friendly error messages
- Avoid silent failures

## Debugging

### Logging Configuration

The daemon uses Python's logging module with syslog integration:

```python
import logging
logging.basicConfig(level=logging.DEBUG)  # For development
```

### Common Debugging Scenarios

1. **Connection Issues**:
   - Verify server URL and credentials
   - Check network connectivity
   - Test with curl or similar tools

2. **File Processing Issues**:
   - Enable debug logging
   - Check file permissions
   - Verify directory paths in configuration

3. **Timing Issues**:
   - Adjust upload/delete delays for testing
   - Use shorter delays during development
   - Monitor file state changes

### Development Testing

For development testing, create a test configuration with:
- Shorter timing delays (1-2 seconds)
- Test directories with appropriate permissions
- Development Nextcloud server or mock server

## Contributing

### Workflow

1. **Fork the repository** on GitHub
2. **Create a feature branch** for your changes
3. **Write tests** for new functionality
4. **Ensure all tests pass** before submitting
5. **Update documentation** as needed
6. **Submit a pull request** with clear description

### Commit Guidelines

- Use descriptive commit messages
- Follow the existing commit message format
- Include German prompt text in commits (per project requirements)
- Reference issue numbers where applicable

### Testing Requirements

- All new features must include unit tests
- Maintain or improve test coverage
- Ensure tests pass on multiple Python versions
- Test edge cases and error conditions

## Architecture Decisions

### Design Principles

1. **Modularity**: Components are loosely coupled and independently testable
2. **Configurability**: Behavior can be customized without code changes
3. **Reliability**: Robust error handling and recovery mechanisms
4. **Performance**: Efficient file monitoring and minimal resource usage
5. **Security**: Secure credential handling and safe file operations

### Technology Choices

- **Python**: Chosen for rapid development and excellent library ecosystem
- **Watchdog**: Robust cross-platform file system monitoring
- **Requests**: Reliable HTTP client for WebDAV communication
- **Syslog**: Standard logging for system integration
- **JSON**: Human-readable configuration format

### Future Considerations

- **Scalability**: Current design handles moderate file volumes
- **Extensibility**: Plugin architecture for additional cloud providers
- **Monitoring**: Enhanced metrics and health checking
- **Security**: OAuth2 authentication support

## Troubleshooting

### Common Development Issues

1. **Import Errors**:
   - Ensure virtual environment is activated
   - Verify all dependencies are installed
   - Check Python path configuration

2. **Test Failures**:
   - Clear any cached bytecode files
   - Ensure test isolation (no shared state)
   - Check for timing-dependent test issues

3. **Configuration Issues**:
   - Validate JSON syntax
   - Check file permissions
   - Verify all required fields are present

### Performance Considerations

- **Memory Usage**: Monitor file state dictionary growth
- **CPU Usage**: Consider file system event frequency
- **Network Usage**: Optimize upload batch operations
- **Disk Usage**: Monitor temporary file creation

## Security Considerations

### Credential Management

- Configuration files should have restricted permissions (600)
- Consider using environment variables for sensitive data
- Implement credential rotation procedures
- Use app passwords instead of primary passwords

### File Operations

- Validate file paths to prevent directory traversal
- Implement proper file locking for concurrent access
- Clean up temporary files promptly
- Monitor disk space usage

### Network Security

- Always use HTTPS for Nextcloud communication
- Validate SSL certificates
- Implement proper timeout handling
- Consider rate limiting for upload operations

## Continuous Integration and Deployment (CI/CD)

### GitHub Actions Workflows

The project uses GitHub Actions for automated testing and quality assurance. The CI/CD pipeline includes:

#### Test Workflow (`.github/workflows/test.yml`)

**Test Matrix**:
- **Operating Systems**: Ubuntu Latest, Windows Latest, macOS Latest
- **Python Versions**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Coverage**: Automated coverage reporting via Codecov

**Test Jobs**:
- **Unit Tests**: Run on all OS/Python combinations
- **System Tests**: Run with real Nextcloud instance on Ubuntu
- **Code Quality**: Linting, formatting, and security checks

**Quality Checks**:
- **Linting**: flake8 for code style and syntax validation
- **Formatting**: black for consistent code formatting
- **Import Sorting**: isort for organized import statements
- **Security**: bandit for security vulnerability detection

**Workflow Triggers**:
- Push to `main` branch
- Pull requests targeting `main` branch

View the latest test results: [GitHub Actions](https://github.com/fermat2a/nextcloud_upload_daemon/actions)

#### Local Testing Before Commits

Before pushing changes, always run the complete test suite locally:

```bash
# Run all tests with coverage
./test_runner.sh

# Or run individual components
python -m pytest tests/ -v
python -m flake8 .
python -m black --check .
python -m isort --check-only .
python -m bandit -r . -x tests/
python -m safety check
```

#### Development Workflow

1. **Feature Development**:
   - Create feature branch from `develop`
   - Write code with corresponding tests
   - Run local tests to ensure they pass
   - Commit changes with meaningful messages

2. **Quality Assurance**:
   - GitHub Actions automatically runs full test suite
   - All tests must pass before merge approval
   - Code coverage reports are generated automatically
   - Security and style checks are enforced

3. **Merge Process**:
   - Pull request must pass all CI checks
   - Code review by maintainers
   - Merge to `develop` for integration testing
   - Release to `main` for production deployment

#### CI/CD Configuration

**Required Dependencies** (automatically installed in CI):
```
pytest>=7.0.0       # Test framework
pytest-cov>=4.0.0   # Coverage plugin
coverage>=7.0.0     # Coverage measurement
flake8>=6.0.0       # Code linting
black>=23.0.0       # Code formatting
isort>=5.12.0       # Import sorting
bandit>=1.7.0       # Security analysis
safety>=2.3.0       # Dependency security check
```

**Environment Variables** (for local development):
- `CODECOV_TOKEN`: For coverage reporting (optional)
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions

#### Troubleshooting CI Issues

**Common CI Failures**:
1. **Test Failures**: Check test output in GitHub Actions logs
2. **Linting Errors**: Run `flake8 .` locally to identify issues
3. **Formatting Issues**: Run `black .` to auto-format code
4. **Import Order**: Run `isort .` to fix import sorting
5. **Security Issues**: Review bandit output for security concerns

**Performance Monitoring**:
- CI run times are monitored across different OS/Python combinations
- Coverage trends are tracked over time
- Security vulnerability reports are generated automatically

---

*This documentation is maintained as part of the Nextcloud Upload Daemon project. For questions or suggestions, please open an issue on the project repository.*