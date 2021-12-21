import curses
import sys
import time
from transitions import Machine
import fake_lcd
import keyboard  # using module keyboard


class Messenger(object):
    key = keyboard
    states = ["main_menu", "send_menu", "received_menu", "settings_menu", "set_address", "set_networkid",
              "set_parameters", "compose_message"]

    def __init__(self, lcd_to_use, row=0, col=0):
        self.lcd = lcd_to_use
        self.row = row
        self.col = col
        self.buffer = ""
        # Initialize the state machine

        self.machine = Machine(model=self, states=Messenger.states, initial='main_menu')

        # Add some transitions. We could also define these using a static list of
        # dictionaries, as we did with states above, and then pass the list to
        # the Machine initializer as the transitions= argument.

        self.machine.add_transition(trigger='send_new', source='main_menu', dest='send_menu')
        self.machine.add_transition('back', 'send_menu', 'main_menu')
        self.machine.add_transition('received_menu', 'main_menu', 'received_menu')
        self.machine.add_transition('back', 'received_menu', 'main_menu')
        self.machine.add_transition('settings_menu', 'main_menu', 'settings_menu')
        self.machine.add_transition('set_network', 'settings_menu', 'set_networkid')
        self.machine.add_transition('set_params', 'settings_menu', 'set_parameters')
        self.machine.add_transition('main_menu', '*', 'main_menu', before="print_menu")
        self.machine.add_transition('compose', 'send_menu', 'compose_message')

    def update_screen(self):
        self.lcd.clear()
        state = self.state
        print(state)
        if state == "main_menu":
            self.print_menu()
        if state == "send_menu":
            self.print_send_menu()
        if state == "received_menu":
            self.print_received_menu()
        if state == "settings_menu":
            self.print_settings_menu()

        self.lcd.set_cursor_pos(self.row, self.col)
        self.lcd.draw_cursor()

    def print_menu(self):
        strings = ("* Send", "* Messages", "* Settings")
        row = 0
        for item in strings:
            self.lcd.set_cursor_pos(row, 0)
            self.lcd.print(item)
            row += 1

    def print_send_menu(self):
        strings = ("To:", "Compose", "                   ", "Main menu")
        row = 0
        for item in strings:
            self.lcd.set_cursor_pos(row, 0)
            self.lcd.print(item)
            row += 1

    def print_received_menu(self):
        strings = ("Sender", "                    ", "                    ", "Main menu")
        row = 0
        for item in strings:
            self.lcd.set_cursor_pos(row, 0)
            self.lcd.print(item)
            row += 1

    def print_settings_menu(self):
        strings = ("* Set addr (0-65535)", "* Set ntwk (0-16)", "                    ", "Main menu")
        row = 0
        for item in strings:
            self.lcd.set_cursor_pos(row, 0)
            self.lcd.print(item)
            row += 1

    def on_up(self):
        if self.row > 0:
            self.row -= 1
            self.lcd.set_cursor_pos(self.row, self.col)
            print("Pressing w!")
            print(str(self.row) + ", " + str(self.col))
        self.update_screen()

    def on_left(self):
        if self.col > 0:
            self.col -= 1
            self.lcd.set_cursor_pos(self.row, self.col)
            print("Pressing a!")
            print(str(self.row) + ", " + str(self.col))
        self.update_screen()

    def on_down(self):
        if self.row < self.lcd.height - 1:
            self.row += 1
            self.lcd.set_cursor_pos(self.row, self.col)
            print("Pressing s!")
            print(str(self.row) + ", " + str(self.col))
        self.update_screen()

    def on_right(self):
        if self.col < self.lcd.width - 1:
            self.col += 1
            self.lcd.set_cursor_pos(self.row, self.col)
            print("Pressing d!")
            print(str(self.row) + ", " + str(self.col))
        self.update_screen()

    def on_p(self):
        print("Pressing p!")
        print(self.lcd.current_cursor_pos())
        print(self.state)
        buffer = []

        for x in range(4):
            for y in range(20):
                # buffer.append(self.lcd.get_char(y,x)) = "".join(buffer, chr(self.lcd.window.getch([y,x])))
                print(chr(curses.window.inch(x,y)))
        # print(buffer)

    def on_enter(self):
        print("Pressing enter")
        state = self.state

        if state == "main_menu":
            if self.row == 0 and self.col == 0:
                self.send_new()
                self.row = 0
                self.col = 0
            if self.row == 1 and self.col == 0:
                self.received_menu()
                self.row = 0
                self.col = 0
            if self.row == 2 and self.col == 0:
                self.settings_menu()
                self.row = 0
                self.col = 0
        elif state == "send_menu":
            if self.row == 1 and self.col == 0:
                self.compose()
                self.row = 0
                self.col = 0
            if self.row == 3 and self.col == 0:
                self.main_menu()
                self.row = 0
                self.col = 0
        elif state == "received_menu":
            if self.row == 3 and self.col == 0:
                self.main_menu()
                self.row = 0
                self.col = 0
        elif state == "settings_menu":
            if self.row == 3 and self.col == 0:
                self.main_menu()
                self.row = 0
                self.col = 0
        self.update_screen()

    def write_char(self, st):
        if self.col < self.lcd.width - 1:
            self.lcd.print(st)
            self.col = self.col + 1
            self.lcd.set_cursor_pos(self.row, self.col)
        elif self.row == self.lcd.height - 2 and self.col == self.lcd.width - 1:
            pass
        else:
            self.row = self.row + 1
            self.col = 0
            self.lcd.print(st)
            self.lcd.set_cursor_pos(self.row, self.col)

    def space(self):
        self.lcd.print(" ")
        self.col = self.col + 1
        self.lcd.set_cursor_pos(self.row, self.col)

    def delete(self):
        if self.col > 0:
            self.lcd.delete(self.col, self.row)
            self.col = self.col - 1
            print("this works")
            print(self.col)
            print(self.row)
            self.lcd.set_cursor_pos(self.row, self.col)
            self.lcd.delete(self.col, self.row)
            self.lcd.draw_cursor()

        elif self.row == self.lcd.height - self.lcd.height and self.col == self.lcd.width - self.lcd.width:
            pass
        else:
            self.lcd.delete(self.col, self.row)
            self.col = self.lcd.width - 1
            self.row = self.row - 1
            self.lcd.set_cursor_pos(self.row, self.col)
            self.lcd.delete(self.col, self.row)
            self.lcd.print(chr(9608))


