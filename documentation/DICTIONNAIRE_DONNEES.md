# Dictionnaire de données

Généré automatiquement, à relire avant diffusion.

Ce dictionnaire est réécrit par `python -m src.reporting.data_dictionary`. Il décrit les colonnes. Il ne commente pas un résultat.

Les rapports de société utilisés pour l'éligibilité restent hors du dépôt.

## Données brutes

### `data/01_raw/fx/fx_rates.csv`

Lignes : 7578.

| Colonne |
|---|
| `cube_id` |
| `series_key` |
| `frequency` |
| `scale` |
| `unit` |
| `header_dim_1` |
| `header_item_1` |
| `header_dim_2` |
| `header_item_2` |
| `value_position` |
| `date` |
| `value` |

### `data/01_raw/macro/saron.csv`

Lignes : 214.

| Colonne |
|---|
| `cube_id` |
| `series_key` |
| `frequency` |
| `scale` |
| `unit` |
| `header_dim_1` |
| `header_item_1` |
| `value_position` |
| `date` |
| `value` |

### `data/01_raw/market/market_prices.csv`

Lignes : 650807.

| Colonne |
|---|
| `input_position` |
| `input_index` |
| `configured_symbol` |
| `resolved_symbol` |
| `symbol_resolution_status` |
| `symbol` |
| `timestamp` |
| `open` |
| `high` |
| `low` |
| `close` |
| `adj_close` |
| `volume` |
| `dividends` |
| `stock_splits` |

### `data/01_raw/odd/odd_assessment.csv`

Lignes : 120.

| Colonne |
|---|
| `Ticker` |
| `Exchange` |
| `Company` |
| `SDG` |
| `Activity` |
| `Positive Contribution` |
| `Negative Contribution` |
| `Evidence` |
| `Source` |
| `Controversy` |
| `Status` |
| `Positive` |

## Univers

### `data/03_universe/eligible/chf_portfolio_universe.csv`

Lignes : 120.

| Colonne |
|---|
| `ticker` |
| `name` |
| `exchange` |
| `listing_currency` |
| `yahoo_symbol` |
| `chf_status` |
| `exclusion_reason` |
| `clean_price_rows` |

## Portefeuilles

### `data/04_portfolios/portfolio_comparison.csv`

Lignes : 6.

| Colonne |
|---|
| `metric` |
| `equal_weight` |
| `minimum_volatility` |
| `maximum_sharpe` |
| `minimum_volatility_minus_equal_weight` |
| `maximum_sharpe_minus_equal_weight` |

### `data/04_portfolios/portfolio_membership.csv`

Lignes : 120.

| Colonne |
|---|
| `yahoo_symbol` |
| `ticker` |
| `name` |
| `exchange` |
| `listing_currency` |
| `history_decision` |
| `history_reason` |
| `odd_status` |
| `decision` |
| `reason` |
| `available_price_months` |
| `required_price_months` |

### `data/04_portfolios/portfolio_metrics.csv`

Lignes : 3.

| Colonne |
|---|
| `strategy` |
| `names` |
| `months` |
| `window_start` |
| `window_end` |
| `annualized_return` |
| `annualized_volatility` |
| `sharpe_ratio` |
| `maximum_drawdown` |
| `maximum_weight` |
| `effective_holdings` |
| `risk_free_series` |
| `risk_free_currency` |

### `data/04_portfolios/portfolio_monthly_returns.csv`

Lignes : 360.

| Colonne |
|---|
| `month` |
| `strategy` |
| `portfolio_return` |
| `risk_free_return` |
| `excess_return` |

### `data/04_portfolios/portfolio_weights.csv`

Lignes : 10440.

| Colonne |
|---|
| `strategy` |
| `month` |
| `yahoo_symbol` |
| `ticker` |
| `name` |
| `listing_currency` |
| `weight` |

## Suivi

### `data/05_monitoring/allocation_by_holding.csv`

Lignes : 87.

| Colonne |
|---|
| `strategy` |
| `yahoo_symbol` |
| `ticker` |
| `name` |
| `listing_currency` |
| `weight` |
| `sector` |
| `country` |
| `zone` |
| `asset_class` |
| `exposure` |

### `data/05_monitoring/allocation_by_sector.csv`

Lignes : 22.

| Colonne |
|---|
| `strategy` |
| `sector` |
| `weight` |
| `names` |

