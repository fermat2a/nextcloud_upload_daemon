<?php
$CONFIG = array (
  'config_is_read_only' => true,
  'auth.bruteforce.protection.enabled' => false,
  'ratelimit.protection.enabled' => false,
  'auth.webauthn.enabled' => false,
  'security.bruteForceProtection.enabled' => false,
  'security.rateLimiting.enabled' => false,
  'htaccess.RewriteBase' => '/',
  'memcache.local' => '\\OC\\Memcache\\APCu',
  'apps_paths' => 
  array (
    0 => 
    array (
      'path' => '/var/www/html/apps',
      'url' => '/apps',
      'writable' => false,
    ),
    1 => 
    array (
      'path' => '/var/www/html/custom_apps',
      'url' => '/custom_apps',
      'writable' => true,
    ),
  ),
  'upgrade.disable-web' => true,
  'passwordsalt' => 'bdLvW9ebcXS/n7GRY3rcUt9ZwkVcTY',
  'secret' => 'yXeyiW70XIi4+enw8QgxFejAFYzdEIv6qOtRfxAFYyzEfkIn',
  'trusted_domains' => 
  array (
    0 => 'localhost',
    1 => 'localhost:8080',
  ),
  'datadirectory' => '/var/www/html/data',
  'dbtype' => 'mysql',
  'version' => '32.0.0.13',
  'overwrite.cli.url' => 'http://localhost',
  'dbname' => 'nextcloud',
  'dbhost' => 'nextcloud-db',
  'dbtableprefix' => 'oc_',
  'mysql.utf8mb4' => true,
  'dbuser' => 'nextcloud',
  'dbpassword' => 'nextcloud',
  'installed' => true,
  'instanceid' => 'ocsnaoirmhy3',
);
