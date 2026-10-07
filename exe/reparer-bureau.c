/*
 * Reparer-bureau.exe — lanceur Windows pour Wine / Proton.
 *
 * Contient le script bureau.sh. Lancé avec Wine ou Proton sous Linux, il
 * l'extrait et l'exécute avec /bin/bash sur le système Linux, sans sudo.
 * Si Wine refuse de lancer un programme Linux, il installe l'outil pour
 * qu'il s'ouvre tout seul à la prochaine connexion.
 *
 * Compilation : voir exe/construire.sh
 */
#include <windows.h>
#include <stdio.h>
#include "script.h" /* généré : bureau_sh[], bureau_sh_len */

#define TITRE L"Réparer le bureau"

typedef char *(CDECL *wine_unix_fn)(LPCWSTR);

static void message(const WCHAR *txt, UINT icone)
{
    MessageBoxW(NULL, txt, TITRE, MB_OK | icone);
}

static BOOL ecrire(const WCHAR *chemin, const void *data, DWORD len)
{
    HANDLE h = CreateFileW(chemin, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                           FILE_ATTRIBUTE_NORMAL, NULL);
    DWORD ecrit = 0;
    BOOL ok;
    if (h == INVALID_HANDLE_VALUE) return FALSE;
    ok = WriteFile(h, data, len, &ecrit, NULL) && ecrit == len;
    CloseHandle(h);
    return ok;
}

/* "/home/x/.local" -> "Z:\home\x\.local" */
static void vers_windows(const WCHAR *unix_path, WCHAR *out, size_t n)
{
    size_t i;
    _snwprintf(out, n, L"Z:%ls", unix_path);
    out[n - 1] = 0;
    for (i = 0; out[i]; i++) if (out[i] == L'/') out[i] = L'\\';
}

static void creer_dossiers(const WCHAR *chemin_fichier)
{
    WCHAR tmp[MAX_PATH];
    size_t i;
    lstrcpynW(tmp, chemin_fichier, MAX_PATH);
    for (i = 3; tmp[i]; i++) {
        if (tmp[i] == L'\\') { tmp[i] = 0; CreateDirectoryW(tmp, NULL); tmp[i] = L'\\'; }
    }
}

/* Plan B : installer l'outil + ouverture automatique à la prochaine connexion */
static BOOL plan_b(void)
{
    WCHAR home[MAX_PATH], base[MAX_PATH], f[MAX_PATH];
    char desktop[2048];
    char home_u8[MAX_PATH * 3];
    int n;

    if (!GetEnvironmentVariableW(L"HOME", home, MAX_PATH)) return FALSE;
    WideCharToMultiByte(CP_UTF8, 0, home, -1, home_u8, sizeof(home_u8), NULL, NULL);
    vers_windows(home, base, MAX_PATH);

    _snwprintf(f, MAX_PATH, L"%ls\\.local\\bin\\reparer-bureau.sh", base);
    creer_dossiers(f);
    if (!ecrire(f, bureau_sh, bureau_sh_len)) return FALSE;

    n = _snprintf(desktop, sizeof(desktop),
        "[Desktop Entry]\nType=Application\nName=R\xc3\xa9parer le bureau\n"
        "Exec=/bin/bash \"%s/.local/bin/reparer-bureau.sh\" %%s\n"
        "Icon=preferences-desktop\nTerminal=false\nCategories=System;Settings;\n",
        home_u8);
    (void)n;

    {
        char d1[2048], d2[2048];
        _snprintf(d1, sizeof(d1), desktop, "");
        _snprintf(d2, sizeof(d2), desktop, "--au-demarrage");
        _snwprintf(f, MAX_PATH, L"%ls\\.local\\share\\applications\\reparer-bureau.desktop", base);
        creer_dossiers(f);
        ecrire(f, d1, (DWORD)strlen(d1));
        _snwprintf(f, MAX_PATH, L"%ls\\.config\\autostart\\reparer-bureau.desktop", base);
        creer_dossiers(f);
        return ecrire(f, d2, (DWORD)strlen(d2));
    }
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE prev, LPWSTR args, int show)
{
    WCHAR tmp[MAX_PATH], script[MAX_PATH], cmd[4 * MAX_PATH], unixw[2 * MAX_PATH];
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    wine_unix_fn vers_unix;
    char *unix_path;
    DWORD code = 0;
    (void)inst; (void)prev; (void)args; (void)show;

    if (!GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "wine_get_version")) {
        message(L"Ce programme répare le bureau d'Ubuntu.\n\n"
                L"Il doit être lancé sous Linux avec Wine ou Proton.", MB_ICONINFORMATION);
        return 1;
    }

    /* 1. Extraire le script dans le dossier temporaire */
    GetTempPathW(MAX_PATH, tmp);
    _snwprintf(script, MAX_PATH, L"%lsreparer-bureau.sh", tmp);
    if (!ecrire(script, bureau_sh, bureau_sh_len)) {
        message(L"Impossible d'écrire le fichier temporaire.", MB_ICONERROR);
        return 1;
    }

    /* 2. Chemin Linux du script */
    vers_unix = (wine_unix_fn)GetProcAddress(GetModuleHandleW(L"kernel32.dll"),
                                             "wine_get_unix_file_name");
    unix_path = vers_unix ? vers_unix(script) : NULL;

    /* 3. Lancer /bin/bash sur Linux */
    if (unix_path) {
        MultiByteToWideChar(CP_UTF8, 0, unix_path, -1, unixw, 2 * MAX_PATH);
        HeapFree(GetProcessHeap(), 0, unix_path);
        _snwprintf(cmd, 4 * MAX_PATH, L"/bin/bash \"%ls\"", unixw);
        ZeroMemory(&si, sizeof(si));
        si.cb = sizeof(si);
        ZeroMemory(&pi, sizeof(pi));
        if (CreateProcessW(L"Z:\\bin\\bash", cmd, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
            WaitForSingleObject(pi.hProcess, INFINITE);
            GetExitCodeProcess(pi.hProcess, &code);
            CloseHandle(pi.hThread);
            CloseHandle(pi.hProcess);
            if (code == 3) {
                message(L"L'outil est installé, mais Proton l'empêche de s'ouvrir ici.\n\n"
                        L"→ Déconnecte-toi puis reconnecte-toi (ou redémarre) :\n"
                        L"   « Réparer le bureau » s'ouvrira tout seul.\n\n"
                        L"→ Ou relance ce .exe avec Wine plutôt que Proton.",
                        MB_ICONINFORMATION);
            }
            return 0;
        }
    }

    /* 4. Plan B */
    if (plan_b()) {
        message(L"L'outil « Réparer le bureau » est installé.\n\n"
                L"→ Déconnecte-toi puis reconnecte-toi (ou redémarre) :\n"
                L"   il s'ouvrira tout seul.\n\n"
                L"→ Ou, en console (Ctrl+Alt+F3) :\n"
                L"   bash ~/.local/bin/reparer-bureau.sh",
                MB_ICONINFORMATION);
        return 0;
    }
    message(L"Échec : impossible d'installer l'outil.\n\n"
            L"En console (Ctrl+Alt+F3), télécharge bureau.sh puis tape :\n"
            L"   bash bureau.sh", MB_ICONERROR);
    return 1;
}