### `data/05_monitoring/allocation_by_zone.csv`

Lignes : 12.

| Colonne |
|---|
| `strategy` |
| `zone` |
| `weight` |
| `names` |

### `data/05_monitoring/concentration.csv`

Lignes : 3.

| Colonne |
|---|
| `strategy` |
| `window_start` |
| `window_end` |
| `names` |
| `invested_names` |
| `maximum_weight` |
| `top_10_weight` |
| `hhi` |
| `effective_holdings` |
| `concentration_multiple` |

### `data/05_monitoring/concentration_history.csv`

Lignes : 360.

| Colonne |
|---|
| `month` |
| `strategy` |
| `names` |
| `invested_names` |
| `maximum_weight` |
| `top_10_weight` |
| `hhi` |
| `effective_holdings` |
| `concentration_multiple` |

### `data/05_monitoring/exposure.csv`

Lignes : 34.

| Colonne |
|---|
| `strategy` |
| `exposure` |
| `weight` |
| `names` |

### `data/05_monitoring/holding_contribution.csv`

Lignes : 10440.

| Colonne |
|---|
| `month` |
| `strategy` |
| `yahoo_symbol` |
| `name` |
| `sector` |
| `weight` |
| `asset_return` |
| `month_contribution` |
| `cumulative_contribution` |

### `data/05_monitoring/limit_watch.csv`

Lignes : 360.

| Colonne |
|---|
| `month` |
| `strategy` |
| `largest_issuer` |
| `largest_issuer_weight` |
| `largest_sector` |
| `largest_sector_weight` |
| `largest_zone` |
| `largest_zone_weight` |
| `largest_currency` |
| `largest_currency_weight` |
| `issuer_over_cap` |
| `sector_over_cap` |
| `zone_over_cap` |
| `currency_over_cap` |
| `invested_names` |
| `positions_outside_band` |

### `data/05_monitoring/monthly_report.csv`

Lignes : 3.

| Colonne |
|---|
| `strategy` |
| `report_month` |
| `window_start` |
| `window_end` |
| `names` |
| `invested_names` |
| `maximum_weight` |
| `top_10_weight` |
| `hhi` |
| `effective_holdings` |
| `concentration_multiple` |
| `largest_sector` |
| `largest_sector_weight` |
| `largest_zone` |
| `largest_zone_weight` |
| `largest_currency` |
| `largest_currency_weight` |

### `data/05_monitoring/portfolio_path.csv`

Lignes : 480.

| Colonne |
|---|
| `month` |
| `strategy` |
| `portfolio_return` |
| `cumulative_wealth` |
| `drawdown` |

### `data/05_monitoring/sector_contribution.csv`

Lignes : 2880.

| Colonne |
|---|
| `month` |
| `strategy` |
| `sector` |
| `month_contribution` |
| `cumulative_contribution` |

### `data/05_monitoring/top10_positions.csv`

Lignes : 30.

| Colonne |
|---|
| `strategy` |
| `rank` |
| `yahoo_symbol` |
| `ticker` |
| `name` |
| `weight` |
| `sector` |
| `zone` |
| `exposure` |

### `data/05_monitoring/turnover.csv`

Lignes : 120.

| Colonne |
|---|
| `month` |
| `strategy` |
| `gross_turnover` |
| `over_quarterly_cap` |
| `trailing_annual_turnover` |
| `over_annual_cap` |

### `data/05_monitoring/weight_changes.csv`

Lignes : 1321.

| Colonne |
|---|
| `month` |
| `strategy` |
| `yahoo_symbol` |
| `name` |
| `weight_before` |
| `weight_after` |
| `weight_change` |

## Performance

### `data/06_performance/active_return.csv`

Lignes : 480.

| Colonne |
|---|
| `month` |
| `strategy` |
| `portfolio_return` |
| `benchmark_return_chf` |
| `active_return` |
| `excess_return` |

### `data/06_performance/benchmark_monthly_return.csv`

Lignes : 120.

| Colonne |
|---|
| `month` |
| `fund_name` |
| `fund_currency` |
| `nav_total_return` |
| `chf_per_unit` |
| `prior_chf_per_unit` |
| `benchmark_return_chf` |

### `data/06_performance/drawdown_episode.csv`

Lignes : 3.

| Colonne |
|---|
| `strategy` |
| `peak_month` |
| `trough_month` |
| `maximum_drawdown` |
| `recovered_month` |

