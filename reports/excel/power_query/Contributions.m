let
    Source = Csv.Document(File.Contents("{{ProjectRoot}}/data/05_monitoring/sector_contribution.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"month", type text}, {"strategy", type text}, {"sector", type text}, {"month_contribution", type number}, {"cumulative_contribution", type number}})
in
    Typed
