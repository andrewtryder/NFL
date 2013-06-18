DROP TABLE IF EXISTS `players`;
-- -----------------------------------------------------
-- Table `players`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `players` (
    `eid` INTEGER PRIMARY KEY NOT NULL,
    `rid` INTEGER,
    `fullname` TEXT NOT NULL,
    `firstname` TEXT NOT NULL,
    `lastname` TEXT NOT NULL,
    `fndm1` TEXT,
    `fndm2` TEXT,
    `lndm1` TEXT,
    `lndm2` TEXT
);

DROP TABLE IF EXISTS `aliases`;
-- -----------------------------------------------------
-- Table `aliases`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `aliases` (
    `id` INTEGER,
    `name` TEXT PRIMARY KEY,
    FOREIGN KEY(id) REFERENCES players(eid) ON DELETE NO ACTION ON UPDATE NO ACTION
);
