import shutil
import os


def make_archive():
    source_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_filename = os.path.join(source_dir, "deployment")

    # Define what to ZIP (whitelist approach is safer, or blacklist)
    # Using ZipFile directly for better control over structure
    import zipfile

    with zipfile.ZipFile(output_filename + ".zip", "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude dirs
            dirs[:] = [
                d
                for d in dirs
                if d not in [".venv", ".git", "__pycache__", "logs", "tests", ".vscode"]
            ]

            for file in files:
                if file in [".env", "deployment.zip", ".DS_Store"]:
                    continue
                if file.endswith(".pyc"):
                    continue

                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)
                print(f"Packed: {arcname}")

    print(f"\n✅ Created: {output_filename}.zip")


if __name__ == "__main__":
    make_archive()
