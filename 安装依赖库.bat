@echo off
echo ��ʼ��װ������...
pip install requests beautifulsoup4 PyQt6
if %errorlevel% equ 0 (
    echo �����ⰲװ�ɹ���
) else (
    echo �����ⰲװʧ�ܣ���������� Python ������
)
pause