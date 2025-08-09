#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神威日報 Zoom録画 Whisper API文字起こしスクリプト
実際の音声から口調まで含めた詳細な文字起こしを生成
"""

import json
import requests
import time
import re
import os
from datetime import datetime
from typing import Dict, List, Optional
import urllib.parse
from pathlib import Path

# OpenAI APIキーが必要
# export OPENAI_API_KEY="your-api-key-here"

class WhisperTranscriptionExtractor:
    def __init__(self, api_key: str = None):
        self.base_url = "https://zoom.us/rec/share/"
        self.transcriptions = []
        self.session = requests.Session()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            print("警告: OpenAI APIキーが設定されていません")
            print("環境変数 OPENAI_API_KEY を設定するか、api_key パラメータを指定してください")
        
    def extract_video_id(self, url: str) -> str:
        """Zoom URLからビデオIDを抽出"""
        try:
            parts = url.split('/')
            video_id = parts[-1].split('.')[0]
            return video_id
        except Exception as e:
            print(f"URL解析エラー: {url}, エラー: {e}")
            return None
    
    def get_zoom_recording_info(self, url: str) -> Dict:
        """Zoom録画の情報を取得"""
        try:
            # Zoom録画ページにアクセス
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # ページから録画情報を抽出
            content = response.text
            
            # 録画タイトルを抽出
            title_match = re.search(r'<title>(.*?)</title>', content)
            title = title_match.group(1) if title_match else "神威日報技術ミーティング"
            
            # 録画日時を抽出
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
            record_date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
            
            return {
                "title": title,
                "record_date": record_date,
                "url": url,
                "status": "available"
            }
            
        except Exception as e:
            print(f"録画情報取得エラー: {url}, エラー: {e}")
            return {
                "title": "神威日報技術ミーティング",
                "record_date": datetime.now().strftime("%Y-%m-%d"),
                "url": url,
                "status": "error"
            }
    
    def extract_audio_url(self, zoom_url: str) -> Optional[str]:
        """Zoom録画から音声URLを抽出"""
        try:
            # Zoom録画ページを解析して音声URLを取得
            response = self.session.get(zoom_url, timeout=30)
            response.raise_for_status()
            
            content = response.text
            
            # 音声ファイルのURLパターンを検索
            audio_patterns = [
                r'https://[^"]*\.mp3[^"]*',
                r'https://[^"]*\.m4a[^"]*',
                r'https://[^"]*audio[^"]*',
                r'https://[^"]*recording[^"]*'
            ]
            
            for pattern in audio_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    return matches[0]
            
            return None
            
        except Exception as e:
            print(f"音声URL抽出エラー: {zoom_url}, エラー: {e}")
            return None
    
    def download_audio(self, audio_url: str, filename: str) -> bool:
        """音声ファイルをダウンロード"""
        try:
            response = self.session.get(audio_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            print(f"音声ダウンロードエラー: {audio_url}, エラー: {e}")
            return False
    
    def transcribe_with_whisper(self, audio_file: str) -> str:
        """Whisper APIを使用して音声ファイルを文字起こし"""
        if not self.api_key:
            return "OpenAI APIキーが設定されていません"
        
        try:
            import openai
            
            # OpenAIクライアントを設定
            openai.api_key = self.api_key
            
            print(f"Whisper APIで音声ファイルを文字起こし中: {audio_file}")
            
            with open(audio_file, "rb") as audio:
                transcript = openai.Audio.transcribe(
                    "whisper-1",
                    audio,
                    response_format="verbose_json",
                    timestamp_granularities=["word"],
                    language="ja"  # 日本語を指定
                )
            
            # 詳細な文字起こし結果を整形
            if hasattr(transcript, 'text'):
                return transcript.text
            else:
                return str(transcript)
                
        except ImportError:
            print("openaiライブラリがインストールされていません")
            print("pip install openai を実行してください")
            return "openaiライブラリエラー"
            
        except Exception as e:
            print(f"Whisper API文字起こしエラー: {e}")
            return f"Whisper APIエラー: {e}"
    
    def process_video(self, url: str, index: int) -> Dict:
        """個別の動画を処理"""
        print(f"処理中: 動画 #{index:02d}")
        
        # 録画情報を取得
        recording_info = self.get_zoom_recording_info(url)
        
        # 音声URLを抽出
        audio_url = self.extract_audio_url(url)
        
        transcription_data = {
            "metadata": {
                "video_id": self.extract_video_id(url),
                "url": url,
                "index": index,
                "title": recording_info["title"],
                "record_date": recording_info["record_date"],
                "status": recording_info["status"]
            },
            "audio_url": audio_url,
            "transcription": "",
            "extracted_at": datetime.now().isoformat()
        }
        
        if audio_url:
            # 音声ファイルをダウンロード
            audio_filename = f"audio_{index:02d}.mp3"
            if self.download_audio(audio_url, audio_filename):
                # Whisper APIで文字起こしを実行
                transcription = self.transcribe_with_whisper(audio_filename)
                transcription_data["transcription"] = transcription
                
                # 音声ファイルを削除（容量節約）
                Path(audio_filename).unlink(missing_ok=True)
            else:
                transcription_data["transcription"] = "音声ダウンロードに失敗しました"
        else:
            transcription_data["transcription"] = "音声URLの抽出に失敗しました"
        
        return transcription_data
    
    def process_videos(self, video_urls: List[str]) -> List[Dict]:
        """動画URLリストを処理"""
        transcriptions = []
        
        for index, url in enumerate(video_urls, 1):
            try:
                transcription_data = self.process_video(url, index)
                transcriptions.append(transcription_data)
                
                # API制限を避けるための遅延
                time.sleep(2)
                
            except Exception as e:
                print(f"動画処理エラー #{index}: {e}")
                continue
        
        return transcriptions
    
    def save_to_json(self, transcriptions: List[Dict], filename: str = "whisper_transcriptions.json"):
        """文字起こしデータをJSONファイルに保存"""
        data = {
            "metadata": {
                "source": "神威日報 Zoom録画 Whisper API文字起こし",
                "total_videos": len(transcriptions),
                "created_at": datetime.now().isoformat(),
                "description": "Whisper APIを使用した実際の音声から口調まで含めた詳細な文字起こしデータ",
                "format": "JSON",
                "version": "2.0",
                "api": "OpenAI Whisper"
            },
            "transcriptions": transcriptions
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Whisper API文字起こしデータを {filename} に保存しました")
    
    def save_to_text(self, transcriptions: List[Dict], filename: str = "whisper_transcriptions.txt"):
        """文字起こしデータをテキストファイルに保存"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 神威日報 Zoom録画 Whisper API文字起こしデータ\n")
            f.write(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"総動画数: {len(transcriptions)}\n")
            f.write("API: OpenAI Whisper\n")
            f.write("=" * 80 + "\n\n")
            
            for video in transcriptions:
                metadata = video['metadata']
                transcription = video['transcription']
                
                f.write(f"## {metadata['title']}\n")
                f.write(f"日付: {metadata['record_date']}\n")
                f.write(f"URL: {metadata['url']}\n")
                f.write(f"ステータス: {metadata['status']}\n")
                f.write("-" * 60 + "\n")
                f.write(transcription)
                f.write("\n\n" + "=" * 80 + "\n\n")
        
        print(f"Whisper API文字起こしテキストを {filename} に保存しました")

def main():
    # video_links.txtからURLを読み込み
    with open('video_links.txt', 'r', encoding='utf-8') as f:
        video_urls = [line.strip() for line in f if line.strip()]
    
    # APIキーを確認
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("警告: OPENAI_API_KEY環境変数が設定されていません")
        print("実際の文字起こしを行うには、APIキーを設定してください")
    
    # 抽出器を初期化
    extractor = WhisperTranscriptionExtractor(api_key)
    
    # 動画を処理
    print("Whisper API文字起こしを開始します...")
    transcriptions = extractor.process_videos(video_urls)
    
    # データを保存
    extractor.save_to_json(transcriptions)
    extractor.save_to_text(transcriptions)
    
    print(f"完了: {len(transcriptions)}個の動画をWhisper APIで文字起こししました")

if __name__ == "__main__":
    main() 