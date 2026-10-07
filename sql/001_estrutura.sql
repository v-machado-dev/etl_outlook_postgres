-- Estrutura do banco etl_tasy
--
-- Pré-requisitos (feitos uma vez, conectado ao banco "postgres"):
--   CREATE ROLE etl_user WITH LOGIN PASSWORD '...';   
--   CREATE DATABASE etl_tasy OWNER etl_user ENCODING 'UTF8' TEMPLATE template0;

-- Como rodar: pgAdmin -> Query Tool NO BANCO etl_tasy -> F5

SET ROLE etl_user;

-- Para recriar do zero (APAGA todas as cargas), descomente as duas linhas:
-- DROP SCHEMA IF EXISTS raw CASCADE;
-- DROP SCHEMA IF EXISTS etl CASCADE;

ALTER DATABASE etl_tasy SET timezone TO 'America/Sao_Paulo';

CREATE SCHEMA etl;   -- controle do processo (metadados)
CREATE SCHEMA raw;   -- dados brutos


-- Tabela para controle. load_id = PK : versão da carga.
CREATE TABLE etl.controle_cargas (
    load_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome_arquivo  TEXT        NOT NULL,
    hash_arquivo  CHAR(64)    NOT NULL UNIQUE,   -- proteção contra carregar o mesmo arquivo duas vezes
    data_envio    TIMESTAMP   NOT NULL,          -- quando o e-mail foi enviado
    qtd_linhas    INTEGER,
    carregado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- Tabela dos dados
CREATE TABLE raw.base_tasy (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    load_id                 BIGINT NOT NULL REFERENCES etl.controle_cargas (load_id),

    conta                TEXT,
    setor_atend          TEXT,
    atendimento          TEXT,
    doc_convenio         TEXT,
    medico               TEXT,
    etapa                TEXT,
    dt_etapa             TIMESTAMP,
    observacao_etapa     TEXT,
    tipo_obs_conta       TEXT,
    observacao_conta     TEXT,
    convenio             TEXT,
    classificacao        TEXT,
    status_1             TEXT,
    conta_enviada        TEXT,
    data_entrada         TIMESTAMP,
    prontuario           TEXT,
    paciente             TEXT,
    estab_atend          TEXT,
    data_entrega         TIMESTAMP,
    status_protocolo     TEXT,
    vl_conta             NUMERIC(14,2),
    data_titulo          TIMESTAMP,
    nr_titulo            TEXT,
    nr_protocolo         TEXT,
    desc_protocolo       TEXT,
    nr_guia              TEXT,
    senha                TEXT,
    usuario_convenio     TEXT,
    plano                TEXT,
    categoria            TEXT,
    estab_conta          TEXT,
    status_2             TEXT,  
    data_nf              TIMESTAMP,
    usuario_etapa        TEXT,
    nr_protocolo_documento  TEXT
);

CREATE INDEX ix_base_tasy_load_id ON raw.base_tasy (load_id);


-- Retrato mais recente: a carga do e-mail enviado por último
-- (usa data_envio, e não max(load_id), para continuar certa mesmo se
--  um arquivo antigo for carregado depois de um mais novo)
CREATE VIEW raw.vw_base_tasy_atual AS
SELECT b.*
FROM raw.base_tasy b
WHERE b.load_id = (
    SELECT load_id
    FROM etl.controle_cargas
    ORDER BY data_envio DESC, load_id DESC
    LIMIT 1
);
