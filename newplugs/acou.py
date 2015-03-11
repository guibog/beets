import os
import json

from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, decargs
from beets import ui

isa = isinstance
PROBABILITY_THRESHOLD = 0.8

acou_cmd = Subcommand('acou', help='do something super')
acou_cmd.parser.add_option('-f', '--file', help='path to acoustic data file')
def acou_func(lib, opts, args):
    print "Hello everybody! I'm a plugin! Acou", opts, args
acou_cmd.func = acou_func

def acoufetch_func(lib, opts, args):
    query = decargs(args)
    for item in lib.items(query):
        if not opts.fetched_files_dir:
            data_ll = _fetch_from_api('low-level', item.mb_trackid)
            data_hl = _fetch_from_api('high-level', item.mb_trackid)
        else:
            data_ll = _fetch_from_dir('low-level', item.mb_trackid, opts.fetched_files_dir)
            data_hl = _fetch_from_dir('high-level', item.mb_trackid, opts.fetched_files_dir)
        if data_ll and data_hl:
            data = _make_data(data_ll, data_hl)
            _save(item, data)
        else:
            print "No data"

def _fetch_from_api(tp, mbid):
    print "TODO", tp, mbid
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


def _make_data(data_ll, data_hl):
    dhl = _make_data_hl(data_hl)
    dll = _make_data_ll(data_ll)
    d = {}
    d.update(dhl)
    d.update(dll)
    return d

def _make_data_hl(data_hl):
    # TODO maybe check that metadata is matching
    hl = data_hl['highlevel']
    d = {}
    for k, v in hl.items():
        if v['probability'] > PROBABILITY_THRESHOLD:
            rk = 'ab_hl_' + k
            d[rk] = v['value']
    return d

def _make_data_ll(data_ll):
    print data_ll.keys()
    d = {}
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
            print v
        else:
            pass
            #print [k, v]
    return d

def _save(item, data):
    print "saving on", item
    item.update(data)
    ui.show_model_changes(item)
    item.try_sync(False)  # Todo pass write, see beets/ui/commands.py:1314

acoufetch_cmd = Subcommand('acoufetch', help='fetch acousticbrainz data')
acoufetch_cmd.parser.add_option('--fetched-files-dir', help="if acousticbrainz "
    "jsons have already been fetched in a dir")
acoufetch_cmd.func = acoufetch_func

class AcouPlug(BeetsPlugin):
    def __init__(self):
        super(AcouPlug, self).__init__()

    def commands(self):
        return [acou_cmd, acoufetch_cmd]
