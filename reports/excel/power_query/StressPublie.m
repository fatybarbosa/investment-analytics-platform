let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/08_stress/stress_results.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"strategy", type text}, {"shock", type text}, {"months", Int64.Type}, {"window_start", type text}, {"window_end", type text}, {"terminal_wealth", type number}, {"maximum_drawdown", type number}, {"annualized_volatility", type number}, {"sharpe_ratio", type number}})
in
    Typed
