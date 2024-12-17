import sys

from PyQt5.QtWidgets import QApplication

from client_shell import IMAPClientShell
from gui import IMAPClientGUI


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        app = QApplication(sys.argv)
        gui = IMAPClientGUI()
        gui.show()
        sys.exit(app.exec_())
    else:
        IMAPClientShell().cmdloop()


if __name__ == "__main__":
    main()
