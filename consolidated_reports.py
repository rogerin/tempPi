"""Shared query and immutable report data for the consolidated sensor screen."""
import os
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
import re
from itsdangerous import URLSafeTimedSerializer, BadData

BRAZIL_TZ = timezone(timedelta(hours=-3))
CHART_LIMIT = 10000
SENSORS = {
    'temp_forno': ('Temp Forno', 'temperature', '#e74c3c'),
    'torre_nivel_1': ('Torre Nível 1', 'temperature', '#3498db'),
    'torre_nivel_2': ('Torre Nível 2', 'temperature', '#2ecc71'),
    'torre_nivel_3': ('Torre Nível 3', 'temperature', '#f39c12'),
    'temp_tanque': ('Temp Tanque', 'temperature', '#9b59b6'),
    'temp_gases': ('Temp Saída Gases', 'temperature', '#1abc9c'),
    'pressao_gases': ('Pressão Gases', 'pressure', '#e67e22'),
    'velocity': ('Velocidade', 'velocity', '#34495e'),
}
GROUP_INTERVALS = {'2s': 2, '4s': 4, '6s': 6, '10s': 10, '30s': 30,
                   '1min': 60, '5min': 300, '15min': 900, '1hour': 3600, '1day': 86400}
# A signed, compressed snapshot travels with the browser. No database copies on every refresh.
# The default key is per process: after a restart the screen must be refreshed.
_serializer = URLSafeTimedSerializer(
    os.environ.get('REPORT_SNAPSHOT_SECRET') or secrets.token_hex(32),
    salt='temppi-consolidated-report-v1',
)


def get_group_interval(group_by):
    return GROUP_INTERVALS.get(group_by)


