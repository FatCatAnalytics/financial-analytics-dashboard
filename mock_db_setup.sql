-- Create schema and table structure to satisfy backend queries
CREATE SCHEMA IF NOT EXISTS cla_uat;

DROP TABLE IF EXISTS cla_uat.mv_t_cla_input_full_upd;
CREATE TABLE cla_uat.mv_t_cla_input_full_upd (
    "ProcessingDateKey" INTEGER NOT NULL,
    "CommitmentAmt" NUMERIC(18,2),
    "OutstandingAmt" NUMERIC(18,2),
    "Region" TEXT,
    "NAICSGrpName" TEXT,
    "CommitmentSizeGroup" TEXT,
    "RiskGroupDesc" TEXT,
    "LineofBusinessId" TEXT,
    "LineofBusiness" TEXT,
    "BankID" TEXT,
    "MaturityTermMonths" INTEGER,
    "SpreadBPS" NUMERIC(10,2),
    "YieldPct" NUMERIC(10,4)
);

-- Drop existing aggregated_analytics view or table if present
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_views 
    WHERE schemaname = 'public' AND viewname = 'aggregated_analytics'
  ) THEN
    EXECUTE 'DROP VIEW public.aggregated_analytics';
  ELSIF EXISTS (
    SELECT 1 FROM pg_tables 
    WHERE schemaname = 'public' AND tablename = 'aggregated_analytics'
  ) THEN
    EXECUTE 'DROP TABLE public.aggregated_analytics';
  END IF;
END $$;
CREATE TABLE public.aggregated_analytics (
    "ProcessingDateKey" INTEGER NOT NULL,
    "CommitmentAmt" NUMERIC(18,2),
    "Deals" INTEGER,
    "OutstandingAmt" NUMERIC(18,2),
    "ProcessingDateKeyPrior" INTEGER,
    "CommitmentAmtPrior" NUMERIC(18,2),
    "OutstandingAmtPrior" NUMERIC(18,2),
    "DealsPrior" INTEGER,
    "ca_diff" NUMERIC(10,6),
    "oa_diff" NUMERIC(10,6),
    "deals_diff" NUMERIC(10,6),
    "ca_model_diff" NUMERIC(10,6),
    "oa_model_diff" NUMERIC(10,6),
    "deals_model_diff" NUMERIC(10,6)
);

-- Seed minimal sample data (3 periods, 2 regions, 2 banks)
INSERT INTO cla_uat.mv_t_cla_input_full_upd (
  "ProcessingDateKey","CommitmentAmt","OutstandingAmt","Region","NAICSGrpName",
  "CommitmentSizeGroup","RiskGroupDesc","LineofBusinessId","LineofBusiness","BankID",
  "MaturityTermMonths","SpreadBPS","YieldPct"
) VALUES
  (20240131, 1000000, 800000, 'Rocky Mountain', 'Manufacturing', 'Small', 'Low', '11', 'Commercial', 'B001', 60, 250, 0.0450),
  (20240131, 500000,  450000, 'Pacific',        'Healthcare',    'Medium','Medium','12', 'SBA',        'B002', 84, 300, 0.0525),
  (20240229, 1200000, 900000, 'Rocky Mountain', 'Manufacturing', 'Small', 'Low',    '11', 'Commercial', 'B001', 60, 250, 0.0450),
  (20240229, 400000,  350000, 'Pacific',        'Healthcare',    'Medium','Medium','12', 'SBA',        'B002', 84, 300, 0.0525),
  (20240331, 1500000, 950000, 'Rocky Mountain', 'Manufacturing', 'Small', 'Low',    '11', 'Commercial', 'B001', 60, 250, 0.0450),
  (20240331, 450000,  380000, 'Pacific',        'Healthcare',    'Medium','Medium','12', 'SBA',        'B002', 84, 300, 0.0525);

-- Populate aggregated_analytics with simple rollups for the same periods
TRUNCATE public.aggregated_analytics;
WITH base AS (
  SELECT 
    "ProcessingDateKey",
    SUM("CommitmentAmt")::NUMERIC(18,2) AS "CommitmentAmt",
    COUNT(*)::INT AS "Deals",
    SUM("OutstandingAmt")::NUMERIC(18,2) AS "OutstandingAmt"
  FROM cla_uat.mv_t_cla_input_full_upd
  GROUP BY 1
  ORDER BY 1
), lagged AS (
  SELECT 
    b."ProcessingDateKey" AS "ProcessingDateKey",
    b."CommitmentAmt" AS "CommitmentAmt",
    b."Deals" AS "Deals",
    b."OutstandingAmt" AS "OutstandingAmt",
    LAG(b."ProcessingDateKey") OVER (ORDER BY b."ProcessingDateKey") AS "ProcessingDateKeyPrior",
    LAG(b."CommitmentAmt") OVER (ORDER BY b."ProcessingDateKey") AS "CommitmentAmtPrior",
    LAG(b."OutstandingAmt") OVER (ORDER BY b."ProcessingDateKey") AS "OutstandingAmtPrior",
    LAG(b."Deals") OVER (ORDER BY b."ProcessingDateKey") AS "DealsPrior"
  FROM base b
)
INSERT INTO public.aggregated_analytics (
  "ProcessingDateKey","CommitmentAmt","Deals","OutstandingAmt",
  "ProcessingDateKeyPrior","CommitmentAmtPrior","OutstandingAmtPrior","DealsPrior",
  "ca_diff","oa_diff","deals_diff","ca_model_diff","oa_model_diff","deals_model_diff"
)
SELECT
  l."ProcessingDateKey",
  l."CommitmentAmt",
  l."Deals",
  l."OutstandingAmt",
  COALESCE(l."ProcessingDateKeyPrior", 0),
  l."CommitmentAmtPrior",
  l."OutstandingAmtPrior",
  l."DealsPrior",
  CASE WHEN l."CommitmentAmtPrior" IS NULL OR l."CommitmentAmtPrior" = 0 THEN NULL
       ELSE (l."CommitmentAmt" / l."CommitmentAmtPrior") - 1 END,
  CASE WHEN l."OutstandingAmtPrior" IS NULL OR l."OutstandingAmtPrior" = 0 THEN NULL
       ELSE (l."OutstandingAmt" / l."OutstandingAmtPrior") - 1 END,
  CASE WHEN l."DealsPrior" IS NULL OR l."DealsPrior" = 0 THEN NULL
       ELSE (l."Deals"::NUMERIC / l."DealsPrior"::NUMERIC) - 1 END,
  NULL, NULL, NULL
FROM lagged l;

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_mv_processing_date ON cla_uat.mv_t_cla_input_full_upd ("ProcessingDateKey");
CREATE INDEX IF NOT EXISTS idx_mv_lob ON cla_uat.mv_t_cla_input_full_upd ("LineofBusinessId");
CREATE INDEX IF NOT EXISTS idx_mv_region ON cla_uat.mv_t_cla_input_full_upd ("Region");
CREATE INDEX IF NOT EXISTS idx_mv_naics ON cla_uat.mv_t_cla_input_full_upd ("NAICSGrpName");
CREATE INDEX IF NOT EXISTS idx_mv_bank ON cla_uat.mv_t_cla_input_full_upd ("BankID");


