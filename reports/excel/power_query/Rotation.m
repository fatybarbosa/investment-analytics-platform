let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/05_monitoring/turnover.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"month", type text}, {"strategy", type text}, {"gross_turnover", type number}, {"over_quarterly_cap", Int64.Type}, {"trailing_annual_turnover", type number}, {"over_annual_cap", Int64.Type}})
in
    Typed
