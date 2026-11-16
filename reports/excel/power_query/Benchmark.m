let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/06_performance/benchmark_monthly_return.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"month", type text}, {"fund_name", type text}, {"fund_currency", type text}, {"nav_total_return", type number}, {"chf_per_unit", type number}, {"prior_chf_per_unit", type number}, {"benchmark_return_chf", type number}})
in
    Typed
