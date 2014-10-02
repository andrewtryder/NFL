DROP TABLE IF EXISTS `nflplayeralias`;
-- -----------------------------------------------------
-- Table `nflplayeralias`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `nflplayeralias` (
    `alias` TEXT PRIMARY KEY,
    `name` TEXT
);

/* NFL PLAYER ALIASES */
INSERT INTO nflplayeralias (alias, name) VALUES ('rgknee', 'robert griffin iii');
