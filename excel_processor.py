import openpyxl
from pathlib import Path
from ftplib import FTP
import os
from dotenv import load_dotenv

load_dotenv()

def parse_excel(file_path):
    """
    Parses the Excel file and extracts the required data.
    """
    try:
        workbook = openpyxl.load_workbook(file_path, data_only=True)
        sheet = workbook.active

        # Extract all the required data
        work_order_number = sheet["C6"].value
        partner = sheet["B7"].value
        aparat = sheet["B12"].value
        serijski_broj = sheet["E12"].value
        sifra_aparata = sheet["B13"].value
        opis_pogreske = sheet["B16"].value
        datum = sheet["E6"].value

        return {
            "work_order_number": work_order_number,
            "partner": partner,
            "aparat": aparat,
            "serijski_broj": serijski_broj,
            "sifra_aparata": sifra_aparata,
            "opis_pogreske": opis_pogreske,
            "datum": datum,
        }

    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def update_data_txt(new_work_order_number, data_txt_path="data.txt"):
    """
    Updates the data.txt file with the new work order number if it is greater than the existing one.
    """
    try:
        with open(data_txt_path, "r") as f:
            current_work_order = f.read().strip()
            current_number = int(current_work_order.split("/")[0])
    except (FileNotFoundError, ValueError):
        current_number = 0

    new_number = int(new_work_order_number.split("/")[0])

    if new_number > current_number:
        with open(data_txt_path, "w") as f:
            f.write(str(new_work_order_number))
        print(f"Updated data.txt with new work order number: {new_work_order_number}")
        return True
    else:
        print("data.txt already has a greater or equal work order number.")
        return False

def generate_details_html(data, output_path="work_order_details.html"):
    """
    Generates an HTML file with the work order details.
    """
    html_content = f"""
<div class="container mt-4">
  <h4>Detalji radnog naloga</h4>
  <table class="table table-striped mt-3">
    <tr>
        <th>Radni nalog</th>
        <td>{data['work_order_number']} <button onclick="copyToClipboard('{data['work_order_number']}')">📋</button></td>
    </tr>
    <tr><th>Partner</th><td>{data['partner']}</td></tr>
    <tr><th>Aparat</th><td>{data['aparat']}</td></tr>
    <tr><th>Serijski broj</th><td>{data['serijski_broj']}</td></tr>
    <tr><th>Šifra aparata</th><td>{data['sifra_aparata']}</td></tr>
    <tr><th>Opis pogreške</th><td>{data['opis_pogreske']}</td></tr>
    <tr>
        <th>Datum</th>
        <td>{data['datum']} <button onclick="copyToClipboard('{data['datum']}')">📋</button></td>
    </tr>
  </table>
</div>
<script>
function copyToClipboard(text) {{
  navigator.clipboard.writeText(text).then(function() {{
    console.log('Copying to clipboard was successful!');
  }}, function(err) {{
    console.error('Could not copy text: ', err);
  }});
}}
</script>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated {output_path}")

def upload_to_ftp(files_to_upload):
    """
    Uploads the specified files to the FTP server.
    """
    host = os.getenv("FTP_HOST")
    user = os.getenv("FTP_USER")
    passwd = os.getenv("FTP_PASS")

    if not all([host, user, passwd]):
        print("FTP credentials not found in config.env. Skipping FTP upload.")
        return

    try:
        with FTP(host) as ftp:
            ftp.login(user, passwd)
            for file_path in files_to_upload:
                with open(file_path, "rb") as f:
                    ftp.storbinary(f"STOR {file_path}", f)
                print(f"Uploaded {file_path} to FTP.")
    except Exception as e:
        print(f"An error occurred during FTP upload: {e}")

if __name__ == "__main__":
    # This is for testing purposes
    file_to_test = Path("Example/RN 0175 2025 Rijeka Susak CT Motion Spicy CTM2426941.xlsx")
    excel_data = parse_excel(file_to_test)

    if excel_data:
        if update_data_txt(excel_data["work_order_number"]):
            generate_details_html(excel_data)
            upload_to_ftp(["data.txt", "work_order_details.html"])
        else:
            # Even if data.txt is not updated, we may still want to update the details page
            generate_details_html(excel_data)
            upload_to_ftp(["work_order_details.html"])
