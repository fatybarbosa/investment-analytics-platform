let
    Source = Csv.Document(File.Contents("{{ProjectRoot}}/data/05_monitoring/limit_watch.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"month", type text}, {"strategy", type text}, {"largest_issuer", type text}, {"largest_issuer_weight", type number}, {"largest_sector", type text}, {"largest_sector_weight", type number}, {"largest_zone", type text}, {"largest_zone_weight", type number}, {"largest_currency", type text}, {"largest_currency_weight", type number}, {"issuer_over_cap", Int64.Type}, {"sector_over_cap", Int64.Type}, {"zone_over_cap", Int64.Type}, {"currency_over_cap", Int64.Type}, {"invested_names", Int64.Type}, {"positions_outside_band", Int64.Type}, {"rebalance_month", Int64.Type}, {"sector_over_ips_cap", Int64.Type}})
in
    Typed
