<?php
// Custom Nextcloud configuration for testing
// Disable rate limiting and brute force protection

$CONFIG = array(
  'auth.bruteforce.protection.enabled' => false,
  'ratelimit.protection.enabled' => false,
  'auth.webauthn.enabled' => false,
  'security.bruteForceProtection.enabled' => false,
  'security.rateLimiting.enabled' => false,
  'trusted_domains' => array(
    0 => 'localhost',
    1 => 'localhost:8080',
  ),
  'datadirectory' => '/var/www/html/data',
  'dbtype' => 'mysql',
  'dbname' => 'nextcloud',
  'dbhost' => 'nextcloud-db',
  'dbuser' => 'nextcloud',
  'dbpassword' => 'nextcloud',
  'debug' => false,
  'log_type' => 'file',
  'logfile' => '/var/log/nextcloud.log',
  'loglevel' => 1,
);