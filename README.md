# 使用方法

## Speech To Text 服务
使用[faster-whisper-server](https://github.com/fedirz/faster-whisper-server)

 docker 部署即可:
```shell
docker run --gpus=all --publish 8000:8000 --volume ~/.cache/huggingface:/root/.cache/huggingface --env WHISPER_MODEL=large-v3 fedirz/faster-whisper-server:latest-cuda
```

## Text to Speech 服务
使用[ChatTTS-forge](https://github.com/lenML/ChatTTS-Forge)

Docker 部署:
```shell
git clone https://github.com/lenML/ChatTTS-Forge.git
cd ChatTTS-Forge
docker-compose -f ./docker-compose.api.yml up -d
```

## 使用
```
cd echoGPT
pip install -r requirement.txt
python main.py
```

`ctrl + k` 开始录音, 按 `Esc` 停止并发送语音, 等待模型生成文本, 并转录语音
