let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/05_monitoring/monthly_report.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"strategy", type text}, {"report_month", type text}, {"window_start", type text}, {"window_end", type text}, {"names", Int64.Type}, {"invested_names", Int64.Type}, {"maximum_weight", type number}, {"top_10_weight", type number}, {"hhi", type number}, {"effective_holdings", type number}, {"concentration_multiple", type number}, {"largest_sector", type text}, {"largest_sector_weight", type number}, {"largest_zone", type text}, {"largest_zone_weight", type number}, {"largest_currency", type text}, {"largest_currency_weight", type number}})
in
    Typed
