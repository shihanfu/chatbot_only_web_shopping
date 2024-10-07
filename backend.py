import json

import boto3
import openai
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
client = openai.OpenAI()


def chat(messages, model="gpt-4o", **kwargs):
    print(messages)
    for message in messages:
        del message["id"]
        new_contents = []
        for content in message["content"]:
            if content["type"] == "image":
                new_content = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{content['source']['media_type']};base64,"
                        + content["source"]["data"]
                    },
                }
                new_contents.append(new_content)
            else:
                new_contents.append(content)
        message["content"] = new_contents
    print(messages)
    try:
        return (
            client.chat.completions.create(model=model, messages=messages, **kwargs)
            .choices[0]
            .message.content
        )
    except Exception as e:
        print(messages)
        print(e)
        raise e


def chat_bedrock(
    messages: list[dict[str, str]],
    model="anthropic.claude-3-5-sonnet-20240620-v1:0",
    **kwargs,
) -> str:
    client = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")
    system_message = messages[0]["content"]
    messages = messages[1:]
    for m in messages:
        del m["id"]
    response = client.invoke_model(
        modelId=model,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 5000,
                "system": system_message,
                "messages": messages,
            }
        ),
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


@app.route("/api/openai", methods=["POST"])
def proxy():
    messages = request.json.get("messages")
    response = chat(messages)
    return jsonify({"message": response}), 200


@app.route("/api/bedrock", methods=["POST"])
def proxy_bedrock():
    messages = request.json.get("messages")
    response = chat_bedrock(messages)
    return jsonify({"message": response}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5001)
