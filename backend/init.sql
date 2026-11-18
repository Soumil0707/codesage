-- Create database if not exists (Docker already does this, but just in case)
CREATE DATABASE IF NOT EXISTS codesage
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE codesage;

-- Grant privileges
GRANT ALL PRIVILEGES ON codesage.* TO 'codesage_user'@'%';
FLUSH PRIVILEGES;

