let
    Source = Csv.Document(File.Contents("{{ProjectRoot}}/data/04_portfolios/portfolio_metrics.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"strategy", type text}, {"names", Int64.Type}, {"months", Int64.Type}, {"window_start", type text}, {"window_end", type text}, {"annualized_return", type number}, {"annualized_volatility", type number}, {"sharpe_ratio", type number}, {"maximum_drawdown", type number}, {"maximum_weight", type number}, {"effective_holdings", type number}, {"risk_free_series", type text}, {"risk_free_currency", type text}})
in
    Typed
