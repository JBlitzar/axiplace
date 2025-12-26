from pyaxidraw import axidraw
import numpy as np
import signal
import sys
import os

ad = axidraw.AxiDraw()
ad.interactive()
connected = ad.connect()

if not connected:
    print("Could not connect to plotter!")
    exit(1)

ad.penup()

cell2inch = 11 / 22 # 11 inches per 22 cells
banned_cells = {(0,0), (31,0), (0,17), (31,17)}
def bezier(cell_x, cell_y, params):
    connected = ad.connect()

    if not connected:
        ad.disconnect()
        print("Could not connect to plotter!")
        exit(1)
    
    if (cell_x, cell_y) in banned_cells:
        ad.disconnect()
        return
    


    x1, y1 = params[0]
    x2, y2 = params[1]
    x3, y3 = params[2]
    x4, y4 = params[3]
    flattened = [x1, y1, x2, y2, x3, y3, x4, y4]
    if any(v is None for v in flattened):
        ad.disconnect()
        return
    if any(not (0 <= v <= 1) for v in flattened):
        ad.disconnect()
        return
    ad.penup()
    points = 100
    flag = False
    
    for t in np.linspace(0, 1, points):
        
        x = (
            (1 - t) ** 3 * x1
            + 3 * (1 - t) ** 2 * t * x2
            + 3 * (1 - t) * t ** 2 * x3
            + t ** 3 * x4
        )
        y = (
            (1 - t) ** 3 * y1
            + 3 * (1 - t) ** 2 * t * y2
            + 3 * (1 - t) * t ** 2 * y3
            + t ** 3 * y4
        )
        ad.goto((cell_x + x) * cell2inch, (cell_y + y) * cell2inch)
        if not flag:
            flag = True
            ad.pendown()

    ad.penup()
    ad.goto(0, 0)
    ad.disconnect()



# def cleanup(signum=None, frame=None):
#     print("\nCleaning up...")
#     ad.penup()
#     ad.goto(0, 0)
#     ad.disconnect()
#     print("Done!")
#     os.system("axi off")
#     sys.exit(0)

# signal.signal(signal.SIGTERM, cleanup)
# signal.signal(signal.SIGINT, cleanup)