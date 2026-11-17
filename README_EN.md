# Portfolio Construction, Monitoring & Risk Analytics Platform

English summary. The project documents, reports and comments are written in French; this page gives a reader of English the scope, the method and the limits. It repeats no result figure: the figures live in the deliverables, where an automated check reads each one back from its source file.

**Author:** Faty Barbosa. Individual training project.

## What it is

A reporting chain for a fictional discretionary equity mandate in Swiss francs, CLIENT001. From the client profile and the investment policy, it builds three hypothetical portfolios on public prices, monitors them against the written limits, measures performance and risk, applies four written shocks, and delivers the result as HTML pages, an Excel annex, a Power BI model, an executive PDF, a management deck, a client report and a manager report on the same books, and automated comments.

The three books are hypothetical portfolios built retrospectively on public data. They were never held. Prices, exchange rates and the SARON rate are real public data: iShares for the fund's holdings and published return, Yahoo Finance for prices, the Swiss National Bank for exchange rates and SARON. The eligibility register is written by hand from the companies' public reports.

There is no custody data: no real positions, no transactions, no fees, no cash flows. Every text says so.

## What a reporting team would look at

| Need | Where it is answered |
|---|---|
| Client requirement before the code | `documentation/00_mandat/` and `documentation/BESOIN_DE_REPORTING.md`: requirement, data, calculation, control, deliverable |
| CLIENT001 report and manager report | `reports/client/`, in French: CLIENT001 receives allocation and mandate limits; the manager receives lines, contributors and weight movements. Performance and risk stay in the executive report |
| Data quality | Six controls on every loaded table, recorded with their cause; `reports/executive/cas_d_investigation.md` for four investigated defects |
| Reconciliation | `reports/excel/`: Excel recomputes every indicator from the monthly returns without reading the Python result; Power BI values are read from the Desktop engine by DAX query; a gap above the tolerance stays open as an EXCEPTION with its cause |
| Automation | One command, `python -m src.pipeline.refresh`, that stops on a failed control; `documentation/AUTOMATISATION_AVANT_APRES.md` for the manual process it replaces |
| Excel | Power Query, structured tables, `XLOOKUP`, `INDEX`/`MATCH`, `SUMIFS`, pivot tables with slicers, sum and rebuild controls |
| SQL | A local SQLite database rebuilt by the pipeline and sixteen queries in `sql/`: controls, joins, window functions, and a recursive query that chains the wealth a third way |
| Python | `src/`, from acquisition to the reports |
| Reporting output | `reports/executive/rapport_executif.pdf`, `reports/management/presentation_management.pptx`, `reports/client/` |
| Automated comments | Sentences filled by written rules; every number is checked against its file and the pipeline fails otherwise |

## Rules the project keeps

- Every figure in a text comes from a pipeline file. A check reads the finished PDF, deck and Markdown back and fails on a number it cannot find.
- A tolerance is written before the comparison and never changed to make a control pass.
- A defect is recorded with its cause and left out of the series. Nothing is interpolated or corrected in silence.
- No personalised investment advice: findings and alerts tied to the written limits of the mandate only.
- Every generated text carries the label "generated automatically, to be reviewed before distribution".

## Limits

- The written sector limit of the IPS (20%) cannot be met by a fully invested long-only book on this list. The books are built with a 40% working cap that the client has not approved, and the reports show the breach of the written limit as an open exception.
- Between two quarterly decisions the weights drift with the market. A weight can pass a cap by drift alone (passive breach), and the turnover is measured against the drifted book. Where a cap and the turnover budget conflict at a trade date, the cap wins and the turnover is reported above its limit.
- Hypothetical books, no custody data, no fees, the books are measured as gross total returns (dividends reinvested through the adjusted close, before fees and withholding tax) while the comparison fund is net of its fees.
- The security list comes from the fund's current holdings: companies that left the fund are not in the history.
- Listed equities only. No private assets, bonds or derivatives.
- Identity of a security is ticker and exchange; no ISIN.
- Shocks are simple parameters applied to the book's monthly return, not to each security.

## Rebuild

Windows, Python 3.12, Excel installed for the annex recalculation, Power BI Desktop open for the measure export.

```bash
python -m src.pipeline.refresh
python -m pytest tests
```

Without Excel or Windows, `python -m src.pipeline.refresh --skip-office` rebuilds everything except the Excel annex and the reports that read it. The raw Yahoo Finance prices are not versioned; `data/input_manifest.json` keeps the SHA-256 of the raw inputs of the last run, so a different result can be traced to different inputs. CI (`.github/workflows/tests.yml`) runs the tests that need neither Excel nor the raw prices.

The tests read the published files of the repository, including the quality control center `audit/data_control_center.xlsx`. They pass on a fresh clone without running the pipeline. Excel must be installed: one test recalculates a workbook through COM.
