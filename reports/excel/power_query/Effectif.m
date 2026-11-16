let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/05_monitoring/concentration_history.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"month", type text}, {"strategy", type text}, {"names", Int64.Type}, {"invested_names", Int64.Type}, {"maximum_weight", type number}, {"top_10_weight", type number}, {"hhi", type number}, {"effective_holdings", type number}, {"concentration_multiple", type number}})
in
    Typed
