An in house Python tool to truth(the capture of address text) a directory of images. Simple tkinter GUI used for the truthing interface and command line scripts for setting up image sets and post-processing results. SqlLite is used as backend storage of data. Tesseract is used to perform OCR. An old C executable for parsing text addresses and lookups into a national USPS directory of addresses is used for determing the 11 digit USPS encoding of the address, if possible.

NicK:
Ok. Turns out I could not get the address directory files on github(too large) to run the C executable. The executable was compiled on Linux, which is why I had instructions below for 'wsl' on Windows.
You can skip the 'wsl' parts. The last python script will abort without doing the USPS database lookups. Path separators will depend will be '\' on Windows. Still working on it...
Ugh. I had to install Visual C++ Redistributable of Visual Studio to use 'opencv' on Windows. Probably best to stick with 'wsl'...

1) 'wsl --install' from Windows terminal and restart windows (This is Linux)
2) In Windows terminal, 'wsl'.
3) Clone the repository on your machine: 
4) On GitHub, navigate to the main page of the repository. 
5) Above the list of files, click 'Code'. 
6) under "HTTPS", click 'copy' icon 
7) In 'wsl' terminal, 'git clone https://github.com/mastm1/AddressTruthing.git'
d) In 'wsl' terminal, enter 'cd /MailPieceTruthing' e) Enter 'chmod +x *'
9) 'conda env create -f environment.yml'
10) 'conda activate fpars_env'
11) 'python importFPARSImages.py -d images/A3/ -s A3.sqlite3' (creates a backend sqlite3 db using the sample images)
12) 'python mainFPARS.py -s A3.sqlite3' (executes the "truther", try it out)
13) Rubberband around the address in the image. Then rubberband around a region(a line or lines) in the newly created image to execute OCR.
14) 'python MatchWithPostalDatabase.py -s A3.sqlite3' (Performs USPS lookup of the OCR results and gives 11 digit ZIP, if successful).
15) The final post-processing script ('MatchWithPostalDatabse.py') is NOT fully operational! It requires US Postal Service address data which I cannot provide.
