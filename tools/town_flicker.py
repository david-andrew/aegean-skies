#!/usr/bin/env python3
"""Compare a fixed static-surface ROI in matching slow-walk PNG sequences.

Requires Pillow. Numeric PNG names are simulation frame numbers. Excludes final.png.
Example: python3 tools/town_flicker.py before after --roi 82,113,122,157

This is a regression aid, not a general motion-compensated flicker detector:
choose a wall/paving interior that stays in the ROI throughout both walks.
Moving silhouettes, vegetation, grain and antialiasing can produce residuals.
Temporal reversals count large changes that immediately change back, the typical
signature of two differently coloured coincident surfaces winning alternately.
"""
import argparse
import json
import statistics
from pathlib import Path
from PIL import Image


def measure(folder, names, roi, threshold):
    frames = []
    for name in names:
        with Image.open(folder / name) as image:
            rgb = image.convert('RGB')
            assert rgb.getbbox() is not None, f'Blank capture: {folder / name}'
            cropped = rgb.crop(roi)
            frames.append(list(cropped.get_flattened_data() if hasattr(cropped, 'get_flattened_data')
                               else cropped.getdata()))
    changed, reversals = [], []
    for a, b in zip(frames, frames[1:]):
        changed.append(sum(max(abs(x-y) for x, y in zip(p, q)) > threshold
                           for p, q in zip(a, b)))
    for a, b, c in zip(frames, frames[1:], frames[2:]):
        reversals.append(sum(any(abs(y-x) > threshold and abs(z-y) > threshold
                                 and (y-x)*(z-y) < 0 for x, y, z in zip(p, q, r))
                             for p, q, r in zip(a, b, c)))
    return dict(frames=len(frames), changed_pixels=changed,
                median_changed=statistics.median(changed), max_changed=max(changed),
                reversal_pixels=reversals, median_reversals=statistics.median(reversals),
                max_reversals=max(reversals))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--roi', required=True, help='left,top,right,bottom in canvas pixels')
    parser.add_argument('--threshold', type=int, default=30)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    roi = tuple(map(int, args.roi.split(',')))
    assert len(roi) == 4 and roi[2] > roi[0] and roi[3] > roi[1]
    names = sorted((p.name for p in args.before.glob('*.png') if p.stem.isdecimal()),
                   key=lambda n: int(Path(n).stem))
    assert len(names) >= 3 and all((args.after / n).exists() for n in names)
    result = dict(roi=roi, pixels=(roi[2]-roi[0])*(roi[3]-roi[1]),
                  threshold_rgb=args.threshold, frame_numbers=[int(Path(n).stem) for n in names],
                  before=measure(args.before, names, roi, args.threshold),
                  after=measure(args.after, names, roi, args.threshold))
    output = json.dumps(result, indent=2)
    if args.json:
        args.json.write_text(output+'\n')
    print(output)


if __name__ == '__main__':
    main()
