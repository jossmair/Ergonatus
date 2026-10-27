"""Local agenda data. Legacy name/when/done records remain readable unchanged."""
from datetime import datetime, time, timedelta

CATEGORIES = {'Personnel': '#D8AA61', 'École': '#8DA8E8', 'Travail': '#A99BE0',
              'Santé': '#77C9B4', 'Famille': '#DD9BAF'}
SUBJECTS = dict(zip(('Français','Mathématiques','Histoire-géographie','EMC','Anglais','Espagnol','Allemand','Italien','Portugais','Chinois','Arabe','Russe','SVT','Physique-chimie','Technologie','EPS','Arts plastiques','Éducation musicale','Latin','Grec','Langue régionale','Langue des signes','Vie de classe','Documentation','Devoirs faits','Orientation'),
    ('#E49B91','#85B7E9','#D9AF69','#C4A0E1','#82C8B8','#E8AC7A','#A7B8D8','#97C892','#D6A2C1','#D0C27A','#81C8D2','#B5A0D4','#88BD72','#85ACD4','#A3B8B0','#DEAE7F','#D698C7','#B0A0E2','#C5B48B','#9CB4B9','#B4C78A','#D6AEAC','#8FBFBD','#C9B9A2','#A9AAD1','#CAB379')))


SUBJECTS['Rendez-vous'] = '#D8AA61'


def month_days(day):
    import calendar
    return calendar.Calendar(firstweekday=0).monthdatescalendar(day.year,day.month)


def normalize_event(data):
    start = datetime.fromtimestamp(float(data['when']))
    end = float(data.get('end', data['when'] + 3600))
    return dict(name=str(data.get('name', '')).strip(), when=start.timestamp(),
                end=max(end, start.timestamp() + 60), done=bool(data.get('done', False)),
                all_day=bool(data.get('all_day', False)), place=str(data.get('place', '')),
                notes=str(data.get('notes', '')), category=data.get('category', 'Personnel')
                if data.get('category', 'Personnel') in CATEGORIES else 'Personnel',
                deleted=bool(data.get('deleted', False)),
                color=data.get('color','') if isinstance(data.get('color'),str) and len(data.get('color'))==7 and data.get('color').startswith('#') and all(c in '0123456789abcdefABCDEF' for c in data.get('color')[1:]) else '',
                subject=str(data.get('subject','')),school_kind=str(data.get('school_kind','Devoirs')),
                notes_html=str(data.get('notes_html','')),highlight=bool(data.get('highlight',False)))


class Agenda:
    def __init__(self, records):
        self.records = records
        self._revision = None
        self._snapshot = []

    def events(self):
        # A month asks for 42 days. Decode SQLite rows once, while observing both
        # this connection's writes and commits from another connection.
        revision = (self.records.db.total_changes,
                    self.records.db.execute('PRAGMA data_version').fetchone()[0])
        if revision == self._revision:
            return list(self._snapshot)
        result = []
        for key, data in self.records.all('event'):
            try:
                event = normalize_event(data)
            except (KeyError, ValueError, TypeError, OverflowError, OSError):
                continue  # Preserve an unreadable record in the database.
            if not event['deleted']:
                result.append((key, event))
        self._snapshot = sorted(result, key=lambda row: (row[1]['when'], row[0]))
        self._revision = revision
        return list(self._snapshot)

    def on(self, day):
        start = datetime.combine(day, time.min).timestamp()
        end = datetime.combine(day + timedelta(days=1), time.min).timestamp()
        return [(key, event) for key, event in self.events()
                if event['when'] < end and event['end'] > start]

    def save(self, data, key=None):
        if not str(data.get('name', '')).strip():
            raise ValueError('Donnez un titre au rendez-vous.')
        if float(data['end']) <= float(data['when']):
            raise ValueError('La fin doit être après le début.')
        event = normalize_event(data)
        if key is None:
            return self.records.add('event', event)
        self.records.update(key, 'event', event)
        return key

    def delete(self, key, event):
        self.records.update(key, 'event', dict(event, deleted=True))

    def restore(self, key, event):
        self.records.update(key, 'event', dict(event, deleted=False))


def event_time(event, day=None):
    if event['all_day']:
        return 'Toute la journée'
    start = datetime.fromtimestamp(event['when'])
    end = datetime.fromtimestamp(event['end'])
    if day and start.date() < day:
        return 'Suite · jusqu’à ' + end.strftime('%H:%M' if end.date() == day else '%d/%m %H:%M')
    return start.strftime('%H:%M') + ' – ' + end.strftime('%H:%M' if start.date() == end.date() else '%d/%m %H:%M')
