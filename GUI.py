import os
import shutil
import requests
from bs4 import BeautifulSoup
import re
from googletrans import Translator
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import tkinter as tk
from tkinter import messagebox

# 请求头，模拟浏览器访问
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 清理非法字符
def sanitize_filename(filename):
    """清理非法字符，保留括号"""
    filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
    return filename

# 提取日文名字
def extract_japanese_name(content):
    """提取演员名字中的日文部分"""
    match = re.search(r'([一-龯ぁ-んア-ン]+)', content)
    if match:
        return match.group(1)
    return content

def process_video(video_id, result_text):
    url = f"https://jvrlibrary.com/jvr?id={video_id}"
    result_text.insert(tk.END, f"正在访问: {url}\n")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        result_text.insert(tk.END, "网页请求成功！\n")

        # 提取信息
        video_title = soup.find('title').text.strip().replace(" - Online Streaming And Download", "")
        og_url = soup.find('meta', property="og:url")['content']
        video_number = re.search(r'id=([A-Za-z0-9\-]+)', og_url).group(1) if og_url else "未找到番号"
        description = soup.find('meta', property="og:description")['content']
        actors = soup.find_all('meta', property="og:video:actor")
        actor_names = [extract_japanese_name(actor['content']) for actor in actors]

        formatted_title = f"[{video_number}] {description}"
        formatted_title = re.sub(r'^\[VR]\s*', '', formatted_title)

        translator = Translator()
        translated_title = translator.translate(formatted_title, src='en', dest='zh-cn').text
        translated_description = translator.translate(description, src='en', dest='zh-cn').text

        # 创建 XML 文件
        movie = ET.Element("movie")
        title = ET.SubElement(movie, "title")
        title.text = translated_title

        plot = ET.SubElement(movie, "plot")
        plot.text = translated_description

        actor_element = ET.SubElement(movie, "actor")
        for actor_name in actor_names:
            actor_name_element = ET.SubElement(actor_element, "name")
            actor_name_element.text = actor_name

        nfo_filename = "movie.nfo"
        tree = ET.ElementTree(movie)
        os.makedirs(translated_title, exist_ok=True)
        nfo_path = os.path.join(translated_title, nfo_filename)
        tree.write(nfo_path, encoding="UTF-8", xml_declaration=True)
        result_text.insert(tk.END, f"movie.nfo 文件已创建！\n")

        # 图片下载
        image_mapping = {
            "pl.jpg": f"{video_number}-fanart.jpg",
            "jp-1.jpg": f"{video_number}-poster.jpg"
        }

        for img in soup.find_all('img'):
            img_url = img.get('src')
            if img_url:
                img_url = urljoin(url, img_url)

                for key, file_name in image_mapping.items():
                    if key in img_url:
                        img_path = os.path.join(translated_title, file_name)
                        try:
                            img_data = requests.get(img_url, headers=headers, timeout=10).content
                            with open(img_path, 'wb') as f:
                                f.write(img_data)
                            result_text.insert(tk.END, f"已成功下载图片: {img_path}\n")
                        except requests.RequestException as e:
                            result_text.insert(tk.END, f"下载图片失败: {e}\n")

        # 移动到演员文件夹
        actor_folder = sanitize_filename(' '.join(actor_names))
        os.makedirs(actor_folder, exist_ok=True)
        shutil.move(translated_title, os.path.join(actor_folder, translated_title))
        result_text.insert(tk.END, f"文件夹已移动到演员文件夹: {os.path.join(actor_folder, translated_title)}\n")

    except requests.RequestException as e:
        result_text.insert(tk.END, f"请求失败: {e}\n")
    except AttributeError as e:
        result_text.insert(tk.END, f"解析失败: {e}\n")
    except Exception as e:
        result_text.insert(tk.END, f"发生未知错误: {e}\n")

def start_scraping():
    video_id = video_id_entry.get().strip().upper()
    if not video_id:
        messagebox.showerror("错误", "请输入一个有效的视频番号")
        return
    result_text.delete(1.0, tk.END)  # 清空结果文本框
    process_video(video_id, result_text)

# 设置GUI窗口
root = tk.Tk()
root.title("视频爬虫")
root.geometry("600x400")

# 视频番号输入框
video_id_label = tk.Label(root, text="请输入番号:")
video_id_label.pack(pady=5)

video_id_entry = tk.Entry(root, width=40)
video_id_entry.pack(pady=5)

# 开始爬取按钮
start_button = tk.Button(root, text="开始爬取", command=start_scraping)
start_button.pack(pady=20)

# 结果显示区域
result_text = tk.Text(root, width=70, height=15)
result_text.pack(pady=10)

# 运行GUI
root.mainloop()
