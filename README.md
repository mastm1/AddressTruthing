An in house Python tool to truth(the capture of address text) a directory of images. SqlLite is used as backend storage of data. Tesseract is used to perform OCR. An old C executable for parsing text addresses and lookups into a national USPS directroy of addresses is used for determing the 11 digit USPS encoding of the address, if possible.

NicK:
Ok. Turns out I could not get the address directory files on github(too large) to run the C executable. The executable was compiled on Linux, which is why I had instructions below for 'wsl' on Windows.
You can skip the 'wsl' parts. The last python script will abort without doing the USPS database lookups.

'wsl --install' from Windows terminal and restart windows (This is Linux)
In Windows terminal, 'wsl'.
Clone the repository on your machine: 
a) On GitHub, navigate to the main page of the repository. 
b) Above the list of files, click 'Code'. 
c) under "HTTPS", click 'copy' icon d) In 'wsl' terminal, 'git clone ' in a suitable directory. 
d) In 'wsl' terminal, enter 'cd /MailPieceTruthing' e) Enter 'chmod 755 *'
'conda env create -f environment.yml'
'conda activate fpars_env'
'python importFPARSImages.py -d data/images/A3/ -s data/sqilite/A3.sqlite3' (creates a backend sqlite3 db using the sample images)
'python mainFPARS.py -s data/sqilite/A3.sqlite3' (executes the "truther", try it out)
Rubberband around the address in the image. Then rubberband around a region(a line or lines) in the newly created image to execute OCR.
'python MatchWithPostalDatabase.py -s data/sqilite/A3.sqlite3' (Performs USPS lookup of the OCR results and gives 11 digit ZIP, if successful)
