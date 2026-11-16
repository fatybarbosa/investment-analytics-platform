let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/05_monitoring/allocation_by_zone.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"strategy", type text}, {"zone", type text}, {"weight", type number}, {"names", Int64.Type}})
in
    Typed
