import tkinter as tk


class Example(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        menubutton = tk.Menubutton(self, text="Choose wisely",
                                   indicatoron=True, borderwidth=1,
                                   relief="raised")
        menu = tk.Menu(menubutton, tearoff=False)
        menubutton.configure(menu=menu)
        menubutton.pack(padx=10, pady=10)

        self.choices = {}
        for choice in ("Iron Man", "Superman", "Batman"):
            self.choices[choice] = tk.IntVar(value=0)
            menu.add_checkbutton(label=choice, variable=self.choices[choice],
                                 onvalue=1, offvalue=0,
                                 command=self.printValues)

    def printValues(self):
        for name, var in self.choices.items():
            print("%s: %s" % (name, var.get()))


if __name__ == "__main__":
    root = tk.Tk()
    Example(root).pack(fill="both", expand=True)
    root.mainloop()
