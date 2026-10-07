#!/usr/bin/env bash
# Reconstruit Reparer-bureau.exe à partir de bureau.sh
# Nécessite : gcc-mingw-w64-x86-64 (sudo apt install gcc-mingw-w64-x86-64)
set -e
cd "$(dirname "$0")"
python3 - <<'PY'
d = open("../bureau.sh", "rb").read()
with open("script.h", "w") as f:
    f.write("static const unsigned char bureau_sh[] = {")
    f.write(",".join(str(b) for b in d))
    f.write("};\nstatic const unsigned int bureau_sh_len = %d;\n" % len(d))
PY
x86_64-w64-mingw32-gcc -O2 -s -municode -mwindows -Wall -o ../Reparer-bureau.exe reparer-bureau.c
rm -f script.h
echo "OK : Reparer-bureau.exe"
