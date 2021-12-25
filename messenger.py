import curses
import sys
import time
from transitions import Machine
import fake_lcd
import keyboard  # using module keyboard
import fake_rylr896


class Messenger(object):
    key = keyboard
    states = ["main_menu", "send_menu", "received_menu", "settings_menu", "set_address", "set_networkid",
              "set_parameters", "compose_message", "sender_list", "sending_message", "send_failed", "send_successful",
              "setting_address", "setting_networkid"]

    def __init__(self, lcd_to_use, lora, row=0, col=0):
        """
        :param lcd_to_use: We are using a 2004a LCD display
        :param lora: currently using the RYLR896 with library
        :param row: sets the default row for the cursor
        :param col: sets the default column for the cursor
        """
        self.lcd = lcd_to_use
        self.lora = lora
        self.lcd.home = (0, 0)
        self.row = row
        self.col = col
        # keeps track of the end of the input string
        self.text_col = 0
        # keeps track of the end of the input string
        self.text_row = 0
        # initializes the state of the machine
        self.state = None
        # dictionary of all menus to write to the screen depending on the state
        self.menus = {"main menu": ("* Send", "* Messages", "* Settings"),
                      "send menu": ("To:", "Compose", "", "M"),
                      "received menu": ("Messages", "", "", "M"),
                      "settings menu": ("* Set addr (0-65535)", "* Set ntwk (0-16)", "", "M"),
                      "compose message": ("Send:", "", "", "M B"),
                      "sender list": ("", "", "", "M N L D"),
                      "sending message": ("Sending message", "", "", ""),
                      "send failed": ("Send failed", "", "", ""),
                      "send successful": ("Send successful", "", "", ""),
                      "setting address": ("Set addr (0-65535)", "", "enter", "M"),
                      "setting networkid": ("* Set ntwk (0-16)", "", "enter", "M"),
                      }
        # error message variable to use
        self.error_message = None
        # used to store date before being sent
        self.data_to_send = {}
        # used to store last sent message
        self.last_sent = {}
        # buffer to store input string
        self.input_buffer = ""
        # Initialize the state machine
        self.machine = Machine(model=self, states=Messenger.states, initial='main_menu')

        # Add some transitions. We could also define these using a static list of
        # dictionaries, and then pass the list to the Machine initializer as the
        # transitions= argument.

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
        self.machine.add_transition('back', 'compose_message', 'send_menu')
        self.machine.add_transition('sending_message', 'compose_message', 'sending_message')
        self.machine.add_transition('send_failed', 'sending_message', 'send_failed')
        self.machine.add_transition('send_successful', 'sending_message', 'send_successful')
        self.machine.add_transition('setting_address', 'settings_menu', 'setting_address')
        self.machine.add_transition('setting_networkid', 'settings_menu', 'setting_networkid')

        self.listening = True
        self.running = True
        self.last_received = {
                            "address": None,
                            "length": None,
                            "data": None,
                            "rssi": None,
                            "snr": None,
                            "time": None,
                            "hash": None
                            }
        # self.last_received = {'address': 65523, 'length': 24, 'data': 'r`l_qgnlai__ojscpflejacf', 'rssi': -5, 'snr': 42,
        #  'time': 1640356965.7930956,
        #  'hash': b'7\x81\xc1;\x15s\xed\xbf\x04\x11p\xd92nW"B\x85V\x89\x08\xc5\xac*l\x8f\x15U\xc4\xcacf'}
        self.messages = [
                         ]
        self.contacts = {"josh": 2}
        self.mailbox_full = False
        self.message_count = 0
        self.sheet = 0
        self.current_message = None


    def update_screen(self):
        """
        refreshes the screen after an event
        :return:
        """
        # clears the LCD
        self.lcd.clear()
        # checks the current state of the machine
        if self.state == "main_menu":
            # prints the menu screen
            self.print_menu(self.menus["main menu"])
            # if there is an error it will display it on the bottom line
            if self.error_message is not None:
                # prints the error message
                self.print_error(self.error_message)
        # checks the current state of the machine
        if self.state == "send_menu":
            # prints the send menu screen
            self.print_menu(self.menus["send menu"])
            # if there is an error it will display it on the bottom line
            if self.error_message is not None:
                # prints the error message
                self.print_error(self.error_message)
        # checks the current state of the machine
        if self.state == "received_menu":
            # prints the received menu screen
            self.print_menu(self.menus["received menu"])
            # if there is an error it will display it on the bottom line
            if self.error_message is not None:
                # prints the error message
                self.print_error(self.error_message)
        if self.state == "sender_list":
            # prints the received menu screen
            self.print_menu(self.menus["sender list"])
            # if there is an error it will display it on the bottom line
            if self.error_message is not None:
                # prints the error message
                self.print_error(self.error_message)
            elif self.messages is not None:
                self.print_message()
        # checks the current state of the machine
        if self.state == "settings_menu":
            # prints the settings menu screen
            self.print_menu(self.menus["settings menu"])
            # if there is an error it will display it on the bottom line
            if self.error_message is not None:
                # prints the error message
                self.print_error(self.error_message)
        # checks the current state of the machine
        if self.state == "setting_address":
            # prints the setting address screen
            self.print_menu(self.menus["setting address"])
            # if there is an error it will display it on the bottom line
            if self.error_message is not None:
                # prints the error message
                self.print_error(self.error_message)
        # checks the current state of the machine
        if self.state == "setting_networkid":
            # prints the setting network screen
            self.print_menu(self.menus["setting networkid"])
            # if there is an error it will display it on the bottom line
            if self.error_message is not None:
                # prints the error message
                self.print_error(self.error_message)
        # checks the current state of the machine
        if self.state == "compose_message":
            # prints the compose message screen
            self.print_menu(self.menus["compose message"])
            # if there is an error it will display it on the bottom line
            if self.error_message is not None:
                # prints the error message
                self.print_error(self.error_message)
        # checks the current state of the machine
        if self.state == "send_successful":
            # prints the send successful screen
            self.print_menu(self.menus["send successful"])
            # if there is an error it will display it on the bottom line
            if self.error_message is not None:
                # prints the error message
                self.print_error(self.error_message)
            # gives 3 seconds to read the screen
            time.sleep(3)
            # returns to main menu state
            self.main_menu()
            # refreshes the screen
            self.update_screen()
        # checks the current state of the machine
        if self.state == "send_failed":
            # prints the send failed screen
            self.print_menu(self.menus["send failed"])
            # if there is an error it will display it on the bottom line
            if self.error_message is not None:
                # prints the error message
                self.print_error(self.error_message)
                # gives 3 seconds to read the screen
                time.sleep(3)
                # returns to main menu state
                self.main_menu()
                # refreshes the screen
                self.update_screen()
        # checks the current state of the machine
        if self.state == "sending_message":
            self.listening = False
            # prints the sending message screen
            self.print_menu(self.menus["sending message"])
            # if there is an error it will display it on the bottom line
            if self.error_message is not None:
                # prints the error message
                self.print_error(self.error_message)
            # sends the data and if returns True....
            if self.lora.send(str(self.data_to_send["data"]), self.data_to_send["address"]):
                # saves the data as last_sent for future use
                self.last_sent = self.data_to_send
                # transitions to the send_successful state
                self.send_successful()
                # clears data_to_send for the next message
                self.data_to_send = {}
                self.listening = True
            else:
                # if False transitions to the send_failed state
                self.sending_message()
            # refreshes the screen
            self.update_screen()
        # prints the input buffer to the screen
        if self.input_buffer != "":
            self.print_input_buffer()
        # sets the cursor to the current row and col
        self.lcd.set_cursor_pos(self.row, self.col)
        # draws the cursor and the cursor position
        self.lcd.draw_cursor()

    # prints the menu to the screen
    # uses a list of strings with a string on each row of the LCD
    # example: ("* Send", "* Messages", "* Settings")
    # best to use a dictionary of possible strings
    def print_menu(self, strings):
        # strings = ("* Send", "* Messages", "* Settings")
        row = 0
        # loops through the strings and prints each one a row
        for item in strings:
            # sets the cursor where to print
            self.lcd.set_cursor_pos(row, 0)
            # prints the string
            self.lcd.print(item)
            # increments to the next row
            row += 1

    def print_message(self):
        space = " "
        length_of_address = len(str(self.messages[self.current_message]["address"]))
        space = space * (11 - length_of_address)
        string_to_print = "Sender = " + str(self.messages[self.current_message]["address"]) + space +"Data = "+ str(self.messages[self.current_message]["data"])
        self.scroll(string_to_print, self.sheet)


    def scroll(self, string, sheet=0, num_lines_to_show=3):
        row = 0
        col = 0
        self.lcd.set_cursor_pos(row, col)
        start = sheet * self.lcd.width
        end = (sheet + num_lines_to_show) * self.lcd.width
        if len(string) < num_lines_to_show * self.lcd.height:
            for char in string:
                self.lcd.set_cursor_pos(row, col)
                self.lcd.print(char)
                if col < self.lcd.width - 1:
                    # Char was placed on current line. No need to reposition cursor.
                    col += 1

                else:
                    # At end of line: go to left side next row. Wrap around to first row if on last row.
                    row += 1
                    col = 0

        else:
            for char in string[start:end]:
                self.lcd.set_cursor_pos(row, col)
                self.lcd.print(char)
                if col < self.lcd.width - 1:
                    # Char was placed on current line. No need to reposition cursor.
                    col += 1
                else:
                    row += 1
                    col = 0

        self.lcd.set_cursor_pos(self.row, self.col)


    def print_error(self, error_message: str):
        """
        put an error message on the menu bar
        :param error_message: the error message to use
        :return: None
        """
        # raises an error when the length of the error message is more than 10
        if len(error_message) > 10:
            raise "Error message too long"
        # sets the row to print
        row = 3
        # sets the column to print
        col = 10
        # loops through the characters of the string
        for char in error_message:
            # sets the cursor where to print
            self.lcd.set_cursor_pos(row, col)
            # prints the character
            self.lcd.print(char)
            # increments the col until it gets to the second to last cell
            if col < 18:
                col += 1
            else:
                # self explanatory
                raise "String cannot print to bottom right cell of LCD. " \
                      "Crashes for some reason and i am too dumb to figure " \
                      "out why so I just don't print that far."
        # sets the cursor back to the users cursor position
        self.lcd.set_cursor_pos(self.row, self.col)

    def print_input_buffer(self):
        """
        Prints the input buffer to the screen based on what state the machine is in.
        :return:
        """
        # checks the state of the machine
        if self.state == "compose_message":
            # sets the row to print on
            row = 0
            # sets the col to print on
            col = 5
            # sets the cursor where to print
            self.lcd.set_cursor_pos(row, col)
            # loops through the characters in the input buffer
            for char in self.input_buffer:
                # checks to make sure its not printing on the last column of the row
                if col < self.lcd.width - 1:
                    # prints the character
                    self.lcd.print(char)
                    # increments the column
                    col += 1
                    # moves the cursor to the next col
                    self.lcd.set_cursor_pos(row, col)
                # checks to see if we are on the last column in line 3 and if so passes
                elif row == self.lcd.height - 2 and col == self.lcd.width - 1:
                    pass
                # prints to the next row
                else:
                    # increments to next row
                    row += 1
                    # sets column back to zero
                    col = 0
                    # prints the character
                    self.lcd.print(char)
                    # moves the cursor to the next col
                    self.lcd.set_cursor_pos(row, col)
                # saves the col of the end of the input buffer
                self.text_col = col
                # saves the row of the end of the input buffer
                self.text_row = row
            # sets the cursor back to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)
        # checks the state of the machine
        if self.state == "send_menu":
            # sets the row to print on
            row = 0
            # sets the col to print on
            col = 3
            # sets the cursor where to print
            self.lcd.set_cursor_pos(row, col)
            # loops through the characters in the input buffer
            for char in self.input_buffer:
                # checks to make sure its not printing on the last column of the row
                if col <= self.lcd.width - 1:
                    # prints the character
                    self.lcd.print(char)
                    # increments the column
                    col += 1
                    # moves the cursor to the next col
                    self.lcd.set_cursor_pos(row, col)
                # checks to see if we are on the last column in line 1 and if so passes
                elif row == self.lcd.height - 3 and col == self.lcd.width - 1:
                    pass
                # passes on every row except the first
                elif row < self.lcd.height - 3:
                    pass
                # saves the col of the end of the input buffer
                self.text_row = row
                # saves the row of the end of the input buffer
                self.text_col = col
            # sets the cursor back to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)
        # checks the state of the machine
        if self.state == "setting_address":
            # sets the row to print on
            row = 1
            # sets the col to print on
            col = 0
            # sets the cursor where to print
            self.lcd.set_cursor_pos(row, col)
            # loops through the characters in the input buffer
            for char in self.input_buffer:
                # checks to make sure its not printing on the last column of the row
                if col <= self.lcd.width - 1:
                    # prints the character
                    self.lcd.print(char)
                    # increments the column
                    col += 1
                    # moves the cursor to the next col
                    self.lcd.set_cursor_pos(row, col)
                # checks to see if we are on the last column in line 3 and if so passes
                elif row == self.lcd.height - 3 and col == self.lcd.width - 1:
                    pass
                # passes on every row except the first
                elif row < self.lcd.height - 3:
                    pass
                # saves the col of the end of the input buffer
                self.text_row = row
                # saves the row of the end of the input buffer
                self.text_col = col
            # sets the cursor back to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)
        # checks the state of the machine
        if self.state == "setting_networkid":
            # sets the row to print on
            row = 1
            # sets the col to print on
            col = 0
            # sets the cursor where to print
            self.lcd.set_cursor_pos(row, col)
            # loops through the characters in the input buffer
            for char in self.input_buffer:
                # checks to make sure its not printing on the last column of the row
                if col < self.lcd.width - 1:
                    # prints the character
                    self.lcd.print(char)
                    # increments the column
                    col += 1
                    # moves the cursor to the next col
                    self.lcd.set_cursor_pos(row, col)
                # checks to see if we are on the last column in line 3 and if so passes
                elif row == self.lcd.height - 2 and col == self.lcd.width - 1:
                    pass
                # prints to the next row
                else:
                    # increments to next row
                    row += 1
                    # sets column back to zero
                    col = 0
                    # prints the character
                    self.lcd.print(char)
                    # moves the cursor to the next col
                    self.lcd.set_cursor_pos(row, col)
                # saves the col of the end of the input buffer
                self.text_col = col
                # saves the row of the end of the input buffer
                self.text_row = row
            # sets the cursor back to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)
        else:
            pass

    def on_up(self):
        """
        Moves the cursor up
        :return:
        """
        # checks to make sure cursor is not on the last row
        if self.row > 0:
            # increments the row
            self.row -= 1
            # moves the cursor to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)
        else:
            if self.sheet > 0:
                self.sheet -= 1
            pass
        # refreshes the screen
        self.update_screen()

    def on_left(self):
        """
        Moves the cursor left
        :return:
        """
        # checks if the cursor is on the last column
        if self.col > 0:
            # decrements the column
            self.col -= 1
            # moves the cursor to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)
        else:
            pass
        # refreshes the screen
        self.update_screen()

    def on_down(self):
        """
        Moves the cursor down
        :return:
        """
        # checks to make sure the cursor is not on the bottom row
        if self.row < self.lcd.height - 1:
            # increments the row
            self.row += 1
            # moves the cursor to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)
        else:
            self.sheet += 1
            pass
        self.update_screen()

    def on_right(self):
        """
        Moves the cursor right
        :return:
        """
        # checks to make sure the cursor is not on the last column
        if self.col < self.lcd.width - 1:
            # increments the column
            self.col += 1
            # moves the cursor to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)
        else:
            pass
        # refreshes the screen
        self.update_screen()

    def on_p(self):
        """
        Used for testing purposes
        """
        # print(self.lcd.current_cursor_pos())
        # print(self.state)
        # print(self.input_buffer)
        # print(self.data_to_send)
        # print(self.last_received)
        print(self.messages)
        pass

    def on_enter(self):
        """
        Excutes the transitions from state to state
        :return:
        """
        state = self.state
        # checks the current state
        if state == "main_menu":
            # checks if the the cursor is at 0,0
            if self.row == 0 and self.col == 0:
                # transitions to the send_new state
                self.send_new()
            # checks if the the cursor is at 1,0
            if self.row == 1 and self.col == 0:
                # transitions to the received_menu state
                self.received_menu()
            # checks if the the cursor is at 2,0
            if self.row == 2 and self.col == 0:
                # transitions to the received_menu state
                self.settings_menu()
            else:
                pass
        # checks the current state
        elif state == "send_menu":
            # checks if the the cursor is at 1,0
            if self.row == 1 and self.col <= 7:
                # checks if the input buffer is empty and if so passes
                if self.input_buffer != "":
                    # transitions to the compose_menu state
                    self.compose_message()
                    # sets the data_to_send address
                    self.data_to_send["address"] = int(self.input_buffer)
                    # clears the input buffer
                    self.input_buffer = ""
                pass
            # checks if the the cursor is at 3,0
            elif self.row == 3 and self.col == 0:
                # transitions to the main_menu state
                self.main_menu()
                # clears the input buffer
                self.input_buffer = ""
            else:
                pass
        # checks the current state
        elif state == "compose_message":
            # checks if the the cursor is at 3,0
            if self.row == 3 and self.col == 0:
                # transitions to the main_menu state
                self.main_menu()
                # clears the input buffer
                self.input_buffer = ""
            # checks if the the cursor is at 3,2
            elif self.row == 3 and self.col == 2:
                # transitions to the send_menu state
                self.send_menu()
                # clears the input buffer
                self.input_buffer = ""
            # checks if the the cursor is at 3,4
            elif self.row == 0 and self.col <= 5:
                # transitions to the sending_message state
                self.sending_message()

                # checks to make sure there is data to send
                if self.input_buffer is not None:
                    self.data_to_send["data"] = str(self.input_buffer)
                # clears the input buffer
                self.input_buffer = ""
            else:
                pass
        # checks the current state
        elif state == "received_menu":
            # checks if the the cursor is at 0,0
            if self.row == 0 and self.col == 0:
                # transitions to the sender_list state
                self.sender_list()
                # resets to last received message
                self.current_message = -1
            # checks if the the cursor is at 3,0
            if self.row == 3 and self.col == 0:
                # transitions to the main_menu state
                self.main_menu()

                self.input_buffer = ""
            else:
                pass
        # checks the current state
        elif state == "sender_list":
            # checks if the the cursor is at 3,0
            if self.row == 3 and self.col == 0:
                # transitions to the main_menu state
                self.main_menu()
                # clears the input buffer
                self.input_buffer = ""
            # checks if the the cursor is at 3,2
            if self.row == 3 and self.col == 2:
                # goes to next message
                self.current_message += 1
                # resets view window
                self.sheet = 0
                # clears the input buffer
                self.input_buffer = ""
            # checks if the the cursor is at 3,4
            if self.row == 3 and self.col == 4:
                # goes to last message
                self.current_message -= 1
                # resets view window
                self.sheet = 0
                # clears the input buffer
                self.input_buffer = ""
            # checks if the the cursor is at 3,6
            if self.row == 3 and self.col == 6:
                # goes to last message
                self.messages.pop(self.current_message)
                print("deleting message")
                # resets view window
                self.sheet = 0
                # clears the input buffer
                self.input_buffer = ""
            else:
                pass
        # checks the current state
        elif state == "settings_menu":
            # checks if the the cursor is at 0,0
            if self.row == 0 and self.col == 0:
                # transitions to the setting_address state
                self.setting_address()
                # clears the input buffer
                self.input_buffer = ""

            # # checks if the the cursor is at 1,0
            if self.row == 1 and self.col == 0:
                # transitions to the setting_address state
                self.setting_networkid()
                # clears the input buffer
                self.input_buffer = ""
            # checks if the the cursor is at 3,0
            if self.row == 3 and self.col == 0:
                # transitions to the main_menu state
                self.main_menu()
                # clears the input buffer
                self.input_buffer = ""
            else:
                pass
        # checks the current state of the machine
        elif state == "setting_address":
            # checks if the the cursor is at between 2,0 and 2,4
            if self.row == 2 and self.col <= 5:
                # transitions to the main_menu state
                self.main_menu()
                # saves the address to the data_to_send
                self.data_to_send["address_to_use"] = int(self.input_buffer)
                print(lora.set_address(self.data_to_send["address_to_use"]))
                self.data_to_send = {}
                # clears the input buffer
                self.input_buffer = ""
            # checks if the the cursor is at 3,0
            if self.row == 3 and self.col == 0:
                # transitions to the main_menu state
                self.main_menu()
                # clears the input buffer
                self.input_buffer = ""
            else:
                pass
        # checks the current state of the machine
        elif state == "setting_networkid":
            # checks if the the cursor is at between 2,0 and 2,4
            if self.row == 2 and self.col <= 5:
                # transitions to the main_menu state
                self.main_menu()
                # saves the address to the data_to_send
                self.data_to_send["networkid_to_use"] = int(self.input_buffer)
                print(lora.set_network_id(self.data_to_send["networkid_to_use"]))
                self.data_to_send = {}
                # clears the input buffer
                self.input_buffer = ""
            # checks if the the cursor is at 3,0
            if self.row == 3 and self.col == 0:
                # transitions to the main_menu state
                self.main_menu()
                # clears the input buffer
                self.input_buffer = ""
            else:
                pass
        # refreshes the screen
        self.update_screen()

    def write_char(self, st):
        """
        Writes the input from the user into the input buffer
        :param st: string to write to the input buffer
        :return:
        """
        # checks the current state
        if self.state == "send_menu":
            # verifies the input is valid and if not gives an error for the user to view
            if self.__is_address_field_valid(st, 65535, 0):
                # clears the error message if input is valid
                self.error_message = None
                # if the users cursor is beyond the end of the text string it will set the
                # cursor to the end of the string
                if self.col > self.text_col and self.row > self.text_row:
                    # sets the users cursor column to the end of the input buffer text
                    self.col = self.text_col
                    # sets the users cursor row to the end of the input buffer text
                    self.row = self.text_row
                # sets the cursor to the current row and col
                self.lcd.set_cursor_pos(self.row, self.col)
                # locates the beginning of the input buffer string
                string_num = self.col + (self.row * self.lcd.width) - 3
                # only allows a string of 5 characters
                if len(self.input_buffer) < 5:
                    # adds a character at the position of the cursor
                    self.input_buffer = self.input_buffer[:string_num] + st + self.input_buffer[string_num:]
                # checks to make sure sure cursor is not on last column of the row
                if self.col < self.lcd.width - 1:
                    # increments the column
                    self.col += 1
                    # sets the cursor to the current row and col
                    self.lcd.set_cursor_pos(self.row, self.col)
                # Does not allow writing to the input buffer past the 3rd line
                elif self.row == self.lcd.height - 3 and self.col == self.lcd.width - 1:
                    pass
                else:
                    # increments the row
                    self.row += 1
                    # sets the col back to zero to wrap the text
                    self.col = 0
            # sets the error
            else:
                self.error_message = "0-65535"
            # checks to make sure the number entered is within the range 0-65535
            if self.__is_address_field_valid(self.input_buffer, 65535, 0):
                # clears the error_message
                self.error_message = None
            else:
                # sets the the error_message
                self.error_message = "0-65535"
            # sets the cursor back to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)
        # checks the current state
        if self.state == "compose_message":
            # if the users cursor is beyond the end of the text string it will set the
            # cursor to the end of the string
            if self.col > self.text_col and self.row > self.text_row:
                # sets the users cursor column to the end of the input buffer text
                self.col = self.text_col
                # sets the users cursor row to the end of the input buffer text
                self.row = self.text_row
            # sets the cursor to the current row and col
            self.lcd.set_cursor_pos(self.row, self.col)
            # locates the beginning of the input buffer string
            string_num = self.col + (self.row * self.lcd.width) - 5
            # adds a character at the position of the cursor
            self.input_buffer = self.input_buffer[:string_num] + st + self.input_buffer[string_num:]
            # checks to make sure sure cursor is not on last column of the row
            if self.col < self.lcd.width - 1:
                # increments the column
                self.col += 1
                # sets the cursor to the current row and col
                self.lcd.set_cursor_pos(self.row, self.col)
                # Does not allow writing to the input buffer past the 3rd line
            elif self.row == self.lcd.height - 3 and self.col == self.lcd.width - 1:
                pass
            else:
                # increments the row
                self.row += 1
                # sets the col back to zero to wrap the text
                self.col = 0
            # sets the cursor back to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)

        if self.state == "sender_list":
            # if the users cursor is beyond the end of the text string it will set the
            # cursor to the end of the string
            if self.col > self.text_col and self.row > self.text_row:
                # sets the users cursor column to the end of the input buffer text
                self.col = self.text_col
                # sets the users cursor row to the end of the input buffer text
                self.row = self.text_row
            # sets the cursor to the current row and col
            self.lcd.set_cursor_pos(self.row, self.col)
            # locates the beginning of the input buffer string
            string_num = self.col + (self.row * self.lcd.width)
            # adds a character at the position of the cursor
            self.input_buffer = self.input_buffer[:string_num] + st + self.input_buffer[string_num:]
            # checks to make sure sure cursor is not on last column of the row
            if self.col < self.lcd.width - 1:
                # increments the column
                self.col += 1
                # sets the cursor to the current row and col
                self.lcd.set_cursor_pos(self.row, self.col)
                # Does not allow writing to the input buffer past the 3rd line
            elif self.row == self.lcd.height - 3 and self.col == self.lcd.width - 1:
                pass
            else:
                # increments the row
                self.row += 1
                # sets the col back to zero to wrap the text
                self.col = 0
            # sets the cursor back to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)

        # checks the current state
        if self.state == "setting_address":
            if self.__is_address_field_valid(st, 65535, 0):
                # clears the error message if input is valid
                self.error_message = None
                # if the users cursor is beyond the end of the text string it will set the
                # cursor to the end of the string
                if self.col > self.text_col and self.row > self.text_row:
                    # sets the users cursor column to the end of the input buffer text
                    self.col = self.text_col
                    # sets the users cursor row to the end of the input buffer text
                    self.row = self.text_row
                # sets the cursor to the current row and col
                self.lcd.set_cursor_pos(self.row, self.col)
                # locates the beginning of the input buffer string
                string_num = self.col + (self.row * self.lcd.width)
                # only allows a string with length of 5
                if len(self.input_buffer) < 5:
                    # adds a character at the position of the cursor
                    self.input_buffer = self.input_buffer[:string_num] + st + self.input_buffer[string_num:]
                # checks to make sure sure cursor is not on last column of the row
                if self.col < self.lcd.width - 1:
                    # increments the column
                    self.col += 1
                    # sets the cursor to the current row and col
                    self.lcd.set_cursor_pos(self.row, self.col)
                    # Does not allow writing to the input buffer past the 3rd line
                elif self.row == self.lcd.height - 1 and self.col == self.lcd.width - 1:
                    pass
                else:
                    # increments the row
                    self.row += 1
                    # sets the col back to zero to wrap the text
                    self.col = 0
            # sets the error
            else:
                self.error_message = "0-65535"
            # checks to make sure the number entered is within the range 0-65535
            if self.__is_address_field_valid(self.input_buffer, 65535, 0):
                # clears the error_message
                self.error_message = None
            else:
                # sets the the error_message
                self.error_message = "0-65535"
            # sets the cursor back to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)

        # checks the current state
        if self.state == "setting_networkid":
            if self.__is_address_field_valid(st, 16, 0):
                # clears the error message if input is valid
                self.error_message = None
                # if the users cursor is beyond the end of the text string it will set the
                # cursor to the end of the string
                if self.col > self.text_col and self.row > self.text_row:
                    # sets the users cursor column to the end of the input buffer text
                    self.col = self.text_col
                    # sets the users cursor row to the end of the input buffer text
                    self.row = self.text_row
                # sets the cursor to the current row and col
                self.lcd.set_cursor_pos(self.row, self.col)
                # locates the beginning of the input buffer string
                string_num = self.col + (self.row * self.lcd.width)
                # only allows a string with length of 5
                if len(self.input_buffer) < 5:
                    # adds a character at the position of the cursor
                    self.input_buffer = self.input_buffer[:string_num] + st + self.input_buffer[string_num:]
                # checks to make sure sure cursor is not on last column of the row
                if self.col < self.lcd.width - 1:
                    # increments the column
                    self.col += 1
                    # sets the cursor to the current row and col
                    self.lcd.set_cursor_pos(self.row, self.col)
                    # Does not allow writing to the input buffer past the 3rd line
                elif self.row == self.lcd.height - 1 and self.col == self.lcd.width - 1:
                    pass
                else:
                    # increments the row
                    self.row += 1
                    # sets the col back to zero to wrap the text
                    self.col = 0
            # sets the error
            else:
                self.error_message = "0-16"
                # checks to make sure the number entered is within the range 0-16
            if self.__is_address_field_valid(self.input_buffer, 16, 0):
                # clears the error_message
                self.error_message = None
            else:
                # sets the the error_message
                self.error_message = "0-16"
            # sets the cursor back to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)
        # refreshes the screen
        self.update_screen()

    # currently not used
    # def print_char(self, st):
    #     state = self.state
    #     if state == "compose_message":
    #         if self.col < self.lcd.width - 1:
    #             self.lcd.print(st)
    #             self.col += 1
    #             self.lcd.set_cursor_pos(self.row, self.col)
    #         elif self.row == self.lcd.height - 2 and self.col == self.lcd.width - 1:
    #             pass
    #         else:
    #             self.row = self.row + 1
    #             self.col = 0
    #             self.lcd.print(st)
    #             self.lcd.set_cursor_pos(self.row, self.col)
    #
    #     elif state == "send_message":
    #         if self.col < self.lcd.width - 1:
    #             self.lcd.print(st)
    #             self.col = self.col + 1
    #             self.lcd.set_cursor_pos(self.row, self.col)
    #         elif self.row == self.lcd.height - 2 and self.col == self.lcd.width - 1:
    #             pass
    #         else:
    #             self.row = self.row + 1
    #             self.col = 0
    #             self.lcd.set_cursor_pos(self.row, self.col)
    #     else:
    #         pass

    def delete(self):
        # checks the current state
        if self.state == "send_menu":
            # sets the start of the string on the first line
            start_of_string = -3
        # checks the current state
        elif self.state == "compose_message":
            # sets the start of the string on the first line
            start_of_string = -5
        elif self.state == "setting_address":
            # sets the start of the string on the first line
            start_of_string = -20
        elif self.state == "setting_networkid":
            # sets the start of the string on the first line
            start_of_string = -20
        else:
            # sets the start of the string on first column and row
            start_of_string = 0
        # only allows delete if there is space
        if self.col > 0:
            # clears the cursor from the screen
            self.lcd.delete(self.col, self.row)
            # locates the beginning of the input buffer string
            string_num = self.col + (self.row * self.lcd.width) + start_of_string
            # removes the character from the input string at the location the left of the cursor
            self.input_buffer = self.input_buffer[:string_num - 1] + self.input_buffer[string_num:]
            # decrements the cursor column
            self.col = self.col - 1
            # moves the cursor to the users cursor
            self.lcd.set_cursor_pos(self.row, self.col)
            # clears the cursor from the screen
            self.lcd.delete(self.col, self.row)
            # redraws the cursor
            self.lcd.draw_cursor()
        # only allows delete in the screen
        elif self.row == self.lcd.height - self.lcd.height and self.col == self.lcd.width - self.lcd.width:
            pass
        else:
            # deletes the cell
            self.lcd.delete(self.col, self.row)
            # sets the cursor column to the far right cell
            self.col = self.lcd.width - 1
            # sets the cursor row one up
            self.row = self.row - 1
            # moves the cursor to the users cursor position
            self.lcd.set_cursor_pos(self.row, self.col)
            # deletes the cursor
            self.lcd.delete(self.col, self.row)
            # redraws the cursor
            self.lcd.print(chr(9608))

    def __is_address_field_valid(self, test_input, high, low):
        """
        Currently only works for send data screen.
        :param test_input: string to verify if it is a valid input.
        :return:
        """
        try:
            data = int(test_input)
        except:
            return False
        if data < int(low):
            return False
        if data > int(high):
            return False
        return True

    def stop(self):
        self.running = False

