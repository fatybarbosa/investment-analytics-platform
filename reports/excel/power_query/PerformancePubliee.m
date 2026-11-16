let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/06_performance/performance_metrics.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"strategy", type text}, {"months", Int64.Type}, {"window_start", type text}, {"window_end", type text}, {"annualized_return", type number}, {"annualized_volatility", type number}, {"sharpe_ratio", type number}, {"sortino_ratio", type number}, {"maximum_drawdown", type number}, {"tracking_error", type number}, {"information_ratio", type number}, {"months_below_risk_free", Int64.Type}, {"reference", type text}})
in
    Typed
