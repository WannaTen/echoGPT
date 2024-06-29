# voice to backend to text
from openai import AsyncOpenAI, OpenAI
import asyncio
import pyaudio
import audioop
import wave
import os
import threading
from queue import Queue
import pygame
import ctypes
import keyboard
import time
from datetime import datetime


# 配置音频流参数
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
RECORD_SECONDS = 2  # 每次录音的时长（秒）
AUDIO_FILE = "temp.wav"


stt_client = AsyncOpenAI(api_key="cant-be-empty", base_url="http://localhost:8000/v1/")
tts_client = AsyncOpenAI(api_key="cant-be-empty", base_url="http://localhost:7870/v1/")
chat_client = OpenAI(api_key="sk-xxxxxxx", base_url="https://api.siliconflow.cn/v1")

# warmup
# audio_file = open("D:\\Code\\warmup.mp3", "rb")


def record_audio(audio_queue, run_flag):
    # 初始化PyAudio
    p = pyaudio.PyAudio()
    # 打开音频流
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    silence_threshold = 500
    try:
        print("开始录音... 按 ESC 停止")
        while run_flag.is_set():
            frames = []

            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK)
                avg_amplitude = audioop.rms(data, 2)  # 计算平均振幅
                if avg_amplitude > silence_threshold:
                    frames.append(data)

            if frames:  # 如果有非静音数据，则加入队列
                audio_queue.put(b''.join(frames))

            time.sleep(0.1)  # 确保文件写入完成
    except KeyboardInterrupt:
        print("录音结束")
    finally:
        # 关闭音频流
        stream.stop_stream()
        stream.close()
        p.terminate()


async def send_audio(audio_queue, text_queue):
    try:
        while True:
            if audio_queue.empty():
                await asyncio.sleep(0.1)
                continue
            audio_data = audio_queue.get()
            
            # 保存音频数据到文件
            with wave.open(AUDIO_FILE, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(audio_data)

            if os.path.exists(AUDIO_FILE):
                with open(AUDIO_FILE, 'rb') as f:
                    audio_data = f.read()
                    # start_time = time.time()
                    # print(f"发送音频中...{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
                    transcript = await stt_client.audio.transcriptions.create(
                            model="large-v3", 
                            file=audio_data, 
                            language="zh",
                            response_format="text"
                        )
                    print(transcript,flush=True)
                    # new_text = await generate(transcript)
                    text_queue.put(transcript)
                    # end_time = time.time()
                    # print(f"接收完成...{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
                    # print("耗时：", end_time - start_time, "秒", flush=True)

                os.remove(AUDIO_FILE)  # 发送成功后删除文件

            await asyncio.sleep(0.1)  # 等待下一次发送
    except KeyboardInterrupt:
        print("发送音频任务结束")


async def generate(text):
    sleep_time = 0.1
    await asyncio.sleep(sleep_time)
    return text


# 文本转语音
async def tts(text):
    if not text:
        return
    speech_file_path = "D:\\Code\\speech.mp3"
    response = await tts_client.audio.speech.create(
        model="chattts-4w",
        input=text,
        voice="female2",
    )
    response.stream_to_file(speech_file_path)
    # 初始化pygame的音频模块
    pygame.mixer.init()
    # 加载音频文件
    pygame.mixer.music.load(speech_file_path)
    # 播放音频
    pygame.mixer.music.play()
    # 等待音频播放完成
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    print("语音合成完成")


def stt_async_worker(audio_queue, text_queue):
    asyncio.run(send_audio(audio_queue, text_queue))


def tts_async_worker(text_queue):
    asyncio.run(tts(text_queue))


def on_activate(run_flag, text_queue):
    if not run_flag.is_set():
        print("Activated - start processes")
        run_flag.set()
        start_processes(run_flag, text_queue)
        print("Processes finished")
    else:
        print("Program is already running")


def start_processes(run_flag, text_queue):
    audio_queue = Queue()
    # text_queue = Queue()
    record_process = threading.Thread(target=record_audio, args=(audio_queue,run_flag,))
    stt_process = threading.Thread(target=stt_async_worker, args=(audio_queue, text_queue))
    record_process.start()
    stt_process.start()


if __name__ == "__main__":
    # asyncio.run(main())
    run_flag = threading.Event()
    while True:
        text_queue = Queue()
        keyboard.add_hotkey('ctrl+k', on_activate, args=(run_flag, text_queue, ))
        print("Press Ctrl+k to start the program")
        keyboard.wait('esc')
        run_flag.clear()
        print("audio stoped")
        texts = []
        while not text_queue.empty():
            texts.append(text_queue.get())
        queue = " ".join(texts)
        print(queue)
        response = chat_client.chat.completions.create(
            model='alibaba/Qwen2-72B-Instruct',
            messages=[
                {'role': 'user', 'content': f"{queue}"}
            ],
            stream=True
        )
        response_text = ""
        for chunk in response:
            if chunk.choices[0].delta.content == None:
                continue
            print(chunk.choices[0].delta.content, end="",flush=True)
            response_text += chunk.choices[0].delta.content
        asyncio.run(tts(response_text))
