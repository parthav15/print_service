import subprocess
import os
from django.conf import settings

def get_connected_printer():
    try:
        command = [r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe', 
                   '-Command', 'Get-Printer | Where-Object {$_.PortName -like "USB*"} | Select-Object -ExpandProperty Name']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        printer_name = result.stdout.strip()
        
        if printer_name:
            return printer_name
        else:
            return None
    
    except subprocess.CalledProcessError as e:
        return None, f"Error getting connected printer: {str(e)}"

def send_to_printer(print_job):
    printer_name = get_connected_printer()
    if not printer_name:
        return False, "No connected printer found."

    document_path = os.path.join(settings.MEDIA_ROOT, print_job.document.name)
    document_path = document_path.replace('/', '\\')

    if not os.path.exists(document_path):
        return False, f"Document not found at {document_path}."

    try:
        if print_job.bw_pages > 0:
            bw_command = f'Set-PrintConfiguration -PrinterName "{printer_name}" -Color $false'
            subprocess.run([r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe', '-Command', bw_command], check=True)
        elif print_job.color_pages > 0:
            color_command = f'Set-PrintConfiguration -PrinterName "{printer_name}" -Color $true'
            subprocess.run([r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe', '-Command', color_command], check=True)
        else:
            return False, "Neither black-and-white nor color pages specified."

        print_command = [
            r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',
            '-Command',
            f'Start-Process -FilePath "{document_path}" -Verb Print'
        ]
        result = subprocess.run(print_command, check=True)

        print_job.is_printed = True
        print_job.save()
        return True, "Document sent to printer successfully."

    except subprocess.CalledProcessError as e:
        return False, f"Error sending document to printer: {str(e)}"