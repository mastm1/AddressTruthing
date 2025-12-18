An in house Python tool to truth(the capture of address text) a directory of images. Simple tkinter GUI used for the truthing interface and command line scripts for setting up image sets and post-processing results. SqlLite is used as backend storage of data. Tesseract is used to perform OCR. An old C executable for parsing text addresses and lookups into a national USPS directory of addresses is used for determing the 11 digit USPS encoding of the address, if possible.

NicK:
Ok. I just realized that 'teeseract_ocr' needs to be installed. This is in addition to the python package wrapper 'pytesseract'). Also, it would need to be installed separately for both wsl linux and windows, depending on your preference.
1) Turns out I could not get the address directory files on github(too large) to run the C executable. The executable was compiled on Linux, which is why I had instructions below for 'wsl' on Windows. Not to mention the fact that the data is from non-public US Postal Service sources...
2) The last python script will abort without doing the USPS database lookups. 
3) Ugh. I had to install Visual C++ Redistributable of Visual Studio to use 'opencv' on Windows and I'm still getting an error.
4) Best to stick with 'wsl'...

1) 'wsl --install' from Windows terminal and restart windows (This is the Linux emulator)
2) In a Windows terminal, 'wsl'.
3) 'sudo apt-get install tesseract-ocr' (will ask for your password)
4) Clone the repository on your machine: 
5) On GitHub, navigate to the main page of the repository. 
6) Above the list of files, click 'Code'. 
7) under "HTTPS", click 'copy' icon 
8) In 'wsl' terminal, 'git clone https://github.com/mastm1/AddressTruthing.git'
9) In 'wsl' terminal, enter 'cd /MailPieceTruthing'
10) Enter 'chmod +x *'
11) 'conda env create -f environment.yml'
12) 'conda activate fpars_env'
13) 'python importFPARSImages.py -d images/A3/ -s A3.sqlite3' (creates a backend sqlite3 db using the sample images)
14) 'python mainFPARS.py -s A3.sqlite3' (executes the "truther", try it out)
15) Rubberband around the address in the image. Then rubberband around a region(a line or lines) in the newly created image to execute OCR.
16) 'python MatchWithPostalDatabase.py -s A3.sqlite3' (Performs USPS lookup of the OCR results and gives 11 digit ZIP, if successful).
17) The final post-processing script ('MatchWithPostalDatabse.py') is NOT fully operational! It requires US Postal Service address data which I cannot provide.
