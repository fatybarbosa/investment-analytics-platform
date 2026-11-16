let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/05_monitoring/portfolio_path.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"month", type text}, {"strategy", type text}, {"portfolio_return", type number}, {"cumulative_wealth", type number}, {"drawdown", type number}})
in
    Typed
