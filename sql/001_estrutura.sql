-- =====================================================================
-- Estrutura do banco etl_tasy
--
-- Pré-requisitos (feitos uma vez, conectado ao banco "postgres"):
--   CREATE ROLE etl_user WITH LOGIN PASSWORD '...';   -- senha fica fora do repositório
--   CREATE DATABASE etl_tasy OWNER etl_user ENCODING 'UTF8' TEMPLATE template0;
--
-- Como rodar: pgAdmin → Query Tool NO BANCO etl_tasy → F5
-- =====================================================================

SET ROLE etl_user;

-- Para recriar do zero (APAGA todas as cargas), descomente as duas linhas:
DROP SCHEMA IF EXISTS raw CASCADE;
DROP SCHEMA IF EXISTS etl CASCADE;

ALTER DATABASE etl_tasy SET timezone TO 'America/Sao_Paulo';

CREATE SCHEMA etl;   -- controle do processo (metadados)
CREATE SCHEMA raw;   -- dados brutos, como vieram da planilha


-- Uma linha por arquivo importado. load_id = versão da carga.
CREATE TABLE etl.controle_cargas (
    load_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome_arquivo  TEXT        NOT NULL,
    hash_arquivo  CHAR(64)    NOT NULL UNIQUE,   -- impede carregar o mesmo arquivo duas vezes
    data_envio    TIMESTAMP   NOT NULL,          -- quando o e-mail foi enviado
    qtd_linhas    INTEGER,
    carregado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- Os dados. Cada linha aponta para a carga (load_id) de onde veio.
CREATE TABLE raw.base_tasy (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    load_id                 BIGINT NOT NULL REFERENCES etl.controle_cargas (load_id),

    nr_conta                BIGINT NOT NULL,
    ds_setor_atendimento    TEXT,
    nr_atendimento          BIGINT NOT NULL,
    cd_doc_convenio         TEXT,
    nm_medico               TEXT,
    ds_etapa                TEXT,
    dt_etapa                TIMESTAMP,
    ds_observacao_etapa     TEXT,
    ds_tipo_obs_conta       TEXT,
    ds_observacao_conta     TEXT,
    nm_convenio             TEXT,
    ds_classificacao        TEXT,
    ds_status               TEXT,
    ie_conta_enviada        TEXT,
    dt_entrada              TIMESTAMP,
    nr_prontuario           BIGINT,
    nm_paciente             TEXT,
    nm_estab_atendimento    TEXT,
    dt_entrega              TIMESTAMP,
    ds_status_protocolo     TEXT,
    vl_conta                NUMERIC(14,2),
    dt_titulo               TIMESTAMP,
    nr_titulo               BIGINT,
    nr_protocolo            BIGINT,
    ds_protocolo            TEXT,
    nr_guia                 TEXT,
    cd_senha                TEXT,
    cd_usuario_convenio     TEXT,
    ds_plano                TEXT,
    ds_categoria            TEXT,
    nm_estab_conta          TEXT,
    ds_status_2             TEXT,   -- 2ª coluna "Status" da planilha (renomear quando souber o que é)
    dt_nf                   TIMESTAMP,
    nm_usuario_etapa        TEXT,
    nr_protocolo_documento  BIGINT
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
