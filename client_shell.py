import cmd
import getpass

from client_wrapper import IMAPClientWrapper


class IMAPClientShell(cmd.Cmd):
    intro = "Welcome to the IMAP client shell. Type help or ? to list commands.\n"
    prompt = "(IMAP) "
    client: IMAPClientWrapper | None = None

    def do_connect(self, arg: str) -> None:
        server: str = input("Server: ")
        port_input: str = input("Port: ")
        try:
            port: int = int(port_input)
        except ValueError:
            print("Port must be an integer.")
            return
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
        if self.client:
            self.client.select_folder(folder)
        else:
            print("Not connected.")

    def do_fetch(self, arg: str) -> None:
        if not self.client:
            print("Not connected.")
            return
        download_attachments: bool = '-d' in arg
        self.client.fetch_emails(download_attachments=download_attachments)

    def do_download_attachments(self, arg: str) -> None:
        if not self.client:
            print("Not connected.")
            return

        messages = self.client.fetch_message_ids()
        if not messages:
            print("No messages available.")
            return

        self.display_available_messages(messages)

        msg_ids = self.get_message_ids_input()
        if not msg_ids:
            print("No valid message IDs provided.")
            return

        for msg_id in msg_ids:
            self.process_message(msg_id)

    def display_available_messages(self, messages: list[int]) -> None:
        print("Available messages:")
        for msg_id in messages:
            msg = self.client.fetch_message(msg_id)
            if msg:
                subject = self.client.extract_subject(msg) or "(No Subject)"
                sender = self.client.extract_sender(msg) or "(No Sender)"
                date = self.client.extract_date(msg) or "(No Date)"
                attachments = self.client.extract_attachments(msg)
                attachment_count = len(attachments) if attachments else 0
                print(
                    f"ID: {msg_id} | Date: {date} | From: {sender} | Subject: {subject} | Attachments: {attachment_count}")

    def get_message_ids_input(self) -> list[int]:
        ids_input = input("Enter message IDs to download attachments from (separated by commas): ")
        try:
            return [int(id_.strip()) for id_ in ids_input.split(',') if id_.strip().isdigit()]
        except ValueError:
            print("Invalid input. Please enter valid message IDs separated by commas.")
            return []

    def process_message(self, msg_id: int) -> None:
        msg = self.client.fetch_message(msg_id)
        if msg is None:
            print(f"Message ID {msg_id} not found.")
            return

        attachments = self.client.extract_attachments(msg)
        if not attachments:
            print(f"No attachments found in message ID {msg_id}.")
            return

        print(f"\nAttachments in message ID {msg_id}:")
        for idx, (filename, _) in enumerate(attachments, start=1):
            print(f"{idx}. {filename}")

        selected_attachments = self.get_attachment_selection(attachments)
        if not selected_attachments:
            print("No valid attachments selected. Skipping this message.")
            return

        self.client.download_specific_attachments(msg_id, selected_attachments)

    def get_attachment_selection(self, attachments: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
        selection = input(
            "Enter attachment numbers to download (separated by commas) or 'all' to download all: ").lower()
        if selection == 'all':
            return attachments

        try:
            indices = [int(num.strip()) for num in selection.split(',') if num.strip().isdigit()]
            return [attachments[i - 1] for i in indices if 0 < i <= len(attachments)]
        except (ValueError, IndexError):
            print("Invalid selection. Skipping this message.")
            return []

    def do_delete(self, arg: str) -> None:
        if not self.client:
            print("Not connected.")
            return

        messages = self.client.fetch_message_ids()
        if not messages:
            print("No messages to delete.")
            return

        print("Available messages:")
        for msg_id in messages:
            msg = self.client.fetch_message(msg_id)
            if msg:
                subject = self.client.extract_subject(msg) or "(No Subject)"
                sender = self.client.extract_sender(msg) or "(No Sender)"
                date = self.client.extract_date(msg) or "(No Date)"
                print(f"ID: {msg_id} | Date: {date} | From: {sender} | Subject: {subject}")

        ids_to_delete_input = input("Enter message IDs to delete (separated by commas): ")
        try:
            ids_to_delete = [int(id_.strip()) for id_ in ids_to_delete_input.split(',') if id_.strip().isdigit()]
        except ValueError:
            print("Invalid input. Please enter valid message IDs separated by commas.")
            return

        if not ids_to_delete:
            print("No valid message IDs provided.")
            return

        confirmation = input(f"Are you sure you want to delete {len(ids_to_delete)} message(s)? (y/n): ").lower()
        if confirmation != 'y':
            print("Deletion cancelled.")
            return

        self.client.delete_emails(ids_to_delete)

    def do_logout(self, arg: str) -> None:
        if self.client:
            self.client.logout()
            self.client = None
        else:
            print("Not connected.")

    def do_exit(self, arg: str) -> None:
        print("Goodbye!")
        if self.client:
            try:
                self.client.logout()
            except Exception as e:
                print(f"Error during logout: {e}")
        self.client = None
        return True  # This exits the cmd loop

    def do_upload(self, arg: str) -> None:
        if not self.client:
            print("Not connected. Use 'connect' and 'login' first.")
            return

        folder = input("Folder to upload email (e.g., 'Sent'): ")
        subject = input("Subject: ")
        body = input("Body: ")
        sender = input("Sender email: ")
        recipients = input("Recipient emails (comma-separated): ").split(',')

        # Clean up recipient emails
        recipients = [email.strip() for email in recipients if email.strip()]

        self.client.upload_email(folder, subject, body, recipients, sender)
