"""Write a synthetic hand-drawn-ish sketch so scripts have an input."""
import os, numpy as np, cv2
d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")
os.makedirs(d, exist_ok=True)
img = np.full((360, 620, 3), 255, np.uint8)
for x in (40, 260, 470):
    cv2.rectangle(img, (x, 150), (x + 110, 210), 0, 2)
cv2.arrowedLine(img, (150, 180), (260, 180), 0, 2)
cv2.arrowedLine(img, (370, 180), (470, 180), 0, 2)
cv2.putText(img, "file", (60, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 0, 2)
cv2.putText(img, "review", (270, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 0, 2)
cv2.putText(img, "decide", (480, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 0, 2)
p = os.path.join(d, "CONTRIB-0007_sample.png")
cv2.imwrite(p, img)
print("wrote", p)
