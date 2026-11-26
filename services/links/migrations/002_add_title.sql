-- Adds a title to every link. Existing rows keep all their data and get
-- their URL's host name as title, which is also the default for new links.
ALTER TABLE links ADD title NVARCHAR(255) NULL;
GO

UPDATE links
SET title = LEFT(
    SUBSTRING(url, CHARINDEX('//', url) + 2,
              CHARINDEX('/', url + '/', CHARINDEX('//', url) + 2) - CHARINDEX('//', url) - 2),
    255)
WHERE title IS NULL;
GO

ALTER TABLE links ALTER COLUMN title NVARCHAR(255) NOT NULL;
