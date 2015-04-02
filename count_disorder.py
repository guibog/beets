

import sys

prev = ''
sm = 0
for l in sys.stdin:
    l = l.strip()
    l = l.replace('/media/guibog/gpa/zic/paradise/', '')
    genre, _, path = l.partition('/')
    i = 0
    for i in xrange(min(len(prev), len(path))):
        if prev[i] != path[i]:
            break
    prev = path
    sm += i
print sm
