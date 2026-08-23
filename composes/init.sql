CREATE TABLE measurements (
    hash_id     VARCHAR(64)  PRIMARY KEY,
    gruppo      VARCHAR(255) NOT NULL,
    progetto    VARCHAR(255) NOT NULL,
    data        TIMESTAMPTZ  NOT NULL,
    esito_sast  VARCHAR(2)   NOT NULL CHECK (esito_sast IN ('OK', 'KO')),
    esito_sca   VARCHAR(2)   NOT NULL CHECK (esito_sca IN ('OK', 'KO'))
);


INSERT INTO measurements
    (hash_id, gruppo, progetto, data, esito_sast, esito_sca)
SELECT
    md5(p.progetto || i::text || clock_timestamp()::text),
    p.gruppo,
    p.progetto,
    NOW() - (i || ' days')::interval,
    CASE
        WHEN random() < 0.85 THEN 'OK'
        ELSE 'KO'
    END,
    CASE
        WHEN random() < 0.80 THEN 'OK'
        ELSE 'KO'
    END
FROM (
    VALUES
        ('ConsoleFusione', 'pl-consolefusione'),
        ('BigliettoDigitale', 'pl-bigliettodigitale'),
        ('Pagamenti', 'pl-pagamenti'),
        ('Anagrafe', 'pl-anagrafe'),
        ('Autenticazione', 'pl-autenticazione'),
        ('Gestionale', 'pl-gestionale')
) AS p(gruppo, progetto)
CROSS JOIN generate_series(0, 99) AS i;