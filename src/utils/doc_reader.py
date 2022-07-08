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

from aiogoogle import Aiogoogle
from docx.api import Document as DocumentParser
from docx.document import Document

__all__ = ("DOCX_FORMAT", "GOOGLE_FORMAT", "docs_aioreader", "BytesAIO")

DOCX_FORMAT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
GOOGLE_FORMAT = "application/vnd.google-apps.document"


class BytesAIO(BytesIO):
    def __init__(self, initial_bytes: bytes = None) -> None:
        super(BytesAIO, self).__init__(initial_bytes)

    async def write(self, __buffer: bytes) -> int:
        return super(BytesAIO, self).write(__buffer)


async def docs_aioreader(document_id: str, aio: Aiogoogle) -> Document:
    file = BytesAIO()
    storage = await aio.discover("drive", "v3")
    info: dict[str, str] = await aio.as_service_account(storage.files.get(fileId=document_id))
    value = info.get("mimeType")
    if value == DOCX_FORMAT:
        query = storage.files.get(
            fileId=document_id,
            pipe_to=file,
            alt="media",
        )
    elif value == GOOGLE_FORMAT:
        query = storage.files.export(
            fileId=document_id,
            pipe_to=file,
            mimeType=DOCX_FORMAT,
            alt="media",
        )
    else:
        raise ValueError(f"{value} format is not supported.")
    await aio.as_service_account(query)
    file.seek(0)
    return DocumentParser(file)
