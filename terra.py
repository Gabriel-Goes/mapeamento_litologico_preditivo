"""
===========================
Interface do Preditor Terra
===========================

"""

import tkinter 

from matplotlib.backends.backend_tkagg import(
        FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

import numpy as np


root = tkinter.Tk()
root.wm_title("Preditor Terra")

fig = Figure(figsize=(5,4),dpi=100)
t = np.arrange(0,3,.01)
ax = fig.add_subplot()
line, = ax.plot(t, 2
