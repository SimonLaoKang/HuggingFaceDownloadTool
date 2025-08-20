# HuggingFace、hf-mirror模型下载工具 V1.0

## 简介

本工具用于批量下载 HuggingFace 上的模型或数据集文件，支持原始地址和镜像地址，集成 IDM（Internet Download Manager）实现高速下载。支持导出下载链接、批量导入 IDM 队列、自动识别仓库类型、文件树选择、URL 编码等功能。

借鉴于：
https://www.bilibili.com/opus/1039284619941249065
https://github.com/CFSO7322/huggingface-download-tool/tree/main
并在这里扩展到数据集和模型，理论上基本都能下到。

## 主要功能

- 自动检测 IDM 安装路径并启动 IDM
- 支持 HuggingFace 原始地址和镜像地址（如 https://hf-mirror.com）
- 支持模型和数据集仓库
- 文件树结构展示，支持多选、全选/全不选
- 显示文件大小、修改时间、已选文件数、总大小
- 导出下载链接为 txt 文件
- 一键批量导入 IDM 下载队列
- 可选自动开始下载
- 下载路径自定义
- 下载链接支持 URL 编码

## 使用方法

1. 安装依赖（需 Python 3.8+）或者直接运行bat脚本：

   ```sh
   pip install requests beautifulsoup4 pywin32 PyQt6
   ```

2. 运行程序：

   ```sh
   python HF模型下载工具\ V1.0.py
   ```

3. 按界面提示填写仓库名（如 `CompVis/stable-diffusion-v-1-4-original`），选择下载地址、Token（如有），点击“读取文件列表”。
4. 勾选需要下载的文件，可全选/全不选。
5. 可导出下载链接或直接导入 IDM 下载队列。
6. 如未自动识别 IDM 路径，可手动选择 IDM 安装目录下的 `IDMan.exe`。
7. 可自定义下载目录。

## 注意事项

- 需提前安装 IDM（Internet Download Manager）。
- 部分镜像站可能不支持所有仓库或文件。
- Token 可选，部分私有仓库需填写。好像是没啥用。
- Windows 系统专用。

## 依赖

- requests
- beautifulsoup4
- pywin32
- PyQt6

## 许可证

无，白嫖ai的劳动力。
