let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/05_monitoring/top10_positions.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"strategy", type text}, {"rank", Int64.Type}, {"yahoo_symbol", type text}, {"ticker", type text}, {"name", type text}, {"weight", type number}, {"sector", type text}, {"zone", type text}, {"exposure", type text}})
in
    Typed
