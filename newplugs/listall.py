from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, decargs
from beets import ui

listall_cmd = Subcommand('listall', help='List all attributes of an item')
listall_cmd.parser.add_all_common_options()

def listall_items(lib, query, album, fmt=''):
    """Print out items in lib matching query. If album, then search for
    albums instead of single items.
    """
    if album:
        for album in lib.albums(query):
            ui.print_("-- Album: %s" % album)
            _print_all_attrs(album)
            items = list(album.items())
            ui.print_("-- Has %d items:" % len(items))
            for item in items:
                _print_item_in_album(item)
    else:
        for item in lib.items(query):
            _print_all_attrs(item)

def _print_all_attrs(item):
    all_keys = sorted(item.keys())
    longest = max(len(_) for _ in all_keys)
    for k in all_keys:
        fmt = "{0:<%d} {1}" % (longest + 1)
        ui.print_(fmt.format(k, item.get(k)))

def _print_item_in_album(item):
    ui.print_(format(item, "$track - $length - $samplerate - $title"))

def listall_func(lib, opts, args):
    listall_items(lib, decargs(args), opts.album)

listall_cmd.func = listall_func

class ListAllPlug(BeetsPlugin):
    def __init__(self):
        super(ListAllPlug, self).__init__()

    def commands(self):
        return [listall_cmd]
