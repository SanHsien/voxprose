// VoxProse native launcher (replaces BAT entry point).
// Compiled by setup_win.bat with the .NET Framework 4.x csc.exe that ships
// with Windows 10/11 — no extra toolchain needed, and a locally-built EXE
// carries no Mark-of-the-Web, so SmartScreen stays quiet.
//
// NOTE: This file must stay UTF-8 *with BOM* (csc assumes the ANSI codepage
// for BOM-less sources, which garbles the Chinese message strings), and the
// syntax must stay C# 5 compatible (csc v4.0.30319 has no string
// interpolation / null-conditional operators).
//
// Launch order mirrors run_voicetype.bat:
//   1. .runtime\pythonw.exe  (portable / embedded Python)
//   2. venv\Scripts\pythonw.exe
//   3. Neither present -> run setup_win.bat in a console, then retry.

using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

static class Launcher
{
    static string FindPythonw(string baseDir)
    {
        string embedded = Path.Combine(baseDir, ".runtime", "pythonw.exe");
        if (File.Exists(embedded))
            return embedded;
        string venv = Path.Combine(baseDir, "venv", "Scripts", "pythonw.exe");
        if (File.Exists(venv))
            return venv;
        return null;
    }

    [STAThread]
    static void Main()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;

        try
        {
            string pythonw = FindPythonw(baseDir);

            if (pythonw == null)
            {
                string setup = Path.Combine(baseDir, "setup_win.bat");
                if (!File.Exists(setup))
                {
                    MessageBox.Show(
                        "找不到 setup_win.bat，請確認程式資料夾完整。\n(setup_win.bat not found)",
                        "VoxProse", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }

                ProcessStartInfo setupInfo = new ProcessStartInfo("cmd.exe", "/c \"" + setup + "\"");
                setupInfo.WorkingDirectory = baseDir;
                setupInfo.UseShellExecute = true; // show the setup console
                using (Process setupProc = Process.Start(setupInfo))
                {
                    setupProc.WaitForExit();
                }

                pythonw = FindPythonw(baseDir);
                if (pythonw == null)
                {
                    MessageBox.Show(
                        "環境安裝未完成，無法啟動。請重新執行 setup_win.bat。\n(Setup did not complete)",
                        "VoxProse", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }
            }

            string mainPy = Path.Combine(baseDir, "main.py");
            ProcessStartInfo info = new ProcessStartInfo(pythonw, "\"" + mainPy + "\"");
            info.WorkingDirectory = baseDir;
            info.UseShellExecute = false;
            info.EnvironmentVariables["PYTHONPATH"] = baseDir;
            Process.Start(info);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "啟動失敗 (Launch failed):\n" + ex.Message,
                "VoxProse", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
