let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/04_portfolios/portfolio_weights.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"strategy", type text}, {"month", type text}, {"yahoo_symbol", type text}, {"ticker", type text}, {"name", type text}, {"listing_currency", type text}, {"weight", type number}})
in
    Typed
