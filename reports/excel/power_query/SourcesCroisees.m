let
    DernierMois = List.Max(Rendements[month]),
    RendementLignes =
        let
            Base = Table.SelectColumns(Rendements, {"strategy", "month", "portfolio_return"}),
            A = Table.AddColumn(Base, "famille", each "rendement"),
            B = Table.AddColumn(A, "libelle", each "portefeuille"),
            C = Table.AddColumn(B, "mesure", each "portfolio_return"),
            D = Table.RenameColumns(C, {{"month", "periode"}, {"portfolio_return", "valeur"}})
        in
            Table.SelectColumns(D, {"famille", "strategy", "periode", "libelle", "mesure", "valeur"}),
    FondsLignes =
        let
            Base = Table.SelectColumns(Benchmark, {"month", "benchmark_return_chf"}),
            A = Table.AddColumn(Base, "strategy", each "benchmark"),
            B = Table.AddColumn(A, "famille", each "rendement"),
            C = Table.AddColumn(B, "libelle", each "fonds"),
            D = Table.AddColumn(C, "mesure", each "benchmark_return_chf"),
            E = Table.RenameColumns(D, {{"month", "periode"}, {"benchmark_return_chf", "valeur"}})
        in
            Table.SelectColumns(E, {"famille", "strategy", "periode", "libelle", "mesure", "valeur"}),
    PoidsLignes =
        let
            Base = Table.SelectColumns(Secteurs, {"strategy", "sector", "weight"}),
            A = Table.AddColumn(Base, "famille", each "poids"),
            B = Table.AddColumn(A, "periode", each DernierMois),
            C = Table.AddColumn(B, "mesure", each "poids"),
            D = Table.RenameColumns(C, {{"sector", "libelle"}, {"weight", "valeur"}})
        in
            Table.SelectColumns(D, {"famille", "strategy", "periode", "libelle", "mesure", "valeur"}),
    ContributionLignes =
        let
            Base = Table.SelectColumns(Contributions, {"strategy", "month", "sector", "month_contribution"}),
            A = Table.AddColumn(Base, "famille", each "contribution"),
            B = Table.AddColumn(A, "mesure", each "contribution_mensuelle"),
            C = Table.RenameColumns(B, {{"month", "periode"}, {"sector", "libelle"}, {"month_contribution", "valeur"}})
        in
            Table.SelectColumns(C, {"famille", "strategy", "periode", "libelle", "mesure", "valeur"}),
    StressNarrow = Table.Unpivot(Table.SelectColumns(StressPublie, {"strategy", "shock", "window_end", "terminal_wealth", "maximum_drawdown", "annualized_volatility", "sharpe_ratio"}), {"terminal_wealth", "maximum_drawdown", "annualized_volatility", "sharpe_ratio"}, "mesure_source", "valeur"),
    StressMapped = Table.AddColumn(StressNarrow, "mesure", each if [mesure_source] = "terminal_wealth" then "richesse_finale" else if [mesure_source] = "maximum_drawdown" then "drawdown_maximal" else if [mesure_source] = "annualized_volatility" then "volatilite" else "sharpe"),
    StressLignes =
        let
            A = Table.AddColumn(StressMapped, "famille", each "stress"),
            B = Table.RenameColumns(A, {{"shock", "libelle"}, {"window_end", "periode"}})
        in
            Table.SelectColumns(B, {"famille", "strategy", "periode", "libelle", "mesure", "valeur"}),
    Combined = Table.Combine({RendementLignes, FondsLignes, PoidsLignes, ContributionLignes, StressLignes}),
    TypedOut = Table.TransformColumnTypes(Combined, {{"famille", type text}, {"strategy", type text}, {"periode", type text}, {"libelle", type text}, {"mesure", type text}, {"valeur", type number}})
in
    TypedOut