def normalize_date_range(start, end, require_both=False):
    """Normalize ISO filters to the UTC-3 wall time written by dashboard.py."""
    if require_both and (not start or not end):
        raise ValueError('Informe o início e o fim do período customizado.')

    def parse(value, is_end=False):
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=BRAZIL_TZ)
            # Include the complete final day/minute at the input's precision.
            if is_end and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
            elif is_end and re.fullmatch(
                    r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?', value):
                parsed = parsed.replace(second=59, microsecond=999999)
            return parsed.astimezone(BRAZIL_TZ)
        except (ValueError, OverflowError, TypeError, AttributeError):
            raise ValueError('Data inválida. Informe uma data e hora ISO 8601.') from None

    first, last = parse(start), parse(end, is_end=True)
    if first and last and first > last:
        raise ValueError('A data inicial deve ser anterior ou igual à data final.')
    # Keep the indexed column untouched; SQLite timestamps use a space, not T.
    return tuple(value.replace(tzinfo=None).isoformat(sep=' ') if value else None
                 for value in (first, last))


def build_snapshot(db_path, options, now):
    """Resolve the period once and query exactly the data returned to the browser."""
    time_range = str(options.get('timeRange', '24'))
    start, end = options.get('startTime'), options.get('endTime')
    custom = time_range == 'custom' or start is not None or end is not None
    if custom:
        start, end = normalize_date_range(start, end, require_both=True)
    else:
        try:
            hours = int(time_range)
            if hours <= 0:
                raise ValueError
            start = (now - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            end = now.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OverflowError):
            raise ValueError('Período em horas inválido.') from None

    group_by = options.get('groupBy', 'none')
    if group_by != 'none' and group_by not in GROUP_INTERVALS:
        raise ValueError('Agrupamento inválido.')
    sensors = options.get('selectedSensors', list(SENSORS))
    if not isinstance(sensors, list) or any(sensor not in SENSORS for sensor in sensors):
        raise ValueError('Seleção de sensores inválida.')
    sensors = list(dict.fromkeys(sensors))
    unit = options.get('pressureUnit', 'psi')
    if unit not in ('psi', 'bar'):
        raise ValueError('Unidade de pressão inválida.')

    interval = get_group_interval(group_by)
    timestamp = (f"datetime((strftime('%s', timestamp) / {interval}) * {interval}, 'unixepoch')"
                 if interval else 'timestamp')
    aggregate = 'AVG' if interval else 'MAX'
    columns = ', '.join(
        f"{aggregate}(CASE WHEN sensor_name = ? THEN {column} END) AS {key}"
        for key, (_, column, _) in SENSORS.items())
    params = [name for name, _, _ in SENSORS.values()] + [start, end]
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(f'''SELECT {timestamp} AS timestamp, {columns}
            FROM sensor_readings WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY 1 ORDER BY 1''', params).fetchall()
    data = [{'timestamp': row['timestamp'], **{
        sensor: round(row[sensor], 2) if row[sensor] is not None else None
        for sensor in SENSORS}} for row in rows]
    return {'data': data, 'filters': {
        'timeRange': time_range, 'startTime': start, 'endTime': end,
        'groupBy': group_by, 'selectedSensors': sensors, 'pressureUnit': unit,
    }}


def sign_snapshot(snapshot):
    return _serializer.dumps(snapshot)


def read_snapshot(token):
    try:
        return _serializer.loads(token, max_age=24 * 60 * 60)
    except (BadData, TypeError):
        raise ValueError('Relatório expirado ou inválido. Clique em Atualizar e abra o relatório novamente.') from None


def render_pdf(snapshot, metadata):
    """Render only frozen data, with deterministic bytes for download and email."""
    from io import BytesIO
    from xml.sax.saxutils import escape
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import matplotlib.dates as mdates
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

    filters = snapshot['filters']
    sensors = filters['selectedSensors']
    unit = filters['pressureUnit']
    if not snapshot['data']:
        raise ValueError('Nenhum dado encontrado para o período especificado')
    if not sensors:
        raise ValueError('Selecione pelo menos um sensor para gerar o relatório.')

    # Convert once, for the chart, statistics and detailed table alike.
    rows = [dict(row) for row in snapshot['data']]
    if unit == 'bar':
        for row in rows:
            if row['pressao_gases'] is not None:
                row['pressao_gases'] *= 0.0689476

    def sensor_label(sensor):
        suffix = unit.upper() if sensor == 'pressao_gases' else ('rpm' if sensor == 'velocity' else '°C')
        return f'{SENSORS[sensor][0]} ({suffix})'

    # Match the browser's chart limit; both detailed tables retain the full period.
    chart_rows = rows[-CHART_LIMIT:]
    timestamps = [datetime.fromisoformat(row['timestamp']) for row in chart_rows]
    figure = Figure(figsize=(10, 6))
    FigureCanvasAgg(figure)
    axis = figure.add_subplot(111)
    pressure_axis = axis.twinx() if 'pressao_gases' in sensors else None
    lines = []
    for sensor in sensors:
        points = [(ts, row[sensor]) for ts, row in zip(timestamps, chart_rows) if row[sensor] is not None]
        if points:
            target = pressure_axis if sensor == 'pressao_gases' else axis
            plotted = target.plot([p[0] for p in points], [p[1] for p in points],
                                  label=sensor_label(sensor), color=SENSORS[sensor][2], linewidth=2)
            lines.extend(plotted)
    axis.set_title('Relatório de Sensores - TempPi')
    axis.set_xlabel('Data/hora - Brasil (UTC-3)')
    axis.set_ylabel('Temperatura (°C) / Velocidade (rpm)')
    axis.set_ylim(bottom=0)
    if pressure_axis:
        pressure_axis.set_ylabel(f'Pressão ({unit.upper()})')
        pressure_axis.set_ylim(bottom=0)
    # A single timestamp needs explicit limits; otherwise Matplotlib may expand by years.
    if len(set(timestamps)) == 1:
        axis.set_xlim(timestamps[0] - timedelta(minutes=1), timestamps[0] + timedelta(minutes=1))
    axis.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=8))
    axis.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    axis.tick_params(axis='x', rotation=35)
    axis.grid(True, alpha=0.3)
    if lines:
        axis.legend(lines, [line.get_label() for line in lines], loc='upper left', fontsize=8)
    figure.tight_layout()
    image = BytesIO()
    figure.savefig(image, format='png', dpi=150)
    image.seek(0)

    output = BytesIO()
    # Invariant removes generation-time/random metadata: the same snapshot yields the same PDF.
    doc = SimpleDocTemplate(output, pagesize=A4, invariant=1,
                            title='Relatório Consolidado - TempPi', author='TempPi')
    styles = getSampleStyleSheet()
    small = ParagraphStyle('TableHeader', parent=styles['Normal'], fontSize=6.5, leading=9)
    story = [Paragraph('Relatório de Sensores - TempPi', styles['Title'])]
    operation = escape(str(metadata.get('operation_name', '')))
    comments = escape(str(metadata.get('comments', ''))).replace('\n', '<br/>')
    if operation:
        story.append(Paragraph(f'<b>Operação:</b> {operation}', styles['Normal']))
    start = filters['startTime'].split('.')[0]
    end = filters['endTime'].split('.')[0]
    story.append(Paragraph(f'<b>Período:</b> {start} a {end} (Brasil, UTC-3)<br/>'
                           f'<b>Agrupamento:</b> {filters["groupBy"]}<br/>'
                           f'<b>Sensores:</b> {", ".join(sensor_label(s) for s in sensors)}<br/>'
                           f'<b>Registros:</b> {len(rows)}', styles['Normal']))
    if comments:
        story.extend([Spacer(1, 8), Paragraph(f'<b>Comentários:</b><br/>{comments}', styles['Normal'])])
    story.extend([Spacer(1, 10), Image(image, width=doc.width, height=doc.width * 0.6)])
    if len(rows) > CHART_LIMIT:
        story.append(Paragraph(f'Gráfico: últimos {CHART_LIMIT} registros, como na tela. '
                               'Estatísticas e tabela: período completo.', styles['Normal']))

    story.extend([Spacer(1, 12), Paragraph('Estatísticas Resumidas', styles['Heading2'])])
    stats = [['Sensor', 'Mín', 'Máx', 'Média']]
    for sensor in sensors:
        values = [row[sensor] for row in rows if row[sensor] is not None]
        if values:
            stats.append([sensor_label(sensor), f'{min(values):.2f}', f'{max(values):.2f}',
                          f'{sum(values) / len(values):.2f}'])
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
    ])
    stats_table = Table(stats, colWidths=[doc.width * 0.46] + [doc.width * 0.18] * 3, repeatRows=1)
    stats_table.setStyle(table_style)
    story.extend([stats_table, PageBreak(), Paragraph('Dados Detalhados', styles['Heading2'])])
    header = [Paragraph('Data/hora (UTC-3)', small)] + [Paragraph(sensor_label(s), small) for s in sensors]
    details = [header]
    for row in rows:
        details.append([row['timestamp']] + ['-' if row[s] is None else f'{row[s]:.2f}' for s in sensors])
    date_width = 96
    detail_table = Table(details, colWidths=[date_width] + [(doc.width - date_width) / len(sensors)] * len(sensors),
                         repeatRows=1)
    detail_table.setStyle(table_style)
    story.append(detail_table)
    doc.build(story)
    return output.getvalue()

