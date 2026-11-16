let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/05_monitoring/allocation_by_holding.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"strategy", type text}, {"yahoo_symbol", type text}, {"ticker", type text}, {"name", type text}, {"listing_currency", type text}, {"weight", type number}, {"sector", type text}, {"country", type text}, {"zone", type text}, {"asset_class", type text}, {"exposure", type text}})
,
    Ranked = Table.AddColumn(Typed, "rang", each
        let
            strategy = [strategy],
            weight = [weight],
            ticker = [ticker]
        in
            Table.RowCount(Table.SelectRows(Typed, each [strategy] = strategy and ([weight] > weight or ([weight] = weight and [ticker] <= ticker))))),
    WithRank = Table.AddColumn(Ranked, "cle_rang", each [strategy] & "|" & Text.From([rang])),
    WithTitle = Table.AddColumn(WithRank, "cle_titre", each [strategy] & "|" & [ticker])
in
    WithTitle
