"""Read chat messages from stdin and generate a local MLX outline."""
import json
import sys

from mlx_lm import generate, load


def main():
    messages = json.load(sys.stdin)
    model, tokenizer = load(sys.argv[1])
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    print(generate(model, tokenizer, prompt=prompt, max_tokens=1200, verbose=False))


if __name__ == '__main__':
    main()
