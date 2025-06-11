from openai import OpenAI
import base64

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISetting(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='ai_', env_file='.env',  extra='ignore')
    base_url: str = Field(default="https://api.studio.nebius.ai/v1/")
    model: str = Field(default="Qwen/Qwen2-VL-72B-Instruct")
    api_key: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env',  extra='ignore')

    project_name: str = Field(default="computer_vision")
    ai: AISetting = AISetting()
    image_path: str


settings = Settings()


def get_product_list(image_path: str) -> str:
    client = OpenAI(
        base_url=settings.ai.base_url,
        api_key=settings.ai.api_key,
    )
    model = settings.ai.model

    FoodRecognitionPrompt = """
        Analyze the provided image, which shows various packaged products.
        Identify each distinct product and count how many units of each are visible.
        Respond ONLY with a JSON array of objects in the following format:
        [{"product": <product_name>, "quantity": <integer count>, }]
        Strictly follow the format.
        Do not include any extra text, comments, or formatting—only output valid JSON.
    """

    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", "text": FoodRecognitionPrompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]

                }
            ],
            temperature=0.6
        )
        message = completion.choices[0].message
    except Exception as err:
        print('AI API returned error %s', err)
        raise err
    return message.content


product_list = get_product_list(settings.image_path)
print(product_list)
