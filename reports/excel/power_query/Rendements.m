let
    Source = Csv.Document(File.Contents("{{ProjectRoot}}/data/04_portfolios/portfolio_monthly_returns.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"month", type text}, {"strategy", type text}, {"portfolio_return", type number}, {"risk_free_return", type number}, {"excess_return", type number}})
in
    Typed
