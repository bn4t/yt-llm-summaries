import yt_dlp
import requests
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from flask import Flask, render_template_string
import openai

# Initialize OpenAI client
openai_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")


# Initialize Flask app
app = Flask(__name__)


def get_latest_video_ids(browser_name='firefox', max_videos=3):
    ydl_opts = {
        'cookiesfrombrowser': (browser_name, None, None, None),
        'extract_flat': True,
        'dump_single_json': True,
        'playlistend': max_videos
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info('https://www.youtube.com/feed/subscriptions', download=False)
        video_entries = result.get('entries', [])
        videos = [{'id': video['id'], 'thumbnails': video['thumbnails'][0]} for video in video_entries if
                  'id' in video and 'thumbnails' in video]
        return videos


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
    completion = openai_client.chat.completions.create(
        model="3thn/dolphin-2.9-llama3-8b-GGUF",
        messages=[
            {"role": "system",
             "content": "You are an intelligent assistant. You always provide well-reasoned answers that are both correct and helpful."},
            {"role": "user",
             "content": "Create a brief overview (using bullet points) of the topics discussed in the following video transcript: \n\nSTART OF TRANSCRIPT\"" + transcript[
                                                                                                                                                               :8000] + "\" END OF TRANSCRIPT"},
        ],
        temperature=0.7,
        stream=True,
    )

    summary = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            summary += chunk.choices[0].delta.content
    return summary


def get_summaries(videos):
    video_ids = [video['id'] for video in videos]
    transcripts = get_transcripts(video_ids)
    summaries = {}
    for video_id, transcript in transcripts.items():
        print(f"Generating Summary for Video ID {video_id}:\n")
        if transcript:
            full_transcript = ' '.join([entry['text'] for entry in transcript])
            summaries[video_id] = send_to_lmstudio(full_transcript)
        else:
            summaries[video_id] = "No transcript available"
    return summaries


@app.route('/')
def index():
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Summaries</title>
    </head>
    <body>
        <h1>YouTube Summaries</h1>
        <ul>
            {% for video in videos %}
                <li>
                    <img src="{{ video.thumbnail }}" alt="Thumbnail">
                    <p>{{ video.summary }}</p>
                </li>
            {% endfor %}
        </ul>
    </body>
    </html>
    """

    return render_template_string(html_template, videos=videos)


videos = []

if __name__ == '__main__':
    videos = get_latest_video_ids()
    summaries = get_summaries(videos)
    for video in videos:
        video['summary'] = summaries.get(video['id'], "No summary available")

    app.run(debug=True)
