# nextcloud_upload_daemon

This project shall upload all data stored in a local directory to a nextcloud instance.
Therefore it shall watch the local directory for new files.
When a new file appears it shall wait until the file was not changed for a given amount of time and then upload the file to nextcloud.
Thereafter it shall remove the file from the local directory.

My personal use case: I have a scanner, that can upload scans to my local file server but not to nextcloud.
Therefore I want the scanner to store the files on the file server.
Thereafter the file server shall upload the data to nextcloud and clean up.

I think this can be solved by nextcloud command line client and some scripting.
But I need a project to learn programming in rust, so I choosed to implement this a daemon.

Currently the coding is not done, and the code does nothing.
