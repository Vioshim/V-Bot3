# Copyright 2022 Vioshim
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from io import BytesIO
from os.path import exists
from typing import Optional

from docx.api import Document as DocumentParser
from docx.document import Document
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import HttpRequest, MediaIoBaseDownload

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]
DOCX_FORMAT = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
GOOGLE_FORMAT = "application/vnd.google-apps.document"


def docs_reader(document_id: str) -> Document:
    """Google Document reader

    Parameters
    ----------
    document_id: str
        Google document's unique ID

    Raises
    ------
    HttpError
        If bad request
    ValueError
        If invalid format

    Returns
    -------
    Document
        Document
    """
    credentials = None
    if exists("token.json"):
        credentials = Credentials.from_authorized_user_file(
            "token.json", SCOPES
        )
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            credentials = flow.run_local_server(port=0)
        with open("token.json", "w") as file:
            file.write(credentials.to_json())

    service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    with service.files() as data:
        request: HttpRequest = data.get(fileId=document_id)
        info: dict[str, str] = request.execute()
        value: Optional[str] = info.get("mimeType")
        if value == DOCX_FORMAT:
            request = data.get_media(
                fileId=document_id,
            )
        elif value == GOOGLE_FORMAT:
            request = data.export_media(
                fileId=document_id,
                mimeType=DOCX_FORMAT,
            )
        else:
            raise ValueError(f"{value} format is not supported.")

        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done: bool = False
        while done is False:
            _, done = downloader.next_chunk()
        return DocumentParser(fh)
