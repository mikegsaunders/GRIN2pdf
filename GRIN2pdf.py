from PIL import Image
from pypdf import PdfReader, PdfWriter
import gnupg
import tarfile
import shutil
import time
import os
import streamlit as st

gpg = gnupg.GPG()
# passphrase = os.environ.get("GRIN")
passphrase = st.secrets["GRIN"]

if "processed_file" not in st.session_state:
    st.session_state.processed_file = None

st.title("GRIN to PDF")
file = st.file_uploader("Upload a gpg file", label_visibility="hidden", type="gpg")
if file is not None and st.session_state.processed_file is None:

    decrypted_data = gpg.decrypt_file(file, passphrase=passphrase)

    if not decrypted_data.ok:
        raise ValueError("Decryption failed: {}".format(decrypted_data.stderr))
    decrypted = f"{file.name[:-4]}"
    with open(decrypted, "wb") as decrypted_output:
        decrypted_output.write(decrypted_data.data)

    st.write(f"File decrypted successfully to {decrypted}")
    st.write("Extracting...")

    with tarfile.open(decrypted) as tar:
        tar.extractall("./book")

    # convert
    folder = os.listdir("./book")
    image_files = []
    for f in folder:
        if f.endswith("jp2") or f.endswith("tif"):
            image_files.append(f)

    total = len(image_files)
    images = []
    progress_bar = st.progress(0, text="Processing...")
    for file in image_files:
        try:
            image = Image.open(f"./book/{file}")
            images.append(image)
        except IOError:
            pass
        count = len(images)
        percent = round((count / total) * 100)

        progress_bar.progress(percent, text=f"Combining images... {percent}%")

    first_image = images[0]
    remaining_images = images[1:]

    with st.spinner(text="Converting to PDF (this takes 30 seconds or so)..."):
        output_pdf = "out.pdf"
        first_image.save(output_pdf, save_all=True, append_images=remaining_images)

        reader = PdfReader(output_pdf)
        writer = PdfWriter()
    with st.spinner(text="Compressing..."):
        for page in reader.pages:
            writer.add_page(page)

        with open("output.pdf", "wb") as fp:
            writer.write(fp)
        time.sleep(5)
        os.remove(output_pdf)
        os.remove(decrypted)
        shutil.rmtree("./book")
        file = None
        with open("output.pdf", "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
        st.session_state.processed_file = pdf_bytes
    st.success("Completed successfully")
if st.session_state.processed_file is not None:
    st.download_button(
        "Download PDF",
        data=st.session_state.processed_file,
        file_name="output.pdf",
        mime="application/octet-stream",
    )
