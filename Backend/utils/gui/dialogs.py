import os

from PySide6.QtWidgets import QFileDialog


class FileHandler:
    def __init__(self):
        super().__init__()

    def open_file(self, caption="打开文件", file="所有文件 (*.*)", default_dir=None):
        if default_dir is None:
            default_dir = os.getcwd()
        file_path, _ = QFileDialog.getOpenFileName(None, caption, default_dir, file)
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                return content, file_path
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='gbk') as file:
                        content = file.read()
                    return content, file_path
                except Exception as e:
                    print(f"读取文件失败: {str(e)}")
            except Exception as e:
                print(f"读取文件失败: {str(e)}")
        return None, None

    def save_file(self, content, caption="保存文件", file="所有文件 (*.*)", default_dir=None, default_filename=""):
        if default_dir is None:
            default_dir = os.getcwd()
        file_path, _ = QFileDialog.getSaveFileName(
            None, caption, os.path.join(default_dir, default_filename), file
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                return file_path
            except Exception as e:
                print(f"保存文件失败: {str(e)}")
        return None

    def open_file_by_path(self, file_path, content=None, ):
        if not file_path:
            return None
        try:
            if content is None:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                return content
            else:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                return None
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    content = file.read()
                return content
            except Exception as e:
                print(f"读取文件失败: {str(e)}")
        except Exception as e:
            print(f"读取文件失败: {str(e)}")
        return None
