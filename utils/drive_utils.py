import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_pdf_to_drive(filepath, filename=None):
    # Carregar credenciais do .env
    json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    service_account_info = json.loads(json_str)
    credentials = service_account.Credentials.from_service_account_info(service_account_info)

    # Criar serviço
    service = build('drive', 'v3', credentials=credentials)

    # Define metadados do arquivo
    file_metadata = {
        'name': filename or os.path.basename(filepath),
        'parents': [os.getenv("GOOGLE_DRIVE_FOLDER_ID")] if os.getenv("GOOGLE_DRIVE_FOLDER_ID") else []
    }

    media = MediaFileUpload(filepath, mimetype='application/pdf')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    # Tornar o arquivo público
    permission = {
        'type': 'anyone',
        'role': 'reader'
    }
    service.permissions().create(fileId=file['id'], body=permission).execute()

    # Gerar link de compartilhamento
    file_info = service.files().get(fileId=file['id'], fields='webViewLink').execute()
    return file_info['webViewLink']


