
sqlite3 -separator ' ' ~/beet_musiclibrary.blb <<< 'select key, value, items.album_id, items.album from item_attributes join items on entity_id = items.id order by key, value*1.0, items.album_id;' > key_diversity.1
cat key_diversity.1 | awk '{print $1, $3}' | uniq -c > key_diversity.2
cat key_diversity.2 | awk '{if ($1 > 1) {a[$2] += $1; print $2, a[$2]}}' > key_diversity.3
cat key_diversity.3 | awk '{if (old != $1) { print prev; old = $1;}; prev = $0}' > key_diversity.4
cat key_diversity.4 | awk '{print $2, $1}' | sort -n > key_diversity.5
