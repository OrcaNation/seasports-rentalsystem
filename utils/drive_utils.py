from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

def upload_pdf_to_drive(filepath, filename=None, folder_id="1vhG-AcLLxtcXCKw2R5B8lgxfXjAsUpti"):
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")

    drive = GoogleDrive(gauth)

    file_drive = drive.CreateFile({
        'title': filename or filepath.split('/')[-1],
        'parents': [{'id': folder_id}] if folder_id else []
    })
    file_drive.SetContentFile(filepath)
    file_drive.Upload()

    # Torna o arquivo público
    file_drive.InsertPermission({
        'type': 'anyone',
        'value': 'anyone',
        'role': 'reader'
    })

    return file_drive['alternateLink']



