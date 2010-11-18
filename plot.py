#!/usr/bin/env python

import csv, re, sys

ts = None
nums = re.compile(r'\d\d\d')
minx = float('inf')
w = csv.writer(sys.stdout)
for line in sys.stdin:
  if line.startswith('From '):
    if minx < float('inf'):
      w.writerow((ts, minx))
      minx = float('inf')
    ts = line.split('  ',1)[1].strip()
  else:
    minx = min(minx, int(nums.search(line).group()))
