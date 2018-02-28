DROP TABLE IF EXISTS cards;
DROP TABLE IF EXISTS atms;

create table cards (
    account_name    text        NOT NULL CHECK (LENGTH(account_name) <= 1024), 
    card_id         text        NOT NULL CHECK (LENGTH(card_id) == 36),
    balance         integer     NOT NULL DEFAULT (0) CHECK (balance >= 0), 

    nonce           integer     CHECK (LENGTH(nonce) == 32), 
    used            integer     NOT NULL DEFAULT (1), 
    timestamp       timestamp   NOT NULL DEFAULT (DATETIME('now','localtime')), 

    pk              integer     DEFAULT NULL CHECK (LENGTH(pk) == 32), 

    primary key (account_name, card_id)
);

CREATE TABLE atms (
    hsm_id          text        PRIMARY KEY, 

    hsm_key         blob        NOT NULL CHECK (LENGTH(hsm_key) == 32),
    num_bills       integer     NOT NULL CHECK (num_bills >= 0)
);