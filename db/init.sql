-- Local and CI only: creates one database and one login per service.
-- Safe to run more than once. On Azure the databases and users are created
-- once during the initial setup (see README).
-- Variables come from sqlcmd: -v LINKS_PASSWORD=... ANALYTICS_PASSWORD=...

IF DB_ID('links') IS NULL CREATE DATABASE links;
GO
IF DB_ID('analytics') IS NULL CREATE DATABASE analytics;
GO

IF SUSER_ID('links_user') IS NULL CREATE LOGIN links_user WITH PASSWORD = '$(LINKS_PASSWORD)';
GO
IF SUSER_ID('analytics_user') IS NULL CREATE LOGIN analytics_user WITH PASSWORD = '$(ANALYTICS_PASSWORD)';
GO

-- Each login gets a user only in its own database, so it cannot read the other one.
USE links;
GO
IF USER_ID('links_user') IS NULL CREATE USER links_user FOR LOGIN links_user;
ALTER ROLE db_ddladmin ADD MEMBER links_user;
ALTER ROLE db_datareader ADD MEMBER links_user;
ALTER ROLE db_datawriter ADD MEMBER links_user;
GO

USE analytics;
GO
IF USER_ID('analytics_user') IS NULL CREATE USER analytics_user FOR LOGIN analytics_user;
ALTER ROLE db_ddladmin ADD MEMBER analytics_user;
ALTER ROLE db_datareader ADD MEMBER analytics_user;
ALTER ROLE db_datawriter ADD MEMBER analytics_user;
GO
