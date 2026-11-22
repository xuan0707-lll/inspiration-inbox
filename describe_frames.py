"""Describe ordered video frames using a locally cached MLX vision model."""
import json
import sys

from mlx_vlm import generate, load
from mlx_vlm.prompt_utils import apply_chat_template


def main():
    prompt = sys.stdin.read()
    model, processor = load(sys.argv[1])
    images = sys.argv[2:]
    formatted = apply_chat_template(processor, model.config, prompt, num_images=len(images))
    answer = generate(model, processor, formatted, images,
                      temperature=0.0, max_tokens=650, verbose=False)
    if answer.finish_reason == 'length':
        raise ValueError('画面描述未在生成上限内结束。')
    print(json.dumps(answer.text, ensure_ascii=False))


if __name__ == '__main__':
    main()
