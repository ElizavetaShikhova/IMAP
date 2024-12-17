import os

from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QLabel, QPushButton, QWidget, QTextEdit, QInputDialog,
                             QLineEdit, QMessageBox)

from client_wrapper import IMAPClientWrapper


class IMAPClientGUI(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.client: bool | None = None
        self.current_messages: dict = {}
        self.initUI()

    def initUI(self) -> None:
        self.setWindowTitle("IMAP Client GUI")
        self.setGeometry(400, 200, 600, 600)

        layout = QVBoxLayout()

        self.status_label = QLabel("Status: Disconnected")
        layout.addWidget(self.status_label)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        buttons = [
            ("Connect", self.connect_to_server),
            ("Login", self.login),
            ("List Folders", self.list_folders),
            ("Select Folder", self.select_folder),
            ("List Emails", self.list_emails),
            ("Download Attachments", self.download_attachments),
            ("Delete Emails", self.delete_emails),
            ("Logout", self.logout)
        ]

        for text, handler in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            layout.addWidget(btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def connect_to_server(self) -> None:
        server, ok = QInputDialog.getText(self, "Server", "Enter IMAP server:")
        if not ok:
            return
        port, ok = QInputDialog.getInt(self, "Port", "Enter port:", 993)
        use_ssl = QMessageBox.question(self, "SSL", "Use SSL?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes

        self.client = IMAPClientWrapper(server, port, use_ssl)
        self.client.connect()
        self.status_label.setText(f"Connected to {server}")
        self.output.append("Connected successfully!")

    def login(self) -> None:
        if not self.client:
            self.output.append("Not connected!")
            return

        username, ok = QInputDialog.getText(self, "Login", "Enter username:")
        if not ok:
            return
        password, ok = QInputDialog.getText(self, "Password", "Enter password:", QLineEdit.Password)
        if not ok:
            return

        self.client.login(username, password)
        self.output.append("Logged in successfully!")

    def list_folders(self) -> None:
        if not self.client:
            self.output.append("Not connected!")
            return

        self.output.append("Fetching folders...\n")
        folders = self.client.list_folders()
        if folders:
            self.output.append("Available Folders:")
            for folder in folders:
                self.output.append(f"- {folder}")
        else:
            self.output.append("No folders found.")

    def select_folder(self) -> None:
        if not self.client:
            self.output.append("Not connected!")
            return
        folder, ok = QInputDialog.getText(self, "Folder", "Enter folder name:")
        if not ok:
            return
        self.client.select_folder(folder)
        self.output.append(f"Selected folder: {folder}")

    def list_emails(self) -> None:
        if not self.client:
            self.output.append("Not connected!")
            return

        self.output.append("Fetching emails...")
        self.current_messages.clear()

        message_ids = self.client.fetch_message_ids()
        if not message_ids:
            self.output.append("No messages found.")
            return

        self.output.append("Available Messages:")
        for msg_id in message_ids:
            msg = self.client.fetch_message(msg_id)
            if msg:
                sender = self.client.extract_sender(msg) or "Unknown Sender"
                subject = self.client.extract_subject(msg) or "No Subject"
                date = self.client.extract_date(msg) or "Unknown Date"
                self.current_messages[msg_id] = (sender, subject, date)
                self.output.append(f"ID: {msg_id} | From: {sender} | Subject: {subject} | Date: {date}")

    def download_attachments(self) -> None:
        if not self.client or not self.current_messages:
            self.output.append("List emails first to view message IDs.")
            return

        msg_id, ok = QInputDialog.getInt(self, "Message ID", "Enter message ID to download attachments:")
        if not ok or msg_id not in self.current_messages:
            self.output.append("Invalid message ID!")
            return

        msg = self.client.fetch_message(msg_id)
        if msg:
            attachments = self.client.extract_attachments(msg)
            if not attachments:
                self.output.append(f"No attachments in message {msg_id}.")
                return

            save_dir = os.path.join(os.getcwd(), "attachments")
            os.makedirs(save_dir, exist_ok=True)
            self.client.download_specific_attachments(msg_id, attachments, save_dir)
            self.output.append(f"Attachments downloaded to {save_dir}")
        else:
            self.output.append(f"Failed to fetch message {msg_id}.")

    def delete_emails(self) -> None:
        if not self.client or not self.current_messages:
            self.output.append("List emails first to view message IDs.")
            return

        ids_input, ok = QInputDialog.getText(self, "Delete Messages", "Enter message IDs to delete (comma-separated):")
        if not ok:
            return

        try:
            ids_to_delete = [int(id_.strip()) for id_ in ids_input.split(',') if id_.strip().isdigit()]
            valid_ids = [id_ for id_ in ids_to_delete if id_ in self.current_messages]
            if not valid_ids:
                self.output.append("No valid message IDs provided.")
                return

            confirmation = QMessageBox.question(
                self, "Confirm Deletion", f"Are you sure you want to delete {len(valid_ids)} message(s)?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirmation == QMessageBox.Yes:
                self.client.delete_emails(valid_ids)
                self.output.append(f"Deleted {len(valid_ids)} message(s).")
                for id_ in valid_ids:
                    del self.current_messages[id_]
        except ValueError:
            self.output.append("Invalid input. Please enter valid message IDs.")

    def logout(self) -> None:
        if self.client:
            self.client.logout()
            self.client = None
            self.current_messages.clear()
            self.status_label.setText("Status: Disconnected")
            self.output.append("Logged out.")