if __name__ == '__main__':
    key = keyboard
    flcd = fake_lcd.Fake_lcd()
    main = Messenger(flcd)

    main.update_screen()
    flcd.set_cursor_pos(0, 0)

    key.add_hotkey("w+right_shift", main.on_up)
    key.add_hotkey("a+right_shift", main.on_left)
    key.add_hotkey("s+right_shift", main.on_down)
    key.add_hotkey("d+right_shift", main.on_right)
    key.add_hotkey("p+right_shift", main.on_p)
    key.add_hotkey("enter", main.on_enter)
    key.add_hotkey("space", main.space)
    key.add_hotkey("backspace", main.delete)
    key.add_hotkey("q", main.write_char, args=["q"], suppress=True)
    key.add_hotkey("w", main.write_char, args=["w"], suppress=True)
    key.add_hotkey("e", main.write_char, args=["e"], suppress=True)
    key.add_hotkey("r", main.write_char, args=["r"], suppress=True)
    key.add_hotkey("t", main.write_char, args=["t"], suppress=True)
    key.add_hotkey("y", main.write_char, args=["y"], suppress=True)
    key.add_hotkey("u", main.write_char, args=["u"], suppress=True)
    key.add_hotkey("i", main.write_char, args=["i"], suppress=True)
    key.add_hotkey("o", main.write_char, args=["o"], suppress=True)
    key.add_hotkey("p", main.write_char, args=["p"], suppress=True)
    key.add_hotkey("a", main.write_char, args=["a"], suppress=True)
    key.add_hotkey("s", main.write_char, args=["s"], suppress=True)
    key.add_hotkey("d", main.write_char, args=["d"], suppress=True)
    key.add_hotkey("f", main.write_char, args=["f"], suppress=True)
    key.add_hotkey("g", main.write_char, args=["g"], suppress=True)
    key.add_hotkey("h", main.write_char, args=["h"], suppress=True)
    key.add_hotkey("j", main.write_char, args=["j"], suppress=True)
    key.add_hotkey("k", main.write_char, args=["k"], suppress=True)
    key.add_hotkey("l", main.write_char, args=["l"], suppress=True)
    key.add_hotkey("z", main.write_char, args=["z"], suppress=True)
    key.add_hotkey("x", main.write_char, args=["x"], suppress=True)
    key.add_hotkey("c", main.write_char, args=["c"], suppress=True)
    key.add_hotkey("v", main.write_char, args=["v"], suppress=True)
    key.add_hotkey("b", main.write_char, args=["b"], suppress=True)
    key.add_hotkey("n", main.write_char, args=["n"], suppress=True)
    key.add_hotkey("m", main.write_char, args=["m"], suppress=True)


    key.wait("q+right_shift")
