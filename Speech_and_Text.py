import speech_recognition as sr
import requests
import time
import hashlib
import base64
import json
import pyttsx3
from aip import AipSpeech
from pydub import AudioSegment
import os.path as path

# 定义SpeechRecognition对象
r = sr.Recognizer()

# 从麦克风获取音频并写入文件
def _record(if_cmu: bool = False):
    with sr.Microphone() as source:
        # 校准环境噪声水平的energy threshold
        r.adjust_for_ambient_noise(source, duration = 1)
        audio = r.listen(source, timeout = 3, phrase_time_limit = 2)

    file_name = path.join(path.dirname(path.abspath(__file__)), "audio/speech.wav")
    with open(file_name, "wb") as f:
        f.write(audio.get_wav_data())
    
    if if_cmu:
        return audio
    else:
        return _get_file_content(file_name)

# 从文件中加载音频
def _get_file_content(file_name):
    # 要转换的音频源文件
    speech = AudioSegment.from_wav(file_name).set_frame_rate(16000)
    return speech.raw_data

def speech_to_text_baidu(audio_path: str = "test.wav", if_microphone: bool = True):
    # https://cloud.baidu.com/product/speech 申请api
    app_id = ""
    api_key = ""
    secret_key = ""
    client = AipSpeech(app_id, api_key, secret_key)

    # 麦克风读入
    if if_microphone:
        result = client.asr(_record(), 'pcm', 16000, {
            'dev_pid': 1537,  # 识别普通话，使用输入法模型
        })
    # 文件读入
    else:
        result = client.asr(_get_file_content(audio_path), 'pcm', 16000, {
            'dev_pid': 1537,  # 识别普通话，使用输入法模型
        })

    if result["err_msg"] != "success.":
        return "..."
    else:
        return result['result'][0]

def speech_to_text_cmu(audio_path: str = "test.wav", if_microphone: bool = True):
    # 语种
    language_type = "zh-CN"

    # 麦克风读入
    if if_microphone:
        audio = _record(if_cmu = True)
    # 文件读入
    else:
        with sr.AudioFile(audio_path) as source:
            audio = r.record(source)

    try:
        # print(r.recognize_sphinx(audio, language=language_type))
        return r.recognize_sphinx(audio, language=language_type)
    except sr.UnknownValueError:
        print("Could not understand")
    except sr.RequestError as e:
        print("Sphinx error; {0}".format(e))


def speech_to_text_ifly(audio_path: str = "test.wav", if_microphone: bool = True):
    url = "http://api.xfyun.cn/v1/service/v1/iat"
    app_id = ""
    api_key = ""

    # aue：音频格式
    # engineType：引擎类型 （sms16k（16k采样率普通话音频）、sms8k（8k采样率普通话音频））
    def get_header(_aue, _engine_type):
        # curTime：当前UTC时间戳
        cur_time = str(int(time.time()))

        param = "{\"aue\":\"" + _aue + "\"" + ",\"engine_type\":\"" + _engine_type + "\"}"
        param_base64 = str(base64.b64encode(param.encode('utf-8')), 'utf-8')  # Base64编码

        # checkSum：令牌 出于安全性考虑，每个checkSum的有效期为5分钟(用curTime计算)
        m2 = hashlib.md5()
        m2.update((api_key + cur_time + param_base64).encode('utf-8'))
        check_sum = m2.hexdigest()

        # 请求头
        header = {
            'X-CurTime': cur_time,
            'X-Param': param_base64,
            'X-Appid': app_id,
            'X-CheckSum': check_sum,
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        }
        return header

    def get_body(filepath):
        
        if if_microphone:
            data = {'audio': base64.b64encode(filepath)}  # Base64编码
        else:
            bin_file = open(filepath, 'rb')  # 二进制
            data = {'audio': base64.b64encode(bin_file.read())}  # Base64编码
        return data

    aue = "raw"
    engine_type = "sms16k"

    # 麦克风读入
    if if_microphone:
        res = requests.post(url, headers=get_header(aue, engine_type), data=get_body(_record()))
    # 文件读入
    else:
        res = requests.post(url, headers=get_header(aue, engine_type), data=get_body(audio_path))
    
    result = res.content.decode('utf-8')
    # string转dict并提取关键字
    return json.loads(result)['data']


def text_to_speech(sentence: str):
    engine = pyttsx3.init()
    engine.say(sentence)
    engine.runAndWait()