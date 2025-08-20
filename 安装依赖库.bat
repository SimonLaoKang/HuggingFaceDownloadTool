@echo off
echo 开始安装依赖库...
pip install requests beautifulsoup4 PyQt6
if %errorlevel% equ 0 (
    echo 依赖库安装成功！
) else (
    echo 依赖库安装失败，请检查网络或 Python 环境。
)
pause