### `data/06_performance/performance_metrics.csv`

Lignes : 4.

| Colonne |
|---|
| `strategy` |
| `months` |
| `window_start` |
| `window_end` |
| `annualized_return` |
| `annualized_volatility` |
| `sharpe_ratio` |
| `sortino_ratio` |
| `maximum_drawdown` |
| `tracking_error` |
| `information_ratio` |
| `months_below_risk_free` |
| `reference` |

## Risque

### `data/07_risk/correlation_matrix.csv`

Lignes : 29.

| Colonne |
|---|
| `symbol` |
| `002129.SZ` |
| `0916.HK` |
| `1044.HK` |
| `3898.HK` |
| `4507.T` |
| `4523.T` |
| `4568.T` |
| `8951.T` |
| `9022.T` |
| `ALNY` |
| `BMY` |
| `C38U.SI` |
| `COV.PA` |
| `DEMANT.CO` |
| `DLR` |
| `EQIX` |
| `GFC.PA` |
| `GMAB.CO` |
| `LAND.L` |
| `NRP.JO` |
| `PSON.L` |
| `REC.MI` |
| `SALM.OL` |
| `SCA-B.ST` |
| `SOBI.ST` |
| `SOON.SW` |
| `SPSN.SW` |
| `SUI` |
| `VWS.CO` |

### `data/07_risk/risk_by_strategy.csv`

Lignes : 4.

| Colonne |
|---|
| `strategy` |
| `months` |
| `window_start` |
| `window_end` |
| `annualized_volatility` |
| `var_95` |
| `expected_shortfall_95` |

### `data/07_risk/universe_correlation.csv`

Lignes : 1.

| Colonne |
|---|
| `names` |
| `average_correlation` |
| `months` |

### `data/07_risk/var_tail.csv`

Lignes : 24.

| Colonne |
|---|
| `strategy` |
| `rank` |
| `month` |
| `portfolio_return` |

## Résistance

### `data/08_stress/stress_paths.csv`

Lignes : 1800.

| Colonne |
|---|
| `strategy` |
| `shock` |
| `month` |
| `portfolio_return` |
| `risk_free_return` |
| `cumulative_wealth` |
| `drawdown` |

### `data/08_stress/stress_results.csv`

Lignes : 15.

| Colonne |
|---|
| `strategy` |
| `shock` |
| `months` |
| `window_start` |
| `window_end` |
| `terminal_wealth` |
| `maximum_drawdown` |
| `annualized_volatility` |
| `sharpe_ratio` |

## Base SQLite

Fichier local `database/sdg_investment.db`. Tables : 19.

### `acquisition_log`

Lignes : 130.

| Colonne |
|---|
| `run_id` |
| `execution_date` |
| `process_type` |
| `output_file` |
| `storage_location` |
| `status` |
| `records_produced` |
| `notes` |
| `created_at` |

### `benchmark_distributions`

Lignes : 21.

| Colonne |
|---|
| `record_date` |
| `ex_date` |
| `payable_date` |
| `total_distribution` |
| `income` |
| `st_cap_gains` |
| `lt_cap_gains` |
| `return_of_capital` |

### `benchmark_historical`

Lignes : 2659.

| Colonne |
|---|
| `as_of` |
| `nav_per_share` |
| `ex_dividends` |
| `shares_outstanding` |
| `non_fv_nav` |

### `benchmark_holdings`

Lignes : 151.

| Colonne |
|---|
| `ticker` |
| `name` |
| `sector` |
| `asset_class` |
| `market_value` |
| `weight` |
| `notional_value` |
| `quantity` |
| `price` |
| `location` |
| `exchange` |
| `currency` |
| `fx_rate` |
| `accrual_date` |

### `benchmark_performance`

Lignes : 127.

| Colonne |
|---|
| `month_end_date` |
| `monthly_total_nav_return` |

### `dataset_registry`

Lignes : 7.

| Colonne |
|---|
| `dataset_id` |
| `source_id` |
| `dataset_name` |
| `output_file_name` |
| `table_name` |
| `load_enabled` |
| `quality_enabled` |
| `chronology_enabled` |
| `active` |
| `output_file` |
| `storage_location` |
| `last_acquisition_date` |
| `last_acquisition_status` |
| `records_loaded` |
| `last_database_load_date` |
| `database_name` |
| `table_available` |
| `created_at` |
| `updated_at` |

