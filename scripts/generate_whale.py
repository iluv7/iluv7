"""Generate a self-contained, script-free animated SVG from real contributions."""
import argparse
import datetime as dt
from html.parser import HTMLParser
from html import escape
import json
import math
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('data-date') and 'data-level' in a:
            self.days[a['data-date']] = int(a['data-level'])


def fetch_calendar(username, html_path=None):
    if html_path:
        source = Path(html_path).read_text()
    elif os.environ.get('GITHUB_TOKEN'):
        query = 'query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionLevel}}}}}}'
        req = urllib.request.Request('https://api.github.com/graphql',
            data=json.dumps({'query': query, 'variables': {'login': username}}).encode(),
            headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'], 'Content-Type': 'application/json', 'User-Agent': 'whale-maid-calendar'})
        with urllib.request.urlopen(req, timeout=45) as response:
            data = json.load(response)
        if data.get('errors'):
            raise RuntimeError('GitHub contribution query failed: ' + str(data['errors']))
        levels = {'NONE': 0, 'FIRST_QUARTILE': 1, 'SECOND_QUARTILE': 2, 'THIRD_QUARTILE': 3, 'FOURTH_QUARTILE': 4}
        weeks = data['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
        return {day['date']: levels[day['contributionLevel']] for week in weeks for day in week['contributionDays']}
    else:
        with urllib.request.urlopen('https://github.com/users/' + username + '/contributions', timeout=45) as response:
            source = response.read().decode()
    parser = CalendarParser()
    parser.feed(source)
    if len(parser.days) < 350:
        raise RuntimeError('Contribution calendar is incomplete; refusing to publish sample data.')
    return parser.days


def animate(attribute, timeline, duration, discrete=False):
    # Collapse identical times so SVG keyTimes remain strictly increasing.
    points = {}
    for t, value in timeline:
        points[round(t / duration, 7)] = str(value)
    times = sorted(points)
    return '<animate attributeName="%s" dur="%.4fs" repeatCount="indefinite" calcMode="%s" keyTimes="%s" values="%s"/>' % (
        attribute, duration, 'discrete' if discrete else 'linear', ';'.join(f'{t:.7f}' for t in times), ';'.join(points[t] for t in times))


def render(days, sprites, username):
    dates = sorted(days)
    first = dt.date.fromisoformat(dates[0])
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)
    cells = []
    for date in dates:
        day = dt.date.fromisoformat(date)
        col, row = divmod((day - start).days, 7)
        cells.append({'date': date, 'col': col, 'row': row, 'x': 48 + col * 14, 'y': 54 + row * 14, 'level': days[date]})
    columns = max(c['col'] for c in cells) + 1
    width, height = columns * 14 + 96, 192
    # Visit active cells only, while retaining every blank day in the display.
    route = sorted((c for c in cells if c['level']), key=lambda c: (c['row'], c['col'] if c['row'] % 2 == 0 else -c['col']))
    x, y, time = 20., 54., 0.
    positions = [(0, f'{x:.3f} {y:.3f}')]
    directions = [(0, '1 1')]
    mouths = [(0, 0)]
    consumed = {}
    for cell in route:
        direction = -1 if cell['row'] % 2 else 1
        nx, ny = cell['x'] - direction * 9, cell['y'] + 7
        distance = math.hypot(nx - x, ny - y)
        travel = max(.20, distance / 76)
        positions.append((time, f'{x:.3f} {y:.3f}'))
        directions.append((time, f'{direction} 1'))
        # Open only in the last few pixels before an active cell, once per cell.
        opening = time + travel * max(0, 1 - 11 / max(distance, 1))
        closing = time + travel * .98
        mouths.extend([(opening, 1), (max(opening + .001, closing), 0)])
        time += travel
        positions.append((time, f'{nx:.3f} {ny:.3f}'))
        consumed[cell['date']] = time - .01
        x, y = nx, ny
    end = time
    duration = max(end + 3.2, 4)
    positions.append((duration, f'{x:.3f} {y:.3f}'))
    directions.extend([(end, '1 1'), (duration, '1 1')])
    mouths.extend([(end, 0), (duration, 0)])
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Whale maid contribution calendar</title>',
        f'<desc id="desc">{escape(username)}: {len(cells)} real calendar days, {len(route)} active days. The whale maid runs continuously, eats only green cells, then celebrates.</desc>',
        '<style>.empty{fill:#ebedf0}.eaten{fill:#ebedf0}@media(prefers-color-scheme:dark){.empty,.eaten{fill:#161b22}}@media(prefers-reduced-motion:reduce){animate,animateTransform{display:none}.actor{display:none}}</style><defs>']
    for name, data in sprites.items():
        parts.append(f'<image id="{name}" x="-42" y="-55" width="84" height="84" xlink:href="data:image/png;base64,{data}"/>')
    parts.append('</defs>')
    colors = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39']
    for c in cells:
        box = f'x="{c["x"]-5}" y="{c["y"]-5}" width="10" height="10" rx="2"'
        parts.append(f'<rect class="empty" {box}/>' )
        if c['level']:
            parts.append(f'<rect {box} fill="{colors[c["level"]]}">' + animate('opacity', [(0, 1), (consumed[c['date']], 0), (duration, 0)], duration, True) + '</rect>')
    parts.append('<g class="actor">')
    move = animate('transform', positions, duration).replace('<animate ', '<animateTransform type="translate" ')
    parts.append(move)
    parts.append('<g>' + animate('transform', directions, duration, True).replace('<animate ', '<animateTransform type="scale" '))
    parts.append('<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -1;0 0" dur="0.55s" repeatCount="indefinite"/>')
    parts.append('<g>' + animate('opacity', [(0, 1), (end, 0), (duration, 0)], duration, True))
    parts.append('<use xlink:href="#run">' + animate('opacity', [(t, 1-int(v)) for t, v in mouths], duration, True) + '</use>')
    parts.append('<use xlink:href="#bite" opacity="0">' + animate('opacity', mouths, duration, True) + '</use></g>')
    parts.append('<use xlink:href="#finish-open" opacity="0">' + animate('opacity', [(0,0),(end,1),(end+.85,0),(duration,0)], duration, True) + '</use>')
    parts.append('<use xlink:href="#finish-chew" opacity="0">' + animate('opacity', [(0,0),(end+.85,1),(duration,1)], duration, True) + '</use>')
    parts.append('</g></g></g></svg>')
    return ''.join(parts), {'days': len(cells), 'active_days': len(route), 'columns': columns, 'duration_seconds': round(duration, 2)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', default=os.environ.get('GITHUB_REPOSITORY_OWNER', 'iluv7'))
    parser.add_argument('--calendar-html')
    parser.add_argument('--output', default=str(ROOT / 'assets' / 'whale-maid.svg'))
    args = parser.parse_args()
    svg, stats = render(fetch_calendar(args.username, args.calendar_html), json.loads((ROOT / 'assets' / 'whale-maid-sprites.json').read_text()), args.username)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg)
    print(json.dumps(stats))
