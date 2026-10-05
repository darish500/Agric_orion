import glob, json, math, os, sys
import cv2
import numpy as np

W, H = 640, 480
HFOV, CAM_H = 1.3, 0.15
F = (W / 2) / math.tan(HFOV / 2)          # about 421 px
CX, CY = W / 2, H / 2

def corridor_polygon(d_far=2.5, d_near=0.4, half_w=0.25):
    pts = []
    for d, sgn in ((d_far, -1), (d_far, 1), (d_near, 1), (d_near, -1)):
        pts.append((int(round(CX + sgn * F * half_w / d)),
                    int(round(CY + F * CAM_H / d))))
    return np.array(pts, np.int32)

def detect(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    chroma = ((hsv[..., 1] > 60) & (hsv[..., 2] > 30)).astype(np.uint8) * 255
    roi = np.zeros((H, W), np.uint8)
    cv2.fillPoly(roi, [corridor_polygon()], 255)
    mask = cv2.bitwise_and(chroma, roi)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, labels, stats, cent = cv2.connectedComponentsWithStats(mask)
    comps = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= 80]
    out = {'visual_obstruction': bool(comps),
           'corridor_occupancy': round(float(mask.sum()) / float(roi.sum()), 4),
           'n_components': len(comps)}
    if comps:
        i = max(comps, key=lambda k: stats[k, cv2.CC_STAT_AREA])
        x, y, w, h, a = (int(v) for v in stats[i])
        cx = float(cent[i][0])
        out['largest_px'] = a
        out['lateral_bin'] = ('left' if cx < CX - 0.08 * W else
                              'right' if cx > CX + 0.08 * W else 'center')
        out['est_range_m'] = round(F * CAM_H / (y + h - CY), 2)
    return out

if __name__ == '__main__':
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/workspace/ros2_ws/stage6_data')
    print(f'cv2 {cv2.__version__}')
    print(f'{"image":14s} obstruction  occupancy  range_m  lateral')
    for p in sorted(glob.glob(os.path.join(folder, '*.png'))):
        r = detect(cv2.imread(p))
        print(f'{os.path.basename(p)[:-4]:14s} {str(r["visual_obstruction"]):11s}  '
              f'{r["corridor_occupancy"]:<9}  {r.get("est_range_m", "-")!s:7s}  {r.get("lateral_bin", "-")}')