if __name__ == '__main__':
    key = keyboard
    txpin = "GP4"
    rxpin = "GP5"
    lora = fake_rylr896.RYLR896(name="lora", rx=rxpin, tx=txpin, timeout=1, debug=True)
    flcd = fake_lcd.Fake_lcd()
    main = Messenger(flcd, lora)


    main.update_screen()
    flcd.set_cursor_pos(0, 0)

    key.add_hotkey("q+right_shift", main.stop)
    key.add_hotkey("w+right_shift", main.on_up)
    key.add_hotkey("a+right_shift", main.on_left)
    key.add_hotkey("s+right_shift", main.on_down)
    key.add_hotkey("d+right_shift", main.on_right)
    key.add_hotkey("p+right_shift", main.on_p)
    key.add_hotkey("enter", main.on_enter)
    key.add_hotkey("space", main.write_char, args=[" "], suppress=True)
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

    while True:
        main.last_received = lora.read_from_device()
        if main.last_received is not None:
            if not main.mailbox_full:
                print("adding mail")
                main.messages.append(main.last_received)

                # elif main.last_received["address"] in main.messages.keys():
                #     current_time = int(time.time())
                #     main.messages[main.last_received["address"]].append(main.last_received)
                main.message_count += 1
                if main.message_count > 39:
                    print("closing mailbox")
                    main.mailbox_full = True
        if main.mailbox_full:
            if len(main.messages) < 40:
                main.mailbox_full = False
                print("opening mailbox")

        if not main.running:
            break
