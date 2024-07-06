import yt_dlp
import requests
from youtube_transcript_api import YouTubeTranscriptApi


# Chat with an intelligent assistant in your terminal
from openai import OpenAI

# Point to the local server
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")


def get_latest_video_ids(browser_name='firefox', max_videos=10):
    ydl_opts = {
        'cookiesfrombrowser': (browser_name, None, None, None),
        'extract_flat': True,
        'dump_single_json': True,
        'playlistend': max_videos
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info('https://www.youtube.com/feed/subscriptions', download=False)
        video_entries = result.get('entries', [])
        video_ids = [video['id'] for video in video_entries if 'id' in video]
        return video_ids

def get_transcripts(video_ids):
    transcripts = {}
    for video_id in video_ids:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript(['en'])
            transcripts[video_id] = transcript.fetch()
        except Exception as e:
            print(f"Could not retrieve transcript for video ID {video_id}: {e}")
            transcripts[video_id] = None
    return transcripts

def send_to_lmstudio(transcript):

    completion = client.chat.completions.create(
        model="3thn/dolphin-2.9-llama3-8b-GGUF",
        messages=[
            {"role": "system", "content": "You are an intelligent assistant. You always provide well-reasoned answers that are both correct and helpful."},
            {"role": "user", "content": "Create a brief overview (using bullet points) of the topics discussed in the following video transcript: \n\nSTART OF TRANSCRIPT\""+transcript[:8000]+"\" END OF TRANSCRIPT"},
        ],
        temperature=0.7,
        stream=True,
    )

    for chunk in completion:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)

    return




def print_summaries(transcripts):
    for video_id, transcript in transcripts.items():
        if transcript:
            full_transcript = ' '.join([entry['text'] for entry in transcript])
            print(f"\nSummary for Video ID {video_id}:\n")
            send_to_lmstudio(full_transcript)
    else:
            print(f"\nNo transcript available for Video ID {video_id}\n")

def main():
    video_ids = get_latest_video_ids()
    print(f"Retrieved video IDs: {video_ids}")
    transcripts = get_transcripts(video_ids)
    print_summaries(transcripts)

if __name__ == '__main__':
    main()
