CREATE TABLE clicks (
    id INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
    slug NVARCHAR(32) NOT NULL,
    referrer NVARCHAR(255) NULL,
    clicked_at DATETIME2 NOT NULL CONSTRAINT df_clicks_clicked_at DEFAULT SYSUTCDATETIME()
);
GO

CREATE INDEX ix_clicks_slug ON clicks (slug);
GO

CREATE TABLE health_check (
    id INT NOT NULL PRIMARY KEY,
    checked_at DATETIME2 NOT NULL
);
INSERT INTO health_check (id, checked_at) VALUES (1, SYSUTCDATETIME());
