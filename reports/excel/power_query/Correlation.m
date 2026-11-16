let
    Source = Csv.Document(File.Contents("C:/Users/MameBARBOSAMONTEIRO/projet01/data/07_risk/correlation_matrix.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"symbol", type text}, {"002129.SZ", type number}, {"0916.HK", type number}, {"1044.HK", type number}, {"3898.HK", type number}, {"4507.T", type number}, {"4523.T", type number}, {"4568.T", type number}, {"8951.T", type number}, {"9022.T", type number}, {"ALNY", type number}, {"BMY", type number}, {"C38U.SI", type number}, {"COV.PA", type number}, {"DEMANT.CO", type number}, {"DLR", type number}, {"EQIX", type number}, {"GFC.PA", type number}, {"GMAB.CO", type number}, {"LAND.L", type number}, {"NRP.JO", type number}, {"PSON.L", type number}, {"REC.MI", type number}, {"SALM.OL", type number}, {"SCA-B.ST", type number}, {"SOBI.ST", type number}, {"SOON.SW", type number}, {"SPSN.SW", type number}, {"SUI", type number}, {"VWS.CO", type number}})
in
    Typed
