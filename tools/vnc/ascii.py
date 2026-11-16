#!/usr/bin/env python3
import sys
from PIL import Image
p = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ui.png'
cols = int(sys.argv[2]) if len(sys.argv) > 2 else 60
rows = int(sys.argv[3]) if len(sys.argv) > 3 else 76
im = Image.open(p).convert('L'); w, h = im.size
chars = " .:-=+*#%@"
for j in range(rows):
    s = ''
    for i in range(cols):
        box = (i*w//cols, j*h//rows, (i+1)*w//cols, (j+1)*h//rows)
        v = im.crop(box).resize((1, 1), Image.LANCZOS).getpixel((0, 0))
        s += chars[min(9, v*10//256)]
    print(s)