### `fx_rates`

Lignes : 7578.

| Colonne |
|---|
| `cube_id` |
| `series_key` |
| `frequency` |
| `scale` |
| `unit` |
| `header_dim_1` |
| `header_item_1` |
| `header_dim_2` |
| `header_item_2` |
| `value_position` |
| `date` |
| `value` |

### `market_prices`

Lignes : 650807.

| Colonne |
|---|
| `input_position` |
| `input_index` |
| `configured_symbol` |
| `resolved_symbol` |
| `symbol_resolution_status` |
| `symbol` |
| `timestamp` |
| `open` |
| `high` |
| `low` |
| `close` |
| `adj_close` |
| `volume` |
| `dividends` |
| `stock_splits` |

### `odd_assessment`

Lignes : 120.

| Colonne |
|---|
| `ticker` |
| `exchange` |
| `company` |
| `sdg` |
| `activity` |
| `positive_contribution` |
| `negative_contribution` |
| `evidence` |
| `source` |
| `controversy` |
| `status` |
| `positive` |

### `published_contributions`

Lignes : 10440.

| Colonne |
|---|
| `month` |
| `strategy` |
| `yahoo_symbol` |
| `name` |
| `sector` |
| `weight` |
| `asset_return` |
| `month_contribution` |
| `cumulative_contribution` |

### `published_returns`

Lignes : 360.

| Colonne |
|---|
| `month` |
| `strategy` |
| `portfolio_return` |
| `risk_free_return` |
| `excess_return` |

### `published_weights`

Lignes : 10440.

| Colonne |
|---|
| `strategy` |
| `month` |
| `yahoo_symbol` |
| `ticker` |
| `name` |
| `listing_currency` |
| `weight` |

### `quality_control_result`

Lignes : 684.

| Colonne |
|---|
| `run_id` |
| `dataset_id` |
| `source_id` |
| `table_name` |
| `control_id` |
| `control_name` |
| `status` |
| `issues` |
| `records_checked` |
| `notes` |
| `execution_date` |
| `created_at` |

### `quality_metric_result`

Lignes : 612.

| Colonne |
|---|
| `run_id` |
| `dataset_id` |
| `source_id` |
| `table_name` |
| `metric_name` |
| `metric_value` |
| `metric_status` |
| `threshold` |
| `weight` |
| `applicable` |
| `records_checked` |
| `execution_date` |
| `created_at` |

### `quality_run`

Lignes : 20.

| Colonne |
|---|
| `run_id` |
| `execution_date` |
| `datasets_checked` |
| `records_checked` |
| `controls_executed` |
| `issues_detected` |
| `global_quality_score` |
| `global_quality_grade` |
| `global_status` |
| `notes` |
| `created_at` |

### `saron`

Lignes : 214.

| Colonne |
|---|
| `cube_id` |
| `series_key` |
| `frequency` |
| `scale` |
| `unit` |
| `header_dim_1` |
| `header_item_1` |
| `value_position` |
| `date` |
| `value` |

### `schema_migrations`

Lignes : 3.

| Colonne |
|---|
| `version` |
| `description` |
| `applied_at` |

### `securities_master`

Lignes : 120.

| Colonne |
|---|
| `ticker` |
| `name` |
| `location` |
| `exchange` |
| `currency` |
| `listing_currency` |
| `asset_class` |
| `yahoo_symbol` |

### `security_candidates`

Lignes : 120.

| Colonne |
|---|
| `ticker` |
| `name` |
| `location` |
| `exchange` |
| `currency` |
| `asset_class` |

## Requêtes SQL

Les fichiers de `sql/` s'exécutent sur la base locale. Ils posent une question de contrôle. Ils ne publient pas un indicateur de portefeuille : ces indicateurs sont dans les fichiers des phases 5 à 9.

- `sql/01_dernier_controle_qualite.sql`
- `sql/02_controles_a_relire.sql`
- `sql/03_registre_des_jeux.sql`
- `sql/04_saron_recent.sql`
- `sql/05_positions_du_fonds.sql`
- `sql/06_couverture_change.sql`
- `sql/07_seances_a_ecarter.sql`
- `sql/08_fonds_contre_registre_odd.sql`
- `sql/09_fonds_sans_referentiel.sql`
- `sql/10_poids_des_livres.sql`
- `sql/11_contributeurs_par_titre.sql`
