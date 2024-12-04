import cmd
import getpass

from client_wrapper import IMAPClientWrapper


class IMAPClientShell(cmd.Cmd):
    intro = "Welcome to the IMAP client shell. Type help or ? to list commands.\n"
    prompt = "(IMAP) "
    client: IMAPClientWrapper | None = None

    def do_connect(self, arg: str) -> None:
        server: str = input("Server: ")
        port: str = input("Port: ")
        use_ssl: bool = input("Use SSL? (y/n): ").lower() == 'y'
        self.client = IMAPClientWrapper(server, port, use_ssl)
        self.client.connect()

    def do_login(self, arg: str) -> None:
        if self.client is None:
            print("Not connected. Use 'connect' first.")
            return
        username: str = input("Username: ")
        password: str = getpass.getpass("Password: ")
        self.client.login(username, password)

    def do_list(self, arg: str) -> None:
        if self.client:
            self.client.list_folders()
        else:
            print("Not connected. Use 'connect' and 'login' first.")

    def do_select(self, arg: str) -> None:
        folder: str = arg or input("Folder: ")
        self.client.select_folder(folder)

    def do_fetch(self, arg: str) -> None:
        download_attachments: bool = '-d' in arg
        self.client.fetch_emails(download_attachments=download_attachments)

    def do_logout(self, arg: str) -> None:
        if self.client:
            self.client.logout()

    def do_exit(self, arg: str) -> None:
        print("Goodbye!")
        if self.client:
            try:
                self.client.logout()
            except Exception as e:
                print(f"Error during logout: {e}")
        self.client = None
        return True

    def do_upload(self, arg: str) -> None:
        if not self.client:
            print("Not connected. Use 'connect' and 'login' first.")
            return

        folder = input("Folder to upload email (e.g., 'Sent'): ")
        subject = input("Subject: ")
        body = input("Body: ")
        sender = input("Sender email: ")
        recipients = input("Recipient emails (comma-separated): ").split(',')

        self.client.upload_email(folder, subject, body, recipients, sender)
