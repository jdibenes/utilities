// Juan Carlos Dibene Simental (jdibenes@outlook.com)
// 2011

#include <Windows.h>
#include <stdio.h>

#define APPNAME       "mWnd"
#define MUTEXNAME     APPNAME"mutex"
#define ERROR_RUNNING APPNAME" is already running"
#define QUIT_MESSAGE  "double click to quit"
#define TRAYWNDCLASS  "TRAYWNDCLASS"

#define WM_TRAYICON   WM_USER
#define CFG_RESTRICT  TRUE
#define CFG_DELAY     1

#define IsKeyDown(vk) (GetAsyncKeyState(vk) & 0x8000)

HANDLE     g_mutex;
HWND       g_trayhwnd;
HWND       g_hwnd;
CURSORINFO g_lastpos;

LRESULT CALLBACK TrayWindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_TRAYICON:
        switch (lParam) {
        case WM_LBUTTONDBLCLK: PostQuitMessage(0); break;
        }
    }

    return DefWindowProc(hwnd, uMsg, wParam, lParam);
}

BOOL CreateNotifyIcon(HINSTANCE hInstance) {
    NOTIFYICONDATA nid;
    WNDCLASS wndclass;

    ZeroMemory(&nid, sizeof(nid));
    ZeroMemory(&wndclass, sizeof(wndclass));

    wndclass.lpszClassName = TRAYWNDCLASS;
    wndclass.lpfnWndProc   = TrayWindowProc;
    wndclass.hInstance     = hInstance;

    if (!RegisterClass(&wndclass)) { return FALSE; }

    g_trayhwnd = CreateWindowEx(0, TRAYWNDCLASS, APPNAME, 0, 0, 0, 0, 0, HWND_MESSAGE, NULL, NULL, NULL);
    if (!g_trayhwnd) { return FALSE; }

    nid.cbSize           = sizeof(nid);
    nid.hWnd             = g_trayhwnd;
    nid.uID              = 0;
    nid.uFlags           = NIF_MESSAGE | NIF_ICON | NIF_TIP;
    nid.uCallbackMessage = WM_TRAYICON;
    nid.hIcon            = LoadIcon(0, IDI_WARNING);

    sprintf(nid.szTip, "%s - %s", APPNAME, QUIT_MESSAGE);

    if (!Shell_NotifyIcon(NIM_ADD, &nid)) { return FALSE;  }

    return TRUE;
}

BOOL RemoveNotifyIcon() {
    NOTIFYICONDATA nid;

    nid.cbSize = sizeof(nid);
    nid.hWnd   = g_trayhwnd;
    nid.uID    = 0;

    return Shell_NotifyIcon(NIM_DELETE, &nid);
}

BOOL SetSingleInstance() {
    DWORD gle;

    g_mutex = CreateMutex(0, TRUE, MUTEXNAME);
    if (!g_mutex) { return FALSE; }

    gle = GetLastError();
    if (gle != ERROR_ALREADY_EXISTS && gle != ERROR_ACCESS_DENIED) { return TRUE; }

    MessageBox(0, ERROR_RUNNING, APPNAME, MB_OK | MB_ICONASTERISK);

    return FALSE;
}

BOOL EndSingleInstance() {
    return CloseHandle(g_mutex);
}

BOOL TestCommand() {
    return IsKeyDown(VK_CONTROL) && IsKeyDown(VK_MENU) && IsKeyDown(GetSystemMetrics(SM_SWAPBUTTON) ? VK_RBUTTON : VK_LBUTTON) ? TRUE : FALSE;
}

BOOL ProcessMsg() {
    MSG msg;

    while (PeekMessage(&msg, 0, 0, 0, PM_REMOVE)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
        if (msg.message == WM_QUIT) { return FALSE; }
    }

    return TRUE;
}

void UpdateWindowPos() {
    CURSORINFO cn;
    RECT       rect;
    int        dx;
    int        dy;
    int        nextx;
    int        nexty;

    cn.cbSize = sizeof(CURSORINFO);

    if (!GetCursorInfo(&cn)) { return; }

    dx = cn.ptScreenPos.x - g_lastpos.ptScreenPos.x;
    dy = cn.ptScreenPos.y - g_lastpos.ptScreenPos.y;

    g_lastpos.ptScreenPos.x = cn.ptScreenPos.x;
    g_lastpos.ptScreenPos.y = cn.ptScreenPos.y;

    if (dx == 0 && dy == 0) { return; }

    if (!GetWindowRect(g_hwnd, &rect)) { return; }

    nextx = rect.left + dx;
    nexty = rect.top  + dy;

    if (!SetWindowPos(g_hwnd, 0, nextx, nexty, 0, 0, SWP_ASYNCWINDOWPOS | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOOWNERZORDER)) { return; }
}

BOOL SelectWindow() {
    POINT           mp;
    WINDOWINFO      wi;
    WINDOWPLACEMENT wpm;
    RECT            rect;
    int             nextx;
    int             nexty;

    g_lastpos.cbSize = sizeof(CURSORINFO);
    if (!GetCursorInfo(&g_lastpos)) { return FALSE; }

    mp.x = g_lastpos.ptScreenPos.x;
    mp.y = g_lastpos.ptScreenPos.y;

    g_hwnd = WindowFromPoint(mp);
    if (!g_hwnd) { return FALSE; }

    g_hwnd = GetAncestor(g_hwnd, GA_ROOT);
    if (!g_hwnd) { return FALSE; }

    wpm.length = sizeof(WINDOWPLACEMENT);
    if (!GetWindowPlacement(g_hwnd, &wpm)) { return FALSE; }

    wi.cbSize = sizeof(WINDOWINFO);
    if (!GetWindowInfo(g_hwnd, &wi)) { return FALSE; }

    if (wpm.showCmd != SW_SHOWNORMAL) { return FALSE; }
    if (CFG_RESTRICT && (wi.dwStyle & WS_CAPTION) != WS_CAPTION) { return FALSE; }

    if (!ShowWindow(g_hwnd, SW_RESTORE)) { return FALSE; }
    if (!GetWindowRect(g_hwnd, &rect)) { return FALSE; }

    if (mp.x < rect.left || mp.x > rect.right)  { nextx = mp.x - ((rect.right  - rect.left) / 2); } else { nextx = rect.left; }
    if (mp.y < rect.top  || mp.y > rect.bottom) { nexty = mp.y - ((rect.bottom - rect.top)  / 2); } else { nexty = rect.top;  }

    if (nextx == rect.left && nexty == rect.top) { return TRUE; }
    if (!SetWindowPos(g_hwnd, 0, nextx, nexty, 0, 0, SWP_ASYNCWINDOWPOS | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOOWNERZORDER)) { return FALSE; }

    return TRUE;
}

void TestBody(BOOL* busy, BOOL* block) {
    if (TestCommand()) {
        if (*block) { return; }
        if (*busy) {
            UpdateWindowPos();
        }
        else {
            *block = TRUE;
            if (!SelectWindow()) { return; }
            *block = FALSE;
            *busy  = TRUE;
        }
    }
    else {
        *busy  = FALSE;
        *block = FALSE;
    }
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nShowCmd) {
    BOOL busy = FALSE;
    BOOL block = FALSE;

    if (!SetSingleInstance()) { return 0; }
    if (!CreateNotifyIcon(hInstance)) { return 0; }

    for (;;) {
        if (!ProcessMsg()) { break; }
        Sleep(CFG_DELAY);
        TestBody(&busy, &block);
    }

    RemoveNotifyIcon();
    EndSingleInstance();

    return 0;
}
