import os
import json
import urllib2
import time
import logging

from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, decargs
from beets import ui

log = logging.getLogger('beets.acou')
deb = log.debug
isa = isinstance
PROBABILITY_THRESHOLD = 0.8
ACOUSTICBRAINZ_URL = "http://acousticbrainz.org/%s/%s"

simi_att = [
    'ab_hl_danceability',
    'ab_hl_gender',
    'ab_hl_genre_dortmund',
    'ab_hl_genre_electronic',
    'ab_hl_genre_rosamerica',
    'ab_hl_genre_tzanetakis',
    'ab_hl_ismir04_rhythm',
    'ab_hl_mood_acoustic',
    'ab_hl_mood_aggressive',
    'ab_hl_mood_electronic',
    'ab_hl_mood_happy',
    'ab_hl_mood_party',
    'ab_hl_mood_relaxed',
    'ab_hl_mood_sad',
    'ab_hl_moods_mirex',
    'ab_hl_timbre',
    'ab_hl_tonal_atonal',
    'ab_hl_voice_instrumental',
]

simi_att1 = ['ab_hl_genre_dortmund']
def _build_first_query(item):
    q = []
    for att in simi_att1:
        if item.get(att):
            q.append('%s:%s' % (att, item.get(att)))
    return u' '.join(q)

acoucache = '/tmp/acoucache'
def _get_all_extrema(lib):
    import marshal
    flush = False
    #flush = True
    if os.path.exists(acoucache) and not flush:
        with open(acoucache) as f:
            ret = marshal.load(f)
    else:
        ret = _get_all_extrema_subcache(lib)
        with open(acoucache, 'w') as f:
            marshal.dump(ret, f)
    return ret

def _get_all_extrema_subcache(lib):
    sql = """
        SELECT
            key,
            min(value*1.0) as min,
            max(value*1.0) as max
        FROM item_attributes
        GROUP BY key
    """
    c = lib._connection().execute(sql)
    r = c.fetchall()
    return {_[0]: (_[1], _[2]) for _ in r}


def _choose_most_extreme_val(item, all_extr):
    curma = 0
    attrs = []
    for att in item:
        if not att.startswith('ab_ll_'):
            continue
        if att in ['ab_ll_status']:
            continue
        val = item.get(att)
        mi, ma = all_extr[att]
        try:
            mi, ma, val = float(mi), float(ma), float(val)
        except ValueError:
            continue
        span = abs(ma - mi)
        if span == 0:
            continue
        diffma = abs(ma - val) / span
        #print att, mi, ma, span, diffma
        if diffma > curma:
            mostma = att
            curma = diffma
        attrs.append((diffma, att))
    attrs.sort()
    return [_ for x, _ in attrs]
    return attrs[0][1], attrs[-1][1]

def _similar_items(lib, item):
    all_extremas = _get_all_extrema(lib)
    attrs = _choose_most_extreme_val(item, all_extremas)
    print attrs
    #qwedqw
    for attr in attrs:
        for simi in _get_simi(attr, item, lib):
            yield simi

def _get_simi(attr, item, lib):
    print
    print ">>> Listing on", attr
    val = item.get(attr)
    sql = """
        SELECT
            av.entity_id,
            abs(av.value*1.0 - ?) as rank
        FROM item_attributes av
        WHERE av.key = ?
            AND av.entity_id != ?
        oRDER BY rank LIMIT 5
    """
    c = lib._connection().execute(sql, (val, attr, item.id))
    on = c.fetchall()
    for simit in on:
        print lib.get_item(simit[0])
    return []

def _get_simi_for_mean_var(attr, item):
    attr_mean = attr + '_mean'
    attr_var = attr + '_var'
    val_var = item.get(attr_var)
    val_mean = item.get(attr_mean)
    sql = """
        SELECT
            av.entity_id,
            abs(av.value - ?) + abs(am.value - ?) as rank
        FROM item_attributes av
        JOIN item_attributes am
            ON av.entity_id = am.entity_id
        WHERE av.key = ?
            AND am.key = ?
            AND av.entity_id != ?
        ORDER BY rank LIMIT 5
    """

    print sql
    c = lib._connection().execute(sql, (val_var, val_mean,
        attr_var, attr_mean, item.id))
    on = c.fetchall()
    print on
    for simit in on:
        print lib.get_item(simit[0])
    return []

def _similar_items_old(lib, item):
    query = _build_first_query(item)
    print query
    bpm = round(float(item.get('ab_ll_bpm', -1)) * 10)
    key = item.get('ab_ll_key_key')
    for simit in lib.items(query):
        if round(float(simit.get('ab_ll_bpm', -1)) * 10) != bpm:
            #print simit, "not same bpm", [bpm, round(float(simit.get('ab_ll_bpm', -1)) * 10)]
            continue
        if simit.get('ab_ll_key_key') != key:
            print "not same key:", [key, simit.get('ab_ll_key_key')]
#            continue
        yield simit


def _should_fetch(tp, item, opts):
    tp_ = {'low-level': 'll', 'high-level': 'hl'}[tp]
    st = item.get('ab_' + tp_ + '_status', 'none')
    if not item.mb_trackid:
        deb("No mb_trackid")
        return False
    if st == 'none':
        return True
    if opts.force:
        return True
    if st == 'missing':
        if opts.missing:
            return True
        else:
            deb("%s data marked as missing in acousticbrainz server", tp)
            return False
    ts = float(st)
    # TODO refetch old entries
    deb("%s data already fetched on %s", tp, ts)
    return False



