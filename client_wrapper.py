import os
from datetime import datetime
from email import message_from_bytes
from email.header import decode_header

from imapclient import IMAPClient


class IMAPClientWrapper:
    def __init__(self, server: str, port: int, use_ssl: bool = True):
        self.server: str = server
        self.port: int = port
        self.use_ssl: bool = use_ssl
        self.client: IMAPClient | None = None

    def connect(self) -> None:
        print(f"Connecting to {self.server}...")
        try:
            self.client = IMAPClient(self.server, port=self.port, ssl=self.use_ssl)
            print(f"Connected to {self.server} succesfully")
        except Exception as e:
            print(f"Connection failed: {e}")

    def login(self, username: str, password: str) -> None:
        try:
            self.client.login(username, password)
            print("Logged in successfully!")
        except Exception as e:
            print(f"Login failed: {e}")
            self.client = None

    def list_folders(self) -> None:
        if self.client:
            folders = self.client.list_folders()
            for folder in folders:
                print(f"* {folder[2]}")
        else:
            print("Not connected!")

    def select_folder(self, folder: str) -> None:
        if self.client:
            self.client.select_folder(folder)
            print(f"Selected folder {folder}")
        else:
            print("Not connected!")

    def fetch_emails(self, download_attachments: bool = False) -> None:
        if not self.client:
            print("Not connected!")
            return

        messages = self.fetch_message_ids()
        if messages is None:
            return

        for msg_id in messages:
            msg = self.fetch_message(msg_id)
            if msg is None:
                continue

            date = self.extract_date(msg)
            sender = self.extract_sender(msg)
            subject = self.extract_subject(msg)
            body, attachments = self.extract_body_and_attachments(msg)

            self.print_email_info(date, sender, subject, body)

            if download_attachments:
                self.save_attachments(attachments)

    def fetch_message_ids(self) -> list[int] | None:
        limit: int = 10
        try:
            messages: list[int] = self.client.search(['ALL'])
            return messages[:limit]
        except Exception:
            print("Select folder first")
            return

    def fetch_message(self, msg_id: int):
        msg_data = self.client.fetch([msg_id], ['RFC822'])
        return message_from_bytes(msg_data[msg_id][b'RFC822'])

    def extract_date(self, msg: message_from_bytes) -> str | None:
        date: str | None = msg['Date']
        if date:
            return datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S')
        return

    def extract_sender(self, msg: message_from_bytes) -> str | None:
        sender: str | None = msg['From']
        if sender:
            sender = decode_header(sender)[0][0]
            if isinstance(sender, bytes):
                return sender.decode('utf-8', errors='ignore')
        return

    def extract_subject(self, msg: message_from_bytes) -> str | None:
        subject: str | None = msg['Subject']
        if subject:
            subject = decode_header(subject)[0][0]
            if isinstance(subject, bytes):
                return subject.decode('utf-8', errors='ignore')
        return

    def extract_body_and_attachments(self, msg: message_from_bytes) -> tuple[str, list[tuple[str, bytes]]]:
        body: str = ""
        attachments: list[tuple[str, bytes]] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type: str = part.get_content_type()

                if content_type == 'text/plain' and not part.get_filename():
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')

                filename: str | None = part.get_filename()
                if filename:
                    filename = decode_header(filename)[0][0]
                    if isinstance(filename, bytes):
                        filename = filename.decode('utf-8', errors='ignore')

                    file_data: bytes | None = part.get_payload(decode=True)
                    if file_data:
                        attachments.append((filename, file_data))
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

        return body, attachments

    def print_email_info(self, date: str | None, sender: str | None, subject: str | None, body: str) -> None:
        body_text: str = body[:50]
        print(f"Дата: {date}")
        print(f"Отправитель: {sender}")
        print(f"Тема: {subject}")
        print(f"Первые 50 символов тела сообщения: {body_text}")
        print("-" * 40)

    def save_attachments(self, attachments: list[tuple[str, bytes]], save_dir: str = "attachments") -> None:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        for filename, file_data in attachments:
            filepath: str = os.path.join(save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(file_data)
            print(f"Attachment saved: {filepath}")

    def logout(self) -> None:
        if self.client:
            self.client.logout()
            print("Logged out.")
