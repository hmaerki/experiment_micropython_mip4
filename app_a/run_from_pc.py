import mp
import mp.micropythonshell

if __name__ == "__main__":
    shell = mp.micropythonshell.MicropythonShell(str_port=None)  # 'COM9')
    shell.sync_folder(
        directory_local="micropython",
        files_to_skip=["config_secrets.py", "config_package_manifest.json"],
    )
    shell.repl(start_main=True)
    shell.close()
