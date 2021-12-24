import curses


class Fake_lcd(object):
    screen_buffer = None
    width = None
    height = None
    cursor_pos = None
    cursor_vis = None


    def __init__(self, width=20, height=4):
        self.width = width
        self.height = height
        self.screen = curses.initscr()
        self.window = curses.newwin(height, width, 0, 0)
        self.cursor_pos = (0, 0)
        self.cursor_vis = curses.curs_set(1)
        curses.noecho()

    def print(self, st):
        st = st.replace("\n","")
        st = st.replace("\r","")
        if self.cursor_pos[1] < self.width-1:
            self.window.addstr(self.cursor_pos[1], self.cursor_pos[0], st)
        else:
            print("string too long")

        self.window.refresh()

    def clear(self):
        self.window = curses.newwin(self.height, self.width, 0, 0)
        self.screen.clear()
        self.screen.refresh()

    def set_cursor_pos(self, row, col):
        self.cursor_pos = (col, row)

    def delete(self, y, x):
        self.window.delch(x,y)

    def current_cursor_pos(self):
        current_pos = self.cursor_pos
        return current_pos

    def draw_cursor(self):
        self.print(chr(9608))

    # def get_char(self, y, x):
    #     print(chr(self.window.inch(y,x)))
    #     # print(str(self.window.inch([y, x])))
