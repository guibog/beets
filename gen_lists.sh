#vim ft=sh

#sqlite3 ~/beet_musiclibrary.blb <<< " select path from item_attributes join items on items.id = entity_id where key = 'ab_ll_melbands_kurtosis_var' order by value; " > all_sorted_by_ab_ll_melbands_kurtosis_var


for f in lists/*; do echo `cat $f |  cut -c-15 | sort | uniq -c | sort | tail -1 | awk '{print $1}'` `basename $f`; done > key_diversity_nb_dupes

for f in lists/*; do echo `cat $f | python count_disorder.py` `basename $f`; done > key_diversity_disorder

cat key_diversity_nb_dupes | awk '{if ($1 < 80) {print $2}}' | while read f; do grep $f key_diversity_disorder; done > key_diversity_disorder.filter

cat key_diversity_disorder.filter | sort -n > key_diversity_disorder.filter.sort
