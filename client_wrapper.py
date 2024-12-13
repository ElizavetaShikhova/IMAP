from email import message_from_bytes
from email import policy
from email.header import decode_header
from email.message import EmailMessage
from pathlib import Path

from dateutil import parser
from imapclient import IMAPClient
from imapclient import exceptions as IMAPClientExceptions

class IMAPClientWrapper:
    def __init__(self, server: str, port: int, use_ssl: bool = True):
        self.server: str = server
        self.port: int = port
        self.use_ssl: bool = use_ssl
        self.client: IMAPClient | None = None
        self.current_folder: str | None = None

    def connect(self) -> None:
        print(f"Connecting to {self.server}:{self.port}...")
        try:
            self.client = IMAPClient(self.server, port=self.port, ssl=self.use_ssl)
            print(f"Connected to {self.server} successfully.")
        except ConnectionError as e:
            print(f"Connection failed: {e}")
        except TimeoutError as e:
            print(f"Connection timed out: {e}")
        except IMAPClientExceptions.IMAPClientError as e:
            print(f"IMAPClient error during connection: {e}")

    def login(self, username: str, password: str) -> None:
        if not self.client:
            print("Error: Not connected to the server. Call 'connect' first.")
            return

        try:
            self.client.login(username, password)
            print("Logged in successfully!")
        except IMAPClientExceptions.IMAPClientError as e:
            print(f"Login failed: {e}")
        except KeyError as e:
            print(f"Key error during login: {e}")
        except TypeError as e:
            print(f"Type error during login: {e}")

    def list_folders(self) -> None:
        if self.client:
            try:
                folders = self.client.list_folders()
                print("Folders:")
                for flags, delimiter, folder in folders:
                    print(f"- {folder}")
            except IMAPClientExceptions.IMAPClientError as e:
                print(f"Error listing folders: {e}")
        else:
            print("Not connected!")

    def select_folder(self, folder: str) -> None:
        if self.client:
            try:
                self.client.select_folder(folder)
                self.current_folder = folder
                print(f"Selected folder '{folder}'.")
            except IMAPClientExceptions.IMAPClientError as e:
                print(f"Error selecting folder '{folder}': {e}")
        else:
            print("Not connected!")

    def fetch_emails(self, download_attachments: bool = False) -> None:
        if not self.client:
            print("Not connected!")
            return

        if not self.current_folder:
            print("No folder selected. Use 'select' to choose a folder.")
            return

        messages = self.fetch_message_ids()
        if not messages:
            print("No messages found.")
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

            if download_attachments and attachments:
                self.save_attachments(attachments)

    def fetch_message_ids(self) -> list[int]:
        limit: int = 10
        try:
            messages = self.client.search(['ALL'])
            return messages[-limit:] if len(messages) >= limit else messages
        except IMAPClientExceptions.IMAPClientError as e:
            print(f"Error fetching message IDs: {e}")
            return []
        except AttributeError:
            print("Client is not initialized. Did you forget to connect?")
            return []

    def fetch_message(self, msg_id: int):
        try:
            msg_data = self.client.fetch([msg_id], ['RFC822'])
            raw_msg = msg_data.get(msg_id, {}).get(b'RFC822', None)
            if raw_msg:
                return message_from_bytes(raw_msg, policy=policy.default)
            else:
                print(f"No data found for message ID {msg_id}.")
                return None
        except IMAPClientExceptions.IMAPClientError as e:
            print(f"Error fetching message {msg_id}: {e}")
            return None

    def extract_date(self, msg: 'email.message.Message') -> str | None:
        date: str | None = msg['Date']
        if date:
            try:
                parsed_date = parser.parse(date)
                return parsed_date.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError) as e:
                print(f"Error parsing date: {e}")
        return None

    def extract_sender(self, msg: 'email.message.Message') -> str | None:
        sender: str | None = msg['From']
        if sender:
            decoded_sender = decode_header(sender)[0][0]
            if isinstance(decoded_sender, bytes):
                try:
                    return decoded_sender.decode('utf-8', errors='ignore')
                except UnicodeDecodeError:
                    return decoded_sender.decode('latin1', errors='ignore')
            return decoded_sender
        return None

    def extract_subject(self, msg: 'email.message.Message') -> str | None:
        subject: str | None = msg['Subject']
        if subject:
            decoded_subject = decode_header(subject)[0][0]
            if isinstance(decoded_subject, bytes):
                try:
                    return decoded_subject.decode('utf-8', errors='ignore')
                except UnicodeDecodeError:
                    return decoded_subject.decode('latin1', errors='ignore')
            return decoded_subject
        return None

    def extract_body_and_attachments(self, msg: 'email.message.Message') -> tuple[str, list[tuple[str, bytes]]]:
        body: str = ""
        attachments: list[tuple[str, bytes]] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type: str = part.get_content_type()
                disposition: str = part.get_content_disposition()

                if content_type == 'text/plain' and disposition != 'attachment':
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode('utf-8', errors='ignore')

                if disposition == 'attachment':
                    filename: str | None = part.get_filename()
                    if filename:
                        decoded_filename = decode_header(filename)[0][0]
                        if isinstance(decoded_filename, bytes):
                            try:
                                filename = decoded_filename.decode('utf-8', errors='ignore')
                            except UnicodeDecodeError:
                                filename = decoded_filename.decode('latin1', errors='ignore')
                        else:
                            filename = decoded_filename
                        file_data: bytes | None = part.get_payload(decode=True)
                        if file_data:
                            attachments.append((filename, file_data))
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')

        return body, attachments

    def extract_attachments(self, msg: 'email.message.Message') -> list[tuple[str, bytes]]:
        attachments: list[tuple[str, bytes]] = []

        if msg.is_multipart():
            for part in msg.walk():
                disposition: str = part.get_content_disposition()
                if disposition == 'attachment':
                    filename: str | None = part.get_filename()
                    if filename:
                        decoded_filename = decode_header(filename)[0][0]
                        if isinstance(decoded_filename, bytes):
                            try:
                                filename = decoded_filename.decode('utf-8', errors='ignore')
                            except UnicodeDecodeError:
                                filename = decoded_filename.decode('latin1', errors='ignore')
                        else:
                            filename = decoded_filename
                        file_data: bytes | None = part.get_payload(decode=True)
                        if file_data:
                            attachments.append((filename, file_data))
        return attachments

    def print_email_info(self, date: str | None, sender: str | None, subject: str | None, body: str) -> None:
        body_preview: str = (body[:50] + '...') if len(body) > 50 else body
        print(f"Дата: {date}")
        print(f"Отправитель: {sender}")
        print(f"Тема: {subject}")
        print(f"Первые 50 символов тела сообщения: {body_preview}")
        print("-" * 40)

    def save_attachments(self, attachments: list[tuple[str, bytes]], save_dir: str = "attachments") -> None:
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        for filename, file_data in attachments:
            filepath = save_path / filename
            try:
                filepath.write_bytes(file_data)
                print(f"Вложение сохранено: {filepath}")
            except OSError as e:
                print(f"Ошибка при сохранении вложения {filename}: {e}")

    def download_specific_attachments(self, msg_id: int, attachments: list[tuple[str, bytes]],
                                      save_dir: str = "attachments") -> None:
        save_path = Path(save_dir) / f"message_{msg_id}"
        save_path.mkdir(parents=True, exist_ok=True)

        for filename, file_data in attachments:
            filepath = save_path / filename
            try:
                filepath.write_bytes(file_data)
                print(f"Вложение '{filename}' из сообщения {msg_id} сохранено: {filepath}")
            except OSError as e:
                print(f"Ошибка при сохранении вложения '{filename}': {e}")

    def delete_emails(self, msg_ids: list[int]) -> None:
        if not self.client:
            print("Not connected!")
            return

        if not self.current_folder:
            print("No folder selected. Use 'select' to choose a folder.")
            return

        try:
            self.client.delete_messages(msg_ids)
            self.client.expunge()
            print(f"Удалено {len(msg_ids)} сообщение(ий).")
        except IMAPClientExceptions.IMAPClientError as e:
            print(f"Ошибка при удалении сообщений: {e}")

    def logout(self) -> None:
        if not self.client:
            print("Client is already disconnected.")
            return

        try:
            self.client.logout()
            print("Logged out successfully.")
        except IMAPClientExceptions.IMAPClientError as e:
            print(f"Error during logout: {e}")
        finally:
            self.client = None

    def upload_email(self, folder: str, subject: str, body: str, recipients: list[str], sender: str) -> None:
        if not self.client:
            print("Not connected!")
            return

        # Создание письма в формате RFC 822
        msg = EmailMessage(policy=policy.default)
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject
        msg.set_content(body)

        try:
            self.client.append(folder, msg.as_bytes())
            print(f"Email uploaded to folder '{folder}' successfully!")
        except IMAPClientExceptions.IMAPClientError as e:
            print(f"IMAPClient error during email upload: {e}")
        except OSError as e:
            print(f"OS error while writing email data: {e}")