def acoufetch_func(lib, opts, args):
    query = decargs(args)
    for item in lib.items(query):
        deb("May fetch acoustic data for: %s", item)
        try:
            if _should_fetch('low-level', item, opts):
                data_ll = _fetch('low-level', item.mb_trackid, opts)
                dll = _make_data_ll(data_ll)
                _save_to_lib(item, dll)
                if opts.save:
                    _save_to_file('low-level', opts.save, item.mb_trackid, data_ll)
            if _should_fetch('high-level', item, opts):
                data_hl = _fetch('high-level', item.mb_trackid, opts)
                dhl = _make_data_hl(data_hl)
                _save_to_lib(item, dhl)
                if opts.save:
                    _save_to_file('high-level', opts.save, item.mb_trackid, data_hl)
        except KeyboardInterrupt:
            break
        except Exception, err:
            log.error("Got an error trying to fetch %s: %s", item, err)


def _fetch(tp, mbid, opts):
    if opts.fetched_files_dir:
        return _fetch_from_dir(tp, mbid, opts.fetched_files_dir)
    else:
        time.sleep(0.2)
        return _fetch_from_api(tp, mbid)

def _fetch_from_api(tp, mbid):
    url = ACOUSTICBRAINZ_URL % (mbid, tp)
    deb("Fetching from %r", url)
    try:
        data = urllib2.urlopen(url, timeout=20)
    except urllib2.HTTPError:
        return {}
    try:
        return json.load(data)
    except ValueError as err:
        print "ERROR", mbid, url, err
        return {}

def _fetch_from_dir(tp, mbid, dir_):
    data_path = os.path.join(dir_, "%s.%s" % (mbid, tp))
    if not os.path.exists(data_path):
        return None
    with open(data_path, 'r') as jf:
        try:
            data = json.load(jf)
        except ValueError as err:
            print "Error loading json", data_path, err
            return
    return data

def _make_data_hl(data_hl):
    # TODO maybe check that metadata is matching
    now = time.time()
    if not data_hl:
        return {'ab_hl_status': 'missing'}
    d = {'ab_hl_status': now}
    hl = data_hl['highlevel']
    for k, v in hl.items():
        if v['probability'] > PROBABILITY_THRESHOLD:
            rk = 'ab_hl_' + k
            d[rk] = v['value']
    return d

def _make_data_ll(data_ll):
    now = time.time()
    if not data_ll:
        return {'ab_ll_status': 'missing'}
    d = {'ab_ll_status': now}
    #print data_ll.keys()
    tonal = data_ll['tonal']
    for k, v in tonal.items():
        if isa(v, (float, int, basestring)):
            d['ab_ll_' + k] = v
    rhythm = data_ll['rhythm']
    for k, v in rhythm.items():
        if isa(v, (float, int, basestring)):
            d['ab_ll_' + k] = v
        elif isa(v, dict) and isa(v.get(u'mean'), float):
            d['ab_ll_' + k + '_mean'] = v[u'mean']
            #print v
        elif k == 'beats_position':
            d['ab_ll_beats_positions_join'] = ' '.join(['%.3f' % _ for _ in v])
        else:
            pass
    if 'ab_ll_bpm' in d:
        d['ab_ll_bpm_round'] = int(round(float(d['ab_ll_bpm'])))
    return d

def _save_to_lib(item, data):
    deb("Saved acoustic data on %s", item)
    item.update(data)
    ui.show_model_changes(item)
    item.try_sync(False)  # Todo pass write, see beets/ui/commands.py:1314

def _save_to_file(tp_, dir_, mbid, data):
    path = os.path.join(dir_, "%s.%s" % (mbid, tp_))
    with open(path, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True, separators=(',', ':'))
    deb("Saved data to file %r" % path)

def acou_func(lib, opts, args):
    query = decargs(args)
    items = lib.items(query)
    for item in items:
        print
        print "##", item
        if item.get('ab_ll_bpm') == None:
            print "No acousticbrainz data fetched"
            continue
        for simit in _similar_items(lib, item):
            print simit


acoufetch_cmd = Subcommand('acoufetch', help='fetch acousticbrainz data')
apa = acoufetch_cmd.parser.add_option
apa('--fetched-files-dir', help="if acousticbrainz "
    "jsons have already been fetched in a dir")
apa('-s', '--save',
    help='save acousticbrainz data to files in this dir')
apa('-f', '--force', action='store_true',
    help='force refetching even if data exists already')
apa('-m', '--missing', action='store_true',
    help='force refetching analysis marked as missing in a previous check')
acoufetch_cmd.func = acoufetch_func

acou_cmd = Subcommand('acou', help='fetch acoustic analysis from acousticbrainz.org')
acou_cmd.parser.add_option('--cache-dir', help='path to acoustic data files, use it instead of fetching website')
acou_cmd.func = acou_func


class AcouPlug(BeetsPlugin):
    def __init__(self):
        super(AcouPlug, self).__init__()

    def commands(self):
        return [acou_cmd, acoufetch_cmd]
