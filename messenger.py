import curses
import sys
import time
from transitions import Machine
import fake_lcd
import keyboard  # using module keyboard


class Messenger(object):
    key = keyboard
    states = ["main_menu", "send_menu", "received_menu", "settings_menu", "set_address", "set_networkid",
              "set_parameters", "compose_message", "sender_list"]

    def __init__(self, lcd_to_use, row=0, col=0):
        self.lcd = lcd_to_use
        self.lcd.home = (0, 0)
        self.row = row
        self.col = col
        self.buffer = ""
        self.menus = {"main menu": ("* Send", "* Messages", "* Settings"),
                      "send menu": ("To:", "Compose", "", "Main menu"),
                      "received menu": ("Sender", "", "", "Main menu"),
                      "settings menu": ("* Set addr (0-65535)", "* Set ntwk (0-16)", "", "Main menu"),
                      "compose message": ("", "", "", "Main menu"),
                      "sender list": ("", "", "", "Main menu")}

        self.input_buffer = ""
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
        self.machine.add_transition('main_menu', '*', 'main_menu')
        self.machine.add_transition('compose_message', 'send_menu', 'compose_message')
        self.machine.add_transition('sender_list', 'received_menu', 'sender_list')

    def update_screen(self):
        self.lcd.clear()
        state = self.state
        print(state)
        if state == "main_menu":
            self.print_menu(self.menus["main menu"])
        if state == "send_menu":
            self.print_menu(self.menus["send menu"])
        if state == "received_menu":
            self.print_menu(self.menus["received menu"])
        if state == "settings_menu":
            self.print_menu(self.menus["settings menu"])
        if state == "compose_message":
            self.print_menu(self.menus["compose message"])
        if state == "sender_list":
            self.print_menu(self.menus["sender list"])

        self.print_input_buffer()
        self.lcd.set_cursor_pos(self.row, self.col)
        self.lcd.draw_cursor()

    def print_menu(self, strings):
        # strings = ("* Send", "* Messages", "* Settings")
        row = 0
        for item in strings:
            self.lcd.set_cursor_pos(row, 0)
            self.lcd.print(item)
            row += 1

    def print_input_buffer(self):
        state = self.state
        if state == "compose_message":
            row = 0
            col = 0
            self.lcd.set_cursor_pos(row, col)
            for char in self.input_buffer:
                if col < self.lcd.width - 1:
                    self.lcd.print(char)
                    col += 1
                    self.lcd.set_cursor_pos(row, col)
                elif row == self.lcd.height - 2 and col == self.lcd.width - 1:
                    pass
                else:
                    row += 1
                    col = 0
                    self.lcd.print(char)
                    self.lcd.set_cursor_pos(row, col)
                self.row = row
                self.col = col
            self.lcd.set_cursor_pos(self.row, self.col)

        if state == "send_menu":
            row = 0
            col = 3
            self.lcd.set_cursor_pos(row, col)
            for char in self.input_buffer:
                if col <= self.col < self.lcd.width - 1:
                    self.lcd.print(char)
                    col += 1
                    self.lcd.set_cursor_pos(row, col)
                elif row == self.lcd.height - 2 and col == self.lcd.width - 1:
                    pass
                else:
                    row += 1
                    col = 0
                    self.lcd.print(char)
                    self.lcd.set_cursor_pos(row, col)
                self.row = row
                self.col = col
            self.lcd.set_cursor_pos(self.row, self.col)

    def on_up(self):
        if self.row > 0:
            self.row -= 1
            self.lcd.set_cursor_pos(self.row, self.col)
        self.update_screen()

    def on_left(self):
        if self.state == "send_menu":
            if self.row > 0:
                self.col -= 1
                self.lcd.set_cursor_pos(self.row, self.col)
            self.update_screen()

    def on_down(self):

        if self.row < self.lcd.height - 1:
            self.row += 1
            self.lcd.set_cursor_pos(self.row, self.col)
        self.update_screen()

    def on_right(self):
        if self.col < self.lcd.width - 1:
            self.col += 1
            self.lcd.set_cursor_pos(self.row, self.col)
        self.update_screen()

    def on_p(self):
        print(self.lcd.current_cursor_pos())
        print(self.state)

    def on_enter(self):
        print("Pressing enter")
        state = self.state

        if state == "main_menu":
            if self.row == 0 and self.col == 0:
                self.send_new()
                self.row = 0
                self.col = 3
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
                self.compose_message()
                self.row = 0
                self.col = 0
            if self.row == 3 and self.col == 0:
                self.main_menu()
                self.row = 0
                self.col = 0
        elif state == "compose_message":
            if self.row == 3 and self.col == 0:
                self.main_menu()
                self.row = 0
                self.col = 0
        elif state == "received_menu":
            if self.row == 0 and self.col == 0:
                self.sender_list()
                self.row = 0
                self.col = 0
            if self.row == 3 and self.col == 0:
                self.main_menu()
                self.row = 0
                self.col = 0
        elif state == "sender_list":
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
        self.input_buffer += st
        self.update_screen()

    def print_char(self, st):
        state = self.state
        if state == "compose_message":
            if self.col < self.lcd.width - 1:
                self.lcd.print(st)
                self.col += 1
                self.lcd.set_cursor_pos(self.row, self.col)
            elif self.row == self.lcd.height - 2 and self.col == self.lcd.width - 1:
                pass
            else:
                self.row = self.row + 1
                self.col = 0
                self.lcd.print(st)
                self.lcd.set_cursor_pos(self.row, self.col)

        elif state == "send_message":
            if self.col < self.lcd.width - 1:
                self.lcd.print(st)
                self.col = self.col + 1
                self.lcd.set_cursor_pos(self.row, self.col)
            elif self.row == self.lcd.height - 2 and self.col == self.lcd.width - 1:
                pass
            else:
                self.row = self.row + 1
                self.col = 0
                self.lcd.set_cursor_pos(self.row, self.col)
        else:
            pass


    def delete(self):
        if self.col > 0:
            self.lcd.delete(self.col, self.row)
            delete_chr = " "
            self.input_buffer = self.input_buffer[:len(self.input_buffer)-1]
            # self.input_buffer = self.input_buffer[]
            self.col = self.col - 1
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
    key.add_hotkey("space", main.write_char, args=[" "], suppress=True)
    key.add_hotkey("backspace", main.delete)
    key.add_hotkey("q", main.print_char, args=["q"], suppress=True)
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
    key.add_hotkey("0", main.write_char, args=["0"], suppress=True)
    key.add_hotkey("1", main.write_char, args=["1"], suppress=True)
    key.add_hotkey("2", main.write_char, args=["2"], suppress=True)
    key.add_hotkey("3", main.write_char, args=["3"], suppress=True)
    key.add_hotkey("4", main.write_char, args=["4"], suppress=True)
    key.add_hotkey("5", main.write_char, args=["5"], suppress=True)
    key.add_hotkey("6", main.write_char, args=["6"], suppress=True)
    key.add_hotkey("7", main.write_char, args=["7"], suppress=True)
    key.add_hotkey("8", main.write_char, args=["8"], suppress=True)
    key.add_hotkey("9", main.write_char, args=["9"], suppress=True)



    key.wait("q+right_shift")
