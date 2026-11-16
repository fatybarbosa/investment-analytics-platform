"""Charts for the Excel annex.

The titles and the series are those of the HTML dashboards in phases 6 to 9.
The points are formulas. This sheet does not paste the HTML pictures.
"""

from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.marker import DataPoint
from openpyxl.chart.series_factory import SeriesFactory as Series
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.text import RichText
from openpyxl.drawing.line import LineProperties
from openpyxl.drawing.text import CharacterProperties, Paragraph, ParagraphProperties
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter


MONTH_LABELS = (
    "jan.",
    "fév.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
)


def axis_label(month, endpoint):
    """Year, or month and year at the ends. No hyphen, so Excel does not show -11."""
    year, month_number = str(month).split("-")
    if endpoint:
        return f"{MONTH_LABELS[int(month_number) - 1]} {year}"
    if month_number == "01":
        return year
    return ""


def add_dashboard(workbook, inputs, recalcul):
    from src.reporting.build_workbook import (
        BOOKS,
        SERIES,
        SERIES_LABELS,
        _series_column,
    )
    from src.stress_testing.build_stress import SHOCK_IDS

    shock_labels = {
        "aucun": "Sans choc",
        "marche": "Marché",
        "taux": "Taux",
        "recession": "Récession",
        "volatilite": "Volatilité",
    }

    sheet = workbook.create_sheet("Series")
    sheet["A1"] = "Séries des graphiques"
    sheet["A1"].font = Font(bold=True, size=16, name="Calibri", color="1F4E79")
    sheet["A2"] = "Chaque point est une formule. Les feuilles Suivi, Performance, Risque et Chocs lisent ces colonnes."
    sheet["A2"].font = Font(name="Calibri", size=11, color="4A4A4A")
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 100

    months = inputs["months"]
    count = len(months)
    origin = recalcul["start"]
    first = 4
    last = first + count - 1
    column = 40

    def cell(col, row, value=None):
        target = sheet.cell(row, col, value)
        return target

    def letter(col):
        return get_column_letter(col)

    def reference(col, row_start, row_end):
        return Reference(sheet, min_col=col, max_col=col, min_row=row_start, max_row=row_end)

    headers = ["month"]
    for series in SERIES:
        headers.append(f"richesse {SERIES_LABELS[series]}")
    headers.append("richesse SARON")
    for series in SERIES:
        headers.append(f"multiple SARON {SERIES_LABELS[series]}")
    for series in SERIES:
        headers.append(f"multiple fonds {SERIES_LABELS[series]}")
    for series in SERIES:
        headers.append(f"glissant {SERIES_LABELS[series]}")
    for series in SERIES:
        headers.append(f"écart {SERIES_LABELS[series]}")
    for series in SERIES:
        headers.append(f"drawdown {SERIES_LABELS[series]}")
    for series in BOOKS:
        headers.append(f"effectif {SERIES_LABELS[series]}")
    for series in BOOKS:
        headers.append(f"secteur max {SERIES_LABELS[series]}")
    headers.append("plafond secteur")
    for series in BOOKS:
        headers.append(f"lignes {SERIES_LABELS[series]}")
    headers.extend(["plancher lignes", "plafond lignes"])
    for shock in SHOCK_IDS:
        headers.append(f"choc {shock_labels[shock]}")
    for shock in SHOCK_IDS:
        headers.append(f"écart choc {shock_labels[shock]}")
    for offset, header in enumerate(headers):
        cell(column + offset, 3, header).font = Font(bold=True, name="Calibri")

    label_col = column - 1
    month_col = column
    cell(label_col, 3, "etiquette").font = Font(bold=True, name="Calibri")
    wealth_col = column + 1
    saron_col = wealth_col + len(SERIES)
    saron_multiple_col = saron_col + 1
    fund_multiple_col = saron_multiple_col + len(SERIES)
    rolling_col = fund_multiple_col + len(SERIES)
    active_col = rolling_col + len(SERIES)
    drawdown_col = active_col + len(SERIES)
    effective_col = drawdown_col + len(SERIES)
    sector_col = effective_col + len(BOOKS)
    cap_col = sector_col + len(BOOKS)
    lines_col = cap_col + 1
    floor_col = lines_col + len(BOOKS)
    ceiling_col = floor_col + 1
    shock_col = ceiling_col + 1
    gap_col = shock_col + len(SHOCK_IDS)
    rf_letter = get_column_letter(_series_column(0, "rf"))
    stress_last = 4 + len(BOOKS) * len(SHOCK_IDS) * count

    for offset in range(count):
        row = first + offset
        source = origin + offset
        cell(month_col, row, f"=Recalcul!A{source}")
        label = axis_label(months[offset], offset in (0, count - 1))
        written = cell(label_col, row, label if label else '=""')
        written.number_format = "@"
        for index in range(len(SERIES)):
            wealth_letter = get_column_letter(_series_column(index, "wealth"))
            cell(wealth_col + index, row, f"=Recalcul!{wealth_letter}{source}")
        if offset == 0:
            cell(saron_col, row, f"=1+Recalcul!{rf_letter}{source}")
        else:
            cell(saron_col, row, f"={letter(saron_col)}{row - 1}*(1+Recalcul!{rf_letter}{source})")
        fund_index = len(SERIES) - 1
        for index in range(len(SERIES)):
            cell(saron_multiple_col + index, row, f"={letter(wealth_col + index)}{row}/{letter(saron_col)}{row}")
            wealth_letter = get_column_letter(_series_column(index, "wealth"))
            if index == fund_index:
                cell(fund_multiple_col + index, row, "=1")
                cell(active_col + index, row, "=0")
            else:
                cell(
                    fund_multiple_col + index,
                    row,
                    f"={letter(wealth_col + index)}{row}/{letter(wealth_col + fund_index)}{row}",
                )
                active_letter = get_column_letter(_series_column(index, "active"))
                cell(active_col + index, row, f"=Recalcul!{active_letter}{source}")
            if offset < 11:
                cell(rolling_col + index, row, '=""')
            elif offset == 11:
                cell(rolling_col + index, row, f"=Recalcul!{wealth_letter}{source}-1")
            else:
                cell(rolling_col + index, row, f"=Recalcul!{wealth_letter}{source}/Recalcul!{wealth_letter}{source - 12}-1")
        for index in range(len(SERIES)):
            drawdown_letter = get_column_letter(_series_column(index, "dd"))
            cell(drawdown_col + index, row, f"=Recalcul!{drawdown_letter}{source}")
        for index, strategy in enumerate(BOOKS):
            cell(
                effective_col + index,
                row,
                f'=SUMIFS(Effectif[effective_holdings],Effectif[strategy],"{strategy}",Effectif[month],{letter(month_col)}{row})',
            )
            cell(
                sector_col + index,
                row,
                f'=SUMIFS(Limites[largest_sector_weight],Limites[strategy],"{strategy}",Limites[month],{letter(month_col)}{row})',
            )
            cell(
                lines_col + index,
                row,
                f'=SUMIFS(Limites[invested_names],Limites[strategy],"{strategy}",Limites[month],{letter(month_col)}{row})',
            )
        cell(cap_col, row, "=PlafondSecteur")
        cell(floor_col, row, "=PlancherLignes")
        cell(ceiling_col, row, "=PlafondLignes")
        for index, shock in enumerate(SHOCK_IDS):
            cell(
                shock_col + index,
                row,
                (
                    f'=SUMIFS(Stress!$H$5:$H${stress_last},Stress!$A$5:$A${stress_last},LivreChoisi,'
                    f'Stress!$B$5:$B${stress_last},"{shock}",Stress!$C$5:$C${stress_last},{letter(month_col)}{row})'
                ),
            )
        for index in range(len(SHOCK_IDS)):
            cell(gap_col + index, row, f"={letter(shock_col + index)}{row}-{letter(shock_col)}{row}")

    cats = reference(label_col, first, last)
    book_names = [SERIES_LABELS[series] for series in BOOKS]
    all_names = [SERIES_LABELS[series] for series in SERIES]
    shock_names = [shock_labels[shock] for shock in SHOCK_IDS]

    chart_labels = {
        "iShares, rendement de la valeur liquidative en CHF": "Fonds iShares",
    }
    book_colors = {
        "Équipondéré": "7EB6FF",
        "Volatilité minimale": "3DDC97",
        "Sharpe maximal": "F0B429",
        "Fonds iShares": "F4F6F8",
        "Plafond": "FF8B7B",
        "Plancher": "9AD1FF",
        "Sans choc": "7EB6FF",
        "Marché": "FF8B7B",
        "Taux": "9AD1FF",
        "Récession": "F0B429",
        "Volatilité": "C9B6FF",
        "VaR": "FF8B7B",
        "Expected shortfall": "F0B429",
        "Poids": "7EB6FF",
        "Titres effectifs": "7EB6FF",
        "Multiple de concentration": "3DDC97",
        "Rendement annualisé": "7EB6FF",
        "Sharpe": "7EB6FF",
        "Sortino": "3DDC97",
        "Ratio d'information": "F0B429",
        "Écart de suivi": "C9B6FF",
    }
    sector_colors = (
        "7EB6FF", "3DDC97", "F0B429", "FF8B7B",
        "5EEAD4", "C9B6FF", "F2A07B", "9AD1FF",
        "D4E157", "F48FB1", "80CBC4", "FFCC80",
        "A5D6A7", "B0BEC5", "CE93D8", "FFAB91",
    )
    book_point_colors = ("7EB6FF", "3DDC97", "F0B429", "F4F6F8")

    def legend(name):
        return chart_labels.get(name, name)

    def color_for(name, index):
        return book_colors.get(name, sector_colors[index % len(sector_colors)])

    def light_text(size):
        props = CharacterProperties(sz=size, solidFill="F4F6F8")
        return RichText(p=[Paragraph(pPr=ParagraphProperties(defRPr=props), endParaRPr=props)])

    def hide_grid(axis):
        axis.majorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(noFill=True)))
        axis.minorGridlines = None

    def paint(series, color, kind, dashed=False):
        line = LineProperties(solidFill=color, w=12700 if kind == "line" else 6000)
        if dashed:
            line.dashStyle = "dash"
        if kind == "line":
            series.graphicalProperties = GraphicalProperties(ln=line)
            series.smooth = False
        else:
            series.graphicalProperties = GraphicalProperties(solidFill=color, ln=line)
            series.invertIfNegative = False

    def paint_points(series, colors):
        points = []
        for index, color in enumerate(colors):
            point = DataPoint(idx=index, invertIfNegative=False)
            point.graphicalProperties = GraphicalProperties(
                solidFill=color,
                ln=LineProperties(solidFill=color, w=6000),
            )
            points.append(point)
        series.data_points = points
        series.invertIfNegative = False

    def finish(chart, names, kind, horizontal=False, percent=False, value_format=None, label_skip=None, zoom=False):
        for index, series in enumerate(chart.series):
            name = names[index] if index < len(names) else ""
            paint(series, color_for(name, index), kind, dashed=name in {"Plafond", "Plancher"})
        if len(chart.series) <= 1 and not getattr(chart, "_keep_legend", False):
            chart.legend = None
        else:
            chart.legend.position = "b"
            chart.legend.overlay = False
            chart.legend.graphicalProperties = GraphicalProperties(solidFill="0B0D10")
            chart.legend.txPr = light_text(900)
        hide_grid(chart.x_axis)
        hide_grid(chart.y_axis)
        chart.graphical_properties = GraphicalProperties(
            solidFill="0B0D10",
            ln=LineProperties(solidFill="2A2E35", w=4000),
        )
        chart.plot_area.graphicalProperties = GraphicalProperties(solidFill="0B0D10")
        axis_line = GraphicalProperties(ln=LineProperties(solidFill="F4F6F8", w=6000))
        chart.x_axis.graphicalProperties = axis_line
        chart.y_axis.graphicalProperties = axis_line
        chart.x_axis.txPr = light_text(900)
        chart.y_axis.txPr = light_text(900)
        chart.x_axis.delete = False
        chart.y_axis.delete = False
        chart.x_axis.tickLblPos = "nextTo"
        chart.y_axis.tickLblPos = "nextTo"
        if label_skip and not horizontal:
            chart.x_axis.tickLblPos = "low"
        chart.x_axis.majorTickMark = "out"
        chart.y_axis.majorTickMark = "out"
        chart.x_axis.title = None
        chart.y_axis.title = None
        if label_skip and not horizontal:
            chart.x_axis.tickLblSkip = label_skip
            chart.x_axis.tickMarkSkip = label_skip
        number_format = value_format or ("0.0%" if percent else "0.00")
        if horizontal:
            chart.x_axis.numFmt = number_format
            chart.x_axis.scaling.min = 0
            chart.y_axis.scaling.orientation = "maxMin"
        else:
            chart.y_axis.numFmt = number_format
            if zoom:
                chart.y_axis.crosses = "min"
        if isinstance(chart, BarChart):
            chart.varyColors = False
            chart.gapWidth = 20
            chart.overlap = 0
        chart.title = None

    class Board:
        def __init__(self, worksheet):
            self.worksheet = worksheet
            self.row = 4

        def add(self, chart, title, height=9.2):
            self.worksheet.merge_cells(
                start_row=self.row,
                start_column=1,
                end_row=self.row,
                end_column=9,
            )
            title_cell = self.worksheet.cell(self.row, 1, title)
            title_cell.font = Font(name="Calibri", size=13, bold=True, color="1F4E79")
            title_cell.alignment = Alignment(horizontal="center", vertical="center")
            self.worksheet.row_dimensions[self.row].height = 22
            chart.width = 18
            chart.height = height
            self.worksheet.add_chart(chart, f"A{self.row + 2}")
            self.row += int(height / 0.42) + 8

    def open_board(name, title, note):
        worksheet = workbook.create_sheet(name)
        worksheet["A1"] = title
        worksheet["A1"].font = Font(name="Calibri", size=18, bold=True, color="1F4E79")
        worksheet.merge_cells("A2:I2")
        worksheet["A2"] = note
        worksheet["A2"].font = Font(name="Calibri", size=11, color="4A4A4A")
        worksheet["A2"].alignment = Alignment(wrap_text=True, vertical="center")
        worksheet.row_dimensions[1].height = 26
        worksheet.row_dimensions[2].height = 32
        worksheet.sheet_view.showGridLines = False
        worksheet.sheet_view.zoomScale = 110
        worksheet.page_setup.orientation = "landscape"
        worksheet.page_setup.fitToPage = True
        worksheet.page_setup.fitToWidth = 1
        worksheet.page_setup.fitToHeight = 0
        worksheet.page_setup.paperSize = worksheet.PAPERSIZE_A4
        worksheet.sheet_properties.pageSetUpPr.fitToPage = True
        worksheet.page_setup.horizontalCentered = True
        worksheet.oddFooter.center.text = title
        worksheet.oddFooter.right.text = "Page &P"
        worksheet.sheet_properties.tabColor = "1F4E79"
        for column_letter in "ABCDEFGHIJKLMN":
            worksheet.column_dimensions[column_letter].width = 11
        return Board(worksheet)

    suivi = open_board(
        "Suivi",
        "Suivi",
        "Mêmes titres que le suivi HTML et que la page Suivi de Power BI. Secteur, zone et devises sont aussi sur Portfolio Overview. L'axe vertical est cadré sur les séries. L'axe des dates va jusqu'au dernier mois.",
    )
    performance = open_board(
        "Performance",
        "Performance",
        "Mêmes titres que la page HTML de performance et que Performance Analytics.",
    )
    risque = open_board(
        "Risque",
        "Risque",
        "Mêmes titres que la page HTML de risque et que Risk Analytics. La matrice de Pearson est sur Correlation.",
    )
    chocs = open_board(
        "Chocs",
        "Chocs",
        "L'écart est la richesse du choc moins la richesse sans choc, pour LivreChoisi. Marché, récession et volatilité seulement : sans choc est la ligne zéro, et le choc de taux ne change pas le rendement. Les barres comparent les cinq chocs, pour les trois livres.",
    )

    def line(start_column, names, percent=False, minimum=None, value_format=None, zoom=False, columns=None):
        chart = LineChart()
        chart.y_axis.title = None
        chart.x_axis.title = None
        if minimum is not None:
            chart.y_axis.scaling.min = minimum
        labels = [legend(name) for name in names]
        chosen = columns if columns is not None else [start_column + index for index in range(len(labels))]
        for index, name in enumerate(labels):
            chart.series.append(Series(reference(chosen[index], first, last), title=name))
        chart.set_categories(cats)
        finish(
            chart,
            labels,
            "line",
            percent=percent,
            value_format=value_format,
            zoom=zoom,
        )
        return chart

    performance.add(line(wealth_col, all_names, minimum=0, value_format="0.00"), "Placement de 1 CHF")
    performance.add(line(drawdown_col, all_names, percent=True), "Drawdown")
    performance.add(line(saron_multiple_col, all_names, minimum=0, value_format="0.00"), "Performance relative au SARON")
    performance.add(line(fund_multiple_col, all_names, minimum=0, value_format="0.00"), "Performance relative au fonds")
    performance.add(line(rolling_col, all_names, percent=True), "Rendement glissant sur 12 mois")
    performance.add(line(active_col, all_names, percent=True), "Écart mensuel avec le fonds")
    suivi.add(line(effective_col, book_names, value_format="0", zoom=True), "Nombre effectif dans le temps")
    suivi.add(line(sector_col, book_names + ["Plafond"], percent=True, zoom=True), "Plus grand secteur dans le temps")
    suivi.add(line(lines_col, book_names + ["Plancher", "Plafond"], value_format="0", zoom=True), "Lignes investies dans le temps")
    visible_shocks = ("marche", "recession", "volatilite")
    chocs.add(
        line(
            gap_col,
            [shock_labels[shock] for shock in visible_shocks],
            value_format="0.00",
            columns=[gap_col + SHOCK_IDS.index(shock) for shock in visible_shocks],
        ),
        "Écart de richesse par rapport au chemin sans choc",
    )

    def bars(labels, values, horizontal=False, percent=False, value_format=None, label_skip=None, zoom=False, point_colors=False):
        chart = BarChart()
        chart.type = "bar" if horizontal else "col"
        chart.grouping = "clustered"
        chart.y_axis.title = None
        chart.x_axis.title = None
        labels_text = [legend(name) for name in values["names"]]
        for index, name in enumerate(labels_text):
            chart.series.append(Series(reference(values["columns"][index], values["first"], values["last"]), title=name))
        chart.set_categories(reference(labels[0], labels[1], labels[2]))
        if point_colors and len(chart.series) == 1:
            paint_points(chart.series[0], book_point_colors)
        finish(
            chart,
            labels_text,
            "bar",
            horizontal=horizontal,
            percent=percent,
            value_format=value_format,
            label_skip=label_skip,
            zoom=zoom,
        )
        return chart

    block = last + 3
    sectors = list(dict.fromkeys(inputs["sectors"]["sector"].astype(str)))
    cell(column, block, "secteur")
    for index, strategy in enumerate(BOOKS):
        cell(column + 1 + index, block, SERIES_LABELS[strategy])
    for index, sector in enumerate(sectors):
        cell(column, block + 1 + index, sector)
        for strategy_index, strategy in enumerate(BOOKS):
            cell(
                column + 1 + strategy_index,
                block + 1 + index,
                f'=SUMIFS(Secteurs[weight],Secteurs[strategy],"{strategy}",Secteurs[sector],{letter(column)}{block + 1 + index})',
            )
    suivi.add(bars(
        (column, block + 1, block + len(sectors)),
        {"names": book_names, "columns": [column + 1 + i for i in range(3)], "first": block + 1, "last": block + len(sectors)},
        horizontal=True,
        percent=True,
    ), "Allocation par secteur", height=2.6 + len(sectors) * 0.62)
    zone_block = block + len(sectors) + 3
    zones = list(dict.fromkeys(inputs["zones"]["zone"].astype(str)))
    cell(column, zone_block, "zone")
    for index, strategy in enumerate(BOOKS):
        cell(column + 1 + index, zone_block, SERIES_LABELS[strategy])
    for index, zone in enumerate(zones):
        cell(column, zone_block + 1 + index, zone)
        for strategy_index, strategy in enumerate(BOOKS):
            cell(
                column + 1 + strategy_index,
                zone_block + 1 + index,
                f'=SUMIFS(Zones[weight],Zones[strategy],"{strategy}",Zones[zone],{letter(column)}{zone_block + 1 + index})',
            )
    suivi.add(bars(
        (column, zone_block + 1, zone_block + len(zones)),
        {"names": book_names, "columns": [column + 1 + i for i in range(3)], "first": zone_block + 1, "last": zone_block + len(zones)},
        horizontal=True,
        percent=True,
    ), "Allocation par zone", height=2.6 + len(zones) * 0.7)
    currency_block = zone_block + len(zones) + 3
    currencies = list(dict.fromkeys(inputs["currencies"]["exposure"].astype(str)))
    cell(column, currency_block, "devise")
    for index, strategy in enumerate(BOOKS):
        cell(column + 1 + index, currency_block, SERIES_LABELS[strategy])
    for index, currency in enumerate(currencies):
        cell(column, currency_block + 1 + index, currency)
        for strategy_index, strategy in enumerate(BOOKS):
            cell(
                column + 1 + strategy_index,
                currency_block + 1 + index,
                f'=SUMIFS(Devises[weight],Devises[strategy],"{strategy}",Devises[exposure],{letter(column)}{currency_block + 1 + index})',
            )
    suivi.add(bars(
        (column, currency_block + 1, currency_block + len(currencies)),
        {"names": book_names, "columns": [column + 1 + i for i in range(3)], "first": currency_block + 1, "last": currency_block + len(currencies)},
        horizontal=True,
        percent=True,
    ), "Devises", height=2.6 + len(currencies) * 0.7)

    rank_count = int(inputs["holdings"].groupby("strategy").size().max())
    rank_block = currency_block + len(currencies) + 3
    cell(column, rank_block, "rang")
    cell(column + 1, rank_block, "titre")
    cell(column + 2, rank_block, "poids")
    for rank in range(1, rank_count + 1):
        row = rank_block + rank
        cell(column, row, rank)
        cell(column + 1, row, f'=IFERROR(INDEX(Positions[name],MATCH(LivreChoisi&"|"&{letter(column)}{row},Positions[cle_rang],0)),"")')
        cell(column + 2, row, f'=IFERROR(INDEX(Positions[weight],MATCH(LivreChoisi&"|"&{letter(column)}{row},Positions[cle_rang],0)),"")')
    suivi.add(bars(
        (column + 1, rank_block + 1, rank_block + rank_count),
        {"names": ["Poids"], "columns": [column + 2], "first": rank_block + 1, "last": rank_block + rank_count},
        horizontal=True,
        percent=True,
    ), "Allocation par titre", height=2.8 + rank_count * 0.48)
    suivi.add(bars(
        (column + 1, rank_block + 1, rank_block + 10),
        {"names": ["Poids"], "columns": [column + 2], "first": rank_block + 1, "last": rank_block + 10},
        horizontal=True,
        percent=True,
    ), "Dix principales positions", height=8.4)

    contribution_block = rank_block + rank_count + 3
    contribution_sectors = list(dict.fromkeys(inputs["contributions"]["sector"].astype(str)))
    cell(month_col, contribution_block, "month")
    for index, sector in enumerate(contribution_sectors):
        cell(month_col + 1 + index, contribution_block, sector)
    for offset in range(count):
        row = contribution_block + 1 + offset
        cell(month_col, row, f"={letter(month_col)}{first + offset}")
        for index, sector in enumerate(contribution_sectors):
            cell(
                month_col + 1 + index,
                row,
                (
                    f'=SUMIFS(Contributions[cumulative_contribution],Contributions[strategy],LivreChoisi,'
                    f'Contributions[sector],{letter(month_col + 1 + index)}${contribution_block},'
                    f'Contributions[month],{letter(month_col)}{row})'
                ),
            )
    contribution = LineChart()
    contribution.height = 7.2
    contribution.width = 24
    for index, sector in enumerate(contribution_sectors):
        contribution.series.append(
            Series(reference(month_col + 1 + index, contribution_block + 1, contribution_block + count), title=sector)
        )
    contribution.set_categories(cats)
    finish(contribution, contribution_sectors, "line", percent=True)
    suivi.add(
        contribution,
        "Contributions cumulées par secteur",
        height=8.4 + min(len(contribution_sectors), 12) * 0.28,
    )

    turnover_months = sorted(inputs["turnover"]["month"].astype(str).unique())
    turnover_block = contribution_block + count + 3
    cell(column, turnover_block, "trimestre")
    for index, strategy in enumerate(BOOKS):
        cell(column + 1 + index, turnover_block, SERIES_LABELS[strategy])
    cell(column + 4, turnover_block, "etiquette")
    for index, month in enumerate(turnover_months):
        cell(column, turnover_block + 1 + index, month)
        turnover_label = axis_label(month, index in (0, len(turnover_months) - 1))
        labelled = cell(column + 4, turnover_block + 1 + index, turnover_label if turnover_label else "")
        labelled.number_format = "@"
        for strategy_index, strategy in enumerate(BOOKS):
            cell(
                column + 1 + strategy_index,
                turnover_block + 1 + index,
                f'=SUMIFS(Rotation[gross_turnover],Rotation[strategy],"{strategy}",Rotation[month],{letter(column)}{turnover_block + 1 + index})',
            )
    suivi.add(bars(
        (column + 4, turnover_block + 1, turnover_block + len(turnover_months)),
        {"names": book_names, "columns": [column + 1 + i for i in range(3)], "first": turnover_block + 1, "last": turnover_block + len(turnover_months)},
        percent=True,
    ), "Rotation brute trimestrielle", height=9.2)

    report_block = turnover_block + len(turnover_months) + 3
    cell(column, report_block, "livre")
    cell(column + 1, report_block, "Titres effectifs")
    cell(column + 2, report_block, "Multiple de concentration")
    for index, strategy in enumerate(BOOKS):
        cell(column, report_block + 1 + index, SERIES_LABELS[strategy])
        cell(column + 1, report_block + 1 + index, f'=SUMIFS(RapportMois[effective_holdings],RapportMois[strategy],"{strategy}")')
        cell(column + 2, report_block + 1 + index, f'=SUMIFS(RapportMois[concentration_multiple],RapportMois[strategy],"{strategy}")')
    suivi.add(bars(
        (column, report_block + 1, report_block + len(BOOKS)),
        {"names": ["Titres effectifs"], "columns": [column + 1], "first": report_block + 1, "last": report_block + len(BOOKS)},
        value_format="0.0",
        point_colors=True,
        zoom=True,
    ), "Titres effectifs")
    suivi.add(bars(
        (column, report_block + 1, report_block + len(BOOKS)),
        {"names": ["Multiple de concentration"], "columns": [column + 2], "first": report_block + 1, "last": report_block + len(BOOKS)},
        value_format="0.00",
        point_colors=True,
        zoom=True,
    ), "Multiple de concentration")

    summary = recalcul["summary"]
    risk_block = report_block + len(BOOKS) + 3
    cell(column, risk_block, "livre")
    for index, header in enumerate(("Volatilité", "VaR", "Expected shortfall")):
        cell(column + 1 + index, risk_block, header)
    for index, strategy in enumerate(BOOKS):
        source = summary + index
        cell(column, risk_block + 1 + index, f"=Recalcul!A{source}")
        cell(column + 1, risk_block + 1 + index, f"=Recalcul!F{source}")
        cell(column + 2, risk_block + 1 + index, f"=Recalcul!L{source}")
        cell(column + 3, risk_block + 1 + index, f"=Recalcul!M{source}")
    fund_source = summary + len(BOOKS)
    fund_row = risk_block + 1 + len(BOOKS)
    cell(column, fund_row, "Fonds iShares")
    cell(column + 1, fund_row, f"=Recalcul!F{fund_source}")
    cell(column + 2, fund_row, f"=Recalcul!L{fund_source}")
    cell(column + 3, fund_row, f"=Recalcul!M{fund_source}")
    risque.add(bars(
        (column, risk_block + 1, fund_row),
        {
            "names": ["Volatilité", "VaR", "Expected shortfall"],
            "columns": [column + 1, column + 2, column + 3],
            "first": risk_block + 1,
            "last": fund_row,
        },
        percent=True,
    ), "Queue historique à 95 %")

    ranks = sorted(inputs["tail"]["rank"].astype(int).unique())
    tail_block = fund_row + 3
    cell(column, tail_block, "rang")
    for index, strategy in enumerate(BOOKS):
        cell(column + 1 + index, tail_block, SERIES_LABELS[strategy])
    cell(column + 1 + len(BOOKS), tail_block, "Fonds iShares")
    for index, rank in enumerate(ranks):
        cell(column, tail_block + 1 + index, int(rank))
        for strategy_index, strategy in enumerate(BOOKS):
            cell(
                column + 1 + strategy_index,
                tail_block + 1 + index,
                f'=SUMIFS(QueueMois[portfolio_return],QueueMois[strategy],"{strategy}",QueueMois[rank],{letter(column)}{tail_block + 1 + index})',
            )
        cell(
            column + 1 + len(BOOKS),
            tail_block + 1 + index,
            f'=SUMIFS(QueueMois[portfolio_return],QueueMois[strategy],"benchmark",QueueMois[rank],{letter(column)}{tail_block + 1 + index})',
        )
    risque.add(bars(
        (column, tail_block + 1, tail_block + len(ranks)),
        {
            "names": book_names + ["Fonds iShares"],
            "columns": [column + 1 + i for i in range(4)],
            "first": tail_block + 1,
            "last": tail_block + len(ranks),
        },
        percent=True,
    ), "Mois de l'expected shortfall")

    stress_row_count = len(BOOKS) * len(SHOCK_IDS)
    stress_first = 5
    stress_end = stress_first + stress_row_count - 1
    metric_columns = (
        ("Performance cumulée sous choc", 14),
        ("Drawdown maximal sous choc", 15),
        ("Volatilité sous choc", 16),
        ("Ratio de Sharpe sous choc", 17),
    )
    metric_block = tail_block + len(ranks) + 3
    for metric_index, (title, source_column) in enumerate(metric_columns):
        header = metric_block + metric_index * (len(SHOCK_IDS) + 3)
        cell(column, header, "choc")
        for index, strategy in enumerate(BOOKS):
            cell(column + 1 + index, header, SERIES_LABELS[strategy])
        for index, shock in enumerate(SHOCK_IDS):
            cell(column, header + 1 + index, shock_labels[shock])
            for strategy_index, strategy in enumerate(BOOKS):
                source_letter = get_column_letter(source_column)
                cell(
                    column + 1 + strategy_index,
                    header + 1 + index,
                    (
                        f'=SUMIFS(Stress!${source_letter}${stress_first}:${source_letter}${stress_end},'
                        f'Stress!$L${stress_first}:$L${stress_end},"{strategy}",'
                        f'Stress!$M${stress_first}:$M${stress_end},"{shock}")'
                    ),
                )
        chocs.add(bars(
            (column, header + 1, header + len(SHOCK_IDS)),
            {"names": book_names, "columns": [column + 1 + i for i in range(3)], "first": header + 1, "last": header + len(SHOCK_IDS)},
            percent=title not in {"Performance cumulée sous choc", "Ratio de Sharpe sous choc"},
            value_format=None if title not in {"Performance cumulée sous choc", "Ratio de Sharpe sous choc"} else "0.00",
        ), title)

    indicator_specs = (
        ("Rendement annualisé", (("annualized_return", "Rendement annualisé"),), "0.0%", True, True),
        ("Sharpe et Sortino", (("sharpe_ratio", "Sharpe"), ("sortino_ratio", "Sortino")), "0.00", False, False),
        ("Ratio d'information", (("information_ratio", "Ratio d'information"),), "0.00", False, True),
        ("Écart de suivi", (("tracking_error", "Écart de suivi"),), "0.0%", True, True),
    )
    header = metric_block + len(metric_columns) * (len(SHOCK_IDS) + 3)
    for title, measures, number_format, percent, colored in indicator_specs:
        cell(column, header, "livre")
        for index, (_field, label) in enumerate(measures):
            cell(column + 1 + index, header, label)
        for book_index, strategy in enumerate(BOOKS):
            cell(column, header + 1 + book_index, SERIES_LABELS[strategy])
            for measure_index, (field, _label) in enumerate(measures):
                written = cell(
                    column + 1 + measure_index,
                    header + 1 + book_index,
                    f'=SUMIFS(PerformancePubliee[{field}],PerformancePubliee[strategy],"{strategy}")',
                )
                written.number_format = number_format
        last = header + len(BOOKS)
        if title != "Ratio d'information":
            last += 1
            cell(column, last, "Fonds iShares")
            for measure_index, (field, _label) in enumerate(measures):
                written = cell(
                    column + 1 + measure_index,
                    last,
                    f'=SUMIFS(PerformancePubliee[{field}],PerformancePubliee[strategy],"benchmark")',
                )
                written.number_format = number_format
        performance.add(bars(
            (column, header + 1, last),
            {
                "names": [label for _field, label in measures],
                "columns": [column + 1 + index for index in range(len(measures))],
                "first": header + 1,
                "last": last,
            },
            percent=percent,
            value_format=number_format,
            point_colors=colored,
        ), title)
        header += len(BOOKS) + 4

    sheet.auto_filter.ref = None
    sheet.sheet_view.zoomScale = 100
