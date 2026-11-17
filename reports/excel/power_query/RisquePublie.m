let
    Source = Csv.Document(File.Contents("{{ProjectRoot}}/data/07_risk/risk_by_strategy.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"strategy", type text}, {"months", Int64.Type}, {"window_start", type text}, {"window_end", type text}, {"annualized_volatility", type number}, {"var_95", type number}, {"expected_shortfall_95", type number}})
in
    Typed
