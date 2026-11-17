let
    Source = Csv.Document(File.Contents("{{ProjectRoot}}/data/02_processed/macro/saron.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"series_id", type text}, {"date", type text}, {"value", type number}, {"rate_currency", type text}, {"rate_note", type text}})
in
    Typed
